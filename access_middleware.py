from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable
from app.database import users_db
import app.keyboards as kb

class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]], event: Message, data: Dict[str, Any]):
        user_id = event.from_user.id
        if users_db.is_table_empty("users"):
            users_db.add_unknown_user_if_not_exists(user_id, event.from_user.full_name)
            users_db.set_user_role(user_id, "first")
        else:
            users_db.add_unknown_user_if_not_exists(user_id, event.from_user.full_name)

        # Блокировка пользователя если админ назначил ему роль "deleted"
        if not users_db.is_table_empty and users_db.get_user_role(user_id) == "deleted":
            # Notify user about restricted access
            await event.answer("Вам заблокирован доступ к боту. "
                               "Если это произошло по ошибке, свяжитесь с администратором. "
                               f"Вот ваш Telegram ID, нажмите на него чтобы скопировать: <code>{user_id}</code>, "
                               "он понадобится для восстановления доступа к боту.",
                               reply_markup=kb.unknown_user_kb)
            return  # Stop further handling

        # Proceed to the handler if the user exists in the database
        return await handler(event, data)