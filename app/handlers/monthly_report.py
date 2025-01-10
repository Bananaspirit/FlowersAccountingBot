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

monthly_report_router = Router()

# ==============================================================================================================
# ПОЛУЧЕНИЕ МЕСЯЧНОГО ОТЧЕТА
# ==============================================================================================================

class MonthlyReport(StatesGroup):
    pass

@monthly_report_router.callback_query(F.data == "monthly_report")
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