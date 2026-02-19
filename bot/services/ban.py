from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl

from services import texts
from services.admin_chat import AdminChatService
from services.backend_api import backend_api
from services.matchmaking import MatchmakingService
from services.settings import settings

if TYPE_CHECKING:
    from services.backend_api import Model as Game
    from services.backend_api import Model as Player
    from services.backend_api import UserModel as User

logger = logging.getLogger(__name__)


async def modify_rating(
    killer_player: Player,
    victim_player: Player,
    killer_k: float = 1.0,
    victim_k: float = 0.0,
    p: float = 1.0,
):
    """After successful kill, update ELO ratings of killer and victim."""
    killer_rating = killer_player.rating
    victim_rating = victim_player.rating

    expected_killer = 1 / (1 + 10 ** ((victim_rating - killer_rating) / settings.ELO_SCALE))
    expected_victim = 1 / (1 + 10 ** ((killer_rating - victim_rating) / settings.ELO_SCALE))

    killer_delta = settings.K_KILLER * (killer_k - expected_killer) * p
    victim_delta = settings.K_VICTIM * (victim_k - expected_victim) * p

    killer_new = killer_rating + killer_delta
    victim_new = victim_rating + victim_delta

    killer_player.rating = round(killer_new)
    victim_player.rating = round(victim_new)

    await backend_api.update_player(killer_player.id, {"rating": killer_player.rating})
    await backend_api.update_player(victim_player.id, {"rating": victim_player.rating})

    if killer_player.rating <= 0:
        if not getattr(killer_player, "user", None):
            killer_player.user = await backend_api.get_user_by_id(killer_player.user_id)
        await ban(killer_player.user, "Отрицательный рейтинг, game over")
    elif victim_player.rating <= 0:
        if not getattr(victim_player, "user", None):
            victim_player.user = await backend_api.get_user_by_id(victim_player.user_id)
        await ban(victim_player.user, "Отрицательный рейтинг, game over")

    return round(killer_delta), round(victim_delta)


def calculate_penalty_at(creation: datetime, at: datetime | None = None) -> float:
    """Penalize reroll based on time passed since KillEvent creation."""
    now = at or datetime.now(settings.timezone)
    end = creation + timedelta(days=7)

    if now >= end:
        return 0.0

    remaining = (end - now).total_seconds()
    total = (end - creation).total_seconds()
    return math.sqrt(remaining / total)


async def recalc_game_ratings(game: Game) -> None:
    """Recalculate all player ratings for the game from scratch (without banned events)."""
    players = await backend_api.list_players(game_id=game.id)
    players_map = {p.user_id: p for p in players}

    # reset ratings to baseline
    for player in players:
        player.rating = 600
    if players:
        await asyncio.gather(*(backend_api.update_player(p.id, {"rating": p.rating}) for p in players))

    # apply all remaining events in chronological order
    events = await backend_api.list_kill_events(game_id=game.id, as_object=True)
    events.sort(key=lambda e: e.created_at)
    for event in events:
        killer_player = players_map.get(event.killer_id)
        victim_player = players_map.get(event.victim_id)
        if not killer_player or not victim_player:
            logger.warning("Player record not found for KillEvent %s", event.id)
            continue

        if event.status == "confirmed":
            await modify_rating(killer_player, victim_player)
        elif event.status == "rejected":
            penalty = calculate_penalty_at(event.created_at, event.updated_at)
            await modify_rating(killer_player, victim_player, 0, 1, penalty)


async def ban(user: User, reason: str) -> str:
    user.status = "banned"
    user.is_in_game = False
    await backend_api.update_user(user.id, {"status": "banned", "is_in_game": False})

    dialog_manager = BgManagerFactoryImpl(router=settings.dispatcher).bg(
        bot=settings.bot,
        user_id=user.tg_id,
        chat_id=user.tg_id,
    )
    await dialog_manager.done()
    await MatchmakingService().reset_queues()

    game = await backend_api.get_active_game()
    removed_events = 0
    if game:
        # находим все килл ивенты, в которых участвовал человек, которого баним
        killer_events = await backend_api.list_kill_events(game_id=game.id, killer_id=user.id)
        victim_events = await backend_api.list_kill_events(game_id=game.id, victim_id=user.id)
        evs = {e.id: e for e in killer_events + victim_events}
        removed_events = len(evs)
        if evs:
            await backend_api.bulk_update_kill_events(evs.keys(), {"status": "canceled"})

        await recalc_game_ratings(game)

    await settings.send_message(
        user.tg_id,
        text=texts.get("ban.user_notification"),
    )
    await AdminChatService(settings.bot).send_message(
        key="discussion",
        text=texts.render("ban.admin_notification", user=user.mention_html(), reason=reason),
    )
    return texts.render("ban.result", removed_events=removed_events)
