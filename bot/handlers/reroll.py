import logging
import math
import random
from datetime import datetime, timedelta

from aiogram import Bot, Router
from aiogram.types import CallbackQuery
from aiogram_dialog import Dialog, DialogManager, ShowMode, Window
from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl
from aiogram_dialog.widgets.kbd import Button, Cancel
from aiogram_dialog.widgets.text import Const

from bot.handlers import mainloop_dialog
from db.models import Chat, KillEvent, Player, User
from services import settings
from services import texts
from services.ban import modify_rating
from services.kills_confirmation import add_back_to_queues
from services.states import MainLoop
from services.states.reroll import Reroll
from services.strings import trim_name

logger = logging.getLogger(__name__)

router = Router()


async def notify_player(user: User, bot: Bot, manager: DialogManager, delta: float):
    await bot.send_message(
        chat_id=user.tg_id,
        text=texts.render(
            "reroll.player_notified",
            score_direction=texts.get("score.lost") if delta < 0 else texts.get("score.gained"),
            points=abs(round(delta)),
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
        show_mode=ShowMode.AUTO,
    )


async def notify_chat(
    bot: Bot,
    killer: User,
    victim: User,
    killer_player: Player,
    victim_player: Player,
    killer_delta: float,
    victim_delta: float,
):
    reason = random.choice(texts.get_list("reroll.fail_reasons"))
    killer_display = killer.full_name or killer.tg_username or texts.get("common.unknown")
    victim_display = victim.full_name or victim.tg_username or texts.get("common.unknown")
    await bot.send_message(
        chat_id=(await Chat.get(key="discussion")).chat_id,
        text=texts.render(
            "reroll.chat_notified",
            killer=killer.mention_html(),
            victim=victim.mention_html(),
            reason=reason,
            killer_name=trim_name(killer_display, 25),
            killer_rating=killer_player.rating,
            killer_delta=f"{'+' if killer_delta >= 0 else '-'}{abs(round(killer_delta))}",
            victim_name=trim_name(victim_display, 25),
            victim_rating=victim_player.rating,
            victim_delta=f"{'+' if victim_delta >= 0 else '-'}{abs(round(victim_delta))}",
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
            Const(texts.get("reroll.prompt")),
            Button(Const(texts.get("reroll.confirm")), id="confirm", on_click=on_confirm_reroll),
            Cancel(Const(texts.get("reroll.cancel"))),
            state=Reroll.confirm,
        )
    )
)
