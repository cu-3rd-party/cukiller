from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram_dialog import Dialog, DialogManager, ShowMode, Window
from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl
from aiogram_dialog.widgets.kbd import Button, Column
from aiogram_dialog.widgets.text import Const

from handlers import mainloop_dialog
from services import (
    MainLoop,
    MatchmakingService,
    format_exit_cooldown,
    is_exit_cooldown_active,
    log_dialog_action,
    settings,
    texts,
)
from services.backend_api import backend_api
from services.states.participation import ParticipationForm

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery

    from services.backend_api import UserModel as User

logger = logging.getLogger(__name__)

router = Router()


@log_dialog_action("CONFIRM_PARTICIPATION")
async def confirm_participation(callback: CallbackQuery, button: Button, manager: DialogManager):
    game = await backend_api.get_active_game()
    if not game:
        await manager.done()
        return
    user: User = manager.middleware_data["user"]
    matchmaking: MatchmakingService = MatchmakingService()
    if is_exit_cooldown_active(user):
        cooldown_until = format_exit_cooldown(user)
        await callback.answer(
            texts.render("common.exit_cooldown", until=cooldown_until),
            show_alert=True,
        )
        await manager.done()
        return
    user.is_in_game = True
    player = await backend_api.create_player(
        {"user_id": user.id, "game_id": game.id, "rating": settings.DEFAULT_RATING}
    )
    logger.debug(
        "Created player for user %s game %s with id %s",
        user.id,
        game.id,
        player.id,
    )
    await backend_api.update_user(user.id, {"is_in_game": True})
    await manager.done()
    await manager.reset_stack()
    user_dialog_manager = BgManagerFactoryImpl(router=mainloop_dialog.router).bg(
        bot=manager.event.bot,
        user_id=user.tg_id,
        chat_id=user.tg_id,
    )
    player_data = {
        "tg_id": user.tg_id,
        "rating": player.rating,
        "type": user.type,
        "course_number": user.course_number,
        "group_name": user.group_name,
    }
    await matchmaking.add_player_to_queues(player_id=user.tg_id, player_data=player_data)
    await user_dialog_manager.start(
        MainLoop.title,
        data={"user_tg_id": user.tg_id, "game_id": (game and game.id) or None},
        show_mode=ShowMode.AUTO,
    )


router.include_router(
    Dialog(
        Window(
            Const(texts.get("participation.prompt")),
            Column(
                Button(
                    Const(texts.get("participation.confirm_yes")),
                    id="confirm",
                    on_click=confirm_participation,
                ),
                Button(
                    Const(texts.get("participation.confirm_no")),
                    id="deny",
                    on_click=lambda c, b, m: m.done(),
                ),
            ),
            state=ParticipationForm.confirm,
        ),
    )
)
