import logging
import math
import random
from datetime import datetime, timedelta

from aiogram import Router, Bot
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, Window, DialogManager, ShowMode
from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl
from aiogram_dialog.widgets.kbd import Button, Cancel
from aiogram_dialog.widgets.text import Const

from bot.handlers import mainloop_dialog
from db.models import Player, User, KillEvent, Chat
from services import settings
from services.kills_confirmation import modify_rating, add_back_to_queues
from services.states import MainLoop
from services.states.reroll import Reroll
from services.strings import trim_name

logger = logging.getLogger(__name__)

router = Router()


async def notify_player(user: User, bot: Bot, manager: DialogManager, delta: int):
    await bot.send_message(
        chat_id=user.tg_id,
        text=(
            f"Убийство отменено!\n\n"
            f"Вы {'потеряли' if delta < 0 else 'получили'} <b>{abs(round(delta))}</b> очков рейтинга"
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
        show_mode=ShowMode.SEND,
    )


FAILED_MESSAGE = [
    "отказался убивать",
    "не осилил убийство",
    "признал, что имеет недостаточно квалификации, чтоб убить",
    "сдался убивать",
]


async def notify_chat(
    bot: Bot,
    killer: User,
    victim: User,
    killer_player: Player,
    victim_player: Player,
    killer_delta: int,
    victim_delta: int,
):
    await bot.send_message(
        chat_id=(await Chat.get(key="discussion")).chat_id,
        text=(
            f"<b>{killer.mention_html()}</b> {random.choice(FAILED_MESSAGE)} <b>{victim.mention_html()}</b>\n\n"
            f"Новый MMR {trim_name(killer.name, 25)}: {killer_player.rating}({'+' if killer_delta >= 0 else '-'}{abs(round(killer_delta))})\n"
            f"Новый MMR {trim_name(victim.name, 25)}: {victim_player.rating}({'+' if victim_delta >= 0 else '-'}{abs(round(victim_delta))})\n"
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
    killer_player: Player = await Player.get_or_none(user_id=requester_user.id, game_id=m.start_data["game_id"])
    kill_event: KillEvent = await KillEvent.get_or_none(
        game_id=m.start_data["game_id"],
        killer_id=requester_user.id,
        status="pending",
    ).prefetch_related("killer", "victim")
    kill_event.status = "rejected"
    await kill_event.save()

    victim_player: Player = await Player.get_or_none(game_id=m.start_data["game_id"], user_id=kill_event.victim.id)

    logger.debug(kill_event)
    killer_delta, victim_delta = await modify_rating(
        killer_player, victim_player, 0, 1, calculate_penalty(kill_event.created_at)
    )
    await add_back_to_queues(kill_event.killer, kill_event.victim, killer_player, victim_player)
    await notify_chat(
        c.bot,
        kill_event.killer,
        kill_event.victim,
        killer_player,
        victim_player,
        killer_delta,
        victim_delta,
    )
    await notify_player(kill_event.killer, c.bot, m, killer_delta)
    await notify_player(kill_event.victim, c.bot, m, victim_delta)


router.include_router(
    Dialog(
        Window(
            Const("Вы уверены что хотите заменить цель?"),
            Button(Const("Да"), id="confirm", on_click=on_confirm_reroll),
            Cancel(Const("Нет, назад")),
            state=Reroll.confirm,
        )
    )
)
