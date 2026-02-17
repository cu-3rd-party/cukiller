from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

T = TypeVar("T")


class EnvironmentMiddleware(BaseMiddleware):
    def __init__(self, **kwargs: object) -> None:
        super().__init__()
        self.kwargs = kwargs

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[T]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> T:
        data.update(self.kwargs)
        return await handler(event, data)
