from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import InputFile, FSInputFile
import app.keyboards.admin as adminkb
import app.keyboards.shared as sharedkb
from aiogram import Bot
from access_middleware import role_required
# from app.database.handler import ensure_db_exists, process_invoice_data
from config import ADMIN_PASSWORD

from app.database import user_requests as urq
from app.database import data_requests as drq
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.manager import DatabaseManager

from datetime import datetime
import re

from . import utils as hu

invoice_router = Router()
other_expenses_router = Router()

# ==============================================================================================================
# ВНЕСЕНИЕ ПРИХОДА
# ==============================================================================================================

## Уровень кнопок - shop_management
class AddInvoice(StatesGroup):
    waiting_for_continue_inserting = State()

    waiting_for_invoice_number = State()
    waiting_for_invoice_date = State()
    waiting_for_delivery_cost = State()

    waiting_for_product_name = State()
    waiting_for_product_quantity = State()
    waiting_for_purchase_price = State()
    waiting_for_sale_price = State()
    waiting_for_promotion_price = State()

@invoice_router.callback_query(F.data == "add_invoice")
@role_required(["admin", 'seller'])
async def add_invoice(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer("> <b>Введите номер накладной</b>",
                                  reply_markup=sharedkb.cancel_action)
    await state.set_state(AddInvoice.waiting_for_invoice_number)

@invoice_router.message(AddInvoice.waiting_for_invoice_number)
@role_required(["admin", 'seller'])
async def add_invoice_state_invoice_number(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    
    if message.text.isdigit():
        await message.answer(f"Номер накладной: {message.text}\n\n"
                             "> <b>Отправьте дату из накладной</b>",
                             reply_markup=sharedkb.cancel_action)
        await state.update_data(invoice_number=int(message.text))
        await state.set_state(AddInvoice.waiting_for_invoice_date)
    else:
        await message.answer("⚠️ Отправьте одно натуральное число",
                             reply_markup=sharedkb.cancel_action)

@invoice_router.message(AddInvoice.waiting_for_invoice_date)
@role_required(["admin", 'seller'])
async def add_invoice_state_invoice_date(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    
    try:
        valid_date = datetime.strptime(message.text, "%d.%m.%Y").date()
        await message.answer(f"Дата накладной: {message.text}\n\n"
                             "> <b>Отправьте стоимость доставки.</b>\nЕсли стоимость доставки не указана, введите 0.",
                             reply_markup=sharedkb.cancel_action)
        await state.update_data(invoice_date = valid_date)
        await state.set_state(AddInvoice.waiting_for_delivery_cost)
    except ValueError:
        await message.answer('⚠️ Отправьте дату в формате "день.месяц.год" (10.05.2024)',
                             reply_markup=sharedkb.cancel_action)

@invoice_router.message(AddInvoice.waiting_for_delivery_cost)
@role_required(["admin", 'seller'])
async def add_invoice_state_delivery_cost(message: Message, state: FSMContext, **kwargs):
    
    cost_regex = r"^\d+(\.\d+)?$"
    if re.match(cost_regex, message.text):
        cost = float(message.text)
        await message.answer(f"Стоимость доставки: {cost}\n\n"
                             "> <b>Отправьте название товара</b>",
                             reply_markup=sharedkb.cancel_action)
        await state.update_data(delivery_cost=cost)
        await state.set_state(AddInvoice.waiting_for_product_name)
    else:
        await message.answer("⚠️ Отправьте одно натуральное или рациональное число",
                             reply_markup=sharedkb.cancel_action)

@invoice_router.message(AddInvoice.waiting_for_product_name)
@role_required(["admin", 'seller'])
async def add_invoice_state_product_name(message: Message, state: FSMContext, **kwargs):

    product_name_pegex = r"^[А-Яа-яA-Za-z0-9\s]+$"
    if re.match(product_name_pegex, message.text):
        await message.answer(f'Название товара: "{message.text}"\n\n'
                            "> <b>Отправьте количество товара</b>",
                            reply_markup=sharedkb.cancel_action)
        await state.update_data(product_name = message.text)
        await state.set_state(AddInvoice.waiting_for_product_quantity)
    else:
        await message.answer('⚠️ Отправьте название товара без спец. символов',
                             reply_markup=sharedkb.cancel_action)
        
@invoice_router.message(AddInvoice.waiting_for_product_quantity)
@role_required(["admin", 'seller'])
async def add_invoice_state_product_quantity(message: Message, state: FSMContext, **kwargs):
    
    if message.text.isdigit():
        await message.answer(f"Количество товара: {message.text}\n\n"
                             "> <b>Отправьте закупочную стоимость</b>",
                             reply_markup=sharedkb.cancel_action)
        await state.update_data(product_quantity = int(message.text))
        await state.set_state(AddInvoice.waiting_for_purchase_price)
    else:
        await message.answer("⚠️ Отправьте одно натуральное число",
                             reply_markup=sharedkb.cancel_action)

@invoice_router.message(AddInvoice.waiting_for_purchase_price)
@role_required(["admin", 'seller'])
async def add_invoice_state_purchase_price(message: Message, state: FSMContext, **kwargs):
    
    cost_regex = r"^\d+(\.\d+)?$"
    if re.match(cost_regex, message.text):
        cost = float(message.text)
        await message.answer(f"Закупочная стоимость товара: {cost}\n\n"
                             "> <b>Отправьте стандартную цену продажи</b>",
                             reply_markup=sharedkb.cancel_action)
        await state.update_data(purchase_price=cost)
        await state.set_state(AddInvoice.waiting_for_sale_price)
    else:
        await message.answer("⚠️ Отправьте одно натуральное или рациональное число",
                             reply_markup=sharedkb.cancel_action)

@invoice_router.message(AddInvoice.waiting_for_sale_price)
@role_required(["admin", 'seller'])
async def add_invoice_state_sale_price(message: Message, state: FSMContext, **kwargs):
    
    cost_regex = r"^\d+(\.\d+)?$"
    if re.match(cost_regex, message.text):
        cost = float(message.text)
        await message.answer(f"Стандартная цена продажи товара: {cost}\n\n"
                            "> <b>Отправьте акционную цену продажи или 0, если её нет</b>",
                            reply_markup=sharedkb.cancel_action)
        await state.update_data(sale_price=cost)
        await state.set_state(AddInvoice.waiting_for_promotion_price)
    else:
        await message.answer("⚠️ Отправьте одно натуральное или рациональное число",
                             reply_markup=sharedkb.cancel_action)

@invoice_router.message(AddInvoice.waiting_for_promotion_price)
@role_required(["admin", 'seller'])
async def add_invoice_state_promotion_price(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    
    cost_regex = r"^\d+(\.\d+)?$"
    if re.match(cost_regex, message.text):

        state_data = await state.get_data()
        invoice_number = state_data.get("invoice_number", "")
        invoice_date = state_data.get("invoice_date", "")
        delivery_cost = state_data.get("delivery_cost", "")
        product_name = state_data.get("product_name", "")
        product_quantity = state_data.get("product_quantity", "")
        purchase_price = state_data.get("purchase_price", "")
        sale_price = state_data.get("sale_price", "")
        promotion_price = float(message.text)

        # Добавляем товар к накладной
        await drq.insert_invoice(data_session, invoice_number, invoice_date, delivery_cost)
        # Добавляем товар
        product_id = await drq.insert_product(data_session, invoice_number, product_name, product_quantity, purchase_price)
        # Начинаем ведение статистики
        await drq.start_statistics(data_session, product_id, sale_price, product_quantity, promotion_price)
        await message.answer(f"📢 Информация о внесенном товаре:\n\n"
                             f"<b>Статус</b>: добавлено к накладной №{invoice_number}\n"
                             f"<b>Название</b>: {product_name}\n"
                             f"<b>Количество</b>: {product_quantity}\n"
                             f"<b>Закупочная стоимость</b>: {purchase_price}\n"
                             f"<b>Стандартная цена продажи</b>: {sale_price}\n"
                             f"<b>Акционная цена продажи</b>: {promotion_price}")
        
        msg = await message.answer("Хотите продолжить внесение товаров?", reply_markup=sharedkb.add_product_question)
        data = await state.get_data()
        message_ids = data.get("message_ids", [])
        message_ids.append(msg.message_id)
        await state.update_data(message_ids=message_ids)
        await state.set_state(AddInvoice.waiting_for_continue_inserting)
    else:
        await message.answer("⚠️ Отправьте одно натуральное или положительное рациональное число",
                             reply_markup=sharedkb.cancel_action)

@invoice_router.message(AddInvoice.waiting_for_continue_inserting)
@role_required(["admin", 'seller'])
async def add_invoice_state_continue_inserting(message: Message, state: FSMContext, **kwargs): 
    msg = await message.answer(
        "Хотите продолжить внесение товаров?",
        reply_markup=sharedkb.add_product_question
    )
    data = await state.get_data()
    message_ids = data.get("message_ids", [])
    message_ids.append(msg.message_id)
    await state.update_data(message_ids=message_ids)

@invoice_router.callback_query(F.data == "add_product_yes")
@role_required(["admin", 'seller'])
async def add_product_yes(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer("")
    await callback.message.answer("> <b>Отправьте название товара.</b>",
                                  reply_markup=sharedkb.cancel_action)
    await state.set_state(AddInvoice.waiting_for_product_name)

@invoice_router.callback_query(F.data == "add_product_no")
@role_required(["admin", 'seller'])
async def add_product_no(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer("")

    state_data = await state.get_data()
    message_ids = state_data.get("message_ids", [])

    for msg_id in message_ids:
        await callback.bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=msg_id,
            reply_markup=None
        )
    await state.clear()
    await callback.message.answer("📢 Внесение накладной завершено.")

# ==============================================================================================================
# ДОБАВЛЕНИЕ ДРУГИХ ТРАТ
# ==============================================================================================================

class AddExpense(StatesGroup):
    waiting_for_expense_id = State()
    waiting_for_expense_name = State()
    waiting_for_expense_spent = State()
    waiting_for_continue_inserting = State()

@other_expenses_router.callback_query(F.data == "add_other_expenses")
@role_required(["admin"])
async def add_other_expenses(callback: CallbackQuery, state: FSMContext, data_session: AsyncSession, **kwargs):
    await callback.answer()
    # проверяем есть ли хотя бы одна запись с тратой
    expenses = await drq.get_expenses_data(data_session)
    if expenses:
        expenses_ids = list()
        expenses_list = list()
        for expense in expenses:
            expenses_ids.append(expense.id)
            expenses_list.append(f'{expense.id}. Название: "{expense.name}"; Потрачено: {expense.spent}')
        expenses_list = "\n".join(expenses_list)
        await callback.message.answer("Список существующих трат:\n"
                                      f"{expenses_list}\n\n",
                                      reply_markup=adminkb.add_expense_choice)
        await state.update_data(expenses_ids=expenses_ids)
    else:
        await callback.message.answer('> <b>Отправьте название траты</b>\n<i>Например: "Налоги" или "ЗП продавцу"</i>')
        await state.set_state(AddExpense.waiting_for_expense_name)

@other_expenses_router.callback_query(F.data == "add_to_existing_expense")
@role_required(["admin"])
async def add_to_existing_expense(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer('> <b>Отправьте идентификатор траты</b>')
    await state.set_state(AddExpense.waiting_for_expense_id)

@other_expenses_router.callback_query(F.data == "create_new_expense")
@role_required(["admin"])
async def create_new_expense(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer('> <b>Отправьте название траты</b>\n<i>Например: "Налоги" или "ЗП продавцу"</i>')
    await state.set_state(AddExpense.waiting_for_expense_name)

@other_expenses_router.message(AddExpense.waiting_for_expense_id)
@role_required(["admin"])
async def add_to_expense_state_id(message: Message, state: FSMContext, **kwargs):
    state_data = await state.get_data()
    expenses_ids = state_data.get("expenses_ids", [])

    if message.text.isdigit():
        if int(message.text) in expenses_ids:
            await message.answer(f"Идентификатор: {message.text}\n\n"
                                 "> <b>Отправьте стоимость траты</b>")
            await state.update_data(expense_id=int(message.text))
            await state.set_state(AddExpense.waiting_for_expense_spent)
        else:
            await message.answer("⚠️ Отправьте идентификатор из предложенного списка",
                             reply_markup=sharedkb.cancel_action)
    else:
        await message.answer("⚠️ Отправьте одно натуральное число",
                             reply_markup=sharedkb.cancel_action)

@other_expenses_router.message(AddExpense.waiting_for_expense_name)
@role_required(["admin"])
async def add_to_expense_state_name(message: Message, state: FSMContext, **kwargs):
    
    product_name_pegex = r"^[А-Яа-яA-Za-z0-9\s]+$"
    if re.match(product_name_pegex, message.text):
        await message.answer(f'Название траты: "{message.text}"\n\n'
                            "> <b>Отправьте стоимость траты</b>")
        await state.update_data(expense_name = message.text)
        await state.set_state(AddExpense.waiting_for_expense_spent)
    else:
        await message.answer('⚠️ Отправьте название товара без спец. символов',
                             reply_markup=sharedkb.cancel_action)

@other_expenses_router.message(AddExpense.waiting_for_expense_spent)
@role_required(["admin"])
async def add_to_expense_state_spent(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    state_data = await state.get_data()
    # для создания траты
    expense_name = state_data.get("expense_name", None)
    # для обновления траты
    expense_id = state_data.get("expense_id", None)

    cost_regex = r"^\d+(\.\d+)?$"
    if re.match(cost_regex, message.text):
        spent = float(message.text)
        # возврат информационный
        expense_id, expense_name, spent = await drq.add_other_expense(data_session, expense_id, expense_name, spent)
        await message.answer("📢 Информация о внесенной трате:\n\n"
                            f"<b>Идентификатор</b>: {expense_id}\n"
                            f"<b>Название</b>: {expense_name}\n"
                            f"<b>Потрачено</b>: {spent}")
        msg = await message.answer("Хотите продолжить внесение других трат?", reply_markup=adminkb.add_expense_question)
        data = await state.get_data()
        message_ids = data.get("message_ids", [])
        message_ids.append(msg.message_id)
        await state.update_data(message_ids=message_ids)
        await state.set_state(AddExpense.waiting_for_continue_inserting)
    else:
        await message.answer("⚠️ Отправьте одно натуральное или рациональное число",
                             reply_markup=sharedkb.cancel_action)
        
@other_expenses_router.message(AddExpense.waiting_for_continue_inserting)
@role_required(["admin"])
async def add_to_expense_state_continue_inserting(message: Message, state: FSMContext, **kwargs):
    msg = await message.answer(
        "Хотите продолжить внесение других трат?",
        reply_markup=adminkb.add_expense_question
    )
    data = await state.get_data()
    message_ids = data.get("message_ids", [])
    message_ids.append(msg.message_id)
    await state.update_data(message_ids=message_ids)

@other_expenses_router.callback_query(F.data == "add_expense_yes")
@role_required(["admin"])
async def add_expense_yes(callback: CallbackQuery, state: FSMContext, data_session: AsyncSession, **kwargs):
    await callback.answer("")
    expenses = await drq.get_expenses_data(data_session)
    if expenses:
        expenses_ids = list()
        expenses_list = list()
        for expense in expenses:
            expenses_ids.append(expense.id)
            expenses_list.append(f'{expense.id}. Название: "{expense.name}"; Потрачено: {expense.spent}')
        expenses_list = "\n".join(expenses_list)
        await callback.message.answer("Список существующих трат:\n"
                                      f"{expenses_list}\n\n",
                                      reply_markup=adminkb.add_expense_choice)
        await state.update_data(expenses_ids=expenses_ids, expense_name=None, expense_id=None)
    else:
        await callback.message.answer('> <b>Отправьте название траты.</b>\n<i>Например</i>: "Налоги" или "ЗП продавцу"')
        await state.set_state(AddExpense.waiting_for_expense_name)

@other_expenses_router.callback_query(F.data == "add_expense_no")
@role_required(["admin"])
async def add_expense_no(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer("")

    state_data = await state.get_data()
    message_ids = state_data.get("message_ids", [])

    for msg_id in message_ids:
        await callback.bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=msg_id,
            reply_markup=None
        )
    await state.clear()
    await callback.message.answer("📢 Внесение других трат завершено.")