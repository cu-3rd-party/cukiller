import logging
import math
from datetime import datetime, timedelta

from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl
from tortoise.expressions import Q

from db.models import User
from db.models import Game, Player, KillEvent
from services import settings
from services.admin_chat import AdminChatService
from services.matchmaking import MatchmakingService


logger = logging.getLogger(__name__)


async def modify_rating(killer_player: Player, victim_player: Player, killer_k=1, victim_k=0, p=1):
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

    await killer_player.save()
    await victim_player.save()

    if killer_player.rating <= 0:
        await killer_player.fetch_related("user")
        await ban(killer_player.user, "Отрицательный рейтинг, game over")
    elif victim_player.rating <= 0:
        await victim_player.fetch_related("user")
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
    players = await Player.filter(game_id=game.id).prefetch_related("user").all()
    players_map = {p.user_id: p for p in players}

    # reset ratings to baseline
    for player in players:
        player.rating = 600
    await Player.bulk_update(players, fields=["rating"])

    # apply all remaining events in chronological order
    events = await KillEvent.filter(game_id=game.id).order_by("created_at").all()
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
    await user.save()

    dialog_manager = BgManagerFactoryImpl(router=settings.dispatcher).bg(
        bot=settings.bot,
        user_id=user.tg_id,
        chat_id=user.tg_id,
    )
    await dialog_manager.done()
    await MatchmakingService().reset_queues()

    game = await Game.get_or_none(end_date=None)
    removed_events = 0
    if game:
        # находим все килл ивенты, в которых участвовал человек, которого баним
        evs: list[KillEvent] = await KillEvent.filter(
            Q(game_id=game.id) & (Q(killer_id=user.id) | Q(victim_id=user.id))
        ).all()
        removed_events = len(evs)
        if evs:
            await KillEvent.filter(id__in=[ev.id for ev in evs]).delete()

        await recalc_game_ratings(game)

    await settings.bot.send_message(
        user.tg_id,
        text="Вы были забанены. Не пытайтесь продолжить взаимодействие с ботом, это бесполезно. Если считаете что это ошибка, то свяжитесь с организатором",
    )
    await AdminChatService(settings.bot).send_message(
        key="discussion", text=f'Игрок {user.mention_html()} был забанен по причине "{reason}"'
    )
    return f"Пользователь забанен, удалено килл-ивентов: {removed_events}"
