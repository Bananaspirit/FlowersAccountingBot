from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import InputFile, FSInputFile
import app.keyboards.main as mainkb
import app.keyboards.admin as adminkb
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
        await message.answer("Поздравляем! Вы можете стать первым администратором бота, если пришлете верный пароль!")
        await state.set_state(CreateFirstAdmin.waiting_for_password)
    elif user_role == "admin":
        await message.answer(f"{message.from_user.first_name}, добро пожаловать!\n"
                                "Ваша роль - администратор.",
                                reply_markup=adminkb.head)
    elif user_role == "seller":
        await message.answer(f"{message.from_user.first_name}, добро пожаловать!\n"
                                "Ваша роль - продавец.")
    elif user_role == None:
        await message.answer(f"{message.from_user.first_name}, добро пожаловать!\n"
                                f"Нажмите на ваш id чтобы скопировать: <code>{message.from_user.id}</code>, "
                                "сообщите его администратору для назначения вам роли",
                                reply_markup=mainkb.unknown_user)
    elif user_role == "deleted":
        await message.answer("Вам заблокирован доступ к боту. "
                             "Если это произошло по ошибке, свяжитесь с администратором. "
                             f"Вот ваш Telegram ID, нажмите на него чтобы скопировать: <code>{message.from_user.id}</code>, "
                             "он понадобится для восстановления доступа к боту.",
                             reply_markup=mainkb.unknown_user)

# Создание первого админа
@role_router.message(CreateFirstAdmin.waiting_for_password)
@role_required(["first"])
async def create_first_admin(message: Message, state: FSMContext, user_session: AsyncSession, dispatcher: Dispatcher, bot: Bot, **kwargs):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс создания администратора отменен.")
        return
    
    if message.text == ADMIN_PASSWORD:
        await rq.create_first_admin(user_session, message.from_user.id)

        users_with_first_role = await rq.get_all_users_by_role(user_session, "first")
        for user in users_with_first_role:
            state_with: FSMContext = FSMContext(storage=dispatcher.storage,
                                                key=StorageKey(bot_id=bot.id,
                                                               chat_id=user.tg_id,
                                                               user_id=user.tg_id))
            await bot.send_message(user.tg_id, "Процесс создания администратора отменен. "
                                               "Один из пользователей уже стал администратором.")
            await state_with.clear()

        await rq.change_all_users_role(user_session, "first")

        await message.answer("Вы стали первым администратором!",
                            reply_markup=adminkb.head)
        await state.clear()
    else:
        await message.answer("Неверный пароль.\n"
                            "Попробуйте заново, или введите /cancel, чтобы отменить создание администратора")

# Список Админов
@role_router.callback_query(F.data == "admins_list")
@role_required(['deleted', 'seller', None, 'admin'])
async def admins_list(callback: CallbackQuery, user_session: AsyncSession, **kwargs):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=await mainkb.inline_admins(user_session))