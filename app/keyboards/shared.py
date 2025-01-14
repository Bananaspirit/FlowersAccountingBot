from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from app.database import user_requests as rq

reply_menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="🛒 Продать")],
    [KeyboardButton(text="📋 Меню")],
    [KeyboardButton(text="❓ Помощь")]],
    resize_keyboard=False)

sell_choice = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Товар поштучно", callback_data="sell_by_piece")],
    [InlineKeyboardButton(text="Товар по акции", callback_data="sell_by_promotion")],
    [InlineKeyboardButton(text="Композиция", callback_data="sell_composition")],
    [InlineKeyboardButton(text="◀️ Назад", callback_data="sell_choice_back")]])

unknown_user = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Получить список администраторов", callback_data="admins_list")]])

cancel_action = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="❌ Отменить действие", callback_data="cancel_action")]])

add_product_question = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Да", callback_data="add_product_yes")],
    [InlineKeyboardButton(text="Нет", callback_data="add_product_no")]])

sell_product_question = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Да", callback_data="sell_product_yes")],
    [InlineKeyboardButton(text="Нет", callback_data="sell_product_no")]])

change_price_question = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Да", callback_data="change_price_yes")],
    [InlineKeyboardButton(text="Нет", callback_data="change_price_no")]])

print_invoice_month = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="За текущий", callback_data="print_current_invoice")],
    [InlineKeyboardButton(text="За другой", callback_data="print_previous_invoice")]])

print_invoice_question = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Да", callback_data="print_invoice_yes")],
        [InlineKeyboardButton(text="Нет", callback_data="print_invoice_no")]
    ]
)

add_invoice_choice = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Добавить к существующей", callback_data="add_to_existing_invoice")],
        [InlineKeyboardButton(text="Создать новую", callback_data="create_new_invoice")],
        [InlineKeyboardButton(text="❌ Отменить действие", callback_data="cancel_action")]
    ]
)

async def inline_admins(session):
    keyboard = InlineKeyboardBuilder()
    admins_list = await rq.get_list_of_admins(session)
    
    for tg_id, full_name in admins_list.items():
        keyboard.add(InlineKeyboardButton(text=full_name, url=f"tg://user?id={tg_id}"))

    return keyboard.adjust(2).as_markup()