from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from tgbot.filters.admin import AdminFilter

router = Router()


@router.message(AdminFilter(is_admin=True), CommandStart())
async def admin_start(message: Message):
    await message.reply("Hello, admin!")
