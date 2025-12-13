import logging
from datetime import datetime

from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, ShowMode, Window
from aiogram_dialog.widgets.kbd import Button, Cancel
from aiogram_dialog.widgets.text import Const

from bot.handlers import mainloop_dialog
from db.models import Game, KillEvent, Player, User
from services import settings
from services.kills_confirmation import modify_rating
from services.logging import log_dialog_action
from services.matchmaking import MatchmakingService
from services.states import MainLoop
from services.states.leave_game import LeaveGame
from services.user_exit import calculate_leave_penalty, compute_exit_cooldown_until

logger = logging.getLogger(__name__)
router = Router()


async def _confirm_pending_victim_event(
    user: User,
    game: Game,
    player: Player,
    now: datetime,
) -> tuple[int, User | None]:
    victim_events = await KillEvent.filter(game_id=game.id, victim_id=user.id, status="pending").prefetch_related("killer")
    if not victim_events:
        return 0, None

    primary_event = victim_events[0]
    killer_player = await Player.get_or_none(game_id=game.id, user_id=primary_event.killer_id)
    killer_user = primary_event.killer if hasattr(primary_event, "killer") else await User.get(id=primary_event.killer_id)

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
        await player.save(update_fields=["rating"])
        logger.warning("Предупреждение для %s", primary_event.id)

    primary_event.status = "confirmed"
    primary_event.killer_confirmed = True
    primary_event.victim_confirmed = True
    primary_event.killer_confirmed_at = now
    primary_event.victim_confirmed_at = now
    await primary_event.save()

    for event in victim_events[1:]:
        event.status = "canceled"
        await event.save()

    return penalty, killer_user


async def _cancel_killer_events(user: User, game: Game):
    killer_events = await KillEvent.filter(game_id=game.id, killer_id=user.id, status="pending").all()
    for event in killer_events:
        event.status = "canceled"
        await event.save()
        logger.info("Отмена kill_event %s для %s", event.id, user.id)


async def _apply_leave_penalty(user: User, game: Game | None, now: datetime) -> tuple[int, User | None]:
    if not game:
        return 0, None

    player = await Player.get_or_none(user_id=user.id, game_id=game.id)
    if not player:
        return 0, None

    penalty, killer_user = await _confirm_pending_victim_event(user, game, player, now)
    await _cancel_killer_events(user, game)

    if penalty == 0:
        penalty = calculate_leave_penalty(player.rating)
        player.rating = max(0, player.rating + penalty)
        await player.save(update_fields=["rating"])

    return penalty, killer_user


async def _notify_killer(bot, killer: User):
    try:
        await bot.send_message(
            killer.tg_id,
            "Убийство без жертв, ваша цель вышла из игры. Убийство засчитано, ищем новые цели...",
        )
    except Exception as exc:
        logger.warning("Не можем оповестить клиллера %s о том что жертва вышла из игры: %s", killer.id, exc)


@log_dialog_action("LEAVE_GAME_CONFIRM")
async def on_confirm_leave(callback: CallbackQuery, button: Button, manager: DialogManager):
    user: User = manager.middleware_data["user"]
    game: Game | None = manager.middleware_data.get("game") or await Game.filter(end_date=None).first()
    now = datetime.now(settings.timezone)

    penalty, killer_user = await _apply_leave_penalty(user, game, now)

    user.is_in_game = False
    user.exit_cooldown_until = compute_exit_cooldown_until(now)
    await user.save(update_fields=["is_in_game", "exit_cooldown_until"])

    if killer_user:
        await _notify_killer(callback.bot, killer_user)

    await MatchmakingService().reset_queues()

    penalty_text = f"Рейтинг изменился на {penalty:+}" if penalty else "Рейтинг не изменился"
    await callback.answer(
        f"Вы вышли из игры и стали NPC с богатым прошлым. {penalty_text}\nВернуться можно после недели ожидания",
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
            Const("Вы уверены что хотите выйти?\nВы потеряете рейтинг как будто вас убили!"),
            Button(Const("Подтвердить"), id="confirm", on_click=on_confirm_leave),
            Cancel(Const("Отменить")),
            state=LeaveGame.confirm,
        )
    )
)
