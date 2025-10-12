from typing import Optional

from aiogram import Bot

from tgbot.config import Config


async def send_message(
    text: str, bot: Bot, config: Config, tag: Optional[str] = None
):
    await bot.send_message(
        chat_id=config.tg_bot.admin_chat_id,
        text=text if not tag else f"#{tag}\n\n{text}",
        parse_mode="HTML",
    )


async def send_photo(
        photo, caption: str, bot: Bot, tag: Optional[str] = None
):
    await bot.send_photo(chat_id=config.tg_bot)

confirm_profile = [
    Window(
        Format()
    )
]
