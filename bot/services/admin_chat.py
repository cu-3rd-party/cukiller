from typing import Optional

from aiogram import Bot

from settings import Settings


async def send_message(
    text: str,
    bot: Bot,
    *,
    config: Settings,
    tag: Optional[str] = None,
) -> None:
    """Send a message to the admin chat if it is configured."""

    if not config.admin_chat_id:
        return

    body = text if not tag else f"#{tag}\n\n{text}"
    await bot.send_message(
        chat_id=config.admin_chat_id,
        text=body,
        parse_mode="HTML",
    )
