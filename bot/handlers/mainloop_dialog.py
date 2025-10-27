import logging

from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Column, Url
from aiogram_dialog.widgets.text import Format, Const

from bot.filters.confirmed import ConfirmedFilter
from bot.filters.user import UserFilter
from bot.handlers.mainloop.button_handlers import (
    on_i_was_killed,
    on_target_info,
    on_i_killed,
    on_back_to_menu,
    on_get_target,
    confirm_participation,
)
from bot.handlers.mainloop.getters import get_main_menu_info, get_target_info
from bot.misc.states import MainLoop
from db.models import User, Game

logger = logging.getLogger(__name__)

router = Router()


main_menu_dialog = Dialog(
    Window(
        Const("главное меню"),
        Format(
            "\n<b>На вас открыта охота!</b>",
            when="is_hunted",
        ),
        Format(
            "\nВы находитесь в очереди на цель, текущая:\nКоличество потенциальных убийц: <b>{killers_queue_length}</b>\nКоличество потенциальных жертв: <b>{victims_queue_length}</b>",
            when="enqueued",
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
            Button(
                Const("Присоединиться к игре"),
                id="join_game",
                on_click=confirm_participation,
                when="user_not_participating",
            ),
            # Game-related buttons
            Button(
                Const("Получить цель"),
                id="get_target",
                on_click=on_get_target,
                when="should_get_target",
            ),
            Button(
                Const("Меня убили"),
                id="i_was_killed",
                on_click=on_i_was_killed,
                when="is_hunted",
            ),
            Button(
                Format("Ваша цель: {target_name}"),
                id="target_info",
                on_click=on_target_info,
                when="has_target",
            ),
        ),
        getter=get_main_menu_info,
        state=MainLoop.title,
    ),
    Window(
        Const("Информация о цели"),
        Column(
            Url(
                Const("Написать репорт"),
                id="write_report",
                url=Format("{report_link}"),
            ),
            Button(
                Const("Я убил"),
                id="i_killed",
                on_click=on_i_killed,
            ),
            Button(
                Const("Назад"),
                id="back_to_menu",
                on_click=on_back_to_menu,
            ),
        ),
        getter=get_target_info,
        state=MainLoop.target_info,
    ),
)

router.include_router(main_menu_dialog)


@router.message(CommandStart(), ConfirmedFilter(), UserFilter())
async def user_start(
    message: Message,
    dialog_manager: DialogManager,
    bot: Bot,
    user: User,
):
    await dialog_manager.reset_stack()
    game = await Game().filter(end_date=None).first()
    user = await User().get(tg_id=user.tg_id)
    await dialog_manager.start(
        MainLoop.title, data={"user": user, "game": game}
    )
