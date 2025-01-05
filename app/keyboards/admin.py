from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# admin_lvl1 = ReplyKeyboardMarkup(keyboard=[
#     [KeyboardButton(text="Управление пользователями"), KeyboardButton(text="Управление магазином")],
#     [KeyboardButton(text="Отчеты")]],
#     resize_keyboard=True,
#     input_field_placeholder="Выберите пункт из меню")

# admin_lvl2 = ReplyKeyboardMarkup(keyboard=[
#     [KeyboardButton(text="Назначить администратора"), KeyboardButton(text="Назначить продавца")],
#     [KeyboardButton(text="Удалить администратора"), KeyboardButton(text="Удалить продавца")],
#     [KeyboardButton(text="Назад")]],
#     resize_keyboard=True,
#     input_field_placeholder="Выберите пункт из меню")

head = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Управление пользователями", callback_data="manage_users")],
    [InlineKeyboardButton(text="Управление магазином", callback_data="manage_shop")],
    [InlineKeyboardButton(text="Отчеты", callback_data="report")]])

user_management = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Назначить администратора", callback_data="create_admin")],
    [InlineKeyboardButton(text="Назначить продавца", callback_data="create_user")],
    [InlineKeyboardButton(text="Удалить администратора", callback_data="delete_admin")],
    [InlineKeyboardButton(text="Удалить продавца", callback_data="delete_user")],
    [InlineKeyboardButton(text="Назад", callback_data="admin_back")]])

shop_management = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Продать", callback_data="sell_choice")],
    [InlineKeyboardButton(text="Внести накладную", callback_data="add_invoice")],
    [InlineKeyboardButton(text="Изменить цену", callback_data="change_price")],
    [InlineKeyboardButton(text="Добавить утиль", callback_data="add_trash")]])

sell_choice = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Товар поштучно", callback_data="sell_by_piece")],
    [InlineKeyboardButton(text="Товар по акции", callback_data="sell_by_promotion")],
    [InlineKeyboardButton(text="Композиция", callback_data="sell_composition")]])

change_price_choice = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Стандартная цена", callback_data="change_stnd_price")],
    [InlineKeyboardButton(text="Акционная цена", callback_data="change_promotion_price")]])