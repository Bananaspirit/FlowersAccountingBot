from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable, Union
import app.keyboards.shared as mainkb
from functools import wraps
from aiogram.types import TelegramObject

from app.database.manager import DatabaseManager
from app.database import user_requests as rq

def role_required(allowed_roles):
    def decorator(func):
        async def wrapper(event, *args, **kwargs):
            user_role = kwargs.get("user_role")
            if user_role not in allowed_roles:
                if hasattr(event, "answer"):
                    await event.answer("У вас нет прав на использование данной команды.", show_alert=True)
                elif hasattr(event, "reply"):
                    await event.answer("У вас нет прав на использование данной команды.", show_alert=True)
                return
            return await func(event, *args, **kwargs)
        return wrapper
    return decorator

class AccessMiddleware(BaseMiddleware):
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager

    async def __call__(self, handler, event: Union[Message, CallbackQuery], data: dict):
        tg_id = event.from_user.id
        user_name = event.from_user.full_name

        # user_session = await self.db_manager.get_user_session()
        # data_session = await self.db_manager.get_data_session()

        data["db_manager"] = self.db_manager
        
        try:
            # async with user_session.begin():
            async with await self.db_manager.get_user_session() as user_session:
                if not await rq.get_list_of_admins(user_session):
                    if await rq.ensure_user_exist(user_session, tg_id) is None:
                        await rq.add_unknown_user(user_session, tg_id, user_name)
                        await rq.set_user_role(user_session, tg_id, "first")
                else:
                    if await rq.ensure_user_exist(user_session, tg_id) is None:
                        await rq.add_unknown_user(user_session, tg_id, user_name)

                user_role = await rq.get_user_role(user_session, tg_id)

                data['user_session'] = user_session
                data['user_role'] = user_role
        
            # async with data_session.begin():
            async with await self.db_manager.get_data_session() as data_session:
                data['data_session'] = data_session
                
            return await handler(event, data)
        finally:
            await user_session.close()
            await data_session.close()