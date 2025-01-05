from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from app.database import user_requests as rq

unknown_user = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Получить список администраторов", callback_data="admins_list")]])

async def inline_admins(session):
    keyboard = InlineKeyboardBuilder()
    admins_list = await rq.get_list_of_admins(session)
    
    for tg_id, name in admins_list.items():
        keyboard.add(InlineKeyboardButton(text=name, url=f"tg://openmessage?user_id={tg_id}"))

    return keyboard.adjust(2).as_markup()