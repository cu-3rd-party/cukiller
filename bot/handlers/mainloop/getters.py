from aiogram import Dispatcher
from aiogram_dialog import DialogManager

from db.models import Game, User, Player, KillEvent
from services.matchmaking import MatchmakingService
from settings import Settings


async def parse_target_info(
    game: Game | None, user: User, matchmaking: MatchmakingService
):
    player = await Player.filter(user=user, game=game).first()
    if not player:
        return {"no_target": False, "has_target": False, "is_hunted": False}

    victim_event = await KillEvent.filter(
        killer=player, status="pending"
    ).first()
    killer_event = await KillEvent.filter(
        victim=player, status="pending"
    ).first()

    target_name = "Неизвестно"
    if victim_event:
        await victim_event.fetch_related("victim__user")
        target_name = victim_event.victim.user.name

    queued_player = await matchmaking.get_player_by_id(user.tg_id)

    return {
        "has_target": victim_event is not None,
        "no_target": victim_event is None,
        "should_get_target": victim_event is None and queued_player is None,
        "is_hunted": killer_event is not None,
        "target_name": target_name,
    }


async def get_main_menu_info(
    dialog_manager: DialogManager,
    settings: Settings,
    dispatcher: Dispatcher,
    **kwargs,
):
    game: Game = dialog_manager.start_data.get("game")
    user: User = dialog_manager.start_data.get("user")
    matchmaking: MatchmakingService = dispatcher.get("matchmaking")

    return {
        "game": game,
        "user": user,
        "discussion_link": settings.discussion_chat_invite_link.invite_link,
        "next_game_link": settings.game_info_link,
        "game_running": game is not None,
        "game_not_running": game is None,
        "user_not_participating": not user.is_in_game and game is not None,
        "user_participating": user.is_in_game and game is not None,
        "not_enqueued": await matchmaking.get_player_by_id(user.id) is None,
        **await parse_target_info(game, user, matchmaking),
    }


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
