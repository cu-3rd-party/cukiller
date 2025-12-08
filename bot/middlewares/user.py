import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, types
from aiogram.types import TelegramObject

from services.events import extract_user
from services.user import get_or_create_user

logger = logging.getLogger(__name__)


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]]:
        tg_user: types.User = extract_user(event)

        if tg_user and not tg_user.is_bot:
            user, created = await get_or_create_user(tg_user)
            if created:
                logger.info("New user created with id: %d and username %s", user.tg_id, user.tg_username)
            if user.status == "banned":
                logger.warning("%d is banned but still tried to interact with bot", user.tg_id)
                return None
            return await handler(event, {**data, "user": user})
        return await handler(event, data)
