import logging

import requests
from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl
from aiogram_dialog.widgets.kbd import Button

from bot.handlers import participation
from bot.handlers.kills_confirmation import (
    ConfirmKillVictim,
    ConfirmKillKiller,
)
from bot.misc.states import MainLoop
from bot.misc.states.participation import ParticipationForm
from db.models import User, Game, KillEvent
from services.matchmaking import MatchmakingService
from settings import settings

logger = logging.getLogger(__name__)


async def on_i_was_killed(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Handle 'I was killed' button click"""
    logger.info("%d сказал, что его убили", callback.from_user.id)
    user: User = manager.middleware_data["user"]
    game: Game = await Game.get(id=manager.start_data.get("game_id"))
    kill_event: KillEvent = await KillEvent.filter(
        victim_id=user.id, game_id=game.id, status="pending"
    ).first()
    await manager.start(
        ConfirmKillVictim.confirm,
        data={"kill_event_id": kill_event.id, "game_id": game.id},
    )


async def on_i_killed(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Handle 'I killed' button click"""
    logger.info("%d сказал, что убил свою цель", callback.from_user.id)
    user: User = manager.middleware_data["user"]
    game: Game = await Game.get(id=manager.start_data.get("game_id"))
    kill_event: KillEvent = await KillEvent.filter(
        killer_id=user.id, game_id=game.id, status="pending"
    ).first()
    await manager.start(
        ConfirmKillKiller.confirm,
        data={"kill_event_id": kill_event.id, "game_id": game.id},
    )


async def on_get_target(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Handle 'Get Target' button click"""
    user: User = manager.middleware_data["user"]
    matchmaking: MatchmakingService = MatchmakingService()

    player_data = {
        "tg_id": user.tg_id,
        "rating": user.rating,
        "type": user.type,
        "course_number": user.course_number,
        "group_name": user.group_name,
    }
    await matchmaking.add_player_to_queue(user.tg_id, player_data, "killer")
    await callback.answer("Вы были поставлены в очередь, ожидайте...")


async def confirm_participation(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    game: Game = await Game.get(id=manager.start_data.get("game_id"))
    user: User = await manager.middleware_data["user"]
    user_dialog_manager = BgManagerFactoryImpl(router=participation.router).bg(
        bot=manager.event.bot,
        user_id=user.tg_id,
        chat_id=user.tg_id,
    )
    await user_dialog_manager.start(
        ParticipationForm.confirm,
        data={"game_id": (game and game.id) or None, "user_tg_id": user.tg_id},
    )
