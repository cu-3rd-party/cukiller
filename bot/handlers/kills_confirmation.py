from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.fsm.state import State, StatesGroup
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.api.entities import ShowMode
from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl
from aiogram_dialog.widgets.kbd import Button, Cancel
from aiogram_dialog.widgets.text import Const

from handlers import mainloop_dialog
from services import MainLoop, add_back_to_queues, modify_rating, texts, trim_name
from services.backend_api import backend_api
from services.settings import settings

if TYPE_CHECKING:
    from aiogram.client.bot import Bot
    from aiogram.types import CallbackQuery
    from aiogram.types import User as TgUser

    from services.backend_api import Model as Player
    from services.backend_api import UserModel as User

logger = logging.getLogger(__name__)
router = Router()


class ConfirmKillVictim(StatesGroup):
    confirm = State()
    double_confirm = State()


class ConfirmKillKiller(StatesGroup):
    confirm = State()
    double_confirm = State()


async def send_double_confirm_dialog(manager: DialogManager, user: User, state: State):
    """Send double-confirm dialog to another participant."""
    dialog_manager = BgManagerFactoryImpl(router=router).bg(
        bot=manager.event.bot,
        user_id=user.tg_id,
        chat_id=user.tg_id,
    )
    await dialog_manager.start(state, data=manager.start_data, show_mode=ShowMode.AUTO)


async def notify_player(user: User, bot: Bot, manager: DialogManager, delta: int):
    await bot.send_message(
        chat_id=user.tg_id,
        text=texts.render(
            "kills.player_notified",
            score_direction=texts.get("score.lost") if delta < 0 else texts.get("score.gained"),
            points=abs(delta),
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


async def notify_chat(  # noqa: PLR0913
    bot: Bot,
    killer: User,
    victim: User,
    killer_player: Player,
    victim_player: Player,
    killer_delta: int,
    victim_delta: int,
):
    killer_display = killer.full_name or killer.tg_username or texts.get("common.unknown")
    victim_display = victim.full_name or victim.tg_username or texts.get("common.unknown")

    discussion_chat = await backend_api.get_chat_by_key("discussion")
    if not discussion_chat:
        logger.warning("Discussion chat not configured")
        return

    await bot.send_message(
        chat_id=discussion_chat.chat_id,
        text=texts.render(
            "kills.chat_notified",
            killer=killer.mention_html(),
            victim=victim.mention_html(),
            killer_name=trim_name(killer_display, 25),
            killer_rating=killer_player.rating,
            killer_delta=f"{'+' if killer_delta >= 0 else '-'}{abs(killer_delta)}",
            victim_name=trim_name(victim_display, 25),
            victim_rating=victim_player.rating,
            victim_delta=f"{'+' if victim_delta >= 0 else '-'}{abs(victim_delta)}",
        ),
    )


async def handle_confirm(  # noqa: PLR0913
    bot: Bot,
    manager: DialogManager,
    role: str,
    opposite_role: str,
    opposite_state: State,
    from_user: TgUser,
):
    """Shared confirmation handler for both killer and victim."""
    kill_event = await backend_api.get_kill_event(manager.start_data["kill_event_id"])
    if not kill_event:
        return
    setattr(kill_event, f"{role}_confirmed", True)
    setattr(kill_event, f"{role}_confirmed_at", datetime.now(settings.timezone))
    await backend_api.update_kill_event(
        kill_event.id,
        {
            f"{role}_confirmed": True,
            f"{role}_confirmed_at": getattr(kill_event, f"{role}_confirmed_at"),
        },
    )

    if not getattr(kill_event, "killer", None):
        kill_event.killer = await backend_api.get_user_by_id(kill_event.killer_id)
    if not getattr(kill_event, "victim", None):
        kill_event.victim = await backend_api.get_user_by_id(kill_event.victim_id)

    if not getattr(kill_event, f"{opposite_role}_confirmed"):
        opposite_user = kill_event.killer if opposite_role == "killer" else kill_event.victim
        if opposite_user:
            await send_double_confirm_dialog(manager, opposite_user, opposite_state)

    if kill_event.killer_confirmed and kill_event.victim_confirmed:
        kill_event.status = "confirmed"
        await backend_api.update_kill_event(kill_event.id, {"status": kill_event.status})
        killer_players = await backend_api.list_players(game_id=kill_event.game_id, user_id=kill_event.killer_id)
        killer_player = killer_players[0] if killer_players else None
        victim_players = await backend_api.list_players(game_id=kill_event.game_id, user_id=kill_event.victim_id)
        victim_player = victim_players[0] if victim_players else None
        if not killer_player or not victim_player:
            return
        if killer_player:
            killer_player.user = kill_event.killer
        if victim_player:
            victim_player.user = kill_event.victim
        killer_delta, victim_delta = await modify_rating(killer_player, victim_player)
        await add_back_to_queues(kill_event.killer, kill_event.victim, killer_player, victim_player)
        await notify_player(kill_event.killer, bot, manager, killer_delta)
        await notify_player(kill_event.victim, bot, manager, victim_delta)
        await notify_chat(
            bot,
            kill_event.killer,
            kill_event.victim,
            killer_player,
            victim_player,
            killer_delta,
            victim_delta,
        )

    await manager.start(
        MainLoop.title,
        data={
            "user_tg_id": from_user.id,
            "game_id": manager.start_data["game_id"],
        },
        show_mode=ShowMode.AUTO,
    )


async def handle_deny(  # noqa: PLR0913
    bot: Bot,
    manager: DialogManager,
    opposite_role: str,
    role: str,
    opposite_state: State,
    from_user: TgUser,
):
    """Shared denial handler for both killer and victim."""
    kill_event = await backend_api.get_kill_event(manager.start_data["kill_event_id"])
    if not kill_event:
        return

    setattr(kill_event, f"{role}_confirmed", False)
    setattr(kill_event, f"{role}_confirmed_at", None)

    logger.info("%d отказался признавать убийство, будучи %s", from_user.id, role)

    await backend_api.update_kill_event(
        kill_event.id,
        {
            f"{role}_confirmed": False,
            f"{role}_confirmed_at": None,
            "status": "rejected",
        },
    )


async def on_victim_confirm(callback: CallbackQuery, button: Button, manager: DialogManager):
    return await handle_confirm(
        callback.bot,
        manager,
        role="victim",
        opposite_role="killer",
        opposite_state=ConfirmKillKiller.double_confirm,
        from_user=callback.from_user,
    )


async def on_killer_confirm(callback: CallbackQuery, button: Button, manager: DialogManager):
    return await handle_confirm(
        callback.bot,
        manager,
        role="killer",
        opposite_role="victim",
        opposite_state=ConfirmKillVictim.double_confirm,
        from_user=callback.from_user,
    )


async def on_victim_deny(callback: CallbackQuery, button: Button, manager: DialogManager):
    return await handle_deny(
        callback.bot,
        manager,
        role="victim",
        opposite_role="killer",
        opposite_state=ConfirmKillKiller.double_confirm,
        from_user=callback.from_user,
    )


async def on_killer_deny(callback: CallbackQuery, button: Button, manager: DialogManager):
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
            Const(texts.get("kills.victim_confirm_prompt")),
            Button(
                Const(texts.get("kills.victim_confirm_button")),
                id="confirm",
                on_click=on_victim_confirm,
            ),
            Cancel(Const(texts.get("buttons.back"))),
            state=ConfirmKillVictim.confirm,
        ),
        Window(
            Const(texts.get("kills.victim_double_confirm_prompt")),
            Button(
                Const(texts.get("kills.victim_confirm_button")),
                id="confirm",
                on_click=on_victim_confirm,
            ),
            Button(
                Const(texts.get("kills.victim_deny_button")),
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
            Const(texts.get("kills.killer_confirm_prompt")),
            Button(Const(texts.get("kills.killer_confirm_button")), id="confirm", on_click=on_killer_confirm),
            Cancel(Const(texts.get("buttons.back"))),
            state=ConfirmKillKiller.confirm,
        ),
        Window(
            Const(texts.get("kills.killer_double_confirm_prompt")),
            Button(Const(texts.get("kills.killer_confirm_button")), id="confirm", on_click=on_killer_confirm),
            Button(
                Const(texts.get("kills.killer_deny_button")),
                id="deny",
                on_click=on_killer_deny,
            ),
            state=ConfirmKillKiller.double_confirm,
        ),
    )
)
