import logging
import secrets
from datetime import datetime

from aiogram import Router
from aiogram.client.bot import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, ShowMode, Window
from aiogram_dialog.widgets.kbd import Button, Cancel
from aiogram_dialog.widgets.text import Const

from db.models import Game, KillEvent, Player, User
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
from services.states.leave_game import LeaveGame

logger = logging.getLogger(__name__)
router = Router()


async def _confirm_pending_victim_event(
    user: User,
    game: Game,
    player: Player,
    now: datetime,
) -> tuple[int, User | None]:
    # TODO: API CALL
    victim_events = []
    if not victim_events:
        return 0, None

    primary_event = victim_events[0]
    # TODO: API CALL
    killer_player = None
    killer_user = None

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
        # TODO: API CALL
        logger.warning("Предупреждение для %s", primary_event.id)

    primary_event.status = "confirmed"
    primary_event.killer_confirmed = True
    primary_event.victim_confirmed = True
    primary_event.killer_confirmed_at = now
    primary_event.victim_confirmed_at = now
    # TODO: API CALL

    for event in victim_events[1:]:
        event.status = "canceled"
        # TODO: API CALL

    return penalty, killer_user


async def _cancel_killer_events(user: User, game: Game) -> None:
    # TODO: API CALL
    killer_events = None
    for event in killer_events:
        event.status = "canceled"
        # TODO: API CALL
        logger.info("Отмена kill_event %s для %s", event.id, user.id)


async def _apply_leave_penalty(user: User, game: Game | None, now: datetime) -> tuple[int, User | None]:
    if not game:
        return 0, None

    # TODO: API CALL
    player = None
    if not player:
        return 0, None

    penalty, killer_user = await _confirm_pending_victim_event(user, game, player, now)
    await _cancel_killer_events(user, game)

    if penalty == 0:
        penalty = calculate_leave_penalty(player.rating)
        player.rating = max(0, player.rating + penalty)
        # TODO: API CALL

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
    # TODO: API CALL
    game: Game | None = None
    now = datetime.now(settings.timezone)

    penalty, killer_user = await _apply_leave_penalty(user, game, now)

    user.is_in_game = False
    user.exit_cooldown_until = compute_exit_cooldown_until(now)
    # TODO: API CALL

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
