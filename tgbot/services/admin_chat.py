from aiogram import Bot

from tgbot.config import Config


async def send_admin_chat_message(text: str, bot: Bot, config: Config):
    # отправляем всем админам в лс
    for chat_id in config.tg_bot.admin_ids:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="HTML",
        )
    # дублируем в общую группу
    await bot.send_message(
        chat_id=config.tg_bot.admin_chat_id,
        text=text,
        parse_mode="HTML",
    )
