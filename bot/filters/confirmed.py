from aiogram.filters import BaseFilter
from aiogram.types import Message

from db.models import User


class ConfirmedFilter(BaseFilter):
    async def __call__(self, message: Message, user: User, **kwargs) -> bool:
        return user is not None and user.status == "confirmed"


class PendingFilter(BaseFilter):
    async def __call__(self, message: Message, user: User, **kwargs) -> bool:
        return user is not None and user.status == "pending"


class ProfileNonexistentFilter(BaseFilter):
    async def __call__(self, message: Message, user: User, **kwargs) -> bool:
        return user is None or (user is not None and (user.status in {"active", "rejected"}))
