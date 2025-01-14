from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import InputFile, FSInputFile
import app.keyboards.shared as sharedkb
import app.keyboards.admin as adminkb
import app.keyboards.seller as sellerkb
from aiogram import Bot, Dispatcher
from access_middleware import role_required
from config import ADMIN_PASSWORD

# from app.database.manager import DatabaseManager
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import user_requests as rq

shared_router = Router()
role_router = Router()

class CreateFirstAdmin(StatesGroup):
    waiting_for_password = State()

# Обработчик команды /start
@shared_router.message(CommandStart())
async def cmd_start(message: Message, user_role, state: FSMContext, **kwargs):
    # Если в БД нет ни одного админа, предлагаем создать администратора
    if user_role == "first":
        await message.answer("Поздравляем! Вы можете стать первым администратором бота, если пришлете верный пароль!",
                             reply_markup=sharedkb.cancel_action)
        await state.set_state(CreateFirstAdmin.waiting_for_password)
    elif user_role == "admin":
        await message.answer(f"{message.from_user.first_name}, добро пожаловать!\n"
                                "Ваша роль - администратор.",
                                reply_markup=sharedkb.reply_menu)
    elif user_role == "seller":
        await message.answer(f"{message.from_user.first_name}, добро пожаловать!\n"
                                "Ваша роль - продавец.",
                                reply_markup=sharedkb.reply_menu)
    elif user_role == None:
        await message.answer(f"{message.from_user.first_name}, добро пожаловать!\n"
                                f"Нажмите на ваш id чтобы скопировать: <code>{message.from_user.id}</code>.\n"
                                "<b>Сообщите его администратору для назначения вам роли</b>",
                                reply_markup=sharedkb.unknown_user)
    elif user_role == "deleted":
        await message.answer("📢 Вам заблокирован доступ к боту. "
                             "Если это произошло по ошибке, свяжитесь с администратором. "
                             f"Вот ваш Telegram ID, нажмите на него чтобы скопировать: <code>{message.from_user.id}</code>, "
                             "он понадобится для восстановления доступа к боту.",
                             reply_markup=sharedkb.unknown_user)

# Создание первого админа
@role_router.message(CreateFirstAdmin.waiting_for_password)
@role_required(["first"])
async def create_first_admin(message: Message, state: FSMContext, user_session: AsyncSession, dispatcher: Dispatcher, bot: Bot, **kwargs):
    
    if message.text == ADMIN_PASSWORD:
        await rq.create_first_admin(user_session, message.from_user.id)

        users_with_first_role = await rq.get_all_users_by_role(user_session, "first")
        for user in users_with_first_role:
            state_with: FSMContext = FSMContext(storage=dispatcher.storage,
                                                key=StorageKey(bot_id=bot.id,
                                                               chat_id=user.tg_id,
                                                               user_id=user.tg_id))
            await bot.send_message(user.tg_id,
                                   "📢 Процесс создания администратора отменен. "
                                   "Один из пользователей уже стал администратором.")
            await bot.send_message(user.tg_id,
                                   f"{user.first_name}, добро пожаловать!\n"
                                   f"Нажмите на ваш id чтобы скопировать: <code>{user.tg_id}</code>.\n"
                                   "<b>Сообщите его администратору для назначения вам роли</b>",
                                   reply_markup=sharedkb.unknown_user)
            await state_with.clear()

        await rq.change_all_users_role(user_session, "first")

        await message.answer("📢 Вы стали первым администратором!",
                            reply_markup=sharedkb.reply_menu)
        await state.clear()
    else:
        await message.answer("⚠️ Неверный пароль",
                             reply_markup=sharedkb.cancel_action)
        
@role_router.message(F.text.lower() == "🛒 продать")
@role_required(['admin', 'seller'])
async def reply_sell_choice(message: Message, **kwargs):
    await message.reply("Выберите опцию", reply_markup=sharedkb.sell_choice)

@role_router.message(F.text.lower() == "📋 меню")
@role_required(['admin', 'seller'])
async def reply_menu(message: Message, user_role, **kwargs):
    if user_role == "admin":
        await message.reply("Выберите опцию", reply_markup=adminkb.head)
    elif user_role == "seller":
        await message.reply("Выберите опцию", reply_markup=sellerkb.shop_management)

@role_router.message(F.text.lower() == "❓ помощь")
@role_required(['admin', 'seller'])
async def reply_help(message: Message, **kwargs):
    pass

## Уровень кнопок - sell_choice
### Возврат на уровень - shop_management
@role_router.callback_query(F.data == "sell_choice_back")
@role_required(["admin", "seller"])
async def sell_choice_back(callback: CallbackQuery, user_role, **kwargs):
    await callback.answer()
    if user_role == "admin":
        await callback.message.edit_reply_markup(reply_markup=adminkb.shop_management)
    else:
        await callback.message.edit_reply_markup(reply_markup=sellerkb.shop_management)

# Список Админов
@role_router.callback_query(F.data == "admins_list")
@role_required(['deleted', 'seller', None, 'admin'])
async def admins_list(callback: CallbackQuery, user_session: AsyncSession, **kwargs):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=await sharedkb.inline_admins(user_session))

@role_router.callback_query(F.data == "cancel_action")
@role_required(['seller', 'admin', "first"])
async def cancel_action(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer("📢 Действие отменено.")
    await state.clear()