from __future__ import annotations

import logging
import secrets
from datetime import datetime
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram_dialog import Dialog, DialogManager, ShowMode, Window
from aiogram_dialog.widgets.kbd import Button, Cancel
from aiogram_dialog.widgets.text import Const

from services import (
    MainLoop,
    MatchmakingService,
    calculate_leave_penalty,
    compute_exit_cooldown_until,
    log_dialog_action,
    modify_rating,
    settings,
    texts,
)
from services.backend_api import backend_api
from services.states.leave_game import LeaveGame

if TYPE_CHECKING:
    from aiogram.client.bot import Bot
    from aiogram.types import CallbackQuery

    from services.backend_api import Model as Game
    from services.backend_api import Model as Player
    from services.backend_api import UserModel as User

logger = logging.getLogger(__name__)
router = Router()


async def _confirm_pending_victim_event(
    user: User,
    game: Game,
    player: Player,
    now: datetime,
) -> tuple[int, User | None]:
    victim_events = await backend_api.list_kill_events(game_id=game.id, victim_id=user.id, status="pending")
    if not victim_events:
        return 0, None

    primary_event = victim_events[0]
    killer_players = await backend_api.list_players(game_id=game.id, user_id=primary_event.killer_id)
    killer_player = killer_players[0] if killer_players else None
    killer_user = await backend_api.get_user_by_id(primary_event.killer_id)

    if killer_player:
        killer_delta, victim_delta = await modify_rating(killer_player, player)
        penalty = victim_delta
        logger.info(
            "User %s leaves game -> confirmed kill_event %s, killer delta %s, victim delta %s",
            user.id,
            primary_event.id,
            killer_delta,
            victim_delta,
        )
    else:
        penalty = calculate_leave_penalty(player.rating)
        player.rating = max(0, player.rating + penalty)
        await backend_api.update_player(player.id, {"rating": player.rating})
        logger.warning("Предупреждение для %s", primary_event.id)

    primary_event.status = "confirmed"
    primary_event.killer_confirmed = True
    primary_event.victim_confirmed = True
    primary_event.killer_confirmed_at = now
    primary_event.victim_confirmed_at = now
    await backend_api.update_kill_event(
        primary_event.id,
        {
            "status": primary_event.status,
            "killer_confirmed": True,
            "victim_confirmed": True,
            "killer_confirmed_at": now,
            "victim_confirmed_at": now,
        },
    )

    for event in victim_events[1:]:
        event.status = "canceled"
        await backend_api.update_kill_event(event.id, {"status": event.status})

    return penalty, killer_user


async def _cancel_killer_events(user: User, game: Game) -> None:
    killer_events = await backend_api.list_kill_events(game_id=game.id, killer_id=user.id, status="pending")
    for event in killer_events:
        event.status = "canceled"
        await backend_api.update_kill_event(event.id, {"status": event.status})
        logger.info("Отмена kill_event %s для %s", event.id, user.id)


async def _apply_leave_penalty(user: User, game: Game | None, now: datetime) -> tuple[int, User | None]:
    if not game:
        return 0, None

    players = await backend_api.list_players(game_id=game.id, user_id=user.id)
    player = players[0] if players else None
    if not player:
        return 0, None

    penalty, killer_user = await _confirm_pending_victim_event(user, game, player, now)
    await _cancel_killer_events(user, game)

    if penalty == 0:
        penalty = calculate_leave_penalty(player.rating)
        player.rating = max(0, player.rating + penalty)
        await backend_api.update_player(player.id, {"rating": player.rating})

    return penalty, killer_user


async def _notify_killer(bot: Bot, killer: User) -> None:
    try:
        killer_notification = secrets.choice(texts.get_list("leave.killer_notification"))
        await bot.send_message(killer.tg_id, killer_notification)
    except (TelegramForbiddenError, TelegramBadRequest) as exc:
        logger.warning("Не можем оповестить клиллера %s о том что жертва вышла из игры: %s", killer.id, exc)


@log_dialog_action("LEAVE_GAME_CONFIRM")
async def on_confirm_leave(callback: CallbackQuery, button: Button, manager: DialogManager):
    user: User = manager.middleware_data["user"]
    game = await backend_api.get_active_game()
    now = datetime.now(settings.timezone)

    penalty, killer_user = await _apply_leave_penalty(user, game, now)

    user.is_in_game = False
    user.exit_cooldown_until = compute_exit_cooldown_until(now)
    await backend_api.update_user(
        user.id,
        {"is_in_game": False, "exit_cooldown_until": user.exit_cooldown_until},
    )

    if killer_user:
        await _notify_killer(callback.bot, killer_user)

    await MatchmakingService().reset_queues()

    penalty_text = (
        texts.render("leave.penalty_changed", penalty=f"{penalty:+}")
        if penalty
        else texts.get("leave.penalty_unchanged")
    )
    await callback.answer(
        texts.render("leave.result", penalty_text=penalty_text),
        show_alert=True,
    )

    await manager.start(
        MainLoop.title,
        data={"user_tg_id": user.tg_id, "game_id": (game and game.id) or None},
        show_mode=ShowMode.AUTO,
    )


router.include_router(
    Dialog(
        Window(
            Const(texts.get("leave.prompt")),
            Button(Const(texts.get("leave.confirm")), id="confirm", on_click=on_confirm_leave),
            Cancel(Const(texts.get("leave.cancel"))),
            state=LeaveGame.confirm,
        )
    )
)
