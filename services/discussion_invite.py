from aiogram import Bot

from settings import Settings


async def generate_discussion_invite_link(bot: Bot, settings: Settings):
    settings.discussion_chat_invite_link = await bot.create_chat_invite_link(
        settings.discussion_chat_id, name="bot", creates_join_request=True
    )
