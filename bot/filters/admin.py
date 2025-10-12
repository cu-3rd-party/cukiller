from aiogram.filters import BaseFilter
from aiogram.types import Message

from settings import Settings


# TODO(Serafim): Перписать фильтр на использование БД
class AdminFilter(BaseFilter):
    def __init__(self, *, is_admin: bool = True) -> None:
        self.is_admin = is_admin

    async def __call__(
        self, message: Message, config: Settings, **kwargs
    ) -> bool:
        if not self.is_admin:
            return True

        telegram_user = message.from_user
        if telegram_user is None:
            return False

        if not config.admin_ids:
            return True

        return telegram_user.id in config.admin_ids
