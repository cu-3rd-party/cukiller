from aiogram.filters import BaseFilter
from aiogram.types import Message

from db.models import User


class InGameFilter(BaseFilter):
    async def __call__(self, message: Message, **kwargs) -> bool:
        telegram_user = message.from_user
        if telegram_user is None:
            return False

        user: User | None = await User().get_or_none(tg_id=telegram_user.id)

        return user is not None and user.is_in_game
