from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from app.database.users_db import get_list_of_admins

admin_kb = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Добавить администратора"), KeyboardButton(text="Добавить пользователя")],
    [KeyboardButton(text="Удалить администратора"), KeyboardButton(text="Удалить пользователя")]],
    resize_keyboard=True,
    input_field_placeholder="Выберите пункт из меню")

unknown_user_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Получить список администраторов", callback_data="admins_list")]])

async def inline_admins():
    keyboard = InlineKeyboardBuilder()
    for user_id, name in get_list_of_admins('admin').items():
        keyboard.add(InlineKeyboardButton(text=name, url=f"tg://openmessage?user_id={user_id}"))
    return keyboard.adjust(2).as_markup()