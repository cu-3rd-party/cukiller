from typing import Callable, Dict, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery, Update

from db.models import User


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            user: User | None = await User.get_or_none(
                tg_id=event.from_user.id
            )
            return await handler(event, {**data, "user": user})
        if isinstance(event, CallbackQuery):
            user: User | None = await User.get_or_none(
                tg_id=event.from_user.id
            )
            return await handler(event, {**data, "user": user})
        if isinstance(event, Update):
            tg_user = (
                (event.message and event.message.from_user)
                or (event.callback_query and event.callback_query.from_user)
                or (event.my_chat_member and event.my_chat_member.from_user)
                or (
                    event.chat_join_request
                    and event.chat_join_request.from_user
                )
            )

            if tg_user:
                user: User | None = await User.get_or_none(tg_id=tg_user.id)
                return await handler(event, {**data, "user": user})
        return await handler(event, data)
