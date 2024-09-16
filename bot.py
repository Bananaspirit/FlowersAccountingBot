import logging
import asyncio
from config import BOT_TOKEN
from aiogram import Bot, Dispatcher
from app.handlers import router

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    asyncio.run(main())