import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any, TypeVar

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from db.models import User
from services import normalize_name_component, settings

logger = logging.getLogger(__name__)
T = TypeVar("T")


class RegisterUserMiddleware(BaseMiddleware):
    """Update user details on interaction, with a short-lived cache to avoid extra DB reads."""

    def __init__(self, cache_ttl: int = 300) -> None:
        super().__init__()
        self._user_cache = {}
        self.cache_ttl = cache_ttl

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[T]],
        event: Message,
        data: dict[str, Any],
    ) -> T:
        user = event.from_user

        cache_key = user.id
        cached_data = self._user_cache.get(cache_key)

        if cached_data and cached_data["timestamp"] > datetime.now(settings.timezone) - timedelta(
            seconds=self.cache_ttl
        ):
            data["user_tg_id"] = cached_data["user"].tg_id
            return await handler(event, data)

        db_user = data["user"]

        if db_user:
            if db_user.status == "confirmed":
                self._user_cache[cache_key] = {
                    "user": db_user,
                    "timestamp": datetime.now(settings.timezone),
                }
                data["user_tg_id"] = db_user.tg_id
                return await handler(event, data)

            user_data = {
                "tg_username": user.username,
                "given_name": normalize_name_component(user.first_name),
                "family_name": normalize_name_component(user.last_name),
            }

            if any(getattr(db_user, field) != value for field, value in user_data.items()):
                for field, value in user_data.items():
                    setattr(db_user, field, value)
                # TODO: API CALL

            self._user_cache[cache_key] = {
                "user": db_user,
                "timestamp": datetime.now(settings.timezone),
            }
            data["user_tg_id"] = db_user.tg_id

        else:
            user_data = {
                "tg_username": user.username,
                "given_name": normalize_name_component(user.first_name),
                "family_name": normalize_name_component(user.last_name),
            }

            # TODO: API CALL
            db_user = None

            self._user_cache[cache_key] = {
                "user": db_user,
                "timestamp": datetime.now(settings.timezone),
            }
            data["user_tg_id"] = db_user.tg_id
            logger.info("New user with telegram id: %s", user.id)

        self._clean_cache()
        return await handler(event, data)

    def _clean_cache(self) -> None:
        """Remove expired cache entries"""
        now = datetime.now(settings.timezone)
        expired_keys = [
            key
            for key, value in self._user_cache.items()
            if value["timestamp"] <= now - timedelta(seconds=self.cache_ttl)
        ]
        for key in expired_keys:
            del self._user_cache[key]
