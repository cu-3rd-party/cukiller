import asyncio
import contextlib
import logging
import math
from datetime import datetime, timedelta
from uuid import UUID

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    CallbackQuery,
    Message,
)
from aiogram_dialog import BaseDialogManager, Dialog, DialogManager, Window
from aiogram_dialog.api.entities import ShowMode
from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Cancel, Column, Row, Select
from aiogram_dialog.widgets.text import Const, Format
from tortoise.expressions import Q

import services.ban
from bot.filters.admin import AdminFilter
from bot.handlers import mainloop_dialog
from db.models import Chat, Game, Player, User, KillEvent
from services import settings, texts
from services.admin_chat import AdminChatService
from services.ban import recalc_game_ratings
from services.credits import CreditsInfo
from services.logging import log_dialog_action
from services.matchmaking import MatchmakingService
from services.states import EditGame, EndGame, MainLoop, StartGame
from services.states.participation import ParticipationForm

logger = logging.getLogger(__name__)

router = Router()


async def set_admin_commands(bot: Bot, chat_id: int):
    await bot.set_my_commands(
        commands=[
            BotCommand(command="/start", description=texts.get("admin.command.start")),
            BotCommand(
                command="/stats",
                description=texts.get("admin.command.stats"),
            ),
            BotCommand(
                command="/creategame",
                description=texts.get("admin.command.creategame"),
            ),
            BotCommand(
                command="/editgame",
                description=texts.get("admin.command.editgame"),
            ),
            BotCommand(
                command="/getservertime",
                description=texts.get("admin.command.server_time"),
            ),
        ],
        scope=BotCommandScopeChat(chat_id=chat_id),
    )


@router.message(AdminFilter(), Command(commands=["stats"]))
async def stats(message: Message, bot: Bot):
    user_count = await User().all().count()
    user_confirmed_count = await User().filter(status="confirmed").count()
    current_game = await Game().filter(end_date=None).first()

    if current_game:
        # Get current game statistics
        info = await CreditsInfo.from_game(current_game)
        stats_text = texts.render(
            "admin.stats.with_game",
            game_name=info.name,
            duration=info.duration,
            rating_top=info.rating_top,
            killers_top=info.killers_top,
            victims_top=info.victims_top,
        )
    else:
        confirmed_percent = (user_confirmed_count / user_count * 100) if user_count else 0
        stats_text = texts.render(
            "admin.stats.no_game",
            user_count=user_count,
            confirmed_count=user_confirmed_count,
            confirmed_percent=confirmed_percent,
        )

    await message.reply(text=stats_text, parse_mode="HTML")


@log_dialog_action("ADMIN_CAMPAIGN_NAME_INPUT")
async def on_name_input(message: Message, message_input: MessageInput, manager: DialogManager):
    manager.dialog_data["name"] = message.text.strip()
    await manager.next()


@log_dialog_action("ADMIN_CAMPAIGN_DESCRIPTION_INPUT")
async def on_description_input(message: Message, message_input: MessageInput, manager: DialogManager):
    manager.dialog_data["description"] = message.text.strip()
    await manager.next()


async def send_notification(bot: Bot, user: User, text: str):
    msg = await bot.send_message(
        user.tg_id,
        text=text,
        parse_mode="HTML",
    )
    asyncio.create_task(delete_later(bot, msg.chat.id, msg.message_id))


async def delete_later(bot: Bot, chat_id: int, msg_id: int):
    await asyncio.sleep(10)
    try:
        await bot.delete_message(chat_id, msg_id)
    except Exception as e:
        logger.warning(f"Failed to delete message {msg_id}: {e}")


@log_dialog_action("ADMIN_CAMPAIGN_FINAL_CONFIRMATION")
async def on_final_confirmation(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    **kwargs,
):
    bot = manager.event.bot
    manager.dialog_data["confirm"] = True

    creation_date = datetime.now(settings.timezone)
    game = await Game().create(
        name=manager.dialog_data.get("name") or "test",
        start_date=creation_date,
    )
    users = (
        await User()
        .filter(is_in_game=False, status="confirmed")
        .filter(Q(exit_cooldown_until__isnull=True) | Q(exit_cooldown_until__lte=creation_date))
        .only("tg_id", "name")
        .all()
    )

    logger.debug(f"Notifying {len(users)} about new game {game.id}")

    tasks = []
    factory = BgManagerFactoryImpl(router=router)

    for user in users:
        message_task = send_notification(
            bot,
            user,
            texts.render("admin.notify_new_game", mention=user.mention_html()),
        )
        tasks.append(message_task)

        user_dialog_manager = factory.bg(
            bot=bot,
            user_id=user.tg_id,
            chat_id=user.tg_id,
        )
        tasks.append(user_dialog_manager.done())
        dialog_task = user_dialog_manager.start(
            ParticipationForm.confirm,
            data={
                "game_id": game.id,
                "user_tg_id": user.tg_id,
            },
            show_mode=ShowMode.AUTO,
        )
        tasks.append(dialog_task)

    if tasks:
        with contextlib.suppress(TelegramForbiddenError):
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Task {i} failed: {result}")

    await manager.done()
    await callback.answer(
        texts.render("admin.game_created_alert", creation_date=creation_date),
        show_alert=True,
    )


@log_dialog_action("ADMIN_RESET_GAME_CREATION")
async def on_reset_game_creation(callback: CallbackQuery, button: Button, manager: DialogManager):
    manager.dialog_data["confirm"] = False

    await manager.switch_to(StartGame.name)


router.include_router(
    Dialog(
        Window(
            Const(texts.get("admin.creategame.ask_name")),
            MessageInput(on_name_input, content_types=ContentType.TEXT),
            state=StartGame.name,
        ),
        Window(
            Const(texts.get("admin.creategame.confirm")),
            Column(
                Button(
                    Const(texts.get("admin.creategame.confirm_yes")),
                    on_click=on_final_confirmation,
                    id="startgame_confirm",
                ),
                Button(
                    Const(texts.get("admin.creategame.confirm_no")),
                    on_click=on_reset_game_creation,
                    id="startgame_reject",
                ),
            ),
            state=StartGame.confirm,
        ),
    )
)


@router.message(AdminFilter(), Command(commands=["creategame"]))
async def creategame(message: Message, bot: Bot, dialog_manager: DialogManager):
    if await Game().filter(end_date=None).exists():
        msg = await message.reply(text=texts.get("admin.creategame.already_running"))
        await asyncio.sleep(10)
        await msg.delete()
        return
    await dialog_manager.start(StartGame.name, show_mode=ShowMode.AUTO)


@router.message(AdminFilter(), Command(commands=["getservertime"]))
async def getservertime(message: Message):
    msg = await message.reply(texts.render("admin.server_time", server_time=datetime.now(settings.timezone)))
    await asyncio.sleep(10)
    await msg.delete()


def parse_game_stage(game: Game) -> str:
    if game.end_date:
        return texts.get("admin.game_stage.finished")
    if game.start_date:
        return texts.get("admin.game_stage.started")
    logger.warning("start: %s; end: %s", game.start_date, game.end_date)
    return texts.get("admin.game_stage.error")


async def get_games_data(**kwargs):
    games = await Game().filter(end_date=None).all()
    return {
        "games": [
            {
                "id": game.id,
                "name": f"{game.name} - {parse_game_stage(game)}",
            }
            for game in games
        ]
    }


async def get_selected_game_data(dialog_manager: DialogManager, **kwargs):
    game_id = dialog_manager.dialog_data.get("game_id")
    if not game_id:
        return {}
    game = await Game.get(id=game_id)
    return {
        "game_name": game.name,
        "show_end_game": game.start_date is not None and game.end_date is None,
    }


@log_dialog_action("ADMIN_GAME_SELECTED")
async def on_game_selected(callback: CallbackQuery, widget, manager: DialogManager, item_id: str):
    await callback.answer(texts.render("admin.game_selected", item_id=item_id))
    manager.dialog_data["game_id"] = item_id
    await manager.next()


@log_dialog_action("ADMIN_GAME_ACTION_CLICKED")
async def on_action_clicked(callback: CallbackQuery, widget, manager: DialogManager):
    action = widget.widget_id
    game = await Game.get(id=manager.dialog_data["game_id"])
    logger.info(action)
    if action == "start_game":
        await handle_start_game(callback, game)
    elif action == "end_game":
        await handle_end_game(callback.bot, manager.middleware_data["dispatcher"], game)
    logger.info(game.start_date)
    await callback.message.delete()
    await manager.switch_to(EditGame.edit)


async def handle_start_game(callback: CallbackQuery, game: Game):
    game.start_date = datetime.now(settings.timezone)
    await game.save()
    await MatchmakingService().reset_queues()


async def handle_end_game(bot: Bot, dp: Dispatcher, game: Game):
    """Handle game ending and send credits to all participants."""
    game.end_date = datetime.now(settings.timezone)
    await game.save()
    await MatchmakingService().reset_queues()

    participants, info, discussion = await asyncio.gather(
        User().all(), CreditsInfo.from_game(game), Chat.get(key="discussion")
    )

    send_tasks = [
        *[user_endgame(bot, dp, user, info) for user in participants],
        send_game_credits(bot, info, discussion.chat_id),
    ]

    results = await asyncio.gather(*send_tasks, return_exceptions=True)

    for user, result in zip(participants, results, strict=False):
        if isinstance(result, Exception):
            logger.error(f"Failed to send credits to user {user.id}: {result}")

    await User().filter(is_in_game=True).update(is_in_game=False)


async def user_endgame(bot: Bot, dp: Dispatcher, user: User, info: CreditsInfo):
    await send_game_credits(bot, info, user.tg_id, user.id)
    await reset_dialog(bot, dp, user.tg_id)


async def send_game_credits(
    bot: Bot,
    info: CreditsInfo,
    chat_id: int,
    user_id: UUID | None = None,
) -> None:
    """Send game credits message to a specific user."""
    personal_stats = get_personal_stats(user_id, info) if user_id else ""
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=texts.render(
                "admin.game_credits",
                name=info.name,
                duration=info.duration,
                rating_top=info.rating_top,
                killers_top=info.killers_top,
                victims_top=info.victims_top,
                personal_stats=personal_stats,
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        msg = f"Failed to send message to chat {chat_id}"
        raise Exception(msg) from e


def get_personal_stats(user_id: UUID, info: CreditsInfo):
    player_info = info.per_player.get(user_id)
    if not player_info:
        return texts.get("admin.personal_stats.empty")
    return texts.render(
        "admin.personal_stats",
        rating=player_info.rating,
        kills=player_info.kills,
        deaths=player_info.deaths,
        log="\n".join(player_info.log),
    )


async def reset_dialog(bot: Bot, dp: Dispatcher, user_id: int):
    user_manager: BaseDialogManager = BgManagerFactoryImpl(mainloop_dialog.router).bg(bot, user_id, user_id)
    await user_manager.done()
    await user_manager.start(
        MainLoop.title,
        data={"user_tg_id": user_id, "game_id": None},
        show_mode=ShowMode.AUTO,
    )


async def game_info_getter(dialog_manager: DialogManager, **kwargs):
    game_id = dialog_manager.dialog_data["game_id"]
    game = await Game().get(id=game_id)
    participants_count = await Player().filter(game=game_id).count()
    return {
        "game_info": texts.render(
            "admin.game_info",
            game_name=game.name,
            game_id=game_id,
            start_date=game.start_date,
            end_date=game.end_date,
            participants_count=participants_count,
        )
    }


router.include_router(
    Dialog(
        Window(
            Const(texts.get("admin.editgame.select_prompt")),
            Column(
                Select(
                    Format("{item[name]}"),
                    id="select_game",
                    items="games",
                    item_id_getter=lambda x: x["id"],
                    on_click=on_game_selected,
                )
            ),
            Cancel(Const(texts.get("buttons.cancel"))),
            state=EditGame.game_id,
            getter=get_games_data,
        ),
        Window(
            Format(texts.get("admin.editgame.what_next")),
            Format(texts.get("admin.editgame.game_title"), when="game_name"),
            Row(
                Button(
                    Const(texts.get("admin.editgame.end_game")),
                    id="end_game",
                    on_click=on_action_clicked,
                    when="show_end_game",
                ),
            ),
            Row(
                Button(
                    Const(texts.get("admin.editgame.show_info")),
                    id="info",
                    on_click=lambda c, b, m: m.switch_to(EditGame.info),
                )
            ),
            Row(
                Button(
                    Const(texts.get("admin.editgame.back")),
                    id="back",
                    on_click=lambda c, w, m: m.switch_to(EditGame.game_id),
                )
            ),
            state=EditGame.edit,
            getter=get_selected_game_data,
        ),
        Window(
            Format("{game_info}"),
            Button(
                Const(texts.get("admin.editgame.back")),
                id="back",
                on_click=lambda c, b, m: m.switch_to(EditGame.edit),
            ),
            state=EditGame.info,
            getter=game_info_getter,
        ),
    )
)


@router.message(AdminFilter(), Command(commands=["editgame"]))
async def editgame(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(EditGame.game_id, show_mode=ShowMode.AUTO)


router.include_router(
    Dialog(
        Window(
            Const(texts.get("admin.editgame.confirm_end")),
            state=EndGame.confirm,
        )
    )
)


@router.message(AdminFilter(), Command(commands=["endgame"]))
async def endgame(
    message: Message,
    bot: Bot,
    dispatcher: Dispatcher,
    dialog_manager: DialogManager,
):
    active_game = await Game().filter(end_date=None).first()
    if not active_game:
        msg = await message.answer(texts.get("admin.no_active_games"))
        await asyncio.sleep(1)
        await msg.delete()
        return
    await handle_end_game(bot, dispatcher, active_game)
    msg = await message.answer(texts.get("admin.game_finished"))
    await asyncio.sleep(1)
    await msg.delete()


@router.message(Command(commands=["cancel"]))
async def cancel(message: Message, dialog_manager: DialogManager):
    await dialog_manager.done()


@router.message(AdminFilter(), Command(commands=["ban"]))
async def ban(
    message: Message,
    bot: Bot,
    dispatcher: Dispatcher,
    dialog_manager: DialogManager,
    command: CommandObject,
):
    logger.info("Ban command used with args %s", command.args)
    if not command.args:
        await message.answer(texts.get("admin.ban.ask_args"))
        return

    try:
        user_id, *reason = command.args.split(" ")
        user_id = int(user_id)
        reason = " ".join(reason)
    except ValueError:
        await message.answer(texts.get("admin.ban.tg_id_must_be_int"))
        return

    user = await User.get_or_none(tg_id=user_id)
    if not user:
        await message.answer(texts.get("admin.ban.user_not_found"))
        return
    await message.answer(await services.ban.ban(user, reason))
