from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.text import Format, Const

from tgbot.config import Config
from tgbot.misc.states import UsersStates
from tgbot.models.commands import add_or_create_user
from tgbot.services import admin_chat



router = Router()
user_dialog = Dialog(
    name="user_dialog",
)
router.include_router(user_dialog)


@router.message(CommandStart())
async def user_start(
    message: Message, dialog_manager: DialogManager, bot: Bot, config: Config
):
    if message.from_user.id != message.chat.id:
        await message.answer(
            "этого бота можно использовать только в личных сообщениях"
        )
        return

    user, created = await add_or_create_user(message.from_user.id)
    if created:
        await admin_chat.send_message(
            f"user {user.tg_id} used the bot first time",
            bot=bot,
            config=config,
            tag="start",
        )
        await dialog_manager.start(UsersStates.title_register)
    else:
        await dialog_manager.start(UsersStates.title)
