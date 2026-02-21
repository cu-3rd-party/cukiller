from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.filters import BaseFilter

from services.logging import log_filter

if TYPE_CHECKING:
    from aiogram.types import Message

    from services.backend_api import UserModel as User


class ConfirmedFilter(BaseFilter):
    async def __call__(self, message: Message, user: object, **kwargs: object) -> bool:
        return user is not None and user.status == "confirmed"


class PendingFilter(BaseFilter):
    async def __call__(self, message: Message, user: User, **kwargs: object) -> bool:
        return user is not None and user.status == "pending"


class ProfileNonexistentFilter(BaseFilter):
    @log_filter("ProfileNonexistentFilter")
    async def __call__(self, message: Message, user: User, **kwargs: object) -> bool:
        return user is None or (user is not None and (user.status in {"active", "rejected"}))
