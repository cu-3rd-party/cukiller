from aiogram.filters import BaseFilter
from aiogram.types import Message


class PrivateMessagesFilter(BaseFilter):
    async def __call__(self, message: Message, **kwargs) -> bool:
        if message.from_user.id != message.chat.id:
            await message.answer(
                "Этот бот работает только в личных сообщениях."
            )
            return False

        return True
