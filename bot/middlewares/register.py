import logging
from collections.abc import Awaitable, Callable
from typing import Any
from datetime import datetime, timedelta

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

from db.models import User

logger = logging.getLogger(__name__)


class RegisterUserMiddleware(BaseMiddleware):
    def __init__(self, cache_ttl: int = 300) -> None:
        super().__init__()
        self._user_cache = {}
        self.cache_ttl = cache_ttl

    async def __call__(
            self,
            handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: dict[str, Any],
    ):
        user = event.from_user

        cache_key = user.id
        cached_data = self._user_cache.get(cache_key)

        if cached_data and cached_data['timestamp'] > datetime.now() - timedelta(seconds=self.cache_ttl):
            data["user"] = cached_data['user']
            return await handler(event, data)

        user_data = {
            "tg_username": user.username,
            "given_name": user.first_name,
            "family_name": user.last_name,
        }

        db_user, created = await User().update_or_create(
            tg_id=user.id,
            defaults=user_data,
        )

        self._user_cache[cache_key] = {
            'user': db_user,
            'timestamp': datetime.now()
        }

        self._clean_cache()

        data["user"] = db_user
        if created:
            logger.info(f"New user with telegram id: {user.id}")

        return await handler(event, data)

    def _clean_cache(self):
        """Remove expired cache entries"""
        now = datetime.now()
        expired_keys = [
            key for key, value in self._user_cache.items()
            if value['timestamp'] <= now - timedelta(seconds=self.cache_ttl)
        ]
        for key in expired_keys:
            del self._user_cache[key]