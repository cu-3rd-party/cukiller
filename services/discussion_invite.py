import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from services import settings

logger = logging.getLogger(__name__)


async def generate_discussion_invite_link(bot: Bot):
    try:
        settings.discussion_chat_invite_link = await bot.create_chat_invite_link(
            settings.discussion_chat_id, name="bot", creates_join_request=True
        )
    except TelegramBadRequest as e:
        logger.warning("Какая-то ошибка %s", e)
        settings.discussion_chat_invite_link = None


async def revoke_discussion_invite_link(bot: Bot):
    if not settings.discussion_chat_invite_link:
        return
    try:
        await bot.revoke_chat_invite_link(
            settings.discussion_chat_id,
            settings.discussion_chat_invite_link.invite_link,
        )
    except TelegramBadRequest as e:
        logger.warning("Какая-то ошибка: %s", e)
