from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import InputFile, FSInputFile
import app.keyboards as kb
from app.database import users_db
from aiogram import Bot

from config import ADMIN_PASSWORD

router = Router()

# Create a finite state machine (FSM) for handling the password input
class CreateFirstAdmin(StatesGroup):
    waiting_for_password = State()

# Обработчик команды /start
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):

    # Если в БД нет ни одного пользователя, предлагаем создать администратора
    if users_db.get_user_role(message.from_user.id) == "first":
        await message.answer("Поздравляем! Вы можете стать первым администратором бота, если пришлете верный пароль!")
        await state.set_state(CreateFirstAdmin.waiting_for_password)
    elif users_db.get_user_role(message.from_user.id) == "admin":
        await message.answer(f"{message.from_user.first_name}, добро пожаловать!\n"
                                "Ваша роль - администратор.",
                                reply_markup=kb.admin_kb)
    elif users_db.get_user_role(message.from_user.id) == "user":
        await message.answer(f"{message.from_user.first_name}, добро пожаловать!\n"
                                "Ваша роль - пользователь.")
    elif users_db.get_user_role(message.from_user.id) == None:
        await message.answer(f"{message.from_user.first_name}, добро пожаловать!\n"
                                f"Нажмите на ваш id чтобы скопировать: <code>{message.from_user.id}</code>, "
                                "сообщите его администратору для назначения вам роли",
                                reply_markup=kb.unknown_user_kb)

# Создание первого админа
@router.message(CreateFirstAdmin.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс создания администратора отменен")
        return
    
    if message.text == ADMIN_PASSWORD:
        users_db.create_first_admin(message.from_user.id, message.from_user.full_name)
        await message.answer("Вы стали первым администратором!",
                             reply_markup=kb.admin_kb)
        await state.clear()
    else:
        await message.answer("Неверный пароль.\n"
                             "Попробуйте заново, или введите /cancel, чтобы отменить создание администратора")

# декоратор @router.message принимает различные фильтры, например определенную текстовую команду
@router.message(Command("help"))
async def get_help(message: Message):
    await message.answer("""Команда /help поможет вам разобраться в боте\n
                            Список основных команд:""")

# Пример обработчика для запроса и отправки файла
@router.message(Command("get_month_stat"))
async def get_month_stat(message: Message):
    await message.reply_document(FSInputFile("excel/updated_Flowers_file.xlsx"))

# магический фильтр позволяет обрабатывать конкретное текстовое сообщение
@router.message(F.text == "Владочка котеночек?")
async def vladochka(message: Message):
    await message.answer("Еще и солнышко)")

@router.message(Command("get_user_info"))
async def get_user_info(message: Message):
    await message.reply(f"Привет!\nТвой ID: {message.from_user.id}\nТвое имя: {message.from_user.full_name}")

# хэндлеры для обработки коллбэков
@router.callback_query(F.data == "admins_list")
async def admins_list(callback: CallbackQuery):
    await callback.answer("")
    await callback.message.answer("Выберите администратора", reply_markup=await kb.inline_admins())

# Создание пользователя
class CreateUser(StatesGroup):
    waiting_for_user_id = State()

@router.message(F.text == "Добавить пользователя")
async def create_user(message: Message, state: FSMContext):
    await message.reply("Для назначения пользователю телеграм роли необходим его ID, отправьте его мне.\n"
                        "Если вы не знаете Telegram ID пользователя, попросите его начать чат с ботом. "
                        "Бот отправит ID пользователя и уведомит его о необходимости передать ID администратору.")
    await state.set_state(CreateUser.waiting_for_user_id)

@router.message(CreateUser.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext, bot: Bot):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс назначения роли отменен.")
        return
    
    user_id = int(message.text) if message.text.isdigit() else await message.answer("id должен содержать только цифры")
    if users_db.user_exists(user_id):
        users_db.update_user_role(user_id, "user")
        await message.answer("Пользователю телеграм успешно назначена роль - пользователь")
        await bot.send_message(int(message.text), "Ваша роль обновлена! Теперь вы - пользователь.")
        await state.clear()
    else:
        await message.answer("Не вышло! Этот пользователь еще не начал чат с ботом, "
                             "попробуйте заново, или введите /cancel, чтобы отменить назначение роли.")
        
# Удаление пользователя
class DeleteUser(StatesGroup):
    waiting_for_user_id = State()

@router.message(F.text == "Удалить пользователя")
async def process_user_id(message: Message, state: FSMContext):
    users = users_db.get_all_users_by_role("user")
    if users:
        user_list = "\n".join([f"Имя: {name}, ID: <code>{user_id}</code>" for user_id, name in users])
        await message.answer(f"Список пользователей:\n{user_list}\n\nОтправьте ID пользователя для удаления.")
        await state.set_state(DeleteUser.waiting_for_user_id)
    else:
        await message.answer("Нет ни одного пользователя.")

@router.message(DeleteUser.waiting_for_user_id)
async def process_user_id(message: Message, state: FSMContext, bot: Bot):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс удаления пользователя отменен.")
        return
    
    user_id = int(message.text) if message.text.isdigit() else await message.answer("id должен содержать только цифры")
    if users_db.user_exists(user_id):
        users_db.delete_user(user_id, "deleted")
        await message.answer("Пользователь успешно удален! Для восстановления пользователя повторите процедуру назначения роли.")
        await bot.send_message(int(message.text),
                               "Вам заблокирован доступ к боту. "
                               "Если это произошло по ошибке, свяжитесь с администратором. "
                               f"Вот ваш Telegram ID, нажмите на него чтобы скопировать: <code>{user_id}</code>, "
                               "он понадобится для восстановления доступа к боту.",
                               reply_markup=kb.unknown_user_kb)
        await state.clear()
    else:
        await message.answer("Не вышло! Этот пользователь еще не начал чат с ботом, "
                             "попробуйте заново, или введите /cancel, чтобы отменить назначение роли.")
        
# Создание администратора
class CreateAdmin(StatesGroup):
    waiting_for_user_id = State()

@router.message(F.text == "Добавить администратора")
async def create_admin(message: Message, state: FSMContext):
    await message.reply("Для назначения пользователю телеграм роли необходим его ID, отправьте его мне.\n"
                        "Если вы не знаете Telegram ID пользователя, попросите его начать чат с ботом. "
                        "Бот отправит ID пользователя и уведомит его о необходимости передать ID администратору.")
    await state.set_state(CreateAdmin.waiting_for_user_id)

@router.message(CreateAdmin.waiting_for_user_id)
async def process_admin_id(message: Message, state: FSMContext, bot: Bot):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс назначения роли отменен.")
        return
    
    user_id = int(message.text) if message.text.isdigit() else await message.answer("id должен содержать только цифры")
    if users_db.user_exists(user_id):
        users_db.update_user_role(user_id, "admin")
        await message.answer("Пользователю телеграм успешно назначена роль - администратор!")
        await bot.send_message(int(message.text), "Ваша роль обновлена! Теперь вы - пользователь.")
        await state.clear()
    else:
        await message.answer("Не вышло! Этот пользователь еще не начал чат с ботом, "
                             "попробуйте заново, или введите /cancel, чтобы отменить назначение роли.")