import logging

from aiogram import Router
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Column, Button
from aiogram_dialog.widgets.text import Const

from bot.misc.states.participation import ParticipationForm
from db.models import Player, Game, User

logger = logging.getLogger(__name__)

router = Router()


async def confirm_participation(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    game: Game = manager.start_data["game"]
    user: User = manager.start_data["user"]
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
    await manager.done()


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
