import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from services import normalize_name_component
from services.backend_api import backend_api

logger = logging.getLogger(__name__)
T = TypeVar("T")


class RegisterUserMiddleware(BaseMiddleware):
    """Update user details on interaction, always fetching from backend."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[T]],
        event: Message,
        data: dict[str, Any],
    ) -> T:
        user = event.from_user

        db_user = await backend_api.get_user_by_tg_id(user.id)

        if db_user:
            if db_user.status == "confirmed":
                data["user"] = db_user
                data["user_tg_id"] = db_user.tg_id
                return await handler(event, data)

            user_data = {
                "tg_username": user.username,
            }

            if any(getattr(db_user, field) != value for field, value in user_data.items()):
                for field, value in user_data.items():
                    setattr(db_user, field, value)
                updated = await backend_api.update_user_by_tg_id(db_user.tg_id, user_data)
                if updated:
                    db_user = updated

            data["user"] = db_user
            data["user_tg_id"] = db_user.tg_id

        else:
            user_data = {
                "tg_username": user.username,
                "given_name": normalize_name_component(user.first_name),
                "family_name": normalize_name_component(user.last_name),
            }

            db_user, _ = await backend_api.get_or_create_user(
                {
                    "tg_id": user.id,
                    "tg_username": user.username,
                    "given_name": user_data["given_name"],
                    "family_name": user_data["family_name"],
                }
            )

            data["user"] = db_user
            data["user_tg_id"] = db_user.tg_id
            logger.info("New user with telegram id: %s", user.id)

        return await handler(event, data)
