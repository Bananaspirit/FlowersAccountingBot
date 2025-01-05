from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import InputFile, FSInputFile
import app.keyboards.admin as adminkb
import app.keyboards.main as mainkb
from aiogram import Bot
from access_middleware import role_required
# from app.database.handler import ensure_db_exists, process_invoice_data
from config import ADMIN_PASSWORD

from app.database import user_requests as urq
from app.database import data_requests as drq
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.manager import DatabaseManager

from . import utils as hu

admin_router = Router()

# Уровень кнопок - head
@admin_router.callback_query(F.data == "manage_users")
@role_required(["admin"])
async def manage_users(callback: CallbackQuery, **kwargs):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=adminkb.user_management)

@admin_router.callback_query(F.data == "manage_shop")
@role_required(["admin"])
async def manage_shop(callback: CallbackQuery, **kwargs):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=adminkb.shop_management)

## Уровень кнопок - user_management
### Возврат на уровень - head
@admin_router.callback_query(F.data == "admin_back")
@role_required(["admin"])
async def admin_back(callback: CallbackQuery, **kwargs):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=adminkb.head)

### Создание продавца
class CreateUser(StatesGroup):
    waiting_for_user_id = State()

@admin_router.callback_query(F.data == "create_user")
@role_required(["admin"])
async def create_user(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer("Для назначения пользователю телеграм роли 'Продавец' необходим его Telegram ID, отправьте его мне.\n"
                        "Если вы не знаете Telegram ID пользователя, попросите его начать чат с ботом. "
                        "Бот отправит Telegram ID пользователя и уведомит его о необходимости передать ID администратору.")
    await state.set_state(CreateUser.waiting_for_user_id)

@admin_router.message(CreateUser.waiting_for_user_id)
@role_required(["admin"])
async def create_user_state_id(message: Message, state: FSMContext, bot: Bot, user_session: AsyncSession, **kwargs):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс назначения роли отменен.")
        return
    
    if message.text.isdigit():
        tg_id = int(message.text)
        if await urq.ensure_user_exist(user_session, tg_id) is not None:
            await urq.set_user_role(user_session, tg_id, "seller")
            await message.answer("Пользователю телеграм успешно назначена роль - 'Продавец'.")
            await bot.send_message(int(message.text), "Ваша роль обновлена! Теперь вы - 'Продавец'.")
            await state.clear()
        else:
            await message.answer("Не вышло! Этот пользователь еще не начал чат с ботом, "
                                "попробуйте заново, или введите /cancel, чтобы отменить назначение роли.")
    else:
        await message.answer("id должен содержать только цифры.")
        
### Удаление продавца
class DeleteSeller(StatesGroup):
    waiting_for_user_id = State()

@admin_router.callback_query(F.data == "delete_user")
@role_required(["admin"])
async def delete_user(callback: CallbackQuery, state: FSMContext, user_session: AsyncSession, **kwargs):
    await callback.answer()
    users = await urq.get_all_users_by_role(user_session, "seller")
    if users:
        user_list = "\n".join([f"<b>Имя</b>: {user.name}, <b>Telegram ID</b>: <code>{user.tg_id}</code>" for user in users])
        await callback.message.answer(f"Список продавцов:\n{user_list}\n\nОтправьте Telegram ID продавца для удаления.")
        await state.set_state(DeleteSeller.waiting_for_user_id)
    else:
        await callback.message.answer("Нет ни одного продавца.")

@admin_router.message(DeleteSeller.waiting_for_user_id)
@role_required(["admin"])
async def delete_user_state_id(message: Message, state: FSMContext, bot: Bot, user_session: AsyncSession, **kwargs):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс удаления продавца отменен.")
        return
    
    if message.text.isdigit():
        tg_id = int(message.text)
        if await urq.ensure_user_exist(user_session, tg_id) is not None:
            await urq.set_user_role(user_session, tg_id, "deleted")
            await message.answer("Продавец успешно удален! Для восстановления продавца повторите процедуру назначения роли.")
            await bot.send_message(int(message.text),
                                "Вам заблокирован доступ к боту. "
                                "Если это произошло по ошибке, свяжитесь с администратором. "
                                f"Вот ваш Telegram ID, нажмите на него чтобы скопировать: <code>{tg_id}</code>, "
                                "он понадобится для восстановления доступа к боту.",
                                reply_markup=mainkb.unknown_user)
            await state.clear()
        else:
            await message.answer("Не вышло! Этот пользователь еще не начал чат с ботом, "
                                "попробуйте заново, или введите /cancel, чтобы отменить удаление продавца.")
    else:
        await message.answer("id должен содержать только цифры.")

### Создание администратора
class CreateAdmin(StatesGroup):
    waiting_for_superuser_pass = State()
    waiting_for_user_id = State()

@admin_router.callback_query(F.data == "create_admin")
@role_required(["admin"])
async def create_admin(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer("Для назначения пользователю телеграм роли 'Администратор' необходим пароль суперпользователя, отправьте его мне.\n")
    await state.set_state(CreateAdmin.waiting_for_superuser_pass)

@admin_router.message(CreateAdmin.waiting_for_superuser_pass)
@role_required(["admin"])
async def create_admin_state_pass(message: Message, state: FSMContext, **kwargs):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс назначения роли отменен.")
        return

    if message.text == ADMIN_PASSWORD:
        await state.clear()
        await message.reply("Для назначения пользователю телеграм роли 'Администратор' необходим его Telegram ID, отправьте его мне.\n"
                            "Если вы не знаете Telegram ID пользователя, попросите его начать чат с ботом. "
                            "Бот отправит Telegram ID пользователя и уведомит его о необходимости передать ID администратору.")
        await state.set_state(CreateAdmin.waiting_for_user_id)
    else:
        await message.answer("Неверный пароль.\n"
                            "Попробуйте заново, или введите /cancel, чтобы отменить назначение роли.")

@admin_router.message(CreateAdmin.waiting_for_user_id)
@role_required(["admin"])
async def create_admin_state_id(message: Message, state: FSMContext, bot: Bot, user_session: AsyncSession, **kwargs):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс назначения роли отменен.")
        return
    
    if message.text.isdigit():
        tg_id = int(message.text)
        if await urq.ensure_user_exist(user_session, tg_id) is not None:
            await urq.set_user_role(user_session, tg_id, "admin")
            await message.answer("Пользователю телеграм успешно назначена роль - 'Aдминистратор'.")
            await bot.send_message(int(message.text), "Ваша роль обновлена! Теперь вы - 'Aдминистратор'.")
            await state.clear()
        else:
            await message.answer("Не вышло! Этот пользователь еще не начал чат с ботом, "
                                "попробуйте заново, или введите /cancel, чтобы отменить назначение роли.")
    else:
        await message.answer("id должен содержать только цифры.")

### Удаление Администратора
class DeleteAdmin(StatesGroup):
    waiting_for_superuser_pass = State()
    waiting_for_user_id = State()

@admin_router.callback_query(F.data == "delete_admin")
@role_required(["admin"])
async def delete_admin(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer("Для удаления администратора необходим пароль суперпользователя, отправьте его мне.\n")
    await state.set_state(DeleteAdmin.waiting_for_superuser_pass)

@admin_router.message(DeleteAdmin.waiting_for_superuser_pass)
@role_required(["admin"])
async def delete_admin_state_pass(message: Message, state: FSMContext, user_session: AsyncSession, **kwargs):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс удаления администратора отменен.")
        return

    if message.text == ADMIN_PASSWORD:
        await state.clear()
        users = await urq.get_all_users_by_role(user_session, "admin")
        if users:
            user_list = "\n".join([f"<b>Имя</b>: {user.name}, <b>Telegram ID</b>: <code>{user.tg_id}</code>" for user in users])
            await message.answer(f"Список администраторов:\n{user_list}\n\nОтправьте Telegram ID администратора для удаления.")
            await state.set_state(DeleteAdmin.waiting_for_user_id)
        else:
            await message.answer("Нет ни одного администратора.")
    else:
        await message.answer("Неверный пароль.\n"
                            "Попробуйте заново, или введите /cancel, чтобы отменить удаление администратора.")
        
@admin_router.message(DeleteAdmin.waiting_for_user_id)
@role_required(["admin"])
async def delete_admin_state_id(message: Message, state: FSMContext, bot: Bot, user_session: AsyncSession, **kwargs):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс удаления администратора отменен.")
        return
    
    if message.text.isdigit():
        tg_id = int(message.text)
        if await urq.ensure_user_exist(user_session, tg_id) is not None:
            await urq.set_user_role(user_session, tg_id, "deleted")
            await message.answer("Администратор успешно удален! Для восстановления администратора повторите процедуру назначения роли.")
            await bot.send_message(int(message.text),
                                "Вам заблокирован доступ к боту. "
                                "Если это произошло по ошибке, свяжитесь с администратором. "
                                f"Вот ваш Telegram ID, нажмите на него чтобы скопировать: <code>{tg_id}</code>, "
                                "он понадобится для восстановления доступа к боту.",
                                reply_markup=mainkb.unknown_user)
            await state.clear()
        else:
            await message.answer("Не вышло! Этот пользователь еще не начал чат с ботом, "
                                "попробуйте заново, или введите /cancel, чтобы отменить удаление администратора.")
    else:
        await message.answer("id должен содержать только цифры.")

## Уровень кнопок - shop_management
### Внесение прихода
class AddArrival(StatesGroup):
    waiting_for_user_input = State()

@admin_router.callback_query(F.data == "add_invoice")
@role_required(["admin"])
async def add_invoice(callback: CallbackQuery, state: FSMContext, db_manager: DatabaseManager, **kwargs):
    await callback.answer()
    await callback.message.answer("Внесите данные из накладной в следующем формате:\n\n"
                                "[Номер накладной]/[Дата]/[Стоимость доставки]\n\n"
                                "[Наименование товара №1]/[Количество]/[Закупочная стоимость]/[Цена продажи]/[Акционная цена]\n"
                                "[Наименование товара №2]/[Количество]/[Закупочная стоимость]/[Цена продажи]/[Акционная цена]\n\n"
                                "Пример:\n"
                                "3961/15.07.24/200\n\n"
                                "Хризантема/20/50.4/75.2/60\n"
                                "Роза/10/100/120/100\n\n"
                                "или\n\n"
                                "3961/15.07.24\n\n"
                                "Хризантема/20/50.4/75.2\n"
                                "Роза/10/100/123.3\n\n"
                                "Примечание: поле [Стоимость доставки] и [Акционная цена] является опциональным.")
    await db_manager.create_data_db()
    await state.set_state(AddArrival.waiting_for_user_input)

@admin_router.message(AddArrival.waiting_for_user_input)
@role_required(["admin"])
async def add_invoice_state_input(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс внесения накладной отменен.")
        return

    # Проверяем формат введенных данных
    result, data = await hu.process_invoice_data(message.text)
    if result:
        invoice_number, date, cost = data["invoice_data"]
        await drq.insert_invoice(data_session, invoice_number, date, cost)
        for product_item in data["product_data"]:
            name, quantity, purchase_price, sale_price, promotion_price = product_item
            await drq.insert_product(data_session, invoice_number, name, quantity, purchase_price)
            product_id = await drq.get_product_id(data_session, name, invoice_number)
            # Начинаем ведение статистики
            await drq.start_statistics(data_session, product_id, sale_price, quantity, promotion_price)
        await state.clear()
        await message.answer("Данные успешно внесены.")
    else:
        await message.answer(data)

### Продажа
class Sell(StatesGroup):
    waiting_for_user_keyword = State()
    waiting_for_user_sell_data = State()

@admin_router.callback_query(F.data == "sell_choice")
@role_required(["admin"])
async def sell_choice(callback: CallbackQuery, **kwargs):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=adminkb.sell_choice)

#### Продажа поштучно
@admin_router.callback_query(F.data == "sell_by_piece")
@role_required(["admin"])
async def sell_by_piece(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer("Для продажи товара выполните поиск по позициям, для этого отправьте ключевое слово."
                                  "Например, 'Хризантема' или 'роза' или 'шар'. Слово не должно содержать ошибок.")
    await state.set_state(Sell.waiting_for_user_keyword)

#### Продажа по акции
@admin_router.callback_query(F.data == "sell_by_promotion")
@role_required(["admin"])
async def sell_by_promotion(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer("Для продажи товара выполните поиск по позициям, для этого отправьте ключевое слово."
                                  "Например, 'Хризантема' или 'роза' или 'шар'. Слово не должно содержать ошибок.")
    await state.update_data(is_promotion=True)
    await state.set_state(Sell.waiting_for_user_keyword)

@admin_router.message(Sell.waiting_for_user_keyword)
@role_required(["admin"])
async def sell_state_keyword(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс продажи отменен.")
        return
    
    # принимаем ключевое слово
    # отправляем найденные позиции
    # принимаем данные для продажи
    data = await state.get_data()
    is_promotion = data.get("is_promotion", False)
    products = await drq.get_product_names(data_session, is_promotion)
    result, data = await hu.dynamic_search(message.text, products)
    if result:
        lst = list()
        product_ids = list()
        for item in data:
            id = item['id']
            date = item['date'].strftime("%d.%m")
            name = item['name']
            remaining_pieces = item['remaining_pieces']
            
            product_ids.append(id)
            lst.append(f"<code>{id}</code>. ({date}) {name} ост.:{remaining_pieces} шт.")
        products_list = "\n".join(lst)
        if len(products_list) != 0:
            await state.update_data(is_promotion=is_promotion, product_ids=product_ids)
            await message.answer(f"Найденные товары:\n\n{products_list}\n\nНажмите на идентификатор товара, чтобы скопировать."
                                "Для продажи отправьте данные в формате: "
                                "[Идентификатор товара]/[Количество для продажи].\n"
                                "Например:\n\n1/2")
            await state.set_state(Sell.waiting_for_user_sell_data)
        else:
            await message.answer("Ничего не найдено! Проверьте ключевое слово и попробуйте заново или нажмите /cancel.")
    else:
        await message.answer(data)

@admin_router.message(Sell.waiting_for_user_sell_data)
@role_required(["admin"])
async def sell_state_sell_data(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс продажи отменен.")
        return

    result, data = await hu.process_sell_data(message.text)
    if result:
        state_data = await state.get_data()
        is_promotion = state_data.get("is_promotion", False)
        product_ids = state_data.get("product_ids", [])
        if is_promotion:
            result, data = await drq.update_product_promotion_revenue(data_session, data, product_ids)
        else:
            result, data = await drq.update_product_revenue(data_session, data, product_ids)
        if result:
            await state.clear()
            await message.answer(data)
        else:
            await message.answer(data)
    else:
        await message.answer(data)

#### Продажа композиции
class CompositionSell(StatesGroup):
    waiting_for_user_keyword = State()
    waiting_for_user_sell_data = State()

@admin_router.callback_query(F.data == "sell_composition")
@role_required(["admin"])
async def sell_composition(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer("Для продажи композиции выполните поиск по нужным товарам, "
                                  "для этого отправьте ключевые слова, по одному на каждой строке. Например:\n\n"
                                  "Хризантема\nРоза\nУпаковка\nт.д.")
    await state.set_state(CompositionSell.waiting_for_user_keyword)

@admin_router.message(CompositionSell.waiting_for_user_keyword)
@role_required(["admin"])
async def composition_sell_state_keyword(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    state_data = await state.get_data()
    is_trash = state_data.get("is_trash", False)
    is_stnd_change_price = state_data.get("is_stnd_change_price", False)
    is_promotion_change_price = state_data.get("is_promotion_change_price", False)
    if message.text == "/cancel":
        await state.clear()
        if is_trash:
            msg = "Процесс добавления утиля отменен."
        elif is_stnd_change_price or is_promotion_change_price:
            msg = "Процесс изменения цены отменен."
        else:
            msg = "Процесс продажи отменен."
        await message.answer(msg)
        return
    
    # проверяем формат ввода, если верный то
    # выполняем поэтапный поиск для каждого ключевого слова
    # возвращаем найденную дату, форматируем и отправляем список для каждого ключевого слова
    # устанавливаем состояние и ждем ввод id/sold_price/sale_price
    result, data = await hu.process_composition_keywords(message.text)
    if result:
        common_dict = dict()
        product_ids = list()
        for keyword in data:
            products = await drq.get_product_names(data_session)
            result, data = await hu.dynamic_search(keyword, products)
            if result:
                lst = list()
                for item in data:
                    id = item['id']
                    date = item['date'].strftime("%d.%m")
                    name = item['name']
                    remaining_pieces = item['remaining_pieces']
                    lost_pieces = item['lost_pieces']

                    product_ids.append(id)
                    lst.append(f"<code>{id}</code>. ({date}) {name} ост.:{remaining_pieces} шт. утиль:{lost_pieces} шт.")
                products_list = "\n".join(lst)
                if len(products_list) != 0:
                    common_dict[keyword] = products_list
                else:
                    common_dict[keyword] = ("Данные не найдены")
            else:
                await message.answer(data)
        compiled_list = "\n\n".join([f"{key}:\n{value}" for key, value in common_dict.items()])
        await state.update_data(
            is_stnd_change_price=is_stnd_change_price,
            is_promotion_change_price=is_promotion_change_price,
            product_ids=product_ids
        )
        if is_trash:
            msg = (f"Найденные товары:\n\n{compiled_list}\n\nНажмите на идентификатор товара, чтобы скопировать."
                   "Для добавления товара в утиль отправьте данные в формате: "
                   "[Идентификатор товара]/[Количество].\n"
                   "Например:\n\n1/2")
            current_state = Trash.waiting_for_user_trash_data
        elif is_stnd_change_price:
            msg = (f"Найденные товары:\n\n{compiled_list}\n\n"
                   "Отправьте данные для каждого товара на новой строке в формате: "
                   "[Идентификатор товара]/[Новая цена продажи].\n"
                   "Например:\n\n"
                   "1/100\n5/150\n10/120.5\nт.д.")
            current_state = ChangePrice.waiting_for_user_data
        elif is_promotion_change_price:
            msg = (f"Найденные товары:\n\n{compiled_list}\n\n"
                   "Отправьте данные для каждого товара на новой строке в формате: "
                   "[Идентификатор товара]/[Новая акционная цена].\n"
                   "Например:\n\n"
                   "1/100\n5/150\n10/120.5\nт.д.")
            current_state = ChangePrice.waiting_for_user_data
        else:
            msg = (f"Найденные товары:\n\n{compiled_list}\n\n"
                   "Отправьте данные для каждого товара на новой строке в формате: "
                   "Утиль/[Идентификатор товара]/[Количество для продажи]/[Цена продажи].\n"
                   "Например:\n\n"
                   "1/2/100\n5/1/150\n10/3/120.5\nт.д.\n\n"
                   "Примечание: Утиль является опциональным ключевым словом, "
                   "добавьте к данным если хотите продать утиль.")
            current_state = CompositionSell.waiting_for_user_sell_data
        await message.answer(msg)
        await state.set_state(current_state)
    else:
        await message.answer(data)

@admin_router.message(CompositionSell.waiting_for_user_sell_data)
@role_required(["admin"])
async def composition_sell_state_sell_data(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс продажи отменен.")
        return
    
    # проверяем корректность ввода в формате id/sold_pieces/sold_price\n, возвращаем данные
    # передаем данные в функцию insert_composition, возвращаем статус и сообщение
    state_data = await state.get_data()
    product_ids = state_data.get("product_ids", [])
    result, data = await hu.process_composition_sell_data(message.text)
    if result:
        result, data = await drq.insert_composition(data_session, data, product_ids)
        if result:
            await state.clear()
            await message.answer(data)
        else:
            await message.answer(data)
    else:
        await message.answer(data)

### Изменение цены
class ChangePrice(StatesGroup):
    waiting_for_user_data = State()

@admin_router.callback_query(F.data == "change_price")
@role_required(["admin"])
async def change_price(callback: CallbackQuery, **kwargs):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=adminkb.change_price_choice)

@admin_router.callback_query(F.data.in_(["change_stnd_price", "change_promotion_price"]))
@role_required(["admin"])
async def change_stnd_price(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer("Для изменения цены выполните поиск по товарам, для этого отправьте ключевые слова, "
                                  "по одному на каждой строке.\nНапример:\n\n"
                                  "Хризантема\nРоза\nУпаковка\nт.д.")
    if callback.data == "change_stnd_price":
        await state.update_data(is_stnd_change_price=True)
    else:
        await state.update_data(is_promotion_change_price=True)
    await state.set_state(CompositionSell.waiting_for_user_keyword)

@admin_router.message(ChangePrice.waiting_for_user_data)
@role_required(["admin"])
async def change_price_state_data(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс изменения цены отменен.")
        return
    
    state_data = await state.get_data()
    is_stnd_change_price = state_data.get("is_stnd_change_price", False)
    product_ids = state_data.get("product_ids", [])
    result, data = await hu.process_change_price_data(message.text)
    if result:
        result, data = await drq.change_price(data_session, data, is_stnd_change_price, product_ids)
        if result:
            await state.clear()
            await message.answer(data)
        else:
            await message.answer(data)
    else:
        await message.answer(data)

### Добавление утиля
class Trash(StatesGroup):
    waiting_for_user_trash_data = State()

@admin_router.callback_query(F.data == "add_trash")
@role_required(["admin"])
async def add_trash(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer("Для добавления утиля выполните поиск по товарам, для этого отправьте ключевые слова, "
                                  "по одному на каждой строке.\nНапример:\n\n"
                                  "Хризантема\nРоза\nУпаковка\nт.д.")
    await state.update_data(is_trash=True)
    await state.set_state(CompositionSell.waiting_for_user_keyword)

@admin_router.message(Trash.waiting_for_user_trash_data)
@role_required(["admin"])
async def sell_state_trash_data(message: Message, state: FSMContext, data_session: AsyncSession, **kwargs):
    if message.text == "/cancel":
        await state.clear()
        await message.answer("Процесс добавления утиля отменен.")
        return

    state_data = await state.get_data()
    product_ids = state_data.get("product_ids", [])
    result, data = await hu.process_trash_data(message.text)
    if result:
        result, data = await drq.add_trash(data_session, data, product_ids)
        if result:
            await state.clear()
            await message.answer(data)
        else:
            await message.answer(data)
    else:
        await message.answer(data)