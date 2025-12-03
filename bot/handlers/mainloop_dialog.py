import logging

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import Dialog, DialogManager, ShowMode, Window
from aiogram_dialog.widgets.kbd import Button, Column, Url, Back
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_dialog.widgets.text import Const, Format

from bot.filters.confirmed import ConfirmedFilter
from bot.filters.user import UserFilter
from bot.handlers.admin import set_admin_commands
from bot.handlers.mainloop.button_handlers import (
    confirm_participation,
    on_get_target,
    on_i_killed,
    on_i_was_killed,
    open_profile,
    open_rules,
    on_reroll,
)
from bot.handlers.mainloop.getters import get_main_menu_info, get_target_info
from db.models import Game, User
from services.states import MainLoop

logger = logging.getLogger(__name__)

router = Router()


main_menu_dialog = Dialog(
    Window(
        Const("Главное меню\n"),
        Format(
            "Ваш текущий рейтинг: <b>{user_rating}</b>\n",
            when="user_rating",
        ),
        Format(
            "Вы запросили подтверждение убийства вас у вашего убийцы, ожидайте",
            when="pending_victim_confirmed",
        ),
        Format(
            "Вы запросили подтверждение вашего убийства у вашей жертвы, ожидайте\n",
            when="pending_kill_confirmed",
        ),
        Format(
            "<b>На вас открыта охота!</b>\n",
            when="is_hunted",
        ),
        Format(
            "Вы находитесь в очереди на цель, текущая:\nКоличество потенциальных убийц: <b>{killers_queue_length}</b>\nКоличество потенциальных жертв: <b>{victims_queue_length}</b>",
            when="enqueued",
        ),
        Column(
            Url(
                Const("Перейти в чат обсуждения"),
                id="discussion_group_link",
                url=Format("{discussion_link}"),
                when="discussion_link",
            ),
            Url(
                Const("Когда следующая игра?"),
                id="next_game_link",
                url=Format("{next_game_link}"),
                when=F["next_game_link"] & ~F["game_running"],
            ),
            Button(
                Const("Присоединиться к игре"),
                id="join_game",
                on_click=confirm_participation,
                when="join_game_button",
            ),
            Button(
                Const("Мой профиль"),
                id="profile",
                on_click=open_profile,
            ),
            Button(
                Const("Правила"),
                id="rules",
                on_click=open_rules,
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
                Format("Ваша цель: {target_name_trimmed}"),
                id="target_info",
                on_click=lambda c, b, m: m.switch_to(MainLoop.target_info),
                when="has_target",
            ),
        ),
        getter=get_main_menu_info,
        state=MainLoop.title,
    ),
    Window(
        Const("Информация о цели"),
        Format("\nИмя: <b>{target_name}</b>\n", when="target_name"),
        Format("{target_advanced_info}", when="target_advanced_info"),
        DynamicMedia("target_photo", when="target_photo"),
        Column(
            Url(
                Const("Написать репорт"),
                id="write_report",
                url=Format("{report_link}"),
                when=F["report_link"],
            ),
            Url(
                Const("Открыть профиль"),
                id="profile",
                url=Format("{target_profile_link}"),
                when=F["target_profile_link"],
            ),
            Button(
                Const("Я сдаюсь"),
                id="reroll",
                on_click=on_reroll,
            ),
            Button(
                Const("Я убил"),
                id="i_killed",
                on_click=on_i_killed,
            ),
            Back(Const("Назад")),
        ),
        getter=get_target_info,
        state=MainLoop.target_info,
    ),
)

router.include_router(main_menu_dialog)


@router.message(CommandStart(), ConfirmedFilter(), UserFilter())
async def confirmed_start(
    message: Message,
    dialog_manager: DialogManager,
    bot: Bot,
    user: User,
):
    if user and user.is_admin:
        await set_admin_commands(bot, message.chat.id)
    await dialog_manager.reset_stack()
    game = await Game().filter(end_date=None).first()
    await dialog_manager.start(
        MainLoop.title,
        data={
            "user_tg_id": message.from_user.id,
            "game_id": (game and game.id) or None,
        },
        show_mode=ShowMode.AUTO,
    )
