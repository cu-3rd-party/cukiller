from aiogram import Router, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message

from tgbot.config import Config
from tgbot.filters.admin import AdminFilter

router = Router()


@router.message(AdminFilter(is_admin=True), CommandStart())
async def admin_start(message: Message, config: Config):
    await message.reply("Hello, admin!")
