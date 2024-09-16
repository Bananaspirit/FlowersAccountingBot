from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

main = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Приход цветка")],
    [KeyboardButton(text="Продажа"), KeyboardButton(text="Утиль")],
    [KeyboardButton(text="Добавить позицию")]
],
                            resize_keyboard=True,
                            input_field_placeholder="Выберите пункт из меню")

settings = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="ютуб", url="https://www.youtube.com")]
])

cars = ["Audi", "Shkoda", "Reno", "Lada"]

async def reply_cars():
    keyboard = ReplyKeyboardBuilder()
    for car in cars:
        keyboard.add(KeyboardButton(text=car))
    return keyboard.adjust(2).as_markup()