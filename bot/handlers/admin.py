from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.filters.admin import AdminFilter

router = Router()


@router.message(AdminFilter, CommandStart())
async def admin_start(message: Message):
    await message.reply("Привет, админ!")
