from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class EnvironmentMiddleware(BaseMiddleware):
    def __init__(self, **kwargs) -> None:
        super().__init__()
        self.kwargs = kwargs

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ):
        data.update(self.kwargs)
        return await handler(event, data)
