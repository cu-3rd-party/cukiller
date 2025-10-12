import typing

from aiogram.filters import BaseFilter
from aiogram.types import Message

from tgbot.config import Config


class AdminFilter(BaseFilter):
    is_admin: typing.Optional[bool] = None

    def __init__(self, is_admin: typing.Optional[bool] = None):
        self.is_admin = is_admin

    async def __call__(self, message: Message, **kwargs) -> bool:
        if self.is_admin is None:
            return False

        config: Config = kwargs.get("config")

        return (
            message.from_user.id in config.tg_bot.admin_ids
        ) == self.is_admin
