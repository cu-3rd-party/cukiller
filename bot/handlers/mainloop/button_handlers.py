import logging

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl
from aiogram_dialog.widgets.kbd import Button

from bot.handlers import participation
from bot.handlers.kills_confirmation import (
    ConfirmKillKiller,
    ConfirmKillVictim,
)
from db.models import Game, KillEvent, Player, User
from services.logging import log_dialog_action
from services.matchmaking import MatchmakingService
from services.states.my_profile import MyProfile
from services.states.participation import ParticipationForm
from services.states.reroll import Reroll
from services.states.rules import RulesStates

logger = logging.getLogger(__name__)


async def _get_user_and_game(manager: DialogManager) -> tuple[User, Game]:
    user: User = manager.middleware_data["user"]
    game_id = manager.start_data.get("game_id")
    game: Game = await Game.get(id=game_id)
    return user, game


async def _start_kill_confirmation(
    manager: DialogManager,
    kill_event: KillEvent,
    state,
):
    await manager.start(
        state,
        data={"kill_event_id": kill_event.id, "game_id": kill_event.game_id},
        show_mode=ShowMode.AUTO,
    )


async def _get_pending_event(user_id: int, game_id: int, role: str):
    """role: 'victim' | 'killer'"""
    filters = {
        "victim": {"victim_id": user_id},
        "killer": {"killer_id": user_id},
    }[role]

    return await KillEvent.filter(**filters, game_id=game_id, status="pending").first()


@log_dialog_action("I_WAS_KILLED")
async def on_i_was_killed(callback: CallbackQuery, button: Button, manager: DialogManager):
    logger.info("%d: reported they were killed", callback.from_user.id)

    user, game = await _get_user_and_game(manager)
    kill_event = await _get_pending_event(user.id, game.id, role="victim")

    await _start_kill_confirmation(manager, kill_event, ConfirmKillVictim.confirm)


@log_dialog_action("I_KILLED")
async def on_i_killed(callback: CallbackQuery, button: Button, manager: DialogManager):
    logger.info("%d: reported they killed their target", callback.from_user.id)

    user, game = await _get_user_and_game(manager)
    kill_event = await _get_pending_event(user.id, game.id, role="killer")

    await _start_kill_confirmation(manager, kill_event, ConfirmKillKiller.confirm)


@log_dialog_action("GET_TARGET")
async def on_get_target(callback: CallbackQuery, button: Button, manager: DialogManager):
    user: User = manager.middleware_data["user"]
    game: Game = manager.middleware_data["game"]
    if not game:
        return
    player: Player = await Player.get(game_id=game.id, user_id=user.id)

    data = {
        "tg_id": user.tg_id,
        "rating": player.rating,
        "type": user.type,
        "course_number": user.course_number,
        "group_name": user.group_name,
    }

    await MatchmakingService().add_player_to_queue(user.tg_id, data, "killer")
    await callback.answer("Вы были поставлены в очередь, ожидайте...")


@log_dialog_action("CONFIRM_PARTICIPATION")
async def confirm_participation(callback: CallbackQuery, button: Button, manager: DialogManager):
    user, game = await _get_user_and_game(manager)

    dialog = BgManagerFactoryImpl(router=participation.router).bg(
        bot=manager.event.bot,
        user_id=user.tg_id,
        chat_id=user.tg_id,
    )

    await dialog.done()

    await dialog.start(
        ParticipationForm.confirm,
        data={"game_id": game.id, "user_tg_id": user.tg_id},
        show_mode=ShowMode.AUTO,
    )


@log_dialog_action("OPEN_PROFILE")
async def open_profile(callback: CallbackQuery, button: Button, manager: DialogManager):
    await manager.start(
        MyProfile.profile,
        data={"user_tg_id": callback.from_user.id},
        show_mode=ShowMode.AUTO,
    )


@log_dialog_action("OPEN_RULES")
async def open_rules(callback: CallbackQuery, button: Button, manager: DialogManager):
    await manager.start(RulesStates.rules)


@log_dialog_action("REROLL")
async def on_reroll(c: CallbackQuery, b: Button, m: DialogManager):
    user, game = await _get_user_and_game(m)
    await m.start(
        Reroll.confirm,
        data={"user_tg_id": user.tg_id, "game_id": game.id},
        show_mode=ShowMode.AUTO,
    )
