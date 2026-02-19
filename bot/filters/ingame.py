from aiogram.filters import BaseFilter
from aiogram.types import Message


class InGameFilter(BaseFilter):
    async def __call__(self, message: Message, user: object, **kwargs: object) -> bool:
        return user is not None and user.is_in_game
