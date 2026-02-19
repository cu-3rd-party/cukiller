from __future__ import annotations

import logging
import math
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from aiogram import Bot, Router
from aiogram_dialog import Dialog, DialogManager, ShowMode, Window
from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl
from aiogram_dialog.widgets.kbd import Button, Cancel
from aiogram_dialog.widgets.text import Const

from handlers import mainloop_dialog
from services import MainLoop, add_back_to_queues, modify_rating, texts, trim_name
from services.backend_api import backend_api
from services.settings import settings
from services.states.reroll import Reroll

if TYPE_CHECKING:
    from aiogram.types import CallbackQuery

    from services.backend_api import Model as Player
    from services.backend_api import UserModel as User

logger = logging.getLogger(__name__)

router = Router()


async def notify_player(user: User, bot: Bot, manager: DialogManager, delta: float):
    await bot.send_message(
        chat_id=user.tg_id,
        text=texts.render(
            "reroll.player_notified",
            score_direction=texts.get("score.lost") if delta < 0 else texts.get("score.gained"),
            points=abs(round(delta)),
        ),
    )

    dialog_manager = BgManagerFactoryImpl(router=mainloop_dialog.router).bg(
        bot=bot,
        user_id=user.tg_id,
        chat_id=user.tg_id,
    )
    await dialog_manager.done()
    await dialog_manager.start(
        MainLoop.title,
        data={**manager.start_data, "user_tg_id": user.tg_id},
        show_mode=ShowMode.AUTO,
    )


@dataclass(frozen=True, slots=True)
class RerollNotification:
    killer: User
    victim: User
    killer_player: Player
    victim_player: Player
    killer_delta: float
    victim_delta: float


async def notify_chat(bot: Bot, notification: RerollNotification) -> None:
    reason = secrets.choice(texts.get_list("reroll.fail_reasons"))
    killer_display = notification.killer.full_name or notification.killer.tg_username or texts.get("common.unknown")
    victim_display = notification.victim.full_name or notification.victim.tg_username or texts.get("common.unknown")
    discussion_chat = await backend_api.get_chat_by_key("discussion")
    if not discussion_chat:
        logger.warning("Discussion chat not configured")
        return
    await bot.send_message(
        chat_id=discussion_chat.chat_id,
        text=texts.render(
            "reroll.chat_notified",
            killer=notification.killer.mention_html(),
            victim=notification.victim.mention_html(),
            reason=reason,
            killer_name=trim_name(killer_display, 25),
            killer_rating=notification.killer_player.rating,
            killer_delta=f"{'+' if notification.killer_delta >= 0 else '-'}{abs(round(notification.killer_delta))}",
            victim_name=trim_name(victim_display, 25),
            victim_rating=notification.victim_player.rating,
            victim_delta=f"{'+' if notification.victim_delta >= 0 else '-'}{abs(round(notification.victim_delta))}",
        ),
    )


def calculate_penalty(creation: datetime) -> float:
    now = datetime.now(settings.timezone)

    # конечная точка (creation + 7 дней)
    end = creation + timedelta(days=7)

    # уже прошло 7+ дней → штраф 0
    if now >= end:
        return 0.0

    # сколько секунд осталось до конца окна
    remaining = (end - now).total_seconds()
    total = (end - creation).total_seconds()

    # итоговая формула: sqrt(remaining / total)
    return math.sqrt(remaining / total)


async def on_confirm_reroll(c: CallbackQuery, b: Button, m: DialogManager):
    requester_user: User = m.middleware_data["user"]
    killer_players = await backend_api.list_players(game_id=m.start_data.get("game_id"), user_id=requester_user.id)
    killer_player = killer_players[0] if killer_players else None
    events = await backend_api.list_kill_events(
        game_id=m.start_data.get("game_id"),
        killer_id=requester_user.id,
        status="pending",
    )
    kill_event = events[0] if events else None
    if not kill_event or not killer_player:
        return
    kill_event.status = "rejected"
    await backend_api.update_kill_event(kill_event.id, {"status": kill_event.status})

    victim_players = await backend_api.list_players(game_id=kill_event.game_id, user_id=kill_event.victim_id)
    victim_player = victim_players[0] if victim_players else None
    if not victim_player:
        return
    if killer_player:
        killer_player.user = kill_event.killer
    if victim_player:
        victim_player.user = kill_event.victim

    logger.debug(kill_event)
    killer_delta, victim_delta = await modify_rating(
        killer_player, victim_player, 0, 1, calculate_penalty(kill_event.created_at)
    )
    await add_back_to_queues(kill_event.killer, kill_event.victim, killer_player, victim_player)
    await notify_chat(
        c.bot,
        RerollNotification(
            killer=kill_event.killer,
            victim=kill_event.victim,
            killer_player=killer_player,
            victim_player=victim_player,
            killer_delta=killer_delta,
            victim_delta=victim_delta,
        ),
    )
    await notify_player(kill_event.killer, c.bot, m, killer_delta)
    await notify_player(kill_event.victim, c.bot, m, victim_delta)


router.include_router(
    Dialog(
        Window(
            Const(texts.get("reroll.prompt")),
            Button(Const(texts.get("reroll.confirm")), id="confirm", on_click=on_confirm_reroll),
            Cancel(Const(texts.get("reroll.cancel"))),
            state=Reroll.confirm,
        )
    )
)
