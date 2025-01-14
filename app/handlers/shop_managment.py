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

shop_managment_router = Router()

# ==============================================================================================================
# ДОБАВЛЕНИЕ НАКЛАДНОЙ
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

@shop_managment_router.callback_query(F.data == "add_invoice")
@role_required(["admin", 'seller'])
async def add_invoice(callback: CallbackQuery, state: FSMContext, data_session: AsyncSession, **kwargs):
    await callback.answer()
    invoices = await drq.get_invoices(data_session)
    if invoices:
        invoices_list = "\n".join(
            [f"№ <b>{number}</b>. от <i>{date[0].strftime('%d.%m.%Y')}</i>" for number, date in invoices.items()]
        )
        await callback.message.answer(
            f"Список накладных за текущий месяц:\n\n{invoices_list}",
            reply_markup=sharedkb.add_invoice_choice
        )
        await state.update_data(existing_invoices=invoices)
    else:
        await callback.message.answer("> <b>Введите номер накладной</b>",
                                      reply_markup=sharedkb.cancel_action)
        await state.set_state(AddInvoice.waiting_for_invoice_number)

@shop_managment_router.callback_query(F.data == "add_to_existing_invoice")
@role_required(["admin", 'seller'])
async def add_to_existing_invoice(callback: CallbackQuery, state: FSMContext, data_session: AsyncSession, **kwargs):
    await callback.answer()

@shop_managment_router.callback_query(F.data == "create_new_invoice")
@role_required(["admin", 'seller'])
async def create_new_invoice(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer("> <b>Введите номер накладной</b>",
                                      reply_markup=sharedkb.cancel_action)
    await state.set_state(AddInvoice.waiting_for_invoice_number)

@shop_managment_router.message(AddInvoice.waiting_for_invoice_number)
@role_required(["admin", 'seller'])
async def add_invoice_state_invoice_number(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    
    if message.text.isdigit():
        await message.answer(f"Номер накладной: №{message.text}\n\n"
                             "> <b>Отправьте дату из накладной</b>",
                             reply_markup=sharedkb.cancel_action)
        await state.update_data(invoice_number=int(message.text))
        await state.set_state(AddInvoice.waiting_for_invoice_date)
    else:
        await message.answer("⚠️ Отправьте одно натуральное число",
                             reply_markup=sharedkb.cancel_action)

@shop_managment_router.message(AddInvoice.waiting_for_invoice_date)
@role_required(["admin", 'seller'])
async def add_invoice_state_invoice_date(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    
    try:
        sanitized_date = message.text.replace(" ", "")

        valid_date = datetime.strptime(sanitized_date, "%d.%m.%Y").date()

        await message.answer(
            f"Дата накладной: {sanitized_date}\n\n"
            "> <b>Отправьте стоимость доставки.</b>\nЕсли стоимость доставки не указана, введите 0.",
            reply_markup=sharedkb.cancel_action
        )
        await state.update_data(invoice_date = valid_date)
        await state.set_state(AddInvoice.waiting_for_delivery_cost)
    except ValueError:
        await message.answer(
            '⚠️ Отправьте дату в формате "день.месяц.год" (10.05.2024)',
            reply_markup=sharedkb.cancel_action
        )

@shop_managment_router.message(AddInvoice.waiting_for_delivery_cost)
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

@shop_managment_router.message(AddInvoice.waiting_for_product_name)
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
        
@shop_managment_router.message(AddInvoice.waiting_for_product_quantity)
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

@shop_managment_router.message(AddInvoice.waiting_for_purchase_price)
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

@shop_managment_router.message(AddInvoice.waiting_for_sale_price)
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

@shop_managment_router.message(AddInvoice.waiting_for_promotion_price)
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

@shop_managment_router.message(AddInvoice.waiting_for_continue_inserting)
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

@shop_managment_router.callback_query(F.data == "add_product_yes")
@role_required(["admin", 'seller'])
async def add_product_yes(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer("")
    await callback.message.answer("> <b>Отправьте название товара.</b>",
                                  reply_markup=sharedkb.cancel_action)
    await state.set_state(AddInvoice.waiting_for_product_name)

@shop_managment_router.callback_query(F.data == "add_product_no")
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
# ВЫВОД НАКЛАДНОЙ -> отрефакторить
# ==============================================================================================================

class PrintInvoice(StatesGroup):
    waiting_for_invoice_number = State()
    waiting_for_invoice_date = State()
    waiting_for_previous_invoice_date = State()
    waiting_for_continue_inserting = State()

@shop_managment_router.callback_query(F.data == "print_invoice")
@role_required(["admin"])
async def print_invoice(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer("")
    await callback.message.answer("Выберите за какой месяц вы хотите получить данные из накладной",
                                  reply_markup=sharedkb.print_invoice_month)

@shop_managment_router.callback_query(F.data == "print_current_invoice")
@role_required(["admin"])
async def print_current_invoice(callback: CallbackQuery, state: FSMContext, data_session: AsyncSession, **kwargs):
    await callback.answer("")
    invoices = await drq.get_invoices(data_session)
    if invoices:
        invoices_list = "\n".join(
            [f"№ <b>{number}</b>. от <i>{date[0].strftime('%d.%m.%Y')}</i>" for number, date in invoices.items()]
        )
        await callback.message.answer(
            f"Список накладных за текущий месяц:\n\n{invoices_list}\n\n"
            "> <b>Отправьте № накладной</b>",
            reply_markup=sharedkb.cancel_action
        )
        await state.update_data(invoices=invoices)
        await state.set_state(PrintInvoice.waiting_for_invoice_number)
    else:
        await callback.message.answer(
            "⚠️ Сначала добавьте хотя бы одну накладную",
            reply_markup=sharedkb.cancel_action
        )

@shop_managment_router.callback_query(F.data == "print_previous_invoice")
@role_required(["admin"])
async def print_previous_invoice(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer("")
    await callback.message.answer(
        "> <b>Отправьте дату в формате мм.гггг</b>",
        reply_markup=sharedkb.cancel_action
    )
    await state.set_state(PrintInvoice.waiting_for_previous_invoice_date)

@shop_managment_router.message(PrintInvoice.waiting_for_invoice_number)
@role_required(["admin"])
async def print_invoice_state_number(
    message: Message,
    state: FSMContext,
    data_session: AsyncSession,
    db_manager: DatabaseManager,
    **kwargs
):
    state_data = await state.get_data()
    invoices = state_data.get("invoices", {})
    previous_invoice_raw_date = state_data.get("previous_invoice_raw_date", None)
    previous_invoice_date = state_data.get("previous_invoice_date", None)

    if message.text.isdigit():
        number = int(message.text)
        dates = invoices[number]
        if number in invoices:
            if len(dates) > 1:
                await message.answer(
                    f"<b>Номер накладной</b>: № {number}\n\n"
                    "> <b>Отправьте дату для этого номера</b>",
                    reply_markup=sharedkb.cancel_action
                )
                await state.update_data(invoice_number=number)
                await state.set_state(PrintInvoice.waiting_for_invoice_date)
            else:
                if previous_invoice_date is not None:
                    target_data_db_path = db_manager.get_data_db_path(date=previous_invoice_date, mkdir=False)
                    if db_manager.database_exists(target_data_db_path):
                        target_engine = db_manager.create_data_engine(target_data_db_path)
                        async with target_engine.connect() as target_conn:
                            products = await drq.get_products_by_invoice(
                                target_conn,
                                number,
                                dates[0]
                            )
                else:
                    products = await drq.get_products_by_invoice(data_session, number, dates[0])

                products_list = list()
                for id, product in enumerate(products, start=1):
                    name, quantity, purchase_price = product
                    products_list.append(
                        f"№ <b>{id}</b>. <i>{name}</i>: {quantity} шт. по {purchase_price} руб."
                    )
                products_list = "\n".join(products_list)

                await message.answer(
                    f"<b>Список товаров для накладной</b>:\n№ <b>{number}</b>. от <i>{dates[0].strftime('%d.%m.%Y')}</i>\n\n"
                    f"{products_list}"
                )

                if previous_invoice_raw_date is not None:
                    date = f"<i>{previous_invoice_raw_date}</i>"
                else:
                    date = "текущий месяц"
                msg = await message.answer(
                    f"Хотите продолжить вывод накладных за {date}?",
                    reply_markup=sharedkb.print_invoice_question
                )
                data = await state.get_data()
                message_ids = data.get("message_ids", [])
                message_ids.append(msg.message_id)
                await state.update_data(message_ids=message_ids)
                await state.set_state(PrintInvoice.waiting_for_continue_inserting)
        else:
            await message.answer(
                "⚠️ Отправьте № из предложенного списка",
                reply_markup=sharedkb.cancel_action
            )
    else:
        await message.answer("⚠️ Отправьте одно натуральное число",
                             reply_markup=sharedkb.cancel_action)

@shop_managment_router.message(PrintInvoice.waiting_for_invoice_date)
@role_required(["admin"])
async def print_invoice_state_date(
    message: Message,
    state: FSMContext,
    data_session: AsyncSession,
    db_manager: DatabaseManager,
    **kwargs
):
    state_data = await state.get_data()
    invoices = state_data.get("invoices", {})
    invoice_number = state_data.get("invoice_number", None)
    previous_invoice_raw_date = state_data.get("previous_invoice_raw_date", None)
    previous_invoice_date = state_data.get("previous_invoice_date", None)

    try:
        sanitized_date = message.text.replace(" ", "")

        valid_date = datetime.strptime(sanitized_date, "%d.%m.%Y").date()

        if sanitized_date == invoices[invoice_number].strftime('%d.%m.%Y'):

            if previous_invoice_date is not None:
                target_data_db_path = db_manager.get_data_db_path(date=previous_invoice_date, mkdir=False)
                if db_manager.database_exists(target_data_db_path):
                    target_engine = db_manager.create_data_engine(target_data_db_path)
                    async with target_engine.connect() as target_conn:
                        products = await drq.get_products_by_invoice(
                            target_conn,
                            invoice_number,
                            valid_date
                        )
            else:
                products = await drq.get_products_by_invoice(data_session, invoice_number, valid_date)

            products_list = list()
            for id, product in enumerate(products, start=1):
                name, quantity, purchase_price = product
                products_list.append(
                    f"№ <b>{id}</b>. <i>{name}</i>: {quantity} шт. по {purchase_price} руб."
                )
            products_list = "\n".join(products_list)

            await message.answer(
                f"<b>Список товаров для накладной</b>:\n№ <b>{invoice_number}</b>. от <i>{sanitized_date}</i>\n\n"
                f"{products_list}"
            )

            if previous_invoice_raw_date is not None:
                date = f"<i>{previous_invoice_raw_date}</i>"
            else:
                date = "текущий месяц"
            msg = await message.answer(
                f"Хотите продолжить вывод накладных за {date}?",
                reply_markup=sharedkb.print_invoice_question
            )
            data = await state.get_data()
            message_ids = data.get("message_ids", [])
            message_ids.append(msg.message_id)
            await state.update_data(message_ids=message_ids)
            await state.set_state(PrintInvoice.waiting_for_continue_inserting)
        else:
            await message.answer(
                "⚠️ Отправьте дату, которая соответствует № из предложенного списка",
                reply_markup=sharedkb.cancel_action
            )
    except ValueError:
        await message.answer(
            '⚠️ Отправьте дату в формате "день.месяц.год" (05.2024)',
            reply_markup=sharedkb.cancel_action
        )

@shop_managment_router.message(PrintInvoice.waiting_for_previous_invoice_date)
@role_required(["admin"])
async def print_invoice_state_previous_date(
    message: Message,
    state: FSMContext,
    db_manager: DatabaseManager,
    **kwargs
):
    sanitized_date = message.text.replace(" ", "")
    
    try:
        valid_date = datetime.strptime(sanitized_date, "%m.%Y").date()
    except ValueError:
        await message.answer(
            '⚠️ Отправьте дату в формате "день.месяц.год" (05.2024)',
            reply_markup=sharedkb.cancel_action
        )
        return
    
    target_data_db_path = db_manager.get_data_db_path(date=valid_date, mkdir=False)

    if db_manager.database_exists(target_data_db_path):
        target_engine = db_manager.create_data_engine(target_data_db_path)
        async with target_engine.connect() as target_conn:
            invoices = await drq.get_invoices(target_conn)

        invoices_list = "\n".join(
            [f"№ <b>{number}</b>. от <i>{date[0].strftime('%d.%m.%Y')}</i>" for number, date in invoices.items()]
        )
        if invoices_list:
            await message.answer(
                f"Список накладных за <i>{sanitized_date}</i>:\n\n{invoices_list}\n\n"
                "> <b>Отправьте № накладной</b>",
                reply_markup=sharedkb.cancel_action
            )
            await state.update_data(
                invoices=invoices,
                previous_invoice_raw_date=sanitized_date,
                previous_invoice_date=valid_date)
            await state.set_state(PrintInvoice.waiting_for_invoice_number)
        else:
            await message.answer(
                "⚠️ Сначала добавьте хотя бы одну накладную",
                reply_markup=sharedkb.cancel_action
            )
    else:
        await message.answer(
            f'⚠️ Не существует данных для даты: <i>{sanitized_date}</i>',
            reply_markup=sharedkb.cancel_action
        )

@shop_managment_router.callback_query(F.data == "print_invoice_yes")
@role_required(["admin"])
async def print_invoice_yes(
    callback: CallbackQuery,
    state: FSMContext,
    data_session: AsyncSession,
    db_manager: DatabaseManager,
    **kwargs
):
    state_data = await state.get_data()
    previous_invoice_raw_date = state_data.get("previous_invoice_raw_date", None)
    previous_invoice_date = state_data.get("previous_invoice_date", None)

    await callback.answer("")
    if previous_invoice_date is not None:
        target_data_db_path = db_manager.get_data_db_path(date=previous_invoice_date, mkdir=False)
        if db_manager.database_exists(target_data_db_path):
            target_engine = db_manager.create_data_engine(target_data_db_path)
            async with target_engine.connect() as target_conn:
                invoices = await drq.get_invoices(target_conn)
    else:
        invoices = await drq.get_invoices(data_session)

    invoices_list = "\n".join(
        [f"№ <b>{number}</b>. от <i>{date[0].strftime('%d.%m.%Y')}</i>" for number, date in invoices.items()]
    )
    if previous_invoice_raw_date is not None:
        date = f"<i>{previous_invoice_raw_date}</i>"
    else:
        date = "текущий месяц"
    if invoices_list:
        await callback.message.answer(
            f"Список накладных за {date}:\n\n{invoices_list}\n\n"
            "> <b>Отправьте № накладной</b>",
            reply_markup=sharedkb.cancel_action
        )
        await state.update_data(invoices=invoices)
        await state.set_state(PrintInvoice.waiting_for_invoice_number)
    else:
        await callback.message.answer(
            "⚠️ Сначала добавьте хотя бы одну накладную",
            reply_markup=sharedkb.cancel_action
        )

@shop_managment_router.callback_query(F.data == "print_invoice_no")
@role_required(["admin"])
async def print_invoice_no(callback: CallbackQuery, state: FSMContext, **kwargs):
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
    await callback.message.answer("📢 Вывод накладных завершен.")

# ==============================================================================================================
# ДОБАВЛЕНИЕ ДРУГИХ ТРАТ
# ==============================================================================================================

class AddExpense(StatesGroup):
    waiting_for_expense_id = State()
    waiting_for_expense_name = State()
    waiting_for_expense_spent = State()
    waiting_for_continue_inserting = State()

@shop_managment_router.callback_query(F.data == "add_other_expenses")
@role_required(["admin"])
async def add_other_expenses(callback: CallbackQuery, state: FSMContext, data_session: AsyncSession, **kwargs):
    await callback.answer()
    # проверяем есть ли хотя бы одна запись с тратой
    expenses = await drq.get_expenses_data(data_session)
    if expenses:
        expenses_ids = dict()
        expenses_list = list()
        for expense in expenses:
            expenses_ids[expense.id] = expense.name
            expenses_list.append(f'№ <b>{expense.id}</b>. <i>{expense.name}</i>: {expense.spent}')
        expenses_list = "\n".join(expenses_list)
        await callback.message.answer("Список существующих трат:\n"
                                      f"{expenses_list}\n\n",
                                      reply_markup=adminkb.add_expense_choice)
        await state.update_data(expenses_ids=expenses_ids)
    else:
        await callback.message.answer('> <b>Отправьте название траты</b>\n<i>Например: "Налог" или "ЗП продавцу"</i>',
                                      reply_markup=sharedkb.cancel_action)
        await state.set_state(AddExpense.waiting_for_expense_name)

@shop_managment_router.callback_query(F.data == "add_to_existing_expense")
@role_required(["admin"])
async def add_to_existing_expense(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer('> <b>Отправьте № траты</b>',
                                  reply_markup=sharedkb.cancel_action)
    await state.set_state(AddExpense.waiting_for_expense_id)

@shop_managment_router.callback_query(F.data == "create_new_expense")
@role_required(["admin"])
async def create_new_expense(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer('> <b>Отправьте название траты</b>\n<i>Например: "Налог" или "ЗП продавцу"</i>',
                                  reply_markup=sharedkb.cancel_action)
    await state.set_state(AddExpense.waiting_for_expense_name)

@shop_managment_router.message(AddExpense.waiting_for_expense_id)
@role_required(["admin"])
async def add_to_expense_state_id(message: Message, state: FSMContext, **kwargs):
    state_data = await state.get_data()
    expenses_ids = state_data.get("expenses_ids", {})

    if message.text.isdigit():
        if int(message.text) in expenses_ids:
            await message.answer(f"<b>Номер</b>: № {message.text}\n"
                                 f"<b>Название</b>: <i>{expenses_ids[int(message.text)]}</i>\n\n"
                                 "> <b>Отправьте стоимость траты</b>",
                                 reply_markup=sharedkb.cancel_action)
            await state.update_data(expense_id=int(message.text))
            await state.set_state(AddExpense.waiting_for_expense_spent)
        else:
            await message.answer("⚠️ Отправьте номер из предложенного списка",
                             reply_markup=sharedkb.cancel_action)
    else:
        await message.answer("⚠️ Отправьте одно натуральное число",
                             reply_markup=sharedkb.cancel_action)

@shop_managment_router.message(AddExpense.waiting_for_expense_name)
@role_required(["admin"])
async def add_to_expense_state_name(message: Message, state: FSMContext, **kwargs):
    
    product_name_pegex = r"^[А-Яа-яA-Za-z0-9\s]+$"
    if re.match(product_name_pegex, message.text):
        await message.answer(f'<b>Название</b>: <i>{message.text}</i>\n\n'
                            "> <b>Отправьте стоимость траты</b>",
                            reply_markup=sharedkb.cancel_action)
        await state.update_data(expense_name = message.text)
        await state.set_state(AddExpense.waiting_for_expense_spent)
    else:
        await message.answer('⚠️ Отправьте название товара без спец. символов',
                             reply_markup=sharedkb.cancel_action)

@shop_managment_router.message(AddExpense.waiting_for_expense_spent)
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
                            f"<b>Название</b>: <i>{expense_name}</i>\n"
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
        
@shop_managment_router.message(AddExpense.waiting_for_continue_inserting)
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

@shop_managment_router.callback_query(F.data == "add_expense_yes")
@role_required(["admin"])
async def add_expense_yes(callback: CallbackQuery, state: FSMContext, data_session: AsyncSession, **kwargs):
    await callback.answer("")
    expenses = await drq.get_expenses_data(data_session)
    if expenses:
        expenses_ids = dict()
        expenses_list = list()
        for expense in expenses:
            expenses_ids[expense.id] = expense.name
            expenses_list.append(f'№ <b>{expense.id}</b>. <i>{expense.name}</i>: {expense.spent}')
        expenses_list = "\n".join(expenses_list)
        await callback.message.answer("Список существующих трат:\n"
                                      f"{expenses_list}\n\n",
                                      reply_markup=adminkb.add_expense_choice)
        await state.update_data(expenses_ids=expenses_ids, expense_name=None, expense_id=None)
    else:
        await callback.message.answer('> <b>Отправьте название траты</b>\n<i>Например: "Налог" или "ЗП продавцу"</i>',
                                      reply_markup=sharedkb.cancel_action)
        await state.set_state(AddExpense.waiting_for_expense_name)

@shop_managment_router.callback_query(F.data == "add_expense_no")
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

# ==============================================================================================================
# ИЗМЕНЕНИЕ ЦЕНЫ
# ==============================================================================================================

class ChangePrice(StatesGroup):
    waiting_for_keyword = State()
    waiting_for_product_id = State()
    waiting_for_sale_price = State()
    waiting_for_continue_selling = State()

class Trash(StatesGroup):
    waiting_for_quantity = State()

@shop_managment_router.callback_query(F.data == "change_price")
@role_required(["admin"])
async def call_change_price(callback: CallbackQuery, **kwargs):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=adminkb.change_price_choice)

@shop_managment_router.callback_query(F.data.in_(["change_stnd_price", "change_promotion_price"]))
@role_required(["admin"])
async def change_stnd_price(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer("Для изменения цены выполните поиск по товарам, отправив ключевое слово.\n\n"
                                  '<i>Например: Хризантема</i>\n\n'
                                  "> <b>Отправьте ключевое слово</b>",
                                  reply_markup=sharedkb.cancel_action)
    if callback.data == "change_stnd_price":
        await state.update_data(is_stnd_change_price=True)

    await state.set_state(ChangePrice.waiting_for_keyword)

@shop_managment_router.message(ChangePrice.waiting_for_keyword)
@role_required(["admin", 'seller'])
async def change_price_state_keyword(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):

    product_name_pegex = r"^[А-Яа-яA-Za-z0-9\s]+$"
    if re.match(product_name_pegex, message.text):
        state_data = await state.get_data()
        is_stnd_change_price = state_data.get("is_stnd_change_price", False)
        is_trash = state_data.get("is_trash", False)
        products = await drq.get_product_names(data_session)
        result = await hu.dynamic_search(message.text, products)

        if result:
            product_data = dict()
            products_list = list()
            for item in result:
                id = item['id']
                date = item['date'].strftime("%d.%m")
                name = item['name']
                remaining_pieces = item['remaining_pieces']
                lost_pieces = item['lost_pieces']
                sale_price = item["sale_price"]
                promotion_price = item["promotion_price"]
                
                product_data[id] = (name, remaining_pieces, lost_pieces, sale_price, promotion_price)

                products_list.append(
                    f"<code>{id}</code>. "
                    f"(от {date}) "
                    f"<i>Название</i>: {name} "
                    f"<i>Остаток</i>: {remaining_pieces}; {f'<i>Утиль</i>: {lost_pieces}' if is_trash else ''}"
                    f"{(f'Стнд. цена: {sale_price}; ' if is_stnd_change_price else f'Акц. цена: {promotion_price}') if not is_trash else ''}"
                )

            products_list = "\n".join(products_list)
            await state.update_data(product_data=product_data)
            await message.answer(f"Найденные товары:\n\n{products_list}\n\n"
                                 "> <b>Отправьте идентификатор товара</b>",
                                 reply_markup=sharedkb.cancel_action)
            await state.set_state(ChangePrice.waiting_for_product_id)
        else:
            await message.answer("⚠️ Ничего не найдено! Проверьте ключевое слово",
                                     reply_markup=sharedkb.cancel_action)
    else:
        await message.answer('⚠️ Отправьте название товара без спец. символов',
                             reply_markup=sharedkb.cancel_action)
        
@shop_managment_router.message(ChangePrice.waiting_for_product_id)
@role_required(["admin", 'seller'])
async def change_price_state_product_id(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    
    if message.text.isdigit():
        state_data = await state.get_data()
        product_data = state_data.get("product_data", {})
        is_trash = state_data.get("is_trash", False)

        if int(message.text) in product_data:
            if is_trash:
                await message.answer(f"Идентификатор: {message.text}\n\n"
                                     "> <b>Отправьте количество</b>",
                                     reply_markup=sharedkb.cancel_action)
                await state.update_data(product_id=int(message.text))
                await state.set_state(Trash.waiting_for_quantity)
            else:
                await message.answer(f"Идентификатор: {message.text}\n\n"
                                    "> <b>Отправьте новую цену</b>",
                                    reply_markup=sharedkb.cancel_action)
                await state.update_data(product_id=int(message.text))
                await state.set_state(ChangePrice.waiting_for_sale_price)
        else:
            await message.answer("⚠️ Выберите идентификатор из предложенного списка",
                                 reply_markup=sharedkb.cancel_action)
    else:
        await message.answer("⚠️ Отправьте одно натуральное число",
                             reply_markup=sharedkb.cancel_action)
        
@shop_managment_router.message(ChangePrice.waiting_for_sale_price)
@role_required(["admin"])
async def change_price_state_sale_price(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):

    cost_regex = r"^\d+(\.\d+)?$"
    match = re.match(cost_regex, message.text)
    if match:
        state_data = await state.get_data()
        product_data = state_data.get("product_data", {})
        product_id = state_data.get("product_id", None)
        is_stnd_change_price = state_data.get("is_stnd_change_price", False)
        remaining_pieces = product_data[product_id][1]
        new_price = float(message.text)

        await drq.change_price(data_session, product_id, remaining_pieces, is_stnd_change_price, new_price)
        old_price_text = (
            f"Стнд. цена: {product_data[product_id][3]}; "
            if is_stnd_change_price
            else f"Акц. цена: {product_data[product_id][4]}"
        )
        new_price_text = (
            f"Новая стнд. цена: {new_price}; "
            if is_stnd_change_price
            else f"Новая акц. цена: {new_price}" 
        )
        await message.answer(f"📢 Информация об изменении цены товара:\n\n"
                            f"<b>Идентификатор</b>: {product_id}\n"
                            f"<b>Название</b>: {product_data[product_id][0]}\n"
                            f"<b>Остаток</b>: {product_data[product_id][1]}\n"
                            f"{old_price_text}\n"
                            f"{new_price_text}")
        msg = await message.answer("Хотите продолжить изменять цены товарам?", reply_markup=sharedkb.change_price_question)
        data = await state.get_data()
        message_ids = data.get("message_ids", [])
        message_ids.append(msg.message_id)
        await state.update_data(message_ids=message_ids)
        await state.set_state(ChangePrice.waiting_for_continue_selling)
    else:
        await message.answer("⚠️ Отправьте одно натуральное или положительное рациональное число",
                             reply_markup=sharedkb.cancel_action)
        
@shop_managment_router.message(Trash.waiting_for_quantity)
@role_required(["admin", 'seller'])
async def trash_state_quantity(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    
    if message.text.isdigit():
        state_data = await state.get_data()
        product_data = state_data.get("product_data", {})
        product_id = state_data.get("product_id", None)
        remaining_pieces = product_data[product_id][1]
        lost_pieces = product_data[product_id][2]
        quantity = int(message.text)

        if remaining_pieces >= quantity:
            remaining_pieces -= quantity
            lost_pieces = await drq.add_trash(data_session, product_id, lost_pieces, quantity, remaining_pieces)
            await message.answer(f"📢 Информация о добавленном утиле:\n\n"
                                f"<b>Идентификатор</b>: {product_id}\n"
                                f"<b>Название</b>: {product_data[product_id][0]}\n"
                                f"<b>Остаток</b>: {remaining_pieces}\n"
                                f"<b>Утиль</b>: {lost_pieces}")
            msg = await message.answer("Хотите продолжить добавлять утиль?", reply_markup=sharedkb.change_price_question)
            data = await state.get_data()
            message_ids = data.get("message_ids", [])
            message_ids.append(msg.message_id)
            await state.update_data(message_ids=message_ids)
            await state.set_state(ChangePrice.waiting_for_continue_selling)
        else:
            await message.answer("⚠️ Вы хотите продать больше утиля чем остаток товара",
                                 reply_markup=sharedkb.cancel_action)
    else:
        await message.answer('⚠️ Отправьте одно натуральное число',
                             reply_markup=sharedkb.cancel_action)
        
@shop_managment_router.message(ChangePrice.waiting_for_continue_selling)
@role_required(["admin", "seller"])
async def change_price_continue_selling(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    state_data = await state.get_data()
    is_trash = state_data.get("is_trash", False)

    if is_trash:
        text = "Хотите продолжить добавлять утиль?"
    else:
        text = "Хотите продолжить изменять цены товарам?"

    msg = await message.answer(
        text,
        reply_markup=sharedkb.change_price_question
    )

    data = await state.get_data()
    message_ids = data.get("message_ids", [])
    message_ids.append(msg.message_id)
    await state.update_data(message_ids=message_ids)

@shop_managment_router.callback_query(F.data == "change_price_yes")
@role_required(["admin", "seller"])
async def change_price_yes(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager, **kwargs):
    await callback.answer("")
    await callback.message.answer("> <b>Отправьте ключевое слово</b>\n<i>Например: Хризантема</i>",
                                  reply_markup=sharedkb.cancel_action)
    await state.set_state(ChangePrice.waiting_for_keyword)

@shop_managment_router.callback_query(F.data == "change_price_no")
@role_required(["admin", "seller"])
async def change_price_no(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager, **kwargs):
    await callback.answer("")

    state_data = await state.get_data()
    message_ids = state_data.get("message_ids", [])

    for msg_id in message_ids:
        await callback.bot.edit_message_reply_markup(
            chat_id=callback.message.chat.id,
            message_id=msg_id,
            reply_markup=None
        )

    state_data = await state.get_data()
    is_trash = state_data.get("is_trash", False)

    if is_trash:
        text = "📢 Добавление утиля завершено."
    else:
        text = "📢 Изменение цен завершено."
        
    await state.clear()

    await callback.message.answer(text)

# ==============================================================================================================
# ДОБАВЛЕНИЕ БРАКА
# ==============================================================================================================

@shop_managment_router.callback_query(F.data == "add_trash")
@role_required(["admin", 'seller'])
async def call_add_trash(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer("Для добавления брака выполните поиск по товарам, отправив ключевое слово.\n\n"
                                  '<i>Например: Хризантема</i>\n\n'
                                  "> <b>Отправьте ключевое слово</b>",
                                  reply_markup=sharedkb.cancel_action)
    await state.update_data(is_trash=True)
    await state.set_state(ChangePrice.waiting_for_keyword)

# ==============================================================================================================
# ПОЛУЧЕНИЕ МЕСЯЧНОГО ОТЧЕТА
# ==============================================================================================================

class MonthlyReport(StatesGroup):
    pass

@shop_managment_router.callback_query(F.data == "monthly_report")
@role_required(["admin"])
async def monthly_report(callback: CallbackQuery, data_session: AsyncSession, **kwargs):
    await callback.answer()
    # получаем общую выручку
    data_total_revenues = await drq.get_total_revenues(data_session)
    # получаем общие траты кроме других траты
    data_total_purchase_expenses = await drq.get_purchase_expenses(data_session)
    # получаем все данные по другим тратам
    data_other_expenses = await drq.get_expenses_data(data_session)

    # производим рассчет
    total_revenue = 0
    for key, value in data_total_revenues.items():
        total_revenue += value

    total_purchase_expenses = 0
    for key, value in data_total_purchase_expenses.items():
        total_purchase_expenses += value

    total_other_expenses = 0
    other_expenses_list = list()
    for expense in data_other_expenses:
        total_other_expenses += expense.spent
        other_expenses_list.append(f"       - <b>{expense.name}</b>: {expense.spent}")

    # форматируем текст
    other_expenses_list = "\n".join(other_expenses_list)
    # отправляем отчет
    await callback.message.answer("📢 Отчет за текущий месяц:\n\n"
                                  f"<b>Общая выручка</b>: {total_revenue}\n"
                                  f"<b>Общие траты</b>: {total_purchase_expenses + total_other_expenses}\n"
                                  f"В том числе траты:\n"
                                  f"> <i>На закупку</i>: {data_total_purchase_expenses['total_purchase']}\n"
                                  f"> <i>На утиль</i>: {data_total_purchase_expenses['total_lost']}\n"
                                  f"> <i>Другие</i>:\n"
                                  f"{other_expenses_list}\n\n"
                                  f"<b>Чистая прибыль</b>: {total_revenue - (total_purchase_expenses + total_other_expenses)}")

# ==============================================================================================================
# ПРОДАЖА
# ==============================================================================================================

class Sell(StatesGroup):
    waiting_for_user_keyword = State()
    waiting_for_product_id = State()
    waiting_for_quantity = State()
    waiting_for_composition_sale_price = State()
    waiting_for_continue_selling = State()

@shop_managment_router.callback_query(F.data == "sell_choice")
@role_required(["admin", 'seller'])
async def sell_choice(callback: CallbackQuery, **kwargs):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=sharedkb.sell_choice)

#### Продажа поштучно, по акции, композиции
@shop_managment_router.callback_query(F.data.in_({"sell_by_piece", "sell_by_promotion", "sell_composition"}))
@role_required(["admin", 'seller'])
async def sell_by_piece(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    
    if callback.data == "sell_composition":
        await callback.message.answer("Для продажи композиции выполните поиск по товарам, отправив ключевое слово.\n\n"
                                      '<i>Например: Хризантема</i>\n\n'
                                      "> <b>Отправьте ключевое слово</b>",
                                      reply_markup=sharedkb.cancel_action)
        await state.update_data(is_composition=True, count=0)
    elif callback.data == "sell_by_promotion":
        await callback.message.answer("Для продажи товара по акции выполните поиск по товарам, отправив ключевое слово.\n\n"
                                      '<i>Например: Хризантема</i>\n\n'
                                      "> <b>Отправьте ключевое слово</b>",
                                      reply_markup=sharedkb.cancel_action)
        await state.update_data(is_promotion=True)
    else:
        await callback.message.answer("Для продажи товара выполните поиск по товарам, отправив ключевое слово.\n\n"
                                      '<i>Например: Хризантема</i>\n\n'
                                      "> <b>Отправьте ключевое слово</b>",
                                      reply_markup=sharedkb.cancel_action)

    await state.set_state(Sell.waiting_for_user_keyword)

@shop_managment_router.message(Sell.waiting_for_user_keyword)
@role_required(["admin", 'seller'])
async def sell_state_keyword(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):

    product_name_pegex = r"^[А-Яа-яA-Za-z0-9\s]+$"
    if re.match(product_name_pegex, message.text):

        state_data = await state.get_data()
        is_promotion = state_data.get("is_promotion", False)
        products = await drq.get_product_names(data_session, is_promotion)
        result = await hu.dynamic_search(message.text, products)

        if result:
            product_data = dict()
            products_list = list()
            for item in result:
                id = item['id']
                date = item['date'].strftime("%d.%m")
                name = item['name']
                remaining_pieces = item['remaining_pieces']
                
                product_data[id] = (name, remaining_pieces)

                products_list.append(f"<code>{id}</code>. (от {date}) <i>Название</i>: <b>{name}</b> <i>Остаток</i>: {remaining_pieces}")

            products_list = "\n".join(products_list)
            await state.update_data(product_data=product_data)
            await message.answer(f"Найденные товары:\n\n{products_list}\n\n"
                                 "> <b>Отправьте идентификатор товара</b>",
                                 reply_markup=sharedkb.cancel_action)
            await state.set_state(Sell.waiting_for_product_id)
        else:
            await message.answer("⚠️ Ничего не найдено! Проверьте ключевое слово",
                                     reply_markup=sharedkb.cancel_action)
    else:
        await message.answer('⚠️ Отправьте название товара без спец. символов',
                             reply_markup=sharedkb.cancel_action)

@shop_managment_router.message(Sell.waiting_for_product_id)
@role_required(["admin", 'seller'])
async def sell_state_product_id(message: Message, state: FSMContext, **kwargs):
    
    if message.text.isdigit():
        state_data = await state.get_data()
        product_data = state_data.get("product_data", {})

        if int(message.text) in product_data:
            await message.answer(
                f"Идентификатор: {message.text}\n\n"
                "> <b>Отправьте количество для продажи.</b> ",
                reply_markup=sharedkb.cancel_action
            )
            await state.update_data(product_id=int(message.text))
            await state.set_state(Sell.waiting_for_quantity)
        else:
            await message.answer("⚠️ Отправьте идентификатор из предложенного списка",
                             reply_markup=sharedkb.cancel_action)
    else:
        await message.answer("⚠️ Отправьте одно натуральное число",
                             reply_markup=sharedkb.cancel_action)

@shop_managment_router.message(Sell.waiting_for_quantity)
@role_required(["admin", 'seller'])
async def sell_state_quantity(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    
    state_data = await state.get_data()
    is_composition = state_data.get("is_composition", False)
    product_id = state_data.get("product_id", None)
    product_data = state_data.get("product_data", {})
    is_promotion = state_data.get("is_promotion", False)
    product_name = product_data[product_id][0]
    remaining_pieces = product_data[product_id][1]
    
    if is_composition:
        if message.text.isdigit():
            quantity = int(message.text)

            if remaining_pieces >= quantity:
                remaining_pieces -= quantity
                await message.answer(
                    f"Количество для продажи: {quantity}\n\n"
                    "> <b>Отправьте цену продажи</b>"
                )
                await state.update_data(remaining_pieces=remaining_pieces, quantity=quantity)
                await state.set_state(Sell.waiting_for_composition_sale_price)
            else:
                await message.answer("⚠️ Вы хотите продать больше товара, чем есть",
                                        reply_markup=sharedkb.cancel_action)
        else:
            await message.answer("⚠️ Отправьте одно натуральное число",
                                reply_markup=sharedkb.cancel_action)
    else:
        if message.text.isdigit():
            if remaining_pieces >= int(message.text):
                if is_promotion:
                    remaining_pieces = await drq.update_product_promotion_revenue(data_session, product_id, remaining_pieces, int(message.text))
                else:
                    remaining_pieces = await drq.update_product_revenue(data_session, product_id, remaining_pieces, int(message.text))
                await message.answer(f"📢 Информация о проданом товаре:\n\n"
                                    f"<b>Идентификатор</b>: {product_id}\n"
                                    f"<b>Название</b>: {product_name}\n"
                                    f"<b>Остаток</b>: {remaining_pieces}\n"
                                    f"<b>Акция</b>: {'Да' if is_promotion else 'Нет'}")
                msg = await message.answer("Хотите продолжить продажу товаров?", reply_markup=sharedkb.sell_product_question)
                data = await state.get_data()
                message_ids = data.get("message_ids", [])
                message_ids.append(msg.message_id)
                await state.update_data(message_ids=message_ids)
                await state.set_state(Sell.waiting_for_continue_selling)
            else:
                await message.answer("⚠️ Вы хотите продать больше товара, чем есть",
                                    reply_markup=sharedkb.cancel_action)
        else:
            await message.answer("⚠️ Отправьте одно натуральное число",
                                reply_markup=sharedkb.cancel_action)

@shop_managment_router.message(Sell.waiting_for_composition_sale_price)
@role_required(["admin", 'seller'])
async def sell_state_sale_price(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    
    state_data = await state.get_data()
    product_id = state_data.get("product_id", None)
    quantity = state_data.get("quantity", None)
    remaining_pieces = state_data.get("remaining_pieces", None)
    product_data = state_data.get("product_data", {})
    count = state_data.get("count", 0)
    product_name = product_data[product_id][0]

    cost_regex = r"^\d+(\.\d+)?$"
    match = re.match(cost_regex, message.text)
    if match:
        sale_price = int(message.text)
        await drq.insert_composition(data_session, product_id, quantity, sale_price, remaining_pieces)
        await message.answer(f"📢 Информация о проданом товаре:\n\n"
                             f"<b>Идентификатор</b>: {product_id}\n"
                             f"<b>Название</b>: {product_name}\n"
                             f"<b>Остаток</b>: {remaining_pieces}\n"
                             f"<b>Цена продажи</b>: {sale_price}")
        count += 1
        if count < 2:
            await message.answer("⚠️ В композиции должно быть минимум два товара, продайте хотя бы ещё один товар.\n\n"
                                 "> <b>Отправьте ключевое слово</b>",
                                 reply_markup=sharedkb.cancel_action)
            await state.update_data(count=count)
            await state.set_state(Sell.waiting_for_user_keyword)
        else:
            msg = await message.answer("Хотите продолжить продажу товаров?", reply_markup=sharedkb.sell_product_question)
            data = await state.get_data()
            message_ids = data.get("message_ids", [])
            message_ids.append(msg.message_id)
            await state.update_data(message_ids=message_ids)
            await state.set_state(Sell.waiting_for_continue_selling)
    else:
        await message.answer("⚠️ Отправьте одно натуральное или положительное рациональное число",
                             reply_markup=sharedkb.cancel_action)

@shop_managment_router.message(Sell.waiting_for_continue_selling)
@role_required(["admin", 'seller'])
async def sell_state_continue_selling(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    msg = await message.answer(
        "Хотите продолжить продажу товаров?",
        reply_markup=sharedkb.sell_product_question
    )
    data = await state.get_data()
    message_ids = data.get("message_ids", [])
    message_ids.append(msg.message_id)
    await state.update_data(message_ids=message_ids)

@shop_managment_router.callback_query(F.data == "sell_product_yes")
@role_required(["admin", 'seller'])
async def sell_product_yes(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer("")
    await callback.message.answer("> <b>Отправьте ключевое слово.</b>",
                                  reply_markup=sharedkb.cancel_action)
    await state.set_state(Sell.waiting_for_user_keyword)

@shop_managment_router.callback_query(F.data == "sell_product_no")
@role_required(["admin", 'seller'])
async def sell_product_no(callback: CallbackQuery, state: FSMContext, **kwargs):
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
    await callback.message.answer("📢 Продажа завершена.")