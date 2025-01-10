from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

shop_management = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🛒 Продать", callback_data="sell_choice")],
    [InlineKeyboardButton(text="➕ Внести накладную", callback_data="add_invoice")],
    [InlineKeyboardButton(text="🗑️ Добавить утиль", callback_data="add_trash")]])