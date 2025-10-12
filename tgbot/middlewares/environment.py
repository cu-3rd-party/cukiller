from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject


class EnvironmentMiddleware(BaseMiddleware):
    def __init__(self, **kwargs):
        super().__init__()
        self.kwargs = kwargs

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        data.update(self.kwargs)
        return await handler(event, data)
