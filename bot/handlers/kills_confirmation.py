import logging
from datetime import datetime

from aiogram import Router
from aiogram.client.bot import Bot
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import CallbackQuery, User as TgUser
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.api.entities import ShowMode
from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl
from aiogram_dialog.widgets.kbd import Button, Cancel
from aiogram_dialog.widgets.text import Const

from bot.handlers import mainloop_dialog
from db.models import KillEvent, User, Chat
from services import settings
from services.matchmaking import MatchmakingService
from services.states import MainLoop

logger = logging.getLogger(__name__)
router = Router()


class ConfirmKillVictim(StatesGroup):
    confirm = State()
    double_confirm = State()


class ConfirmKillKiller(StatesGroup):
    confirm = State()
    double_confirm = State()


async def send_double_confirm_dialog(
    manager: DialogManager, user: User, state
):
    """Send double-confirm dialog to another participant."""
    dialog_manager = BgManagerFactoryImpl(router=router).bg(
        bot=manager.event.bot,
        user_id=user.tg_id,
        chat_id=user.tg_id,
    )
    await dialog_manager.start(
        state, data=manager.start_data, show_mode=ShowMode.DELETE_AND_SEND
    )


async def add_back_to_queues(killer: User, victim: User):
    """Return both players to matchmaking queues."""
    matchmaking = MatchmakingService()
    for player, qtype in ((killer, "killer"), (victim, "victim")):
        await matchmaking.add_player_to_queue(
            player.tg_id,
            {
                "tg_id": player.tg_id,
                "rating": player.rating,
                "type": player.type,
                "course_number": player.course_number,
                "group_name": player.group_name,
            },
            queue_type=qtype,
        )


async def modify_rating(killer: User, victim: User):
    """After successful kill, update ELO ratings of killer and victim."""
    killer_rating = killer.rating
    victim_rating = victim.rating

    expected_killer = 1 / (
        1 + 10 ** ((victim_rating - killer_rating) / settings.ELO_SCALE)
    )
    expected_victim = 1 / (
        1 + 10 ** ((killer_rating - victim_rating) / settings.ELO_SCALE)
    )

    killer_delta = settings.K_KILLER * (1 - expected_killer)
    victim_delta = settings.K_VICTIM * (0 - expected_victim)

    killer_new = killer_rating + killer_delta
    victim_new = victim_rating + victim_delta

    killer.rating = round(killer_new)
    victim.rating = round(victim_new)

    await killer.save()
    await victim.save()

    return killer_delta, victim_delta


async def notify_player(
    user: User, bot: Bot, manager: DialogManager, delta: int
):
    await bot.send_message(
        chat_id=user.tg_id,
        text=(
            f"Убийство было обоюдно подтверждено!\n\n"
            f"Вы {'потеряли' if delta < 0 else 'получили'} <b>{abs(round(delta))}</b> очков рейтинга"
        ),
    )

    dialog_manager = BgManagerFactoryImpl(router=mainloop_dialog.router).bg(
        bot=bot,
        user_id=user.tg_id,
        chat_id=user.tg_id,
    )
    await dialog_manager.start(
        MainLoop.title,
        data={**manager.start_data, "user_tg_id": user.tg_id},
        show_mode=ShowMode.DELETE_AND_SEND,
    )


async def notify_chat(
    bot: Bot, killer: User, victim: User, killer_delta: int, victim_delta: int
):
    await bot.send_message(
        chat_id=(await Chat.get(key="discussion")).chat_id,
        text=(
            f"<b>{killer.name}</b> убил <b>{victim.name}</b>\n\n"
            f"Новый MMR {killer.name}: {killer.rating}({'+' if killer_delta >= 0 else '-'}{abs(round(killer_delta))})\n"
            f"Новый MMR {victim.name}: {victim.rating}({'+' if victim_delta >= 0 else '-'}{abs(round(victim_delta))})\n"
        ),
    )


async def handle_confirm(
    bot: Bot,
    manager: DialogManager,
    role: str,
    opposite_role: str,
    opposite_state: State,
    from_user: TgUser,
):
    """Shared confirmation handler for both killer and victim."""
    kill_event: KillEvent = await KillEvent.get(
        id=manager.start_data["kill_event_id"]
    )
    setattr(kill_event, f"{role}_confirmed", True)
    setattr(kill_event, f"{role}_confirmed_at", datetime.now())

    await kill_event.fetch_related("killer")
    await kill_event.fetch_related("victim")

    if not getattr(kill_event, f"{opposite_role}_confirmed"):
        opposite_user: User = await User.get(
            id=getattr(kill_event, opposite_role).id
        )
        await send_double_confirm_dialog(
            manager, opposite_user, opposite_state
        )

    if kill_event.killer_confirmed and kill_event.victim_confirmed:
        kill_event.status = "confirmed"
        killer_delta, victim_delta = await modify_rating(
            kill_event.killer, kill_event.victim
        )
        await notify_player(kill_event.killer, bot, manager, killer_delta)
        await notify_player(kill_event.victim, bot, manager, victim_delta)
        await notify_chat(
            bot,
            kill_event.killer,
            kill_event.victim,
            killer_delta,
            victim_delta,
        )
        await add_back_to_queues(kill_event.killer, kill_event.victim)

    await kill_event.save()
    await manager.start(
        MainLoop.title,
        data={
            "user_tg_id": from_user.id,
            "game_id": manager.start_data["game_id"],
        },
    )


async def handle_deny(
    bot: Bot,
    manager: DialogManager,
    opposite_role: str,
    role: str,
    opposite_state: State,
    from_user: TgUser,
):
    """Shared denial handler for both killer and victim."""
    kill_event: KillEvent = await KillEvent.get(
        id=manager.start_data["kill_event_id"]
    )

    setattr(kill_event, f"{role}_confirmed", False)
    setattr(kill_event, f"{role}_confirmed_at", None)

    logger.info(
        "%d отказался признавать убийство, будучи %s", from_user.id, role
    )

    await kill_event.save()


async def on_victim_confirm(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    return await handle_confirm(
        callback.bot,
        manager,
        role="victim",
        opposite_role="killer",
        opposite_state=ConfirmKillKiller.double_confirm,
        from_user=callback.from_user,
    )


async def on_killer_confirm(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    return await handle_confirm(
        callback.bot,
        manager,
        role="killer",
        opposite_role="victim",
        opposite_state=ConfirmKillVictim.double_confirm,
        from_user=callback.from_user,
    )


async def on_victim_deny(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    return await handle_deny(
        callback.bot,
        manager,
        role="victim",
        opposite_role="killer",
        opposite_state=ConfirmKillKiller.double_confirm,
        from_user=callback.from_user,
    )


async def on_killer_deny(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    return await handle_deny(
        callback.bot,
        manager,
        role="killer",
        opposite_role="victim",
        opposite_state=ConfirmKillVictim.double_confirm,
        from_user=callback.from_user,
    )


router.include_router(
    Dialog(
        Window(
            Const("Вы уверены что хотите подтвердить, что вас убили?"),
            Button(
                Const("Да, меня убили"),
                id="confirm",
                on_click=on_victim_confirm,
            ),
            Cancel(Const("Назад")),
            state=ConfirmKillVictim.confirm,
        ),
        Window(
            Const("Ваш убийца утверждает, что он вас убил. Это правда?"),
            Button(
                Const("Да, меня убили"),
                id="confirm",
                on_click=on_victim_confirm,
            ),
            Button(
                Const("Наглая ложь, меня не убивали"),
                id="deny",
                on_click=on_victim_deny,
            ),
            state=ConfirmKillVictim.double_confirm,
        ),
    )
)

router.include_router(
    Dialog(
        Window(
            Const("Вы уверены что вы убили цель?"),
            Button(
                Const("Да, я убил"), id="confirm", on_click=on_killer_confirm
            ),
            Cancel(Const("Назад")),
            state=ConfirmKillKiller.confirm,
        ),
        Window(
            Const("Ваша жертва утверждает, что вы ее убили. Это правда?"),
            Button(
                Const("Да, я убил"), id="confirm", on_click=on_killer_confirm
            ),
            Button(
                Const("Нет, я ее не убивал"),
                id="deny",
                on_click=on_killer_deny,
            ),
            state=ConfirmKillKiller.double_confirm,
        ),
    )
)
