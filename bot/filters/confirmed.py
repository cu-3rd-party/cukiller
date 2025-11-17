from typing import Any, Union, Dict

from aiogram.filters import BaseFilter
from aiogram.types import Message

from db.models import User


class ConfirmedFilter(BaseFilter):
    async def __call__(self, message: Message, **kwargs) -> bool:
        telegram_user = message.from_user
        if telegram_user is None:
            return False

        user: User | None = await User().get_or_none(tg_id=telegram_user.id)

        return user is not None and user.status == "confirmed"

class PendingFilter(BaseFilter):
    async def __call__(self, message: Message, **kwargs) -> bool:
        telegram_user = message.from_user
        if telegram_user is None:
            return False

        user: User | None = await User().get_or_none(tg_id=telegram_user.id)

        return user is not None and user.status == "pending"

class ProfileNonexistentFilter(BaseFilter):
    async def __call__(self, message: Message, **kwargs: Any) -> Union[bool, Dict[str, Any]]:
        telegram_user = message.from_user
        if telegram_user is None:
            return False

        user: User | None = await User().get_or_none(tg_id=telegram_user.id)

        return user is not None and (user.status == "active" or user.status == "rejected")
