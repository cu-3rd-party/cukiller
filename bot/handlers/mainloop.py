import logging

from aiogram import Router, Bot
from aiogram.enums import ContentType
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Group, Column, Url
from aiogram_dialog.widgets.text import Format, Const

from bot.filters.confirmed import ConfirmedFilter
from bot.filters.private_messages import PrivateMessagesFilter
from bot.filters.user import UserFilter
from bot.misc.states import RegisterForm, MainLoop
from bot.services.admin_chat import AdminChatService
from db.models import User
from settings import Settings

logger = logging.getLogger(__name__)

router = Router()


async def get_discussion_link(**kwargs):
    manager = kwargs["dialog_manager"]
    settings: Settings = manager.middleware_data["settings"]
    return {
        "discussion_link": settings.discussion_chat_invite_link.invite_link
    }


main_menu_dialog = Dialog(
    Window(
        Const("главное меню"),
        Column(
            Url(
                Const("Перейти в чат обсуждения"),
                id="discussion_group_link",
                url=Format("{discussion_link}"),
            ),
        ),
        getter=get_discussion_link,
        state=MainLoop.title,
    ),
)

router.include_router(main_menu_dialog)


@router.message(
    CommandStart(), ConfirmedFilter(), PrivateMessagesFilter(), UserFilter()
)
async def user_start(
    message: Message,
    dialog_manager: DialogManager,
    bot: Bot,
):
    await dialog_manager.start(MainLoop.title)
