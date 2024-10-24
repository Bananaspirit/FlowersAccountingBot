from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from app.database.create_users_db import get_list_of_admins

unknown_user_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Получить список админов", callback_data="admins_list")]
])

# show_admins = InlineKeyboardMarkup(inline_keyboard=[
#     [InlineKeyboardButton(text='Админ1', url=f"tg://openmessage?user_id={get_list_of_admins('admin')[0]}")]
# ])

main = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Приход цветка")],
    [KeyboardButton(text="Продажа"), KeyboardButton(text="Утиль")],
    [KeyboardButton(text="Добавить позицию")]
],
                            resize_keyboard=True,
                            input_field_placeholder="Выберите пункт из меню")

async def inline_admins():
    keyboard = InlineKeyboardBuilder()
    count = 1
    for user_id in get_list_of_admins('admin'):
        name = f"Админ{count}"
        keyboard.add(InlineKeyboardButton(text=name, url=f"tg://openmessage?user_id={user_id}"))
    return keyboard.adjust(2).as_markup()