import logging
from datetime import datetime

from aiogram import Router
from aiogram.client.bot import Bot
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from aiogram.types import User as TgUser
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.api.entities import ShowMode
from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl
from aiogram_dialog.widgets.kbd import Button, Cancel
from aiogram_dialog.widgets.text import Const

from bot.handlers import mainloop_dialog
from db.models import Chat, KillEvent, Player, User
from services import settings
from services.ban import modify_rating
from services.kills_confirmation import add_back_to_queues
from services.states import MainLoop
from services.strings import trim_name
from services import texts

logger = logging.getLogger(__name__)
router = Router()


class ConfirmKillVictim(StatesGroup):
    confirm = State()
    double_confirm = State()


class ConfirmKillKiller(StatesGroup):
    confirm = State()
    double_confirm = State()


async def send_double_confirm_dialog(manager: DialogManager, user: User, state):
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


async def notify_chat(
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

    await bot.send_message(
        chat_id=(await Chat.get(key="discussion")).chat_id,
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


async def handle_confirm(
    bot: Bot,
    manager: DialogManager,
    role: str,
    opposite_role: str,
    opposite_state: State,
    from_user: TgUser,
):
    """Shared confirmation handler for both killer and victim."""
    kill_event: KillEvent = await KillEvent.get(id=manager.start_data["kill_event_id"])
    setattr(kill_event, f"{role}_confirmed", True)
    setattr(kill_event, f"{role}_confirmed_at", datetime.now(settings.timezone))
    await kill_event.save()

    await kill_event.fetch_related("killer")
    await kill_event.fetch_related("victim")

    if not getattr(kill_event, f"{opposite_role}_confirmed"):
        opposite_user: User = await User.get(id=getattr(kill_event, opposite_role).id)
        await send_double_confirm_dialog(manager, opposite_user, opposite_state)

    if kill_event.killer_confirmed and kill_event.victim_confirmed:
        kill_event.status = "confirmed"
        await kill_event.save()
        killer_player = await Player.get(
            game_id=manager.middleware_data["game"].id,
            user_id=kill_event.killer.id,
        )
        victim_player = await Player.get(
            game_id=manager.middleware_data["game"].id,
            user_id=kill_event.victim.id,
        )
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


async def handle_deny(
    bot: Bot,
    manager: DialogManager,
    opposite_role: str,
    role: str,
    opposite_state: State,
    from_user: TgUser,
):
    """Shared denial handler for both killer and victim."""
    kill_event: KillEvent = await KillEvent.get(id=manager.start_data["kill_event_id"])

    setattr(kill_event, f"{role}_confirmed", False)
    setattr(kill_event, f"{role}_confirmed_at", None)

    logger.info("%d отказался признавать убийство, будучи %s", from_user.id, role)

    await kill_event.save()


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
