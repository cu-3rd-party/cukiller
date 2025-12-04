from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message


class PrivateMessagesMiddleware(BaseMiddleware):
    async def __init__(self, *exclusions) -> None:
        self.exclusions = exclusions
    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if event.text in self.exclusions:
            return await handler(event, data)
        if event.from_user.id != event.chat.id:
            await event.answer("Этот бот работает только в личных сообщениях.")
            return None

        return await handler(event, data)
