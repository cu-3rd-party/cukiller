import logging

from aiogram import Dispatcher
from aiogram_dialog import DialogManager

from db.models import Game, User, Player, KillEvent
from services.matchmaking import MatchmakingService, QueuePlayer
from settings import Settings


logger = logging.getLogger(__name__)


async def parse_target_info(
    game: Game | None, user: User, matchmaking: MatchmakingService
):
    player = await Player.filter(user=user, game=game).first()
    if not player:
        return {"no_target": False, "has_target": False, "is_hunted": False}

    victim_event = await KillEvent.filter(
        game=game, victim_id=user.id, status="pending"
    ).first()
    killer_event = await KillEvent.filter(
        game=game, killer_id=user.id, status="pending"
    ).first()
    logger.debug(f"Found killer event {killer_event} and {victim_event}")

    target_name = "Неизвестно"
    if killer_event:
        await killer_event.fetch_related("victim")
        target_name = killer_event.victim.name

    (
        killers_queue,
        victims_queue,
    ) = await matchmaking.get_queues_length()
    killer_queued, victim_queued = await matchmaking.get_player_by_id(
        user.tg_id
    )

    ret = {
        "has_target": killer_event is not None,
        "no_target": killer_event is None,
        "should_get_target": killer_event is None and not killer_queued,
        "enqueued": killer_queued,
        "not_enqueued": not killer_queued,
        "killers_queue_length": killers_queue,
        "victims_queue_length": victims_queue,
        "is_hunted": victim_event is not None,
        "target_name": target_name,
    }
    logger.debug(ret)
    return ret


async def get_main_menu_info(
    dialog_manager: DialogManager,
    settings: Settings,
    dispatcher: Dispatcher,
    **kwargs,
):
    game: Game = dialog_manager.start_data.get("game")
    user: User = dialog_manager.start_data.get("user")
    matchmaking: MatchmakingService = dispatcher.get("matchmaking")

    ret = {
        "game": game,
        "user": user,
        "discussion_link": settings.discussion_chat_invite_link.invite_link,
        "next_game_link": settings.game_info_link,
        "game_running": game is not None,
        "game_not_running": game is None,
        "user_not_participating": not user.is_in_game and game is not None,
        "user_participating": user.is_in_game and game is not None,
        **await parse_target_info(game, user, matchmaking),
    }
    logger.debug(ret)
    return ret


async def get_target_info(
    dialog_manager: DialogManager, dispatcher: Dispatcher, **kwargs
):
    """Getter for target info window"""
    settings: Settings = dialog_manager.middleware_data["settings"]
    game = dialog_manager.start_data.get("game")
    matchmaking: MatchmakingService = dispatcher.get("matchmaking")

    return {
        "report_link": settings.report_link,
        **await parse_target_info(
            game, dialog_manager.start_data["user"], matchmaking
        ),
    }
