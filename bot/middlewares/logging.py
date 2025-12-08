import logging

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

logger = logging.getLogger("user_actions")


class VerboseLoggingMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: TelegramObject, data: dict):
        if isinstance(event, Message):
            logger.info(
                "MESSAGE: user=%s chat=%s text=%r",
                event.from_user.id,
                event.chat.id,
                event.text,
            )

        elif isinstance(event, CallbackQuery):
            logger.info(
                "CALLBACK: user=%s chat=%s data=%r message_id=%s",
                event.from_user.id,
                event.message.chat.id,
                event.data,
                event.message.message_id,
            )

        elif isinstance(event, Update):
            logger.debug("RAW UPDATE: %r", event.dict())

        return await handler(event, data)
