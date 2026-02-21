import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from services.metrics import metrics

logger = logging.getLogger("user_actions")
T = TypeVar("T")


class VerboseLoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[T]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> T:
        if isinstance(event, Message):
            metrics.increment_message_received("message")
            logger.info(
                "MESSAGE: user=%s chat=%s text=%r",
                event.from_user.id,
                event.chat.id,
                event.text,
            )
            if event.text and event.text.startswith("/"):
                command = event.text.split()[0].lstrip("/")
                if command:
                    metrics.increment_command_executed(command)

        elif isinstance(event, CallbackQuery):
            metrics.increment_message_received("callback_query")
            logger.info(
                "CALLBACK: user=%s chat=%s data=%r message_id=%s",
                event.from_user.id,
                event.message.chat.id,
                event.data,
                event.message.message_id,
            )

        elif isinstance(event, Update):
            metrics.increment_message_received("update")
            logger.debug("RAW UPDATE: %r", event.dict())
        else:
            metrics.increment_message_received("other")

        return await handler(event, data)
