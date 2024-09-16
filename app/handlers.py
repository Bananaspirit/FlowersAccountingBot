from aiogram import F, Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import app.keyboards as kb

router = Router()

# Handler for the /start command
@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("Привет! Я ваше персональное телеграм-приложение для бухгалтерского учета.",
                         reply_markup=await kb.reply_cars())

# декоратор @router.message принимает различные фильтры, например определенную текстовую команду
@router.message(Command("help"))
async def get_help(message: Message):
    await message.answer("Команда /help поможет вам разобраться в боте")

# магический фильтр позволяет обрабатывать конкретное текстовое сообщение
@router.message(F.text == "Владочка котеночек?")
async def vladochka(message: Message):
    await message.answer("Еще и солнышко)")

@router.message(Command("get_user_info"))
async def get_user_info(message: Message):
    await message.reply(f"Привет!\nТвой ID: {message.from_user.id}\nТвое имя: {message.from_user.full_name}")

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