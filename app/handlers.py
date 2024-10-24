from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import InputFile, FSInputFile
import app.keyboards as kb
from app.database.create_users_db import is_table_empty, create_admin, get_user_role, get_list_of_admins
from config import ADMIN_PASSWORD

router = Router()

# Create a finite state machine (FSM) for handling the password input
class CreateAdmin(StatesGroup):
    waiting_for_password = State()

# Handler for the /start command
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    if is_table_empty("users"):
        await message.answer("Поздравляем! Вы можете стать первым админом бота если пришлете верный пароль!")
        await state.set_state(CreateAdmin.waiting_for_password)
    else:
        if get_user_role(message.from_user.id) == "admin":
            await message.answer("Добро пожаловать! Вы уже админ")
        elif get_user_role(message.from_user.id) == "user":
            await message.answer("Добро пожаловать! Вы уже юзер")
        else:
            await message.answer(f"""Добро пожаловать! Нажмите на ваш id чтобы скопировать: <code>{message.from_user.id}</code>, 
                                 сообщите его админу для назначения вам роли""",
                                 reply_markup=kb.unknown_user_kb)
    
# State handler for the password input
@router.message(CreateAdmin.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс создания админа отменен")
        return
    
    if message.text == ADMIN_PASSWORD:
        create_admin(message.from_user.id)
        await message.answer("Теперь вы Админ!")
        await state.clear()
    else:
        await message.answer("Неверный пароль. Попробуйте заново, или введите /cancel, чтобы отменить создание админа")

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
    await callback.message.answer("Выберите админа", reply_markup=await kb.inline_admins())

# Echo handler
# @router.message(F.text)
# async def echo(message: Message):
#     await message.answer(f"Вы сказали: {message.text}")

# Command handler for /menu
# @router.message(Command("menu"))
# async def inline_menu(message: Message):
#     keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Click me!", callback_data="button_clicked")]])
#     await message.answer("Choose an option:", reply_markup=keyboard)

# Handling button press
# @router.callback_query(F.data == "button_clicked")
# async def handle_callback(callback_query: types.CallbackQuery):
#     await callback_query.message.answer("Button was clicked!")
#     await callback_query.answer()  # To stop Telegram from showing "loading..."