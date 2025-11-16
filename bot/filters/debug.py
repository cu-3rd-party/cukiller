from aiogram.filters import BaseFilter
from aiogram.types import Message

from settings import settings


class DebugFilter(BaseFilter):
    async def __call__(self, message: Message, **kwargs) -> bool:
        return settings.debug
