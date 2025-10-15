from aiogram.filters import BaseFilter
from aiogram.types import Message


class UserFilter(BaseFilter):
    async def __call__(self, message: Message, **kwargs) -> bool:
        telegram_user = message.from_user

        if telegram_user is None:
            await message.answer("Не удалось определить пользователя.")
            return False

        return True
