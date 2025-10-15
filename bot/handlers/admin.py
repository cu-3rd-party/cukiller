from aiogram import Router, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, BotCommand

from bot.filters.admin import AdminFilter

router = Router()


@router.message(AdminFilter(), CommandStart())
async def admin_start(message: Message, bot: Bot):
    await bot.set_my_commands(commands=[
        BotCommand(command="/start", description="Начать работу с ботом"),
    ])
    await message.reply(text=(
        "Привет, админ!\n"
        "Добавил тебе список команд в менюшку, полюбуйся)\n"
    ))
