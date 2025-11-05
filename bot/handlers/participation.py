import logging

import requests
from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl
from aiogram_dialog.widgets.kbd import Column, Button
from aiogram_dialog.widgets.text import Const

from bot.handlers import mainloop_dialog
from bot.misc.states import MainLoop
from bot.misc.states.participation import ParticipationForm
from db.models import Player, Game, User
from services.matchmaking import MatchmakingService

logger = logging.getLogger(__name__)

router = Router()


async def confirm_participation(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    game: Game = manager.start_data["game"]
    user: User = manager.start_data["user"]
    matchmaking: MatchmakingService = manager.start_data["matchmaking"]
    user.is_in_game = True
    await user.save()
    player: Player = await Player().create(
        user=user,
        game=game,
    )
    logger.debug(
        "Created player for user %s game %s with id %s",
        user.id,
        game.id,
        player.id,
    )
    await callback.message.delete()
    await manager.done()
    await manager.reset_stack()
    user_dialog_manager = BgManagerFactoryImpl(
        router=mainloop_dialog.router
    ).bg(
        bot=manager.event.bot,
        user_id=user.tg_id,
        chat_id=user.tg_id,
    )
    player_data = {
        "player_id": user.tg_id,
        "rating": user.rating,
        "type": user.type,
        "course_number": user.course_number,
        "group_name": user.group_name,
    }
    await matchmaking.add_player_to_queues(
        player_id=user.tg_id, player_data=player_data
    )
    await user_dialog_manager.start(
        MainLoop.title,
        data={"user": user, "game": game, "matchmaking": matchmaking},
    )


router.include_router(
    Dialog(
        Window(
            Const("Начинается новая игра, хотите принять в ней участие?"),
            Column(
                Button(
                    Const("Да, хочу"),
                    id="confirm",
                    on_click=confirm_participation,
                ),
                Button(
                    Const("Нет, спасибо"),
                    id="deny",
                    on_click=lambda c, b, m: m.done(),
                ),
            ),
            state=ParticipationForm.confirm,
        ),
    )
)
