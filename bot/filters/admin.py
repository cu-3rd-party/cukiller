from aiogram.filters import BaseFilter
from aiogram.types import Message

from db.models import User


class AdminFilter(BaseFilter):
    async def __call__(
        self, message: Message, **kwargs
    ) -> bool:
        telegram_user = message.from_user
        if telegram_user is None:
            return False

        user: User | None = await User.get_or_none(
            telegram_id=telegram_user.id
        )

        return user is not None and user.is_admin


class NotAdminFilter(BaseFilter):
    async def __call__(
        self, message: Message, **kwargs
    ) -> bool:
        telegram_user = message.from_user
        if telegram_user is None:
            return False

        user: User | None = await User.get_or_none(
            telegram_id=telegram_user.id
        )

        return user is None or not user.is_admin
