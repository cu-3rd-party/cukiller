import logging

from aiogram import Dispatcher
from aiogram.enums import ContentType
from aiogram_dialog import DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId

from bot.handlers.registration_dialog import COURSE_TYPES
from db.models import Game, User, Player, KillEvent
from services import settings
from services.matchmaking import MatchmakingService

logger = logging.getLogger(__name__)


async def get_user(manager: DialogManager):
    return await User.get(tg_id=manager.start_data.get("user_tg_id"))


async def get_user_and_game(manager: DialogManager):
    """Load user and game from dialog start data."""
    game_id = manager.start_data.get("game_id")
    game = await Game.get(id=game_id) if game_id is not None else None
    return await get_user(manager), game


async def get_pending_events(game: Game, user: User):
    """Return killer_event and victim_event for a user."""
    victim_event = await KillEvent.filter(
        game=game, victim_id=user.id, status="pending"
    ).first()

    killer_event = await KillEvent.filter(
        game=game, killer_id=user.id, status="pending"
    ).first()

    logger.debug(f"Found killer event {killer_event} and {victim_event}")
    return killer_event, victim_event


def get_advanced_info(user: User):
    ret = [f"Тип: {COURSE_TYPES[user.type]}"]
    if user.course_number:
        ret.append(f"Курс: {user.course_number}")
    if user.group_name:
        ret.append(f"Поток: {user.group_name}")
    if user.about_user:
        ret.append(f"О себе: {user.about_user}")
    return "\n".join(ret)


async def extract_target(killer_event: KillEvent | None):
    """Return target info."""
    if not killer_event:
        return "Неизвестно", None, None, None

    await killer_event.fetch_related("victim")
    victim: User = killer_event.victim
    return (
        victim.name,
        victim.tg_id,
        MediaAttachment(
            type=ContentType.PHOTO, file_id=MediaId(file_id=victim.photo)
        )
        if victim.photo != "fastreg"
        else None,
        get_advanced_info(victim),
    )


async def parse_target_info(
    game: Game | None, user: User, matchmaking: MatchmakingService
):
    """Compute target-related info for the main menu or target window."""
    player = await Player.filter(user=user, game=game).first()
    if not player:
        return {"no_target": False, "has_target": False, "is_hunted": False}

    killer_event, victim_event = await get_pending_events(game, user)
    (
        target_name,
        target_tg_id,
        target_photo,
        target_advanced_info,
    ) = await extract_target(killer_event)

    (
        killers_queue_len,
        victims_queue_len,
    ) = await matchmaking.get_queues_length()
    killer_queued, victim_queued = await matchmaking.get_player_by_id(
        user.tg_id
    )

    return {
        "has_target": killer_event is not None
        and not killer_event.killer_confirmed,
        "pending_kill_confirmed": killer_event is not None
        and killer_event.killer_confirmed,
        "no_target": killer_event is None,
        "should_get_target": killer_event is None and not killer_queued,
        "enqueued": killer_queued,
        "not_enqueued": not killer_queued,
        "killers_queue_length": killers_queue_len,
        "victims_queue_length": victims_queue_len,
        "is_hunted": victim_event is not None
        and not victim_event.victim_confirmed,
        "pending_victim_confirmed": victim_event is not None
        and victim_event.victim_confirmed,
        "target_name": target_name,
        "target_photo": target_photo,
        "target_advanced_info": target_advanced_info,
        "target_profile_link": target_tg_id and f"tg://user?id={target_tg_id}",
    }


async def get_user_rating(user: User, game: Game):
    if not game:
        return {}
    player = await Player.filter(game_id=game.id, user_id=user.id).first()
    if not player:
        return {}
    return {
        "user_rating": player.rating,
    }


async def get_main_menu_info(
    dialog_manager: DialogManager, dispatcher: Dispatcher, **kwargs
):
    user, game = await get_user_and_game(dialog_manager)
    matchmaking = MatchmakingService()

    return {
        "discussion_link": settings.discussion_chat_invite_link.invite_link,
        "next_game_link": settings.game_info_link,
        "game_running": game is not None,
        "game_not_running": game is None,
        "user_not_participating": game is not None and not user.is_in_game,
        "user_participating": game is not None and user.is_in_game,
        **await get_user_rating(user, game),
        **await parse_target_info(game, user, matchmaking),
    }


async def get_target_info(
    dialog_manager: DialogManager, dispatcher: Dispatcher, **kwargs
):
    """Getter for target info window."""
    user, game = await get_user_and_game(dialog_manager)
    matchmaking = MatchmakingService()

    return {
        "report_link": settings.report_link,
        **await parse_target_info(game, user, matchmaking),
    }
