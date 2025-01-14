from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

head = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🏪 Управление магазином", callback_data="manage_shop")],
    [InlineKeyboardButton(text="👥 Управление пользователями", callback_data="manage_users")],
    [InlineKeyboardButton(text="📊 Отчет за месяц", callback_data="monthly_report")]])

user_management = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="👑 Назначить администратора", callback_data="create_admin")],
    [InlineKeyboardButton(text="🛍️ Назначить продавца", callback_data="create_user")],
    [InlineKeyboardButton(text="❌ Удалить администратора", callback_data="delete_admin")],
    [InlineKeyboardButton(text="❌ Удалить продавца", callback_data="delete_user")],
    [InlineKeyboardButton(text="◀️ Назад", callback_data="user_management_back")]])

shop_management = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🛒 Продать", callback_data="sell_choice")],
    [InlineKeyboardButton(text="🧾 Внести накладную", callback_data="add_invoice")],
    [InlineKeyboardButton(text="📝 Изменить цену", callback_data="change_price")],
    [InlineKeyboardButton(text="🗑️ Добавить брак", callback_data="add_trash")],
    [InlineKeyboardButton(text="⚖️ Добавить другие траты", callback_data="add_other_expenses")],
    [InlineKeyboardButton(text="🧾 Вывести накладную", callback_data="print_invoice")],
    [InlineKeyboardButton(text="◀️ Назад", callback_data="shop_management_back")]])

change_price_choice = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Стандартная цена", callback_data="change_stnd_price")],
    [InlineKeyboardButton(text="Акционная цена", callback_data="change_promotion_price")],
    [InlineKeyboardButton(text="◀️ Назад", callback_data="change_price_choice_back")]])

add_expense_choice = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Добавить к существующей", callback_data="add_to_existing_expense")],
    [InlineKeyboardButton(text="Создать новую", callback_data="create_new_expense")],
    [InlineKeyboardButton(text="❌ Отменить действие", callback_data="cancel_action")]])

add_expense_question = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Да", callback_data="add_expense_yes")],
    [InlineKeyboardButton(text="Нет", callback_data="add_expense_no")]])