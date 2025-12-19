from aiogram.filters import BaseFilter
from aiogram.types import Message

from services import texts


class UserFilter(BaseFilter):
    async def __call__(self, message: Message, **kwargs) -> bool:
        telegram_user = message.from_user

        if telegram_user is None:
            await message.answer(texts.get("common.user_missing"))
            return False

        return True
