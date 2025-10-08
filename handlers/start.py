from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

import db

router = Router()


@router.message(CommandStart())
async def start_command(message: Message) -> None:
    db.try_register_user(message.chat.id, message.from_user.id, message.from_user.username)
    await message.answer(text="Hello, world!")
