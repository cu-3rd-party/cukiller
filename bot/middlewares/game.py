from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from services.backend_api import backend_api

T = TypeVar("T")


class GameMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[T]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> T:
        game = await backend_api.get_active_game()
        return await handler(event, {**data, "game": game})
