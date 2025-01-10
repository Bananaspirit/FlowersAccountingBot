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

sell_router = Router()

### Продажа
class Sell(StatesGroup):
    waiting_for_user_keyword = State()
    waiting_for_product_id = State()
    waiting_for_quantity = State()
    waiting_for_composition_sale_price = State()
    waiting_for_continue_selling = State()

@sell_router.callback_query(F.data == "sell_choice")
@role_required(["admin", 'seller'])
async def sell_choice(callback: CallbackQuery, **kwargs):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=sharedkb.sell_choice)

#### Продажа поштучно, по акции, композиции
@sell_router.callback_query(F.data.in_({"sell_by_piece", "sell_by_promotion", "sell_composition"}))
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

@sell_router.message(Sell.waiting_for_user_keyword)
@role_required(["admin", 'seller'])
async def sell_state_keyword(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):

    product_name_pegex = r"^[А-Яа-яA-Za-z0-9\s]+$"
    if re.match(product_name_pegex, message.text):

        state_data = await state.get_data()
        is_promotion = state_data.get("is_promotion", False)
        is_composition = state_data.get("is_composition", False)
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
                lost_pieces = item['lost_pieces']
                
                product_data[id] = (name, remaining_pieces, lost_pieces)

                if is_composition:
                    products_list.append(f"<code>{id}</code>. (от {date}) <i>Название</i>: <b>{name}</b>. <i>Остаток</i>: {remaining_pieces}; <i>Утиль</i>: {lost_pieces}")
                else:
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

@sell_router.message(Sell.waiting_for_product_id)
@role_required(["admin", 'seller'])
async def sell_state_product_id(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    
    if message.text.isdigit():
        state_data = await state.get_data()
        product_data = state_data.get("product_data", {})
        is_composition = state_data.get("is_composition", False)

        if int(message.text) in product_data:
            if is_composition:
                await message.answer(f"Идентификатор: {message.text}\n\n"
                                    "> <b>Отправьте количество для продажи.</b> "
                                    'Если хотите продать утиль, добавьте ключевое слово "Утиль" или "утиль" к количеству.\n\n'
                                    "<i>Например: Утиль 4 или утиль 5</i>",
                                    reply_markup=sharedkb.cancel_action)
            else:
                await message.answer(f"Идентификатор: {message.text}\n\n"
                                    "> <b>Отправьте количество для продажи</b>",
                                    reply_markup=sharedkb.cancel_action)
            await state.update_data(product_id=int(message.text))
            await state.set_state(Sell.waiting_for_quantity)
        else:
            await message.answer("⚠️ Отправьте идентификатор из предложенного списка",
                             reply_markup=sharedkb.cancel_action)
    else:
        await message.answer("⚠️ Отправьте одно натуральное число",
                             reply_markup=sharedkb.cancel_action)

@sell_router.message(Sell.waiting_for_quantity)
@role_required(["admin", 'seller'])
async def sell_state_quantity(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    
    state_data = await state.get_data()
    is_composition = state_data.get("is_composition", False)
    product_id = state_data.get("product_id", None)
    product_data = state_data.get("product_data", {})
    is_promotion = state_data.get("is_promotion", False)
    product_name = product_data[product_id][0]
    remaining_pieces = product_data[product_id][1]
    lost_pieces = product_data[product_id][2]
    
    if is_composition:
        regex = r"^(?:утиль\s*(\d+)|(\d+))$"
        match = re.match(regex, message.text, re.IGNORECASE)
        if match:
            trash_keyword =  trash_keyword = match.group(1) is not None
            quantity = int(match.group(1) or match.group(2))

            if trash_keyword:
                if lost_pieces >= quantity:
                    await state.update_data(trash_keyword=trash_keyword, quantity=quantity)
                else:
                    await message.answer("⚠️ Вы хотите продать больше утиля, чем есть",
                                         reply_markup=sharedkb.cancel_action)
                    return
            else:
                if remaining_pieces >= quantity:
                    await state.update_data(quantity=quantity)
                else:
                    await message.answer("⚠️ Вы хотите продать больше товара, чем есть",
                                         reply_markup=sharedkb.cancel_action)
                    return
            await message.answer(f"Количество для продажи: {quantity}\n\n"
                                "> <b>Отправьте цену продажи</b>")
            await state.set_state(Sell.waiting_for_composition_sale_price)
        else:
            await message.answer('⚠️ Отправьте одно натуральное число или добавьте перед ним слово "Утиль"',
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

@sell_router.message(Sell.waiting_for_composition_sale_price)
@role_required(["admin", 'seller'])
async def sell_state_sale_price(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    
    state_data = await state.get_data()
    product_id = state_data.get("product_id", None)
    quantity = state_data.get("quantity", None)
    trash_keyword = state_data.get("trash_keyword", False)
    product_data = state_data.get("product_data", {})
    count = state_data.get("count", 0)
    product_name = product_data[product_id][0]
    remaining_pieces = product_data[product_id][1]
    lost_pieces = product_data[product_id][2]

    cost_regex = r"^\d+(\.\d+)?$"
    match = re.match(cost_regex, message.text)
    if match:
        sale_price = int(message.text)
        result = await drq.insert_composition(data_session, product_id, trash_keyword, lost_pieces, quantity, sale_price, remaining_pieces)
        await message.answer(f"📢 Информация о проданом товаре:\n\n"
                             f"<b>Идентификатор</b>: {product_id}\n"
                             f"<b>Название</b>: {product_name}\n"
                             f"<b>Остаток</b>: {remaining_pieces if trash_keyword else result}\n"
                             f"<b>Утиль</b>: {result if trash_keyword else lost_pieces}\n"
                             f"<b>Утиль</b>: {'Да' if trash_keyword else 'Нет'}\n"
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

@sell_router.message(Sell.waiting_for_continue_selling)
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

@sell_router.callback_query(F.data == "sell_product_yes")
@role_required(["admin", 'seller'])
async def sell_product_yes(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager, **kwargs):
    await callback.answer("")
    await callback.message.answer("> <b>Отправьте ключевое слово.</b>",
                                  reply_markup=sharedkb.cancel_action)
    await state.set_state(Sell.waiting_for_user_keyword)

@sell_router.callback_query(F.data == "sell_product_no")
@role_required(["admin", 'seller'])
async def sell_product_no(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager, **kwargs):
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