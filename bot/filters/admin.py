from aiogram import Dispatcher
from aiogram.filters import BaseFilter
from aiogram.types import Message

from db.models import User


class AdminFilter(BaseFilter):
    async def __call__(self, message: Message, user: User, **kwargs) -> bool:
        return user is not None and user.is_admin
