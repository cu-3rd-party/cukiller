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
from db.models import User, Game, Player
from settings import Settings

logger = logging.getLogger(__name__)

router = Router()


async def get_mainmenu_info(dialog_manager: DialogManager, **kwargs):
    settings: Settings = dialog_manager.middleware_data["settings"]
    game = await Game().filter(end_date=None).first()
    tg_id = dialog_manager.event.from_user.id
    user = await User().get(tg_id=tg_id)
    ret = {
        "discussion_link": settings.discussion_chat_invite_link.invite_link,
        "next_game_link": settings.game_info_link,
        "game_running": game is not None,
        "game_not_running": game is None,
    }
    if game is not None and user is not None:
        player = (
            await Player()
            .filter(
                user_id=user.id,
                game_id=game.id,
            )
            .first()
        )
        ret["player_rating"] = (
            player.player_rating
        )  # TODO: добавить проверку что игрок играет
    return ret


main_menu_dialog = Dialog(
    Window(
        Format("<b>Главное меню</b>\n\n"),
        Format(
            "Мой рейтинг: {player_rating}",
            when="game_running",
        ),
        Format(
            "Сейчас игра <b>не идет</b>\n",
            when="game_not_running",
        ),
        Column(
            Url(
                Const("Перейти в чат обсуждения"),
                id="discussion_group_link",
                url=Format("{discussion_link}"),
            ),
            Url(
                Const("Когда следующая игра?"),
                id="next_game_link",
                url=Format("{next_game_link}"),
                when="game_not_running",
            ),
        ),
        getter=get_mainmenu_info,
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
