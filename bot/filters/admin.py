from aiogram.filters import BaseFilter
from aiogram.types import Message

from services import log_filter


class AdminFilter(BaseFilter):
    @log_filter("AdminFilter")
    async def __call__(self, message: Message, user: object, **kwargs: object) -> bool:
        return user is not None and user.is_admin
