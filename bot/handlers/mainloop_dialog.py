import logging

from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import Dialog, DialogManager, ShowMode, Window
from aiogram_dialog.widgets.kbd import Back, Button, Column, Url
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
    on_leave_game,
    on_reroll,
    open_profile,
    open_rules,
    open_gameplay_rules,
    open_profile_rules,
)
from bot.handlers.mainloop.getters import get_main_menu_info, get_target_info
from db.models import Game, User
from services import texts
from services.states import MainLoop

logger = logging.getLogger(__name__)

router = Router()


main_menu_dialog = Dialog(
    Window(
        Const(texts.get("main_menu.title")),
        Format(
            texts.get("main_menu.rating"),
            when="user_rating",
        ),
        Format(
            texts.get("main_menu.exit_cooldown"),
            when="exit_cooldown_until",
        ),
        Format(
            texts.get("main_menu.waiting_victim_confirm"),
            when="pending_victim_confirmed",
        ),
        Format(
            texts.get("main_menu.waiting_kill_confirm"),
            when="pending_kill_confirmed",
        ),
        Format(
            texts.get("main_menu.queue_stats"),
            when="enqueued",
        ),
        Column(
            Url(
                Const(texts.get("buttons.discussion")),
                id="discussion_group_link",
                url=Format("{discussion_link}"),
                when="discussion_link",
            ),
            Url(
                Const(texts.get("buttons.next_game")),
                id="next_game_link",
                url=Format("{next_game_link}"),
                when=F["next_game_link"] & ~F["game_running"],
            ),
            Button(
                Const(texts.get("buttons.join_game")),
                id="join_game",
                on_click=confirm_participation,
                when="join_game_button",
            ),
            Button(
                Const(texts.get("buttons.leave_game")),
                id="leave_game",
                on_click=on_leave_game,
                when="user_is_in_game",
            ),
            Button(
                Const(texts.get("buttons.profile")),
                id="profile",
                on_click=open_profile,
            ),
            Button(
                Const(texts.get("buttons.rules")),
                id="rules",
                on_click=open_rules,
            ),
            Button(
                Const(texts.get("buttons.rules_gameplay")),
                id="rules_gameplay",
                on_click=open_gameplay_rules,
            ),
            Button(
                Const(texts.get("buttons.rules_profile")),
                id="rules_profile",
                on_click=open_profile_rules,
            ),
            # Game-related buttons
            Button(
                Const(texts.get("buttons.get_target")),
                id="get_target",
                on_click=on_get_target,
                when="should_get_target",
            ),
            Button(
                Const(texts.get("buttons.was_killed")),
                id="i_was_killed",
                on_click=on_i_was_killed,
                when="user_is_in_game",
            ),
            Button(
                Format(texts.get("main_menu.target_label")),
                id="target_info",
                on_click=lambda c, b, m: m.switch_to(MainLoop.target_info),
                when="has_target",
            ),
        ),
        getter=get_main_menu_info,
        state=MainLoop.title,
    ),
    Window(
        Const(texts.get("main_menu.target_info_title")),
        Format(texts.get("main_menu.target_name"), when="target_name"),
        Format(texts.get("main_menu.target_advanced_info"), when="target_advanced_info"),
        DynamicMedia("target_photo", when="target_photo"),
        Column(
            Url(
                Const(texts.get("buttons.write_report")),
                id="write_report",
                url=Format("{report_link}"),
                when=F["report_link"],
            ),
            Url(
                Const(texts.get("buttons.open_profile")),
                id="profile",
                url=Format("{target_profile_link}"),
                when=F["target_profile_link"],
            ),
            Button(
                Const(texts.get("buttons.surrender")),
                id="reroll",
                on_click=on_reroll,
            ),
            Button(
                Const(texts.get("buttons.i_killed")),
                id="i_killed",
                on_click=on_i_killed,
            ),
            Back(Const(texts.get("buttons.back"))),
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

    if user.family_name_required:
        await message.answer(texts.get("profile.family_name_required"))
        from services.states.my_profile import MyProfile

        await dialog_manager.start(
            MyProfile.profile,
            data={
                "user_tg_id": message.from_user.id,
            },
            show_mode=ShowMode.AUTO,
        )
        return

    game = await Game().filter(end_date=None).first()
    await dialog_manager.start(
        MainLoop.title,
        data={
            "user_tg_id": message.from_user.id,
            "game_id": (game and game.id) or None,
        },
        show_mode=ShowMode.AUTO,
    )
