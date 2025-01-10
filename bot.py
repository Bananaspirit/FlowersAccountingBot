import logging
import asyncio
from aiogram.client.default import DefaultBotProperties
from aiogram.enums.parse_mode import ParseMode
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from config import USERS_BASE_DIR, DATA_BASE_DIR
from access_middleware import AccessMiddleware
from app.database.manager import DatabaseManager
from app.handlers.admin import admin_router
from app.handlers.shared import shared_router, role_router
from app.handlers.add_invoice import invoice_router, other_expenses_router
from app.handlers.sell import sell_router
from app.handlers.change_price_add_trash import change_price_router, add_trash_router
from app.handlers.monthly_report import monthly_report_router

dp = Dispatcher(storage=MemoryStorage())
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

db_manager = DatabaseManager(user_base_dir=USERS_BASE_DIR, data_base_dir=DATA_BASE_DIR)

async def on_startup(bot):
    user_param = False
    if user_param:
        await db_manager.drop_user_db()
    
    # data_param = True
    # if data_param:
    #     await db_manager.drop_data_db()

    await db_manager.create_user_db()

    await db_manager.migrate_to_new_month()

async def on_shutdown(bot):
    await db_manager.cleanup_sessions()
    await db_manager.user_engine.dispose()
    if db_manager.current_data_db_path:
        engine = db_manager.create_data_engine(db_manager.current_data_db_path)
        await engine.dispose()

    logging.info("Exit")

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.include_router(admin_router)
    dp.include_router(role_router)
    dp.include_router(shared_router)
    dp.include_router(invoice_router)
    dp.include_router(sell_router)
    dp.include_router(change_price_router)
    dp.include_router(add_trash_router)
    dp.include_router(other_expenses_router)
    dp.include_router(monthly_report_router)

    dp.message.middleware(AccessMiddleware(db_manager))
    dp.callback_query.middleware(AccessMiddleware(db_manager))

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO) # в прод выключить
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    asyncio.run(main())