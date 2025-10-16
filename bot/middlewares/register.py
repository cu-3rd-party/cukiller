import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

from db.models import User


logger = logging.getLogger(__name__)


class RegisterUserMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ):
        user = event.from_user
        user, created = await User().update_or_create(
            tg_id=user.id,
            defaults={
                "tg_username": user.username,
                "given_name": user.first_name,
                "family_name": user.last_name,
            },
        )
        data["user"] = user
        if created:
            logger.info(f"New user with telegram id: {user.tg_id}")

        return await handler(event, data)
