import logging
import asyncio
from config import BOT_TOKEN
from aiogram import Bot, Dispatcher
from app.handlers import router
from app.database.create_users_db import init_db

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

init_db()

async def main():
    dp.include_router(router)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO) # в прод выключить

    asyncio.run(main())
