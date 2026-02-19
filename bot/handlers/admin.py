import asyncio
import contextlib
import logging
from datetime import datetime
from uuid import UUID

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ContentType
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError
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

from db.models import Chat, Game, KillEvent, Player, User
from filters.admin import AdminFilter
from handlers import mainloop_dialog
from services import (
    AdminChatService,
    EditGame,
    EndGame,
    MainLoop,
    MatchmakingService,
    StartGame,
    log_dialog_action,
    recalc_game_ratings,
    settings,
    texts,
)
from services.ban import ban as ban_user
from services.credits import CreditsInfo
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
            BotCommand(
                command="/rollbackkill",
                description=texts.get("admin.command.rollbackkill"),
            ),
        ],
        scope=BotCommandScopeChat(chat_id=chat_id),
    )


@router.message(AdminFilter(), Command(commands=["stats"]))
async def stats(message: Message, bot: Bot):
    # TODO: API CALL
    user_count = None
    # TODO: API CALL
    user_confirmed_count = None
    # TODO: API CALL
    current_game = None

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
        chat_id=user.tg_id,
        text=text,
        parse_mode="HTML",
    )
    return asyncio.create_task(delete_later(bot, msg.chat.id, msg.message_id))


async def delete_later(bot: Bot, chat_id: int, msg_id: int):
    await asyncio.sleep(10)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=msg_id)
    except TelegramAPIError as exc:
        logger.warning("Failed to delete message %s: %s", msg_id, exc)


@log_dialog_action("ADMIN_CAMPAIGN_FINAL_CONFIRMATION")
async def on_final_confirmation(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    **kwargs: object,
):
    bot = manager.event.bot
    manager.dialog_data["confirm"] = True

    creation_date = datetime.now(settings.timezone)
    # TODO: API CALL
    game = None
    users = []

    logger.debug("Notifying %s about new game %s", len(users), game.id)

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
                    logger.error("Task %s failed: %s", i, result)

    await manager.done()
    await callback.answer(
        texts.render("admin.game_created_alert", creation_date=creation_date),
        show_alert=True,
    )


@log_dialog_action("ADMIN_RESET_GAME_CREATION")
async def on_reset_game_creation(callback: CallbackQuery, button: Button, manager: DialogManager):
    manager.dialog_data["confirm"] = False

    # TODO: API CALL


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
    # TODO: API CALL
    if False:
        msg = await message.reply(text=texts.get("admin.creategame.already_running"))
        await asyncio.sleep(10)
        # TODO: API CALL
        return
    # TODO: API CALL
    await dialog_manager.start(StartGame.name, show_mode=ShowMode.AUTO)


@router.message(AdminFilter(), Command(commands=["getservertime"]))
async def getservertime(message: Message):
    msg = await message.reply(texts.render("admin.server_time", server_time=datetime.now(settings.timezone)))
    await asyncio.sleep(10)
    # TODO: API CALL


def parse_game_stage(game: Game) -> str:
    if game.end_date:
        return texts.get("admin.game_stage.finished")
    if game.start_date:
        return texts.get("admin.game_stage.started")
    logger.warning("start: %s; end: %s", game.start_date, game.end_date)
    return texts.get("admin.game_stage.error")


async def get_games_data(**kwargs: object):
    # TODO: API CALL
    games = None
    return {
        "games": [
            {
                "id": game.id,
                "name": f"{game.name} - {parse_game_stage(game)}",
            }
            for game in games
        ]
    }


async def get_selected_game_data(dialog_manager: DialogManager, **kwargs: object):
    game_id = dialog_manager.dialog_data.get("game_id")
    if not game_id:
        return {}
    # TODO: API CALL
    game = None
    return {
        "game_name": game.name,
        "show_end_game": game.start_date is not None and game.end_date is None,
    }


@log_dialog_action("ADMIN_GAME_SELECTED")
async def on_game_selected(callback: CallbackQuery, widget: Select, manager: DialogManager, item_id: str):
    await callback.answer(texts.render("admin.game_selected", item_id=item_id))
    manager.dialog_data["game_id"] = item_id
    await manager.next()


@log_dialog_action("ADMIN_GAME_ACTION_CLICKED")
async def on_action_clicked(callback: CallbackQuery, widget: Button, manager: DialogManager):
    action = widget.widget_id
    # TODO: API CALL
    game = None
    logger.info(action)
    if action == "start_game":
        await handle_start_game(callback, game)
    elif action == "end_game":
        await handle_end_game(callback.bot, manager.middleware_data["dispatcher"], game)
    logger.info(game.start_date)
    # TODO: API CALL
    # TODO: API CALL


async def handle_start_game(callback: CallbackQuery, game: Game):
    game.start_date = datetime.now(settings.timezone)
    # TODO: API CALL
    await MatchmakingService().reset_queues()


async def handle_end_game(bot: Bot, dp: Dispatcher, game: Game):
    """Handle game ending and send credits to all participants."""
    game.end_date = datetime.now(settings.timezone)
    # TODO: API CALL
    await MatchmakingService().reset_queues()

    # TODO: API CALL
    participants, info, discussion = [], None, None

    send_tasks = [
        *[user_endgame(bot, dp, user, info) for user in participants],
        send_game_credits(bot, info, discussion.chat_id),
    ]

    results = await asyncio.gather(*send_tasks, return_exceptions=True)

    for user, result in zip(participants, results, strict=False):
        if isinstance(result, Exception):
            logger.error("Failed to send credits to user %s: %s", user.id, result)

    # TODO: API CALL


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
    except TelegramAPIError as exc:
        msg = f"Failed to send message to chat {chat_id}"
        raise RuntimeError(msg) from exc


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


async def game_info_getter(dialog_manager: DialogManager, **kwargs: object):
    game_id = dialog_manager.dialog_data["game_id"]
    # TODO: API CALL
    game = None
    # TODO: API CALL
    participants_count = None
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
    # TODO: API CALL
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
    # TODO: API CALL
    active_game = None
    if not active_game:
        msg = await message.answer(texts.get("admin.no_active_games"))
        await asyncio.sleep(1)
        # TODO: API CALL
        return
    await handle_end_game(bot, dispatcher, active_game)
    msg = await message.answer(texts.get("admin.game_finished"))
    await asyncio.sleep(1)
    # TODO: API CALL


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

    # TODO: API CALL
    user = None
    if not user:
        await message.answer(texts.get("admin.ban.user_not_found"))
        return
    await message.answer(await ban_user(user, reason))


@router.message(AdminFilter(), Command(commands=["rollbackkill"]))
async def rollbackkill(message: Message, bot: Bot, command: CommandObject):
    if not command.args:
        await message.answer(texts.get("admin.rollbackkill.ask_args"))
        return

    try:
        kill_event_id = UUID(command.args.strip())
    except ValueError:
        await message.answer(texts.get("admin.rollbackkill.id_must_be_uuid"))
        return

    # TODO: API CALL
    kill_event: KillEvent | None = None
    if not kill_event:
        await message.answer(texts.get("admin.rollbackkill.not_found"))
        return

    if kill_event.status != "confirmed":
        await message.answer(texts.render("admin.rollbackkill.not_confirmed", status=kill_event.status))
        return

    kill_event.status = "canceled"
    kill_event.killer_confirmed = False
    kill_event.killer_confirmed_at = None
    kill_event.victim_confirmed = False
    kill_event.victim_confirmed_at = None
    # TODO: API CALL

    await recalc_game_ratings(kill_event.game)

    # TODO: API CALL
    killer_player = None
    # TODO: API CALL
    victim_player = None

    await AdminChatService(bot).send_message(
        key="discussion",
        text=texts.render(
            "admin.rollbackkill.discussion",
            kill_event_id=kill_event.id,
            killer=kill_event.killer.mention_html(),
            victim=kill_event.victim.mention_html(),
            killer_rating=killer_player.rating if killer_player else texts.get("common.unknown"),
            victim_rating=victim_player.rating if victim_player else texts.get("common.unknown"),
        ),
    )

    await message.answer(texts.render("admin.rollbackkill.done", kill_event_id=kill_event.id))
