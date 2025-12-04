import logging
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from db.models import User
from services import settings

logger = logging.getLogger(__name__)


class RegisterUserMiddleware(BaseMiddleware):
    """
    Используется, чтоб дополнять информацию о пользователе, когда он с нами взаимодействует.

    Важно: оно не должно при каждом взаимодействии делать множество запросов в базу данных, также как
    и не должно обновлять информацию после подтверждения профиля пользователя. В кеше должно храниться
    ключ: telegram_id юзера
    значение: telegram_username и имя фамилия в случае если status пользователя не является confirmed, если профиль
            пользователя подтвержден, то мы не должны никак его менять
    """

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
                "name": " ".join(
                    (
                        user.first_name if user.first_name else "",
                        user.last_name if user.last_name else "",
                    )
                ).strip(),
            }

            if db_user.tg_username != user.username or db_user.name != user_data["name"]:
                for field, value in user_data.items():
                    setattr(db_user, field, value)
                await db_user.save()

            self._user_cache[cache_key] = {
                "user": db_user,
                "timestamp": datetime.now(settings.timezone),
            }
            data["user_tg_id"] = db_user.tg_id

        else:
            user_data = {
                "tg_username": user.username,
                "name": " ".join(
                    (
                        user.first_name if user.first_name else "",
                        user.last_name if user.last_name else "",
                    )
                ).strip(),
            }

            db_user = await User().create(tg_id=user.id, **user_data)

            self._user_cache[cache_key] = {
                "user": db_user,
                "timestamp": datetime.now(settings.timezone),
            }
            data["user_tg_id"] = db_user.tg_id
            logger.info(f"New user with telegram id: {user.id}")

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
