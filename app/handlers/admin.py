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
@admin_router.callback_query(F.data == "user_management_back")
@role_required(["admin"])
async def user_management_back(callback: CallbackQuery, **kwargs):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=adminkb.head)

## Уровень кнопок - shop_management
### Возврат на уровень - head
@admin_router.callback_query(F.data == "shop_management_back")
@role_required(["admin"])
async def shop_management_back(callback: CallbackQuery, **kwargs):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=adminkb.head)

## Уровень кнопок - change_price_choice
### Возврат на уровень - shop_management
@admin_router.callback_query(F.data == "change_price_choice_back")
@role_required(["admin"])
async def change_price_choice_back(callback: CallbackQuery, **kwargs):
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=adminkb.shop_management)

### Создание продавца
class CreateUser(StatesGroup):
    waiting_for_user_id = State()

@admin_router.callback_query(F.data == "create_user")
@role_required(["admin"])
async def create_user(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer('Для назначения пользователю роли "Продавец", необходим его Telegram ID.\n\n'
                                  "Если у вас нет Telegram ID пользователя, попросите его начать чат с ботом. "
                                  "Бот отправит Telegram ID пользователю и уведомит его о необходимости передать ID администратору.\n\n"
                                  "> <b>Отправьте Telegram ID</b>",
                                  reply_markup=sharedkb.cancel_action)
    await state.set_state(CreateUser.waiting_for_user_id)

@admin_router.message(CreateUser.waiting_for_user_id)
@role_required(["admin"])
async def create_user_state_id(message: Message, state: FSMContext, bot: Bot, user_session: AsyncSession, **kwargs):

    if message.text.isdigit():
        tg_id = int(message.text)
        if await urq.ensure_user_exist(user_session, tg_id) is not None:
            await urq.set_user_role(user_session, tg_id, "seller")
            await message.answer('📢 Пользователю успешно назначена роль - "Продавец".')
            await bot.send_message(int(message.text),
                                   '📢 Ваша роль обновлена! Теперь вы - "Продавец".',
                                   reply_markup=sharedkb.reply_menu)
            await state.clear()
        else:
            await message.answer("⚠️ Этот пользователь еще не начал чат с ботом",
                                reply_markup=sharedkb.cancel_action)
    else:
        await message.answer("⚠️ Telegram ID это натуральное число",
                             reply_markup=sharedkb.cancel_action)
        
### Удаление продавца
class DeleteSeller(StatesGroup):
    waiting_for_user_id = State()

@admin_router.callback_query(F.data == "delete_user")
@role_required(["admin"])
async def delete_user(callback: CallbackQuery, state: FSMContext, user_session: AsyncSession, **kwargs):
    await callback.answer()
    users = await urq.get_all_users_by_role(user_session, "seller")
    if users:
        user_list = "\n".join([f"<b>Имя</b>: {user.full_name}, <b>Telegram ID</b>: <code>{user.tg_id}</code>" for user in users])
        await callback.message.answer(f"Список продавцов:\n{user_list}\n\n> Отправьте Telegram ID продавца.",
                                      reply_markup=sharedkb.cancel_action)
        await state.set_state(DeleteSeller.waiting_for_user_id)
    else:
        await callback.message.answer("⚠️ Нет ни одного продавца")

@admin_router.message(DeleteSeller.waiting_for_user_id)
@role_required(["admin"])
async def delete_user_state_id(message: Message, state: FSMContext, bot: Bot, user_session: AsyncSession, **kwargs):
    
    if message.text.isdigit():
        tg_id = int(message.text)
        if await urq.ensure_user_exist(user_session, tg_id) is not None:
            await urq.set_user_role(user_session, tg_id, "deleted")
            await message.answer("📢 Продавец успешно удален! Для восстановления продавца повторите процедуру назначения роли.")
            await bot.send_message(int(message.text),
                                "📢 Вам заблокирован доступ к боту. "
                                "Если это произошло по ошибке, свяжитесь с администратором. "
                                f"Вот ваш Telegram ID, нажмите на него чтобы скопировать: <code>{tg_id}</code>, "
                                "он понадобится для восстановления доступа к боту.",
                                reply_markup=sharedkb.unknown_user)
            await state.clear()
        else:
            await message.answer("⚠️ Этот пользователь еще не начал чат с ботом",
                                reply_markup=sharedkb.cancel_action)
    else:
        await message.answer("⚠️ Telegram ID это натуральное число",
                             reply_markup=sharedkb.cancel_action)

### Создание администратора
class CreateAdmin(StatesGroup):
    waiting_for_superuser_pass = State()
    waiting_for_user_id = State()

@admin_router.callback_query(F.data == "create_admin")
@role_required(["admin"])
async def create_admin(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer('Для этого действия необходим пароль суперпользователя.\n\n'
                                  "> Отправьте пароль.",
                                  reply_markup=sharedkb.cancel_action)
    await state.set_state(CreateAdmin.waiting_for_superuser_pass)

@admin_router.message(CreateAdmin.waiting_for_superuser_pass)
@role_required(["admin"])
async def create_admin_state_pass(message: Message, state: FSMContext, **kwargs):

    if message.text == ADMIN_PASSWORD:
        await state.clear()
        await message.reply('Для назначения пользователю телеграм роли "Администратор" необходим его Telegram ID.\n'
                            "Если у вас нет Telegram ID пользователя, попросите его начать чат с ботом. "
                            "Бот отправит Telegram ID пользователя и уведомит его о необходимости передать ID администратору.\n\n"
                            "> Отправьте Telegram ID.",
                            reply_markup=sharedkb.cancel_action)
        await state.set_state(CreateAdmin.waiting_for_user_id)
    else:
        await message.answer("⚠️ Неверный пароль",
                             reply_markup=sharedkb.cancel_action)

@admin_router.message(CreateAdmin.waiting_for_user_id)
@role_required(["admin"])
async def create_admin_state_id(message: Message, state: FSMContext, bot: Bot, user_session: AsyncSession, **kwargs):

    if message.text.isdigit():
        tg_id = int(message.text)
        if await urq.ensure_user_exist(user_session, tg_id) is not None:
            await urq.set_user_role(user_session, tg_id, "admin")
            await message.answer('📢 Пользователю телеграм успешно назначена роль - "Aдминистратор".')
            await bot.send_message(int(message.text),
                                   '📢 Ваша роль обновлена! Теперь вы - "Aдминистратор".',
                                   reply_markup=sharedkb.reply_menu)
            await state.clear()
        else:
            await message.answer("⚠️ Этот пользователь еще не начал чат с ботом",
                                reply_markup=sharedkb.cancel_action)
    else:
        await message.answer("⚠️ Telegram ID это натуральное число",
                             reply_markup=sharedkb.cancel_action)

### Удаление Администратора
class DeleteAdmin(StatesGroup):
    waiting_for_superuser_pass = State()
    waiting_for_user_id = State()

@admin_router.callback_query(F.data == "delete_admin")
@role_required(["admin"])
async def delete_admin(callback: CallbackQuery, state: FSMContext, **kwargs):
    await callback.answer()
    await callback.message.answer('Для этого действия необходим пароль суперпользователя.\n\n'
                                  "> Отправьте пароль.",
                                  reply_markup=sharedkb.cancel_action)
    await state.set_state(DeleteAdmin.waiting_for_superuser_pass)

@admin_router.message(DeleteAdmin.waiting_for_superuser_pass)
@role_required(["admin"])
async def delete_admin_state_pass(message: Message, state: FSMContext, user_session: AsyncSession, **kwargs):

    if message.text == ADMIN_PASSWORD:
        await state.clear()
        users = await urq.get_all_users_by_role(user_session, "admin")
        if users:
            user_list = "\n".join([f"<b>Имя</b>: {user.full_name}, <b>Telegram ID</b>: <code>{user.tg_id}</code>" for user in users])
            await message.answer(f"Список администраторов:\n{user_list}\n\nОтправьте Telegram ID администратора для удаления.",
                                 reply_markup=sharedkb.cancel_action)
            await state.set_state(DeleteAdmin.waiting_for_user_id)
        else:
            await message.answer("⚠️ Нет ни одного администратора")
    else:
        await message.answer("⚠️ Неверный пароль",
                             reply_markup=sharedkb.cancel_action)
        
@admin_router.message(DeleteAdmin.waiting_for_user_id)
@role_required(["admin"])
async def delete_admin_state_id(message: Message, state: FSMContext, bot: Bot, user_session: AsyncSession, **kwargs):
    
    if message.text.isdigit():
        tg_id = int(message.text)
        if await urq.ensure_user_exist(user_session, tg_id) is not None:
            await urq.set_user_role(user_session, tg_id, "deleted")
            await message.answer("📢 Администратор успешно удален! Для восстановления администратора повторите процедуру назначения роли.")
            await bot.send_message(int(message.text),
                                "📢 Вам заблокирован доступ к боту. "
                                "Если это произошло по ошибке, свяжитесь с администратором. "
                                f"Вот ваш Telegram ID, нажмите на него чтобы скопировать: <code>{tg_id}</code>, "
                                "он понадобится для восстановления доступа к боту.",
                                reply_markup=sharedkb.unknown_user)
            await state.clear()
        else:
            await message.answer("⚠️ Этот пользователь еще не начал чат с ботом",
                                reply_markup=sharedkb.cancel_action)
    else:
        await message.answer("⚠️ Telegram ID это натуральное число",
                             reply_markup=sharedkb.cancel_action)