from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message

from services import texts


class PrivateMessagesMiddleware(BaseMiddleware):
    def __init__(self, *exclusions: list[str]) -> None:
        self.exclusions = exclusions

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Callable[[Message, dict[str, Any]], Awaitable[Any]]:
        if event.text in self.exclusions:
            return await handler(event, data)
        if event.from_user.id != event.chat.id:
            await event.answer(texts.get("common.private_only"))
            return None

        return await handler(event, data)
