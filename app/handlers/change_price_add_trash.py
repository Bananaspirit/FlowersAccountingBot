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

change_price_router = Router()
add_trash_router = Router()

### Изменение цены
class ChangePrice(StatesGroup):
    waiting_for_keyword = State()
    waiting_for_product_id = State()
    waiting_for_sale_price = State()
    waiting_for_continue_selling = State()

class Trash(StatesGroup):
    waiting_for_quantity = State()

@change_price_router.callback_query(F.data == "change_price")
@role_required(["admin"])
async def call_change_price(callback: CallbackQuery, **kwargs):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=adminkb.change_price_choice)

@change_price_router.callback_query(F.data.in_(["change_stnd_price", "change_promotion_price"]))
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

@change_price_router.message(ChangePrice.waiting_for_keyword)
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
                    f"({date}) "
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
        
@change_price_router.message(ChangePrice.waiting_for_product_id)
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
        
@change_price_router.message(ChangePrice.waiting_for_sale_price)
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
        
@add_trash_router.message(Trash.waiting_for_quantity)
@role_required(["admin", 'seller'])
async def trash_state_quantity(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    
    if message.text.isdigit():
        state_data = await state.get_data()
        product_data = state_data.get("product_data", {})
        product_id = state_data.get("product_id", None)
        remaining_pieces = product_data[product_id][1]
        lost_pieces = product_data[product_id][2]

        if remaining_pieces >= int(message.text):
            lost_pieces = await drq.add_trash(data_session, product_id, lost_pieces, int(message.text), remaining_pieces)
            await message.answer(f"📢 Информация о добавленном утиле:\n\n"
                                f"<b>Идентификатор</b>: {product_id}\n"
                                f"<b>Название</b>: {product_data[product_id][0]}\n"
                                f"<b>Остаток</b>: {product_data[product_id][1]}\n"
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
        
@change_price_router.message(ChangePrice.waiting_for_continue_selling)
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

@change_price_router.callback_query(F.data == "change_price_yes")
@role_required(["admin", "seller"])
async def change_price_yes(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager, **kwargs):
    await callback.answer("")
    await callback.message.answer("> <b>Отправьте ключевое слово</b>\n<i>Например: Хризантема</i>",
                                  reply_markup=sharedkb.cancel_action)
    await state.set_state(ChangePrice.waiting_for_keyword)

@change_price_router.callback_query(F.data == "change_price_no")
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

### Добавление утиля
@add_trash_router.callback_query(F.data == "add_trash")
@role_required(["admin", 'seller'])
async def call_add_trash(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer("Для изменения цены выполните поиск по товарам, отправив ключевое слово.\n\n"
                                  '<i>Например: Хризантема</i>\n\n'
                                  "> <b>Отправьте ключевое слово</b>",
                                  reply_markup=sharedkb.cancel_action)
    await state.update_data(is_trash=True)
    await state.set_state(ChangePrice.waiting_for_keyword)