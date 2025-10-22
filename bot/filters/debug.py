from aiogram.filters import BaseFilter
from aiogram.types import Message

from settings import Settings


class DebugFilter(BaseFilter):
    async def __call__(
        self, message: Message, settings: Settings, **kwargs
    ) -> bool:
        return settings.debug
