import asyncio
import logging
from datetime import datetime
from uuid import UUID

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ContentType
from aiogram.filters import Command
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

from bot.filters.admin import AdminFilter
from bot.handlers import mainloop_dialog
from db.models import Chat, Game, Player, User
from services import settings
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
            BotCommand(command="/start", description="Начать работу с ботом"),
            BotCommand(
                command="/stats",
                description="Получить краткую статистику по боту",
            ),
            BotCommand(
                command="/creategame",
                description="Создать новую игру",
            ),
            BotCommand(
                command="/editgame",
                description="Посмотреть список всех игр",
            ),
            BotCommand(
                command="/getservertime",
                description="Получить текущее время на сервере",
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
        stats_text = (
            "Держи статистику текущей игры\n\n"
            f"<b>Игра: {info.name}</b>\n"
            f"Продолжительность с начала: {info.duration}\n"
            "\n"
            "<b>Топ по рейтингу:</b>\n"
            f"{info.rating_top}\n"
            "\n"
            "<b>Топ по убийствам:</b>\n"
            f"{info.killers_top}\n"
            "\n"
            "<b>Топ по смертям:</b>\n"
            f"{info.victims_top}"
        )
    else:
        stats_text = (
            "Держи краткую статистику по боту\n\n"
            f"В базе данных сейчас находится {user_count} уникальных пользователей\n"
            f"Из них {user_confirmed_count} имеют подтвержденные профили, что составляет {user_confirmed_count / user_count * 100:.1f}%\n"
            "Сейчас игра <b>не идет</b>\n"
            "\nДругие статистики будут добавляться по ходу дела, хозяин"
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
    users = await User().filter(is_in_game=False, status="confirmed").only("tg_id", "name").all()

    logger.debug(f"Notifying {len(users)} about new game {game.id}")

    tasks = []
    factory = BgManagerFactoryImpl(router=router)

    for user in users:
        message_task = send_notification(bot, user, f"Внимание, {user.mention_html()}!!")
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
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Task {i} failed: {result}")

    await manager.done()
    await callback.answer(
        f"Новая игра создана. Дата создания: {creation_date}",
        show_alert=True,
    )


@log_dialog_action("ADMIN_RESET_GAME_CREATION")
async def on_reset_game_creation(callback: CallbackQuery, button: Button, manager: DialogManager):
    manager.dialog_data["confirm"] = False

    await manager.switch_to(StartGame.name)


router.include_router(
    Dialog(
        Window(
            Const("Ну вот ты хочешь начать новую игру, как назовем ее?"),
            MessageInput(on_name_input, content_types=ContentType.TEXT),
            state=StartGame.name,
        ),
        Window(
            Const("Ну в принципе я получил все что мне надо было, стартуем?"),
            Column(
                Button(
                    Const("Да, погнали"),
                    on_click=on_final_confirmation,
                    id="startgame_confirm",
                ),
                Button(
                    Const("Нет, назад"),
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
        msg = await message.reply(
            text=(
                "Ты уверен, что хочешь начать новую игру, не закончив старую?\n\n"
                "Даже если уверен, то ты меня не научил так делать, так "
                "что начала закончи текущую активную игру\n"
                "Для этого можешь воспользоваться /editgame\n"
            )
        )
        await asyncio.sleep(10)
        await msg.delete()
        return
    await dialog_manager.start(StartGame.name, show_mode=ShowMode.AUTO)


@router.message(AdminFilter(), Command(commands=["getservertime"]))
async def getservertime(message: Message):
    msg = await message.reply(f"Сейчас на сервере: {datetime.now(settings.timezone)}")
    await asyncio.sleep(10)
    await msg.delete()


def parse_game_stage(game: Game) -> str:
    if game.end_date:
        return "Завершена"
    if game.start_date:
        return "Начата"
    logger.warning("start: %s; end: %s", game.start_date, game.end_date)
    return "err"


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
    await callback.answer(f"Вы выбрали игру {item_id}")
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
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=(
                f"Игра <b>{info.name}</b> закончилась!\n"
                f"Она продлилась {info.duration}\n"
                "\n"
                "<b>Топ по рейтингу:</b>\n"
                f"{info.rating_top}\n"
                "\n"
                "<b>Топ по убийствам:</b>\n"
                f"{info.killers_top}\n"
                "\n"
                "<b>Топ по смертям:</b>\n"
                f"{info.victims_top}\n"
                "\n"
                f"{get_personal_stats(user_id, info) if user_id else ''}"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        raise Exception(f"Failed to send message to chat {chat_id}") from e


def get_personal_stats(user_id: UUID, info: CreditsInfo):
    player_info = info.per_player.get(user_id)
    if not player_info:
        return "Нет данных"
    return (
        "<b>Ваша статистика:</b>\n"
        f"Ваш рейтинг к концу игры: <b>{player_info.rating}</b>\n"
        f"Ваш К/Д: <b>{player_info.kills}/{player_info.deaths}</b>\n"
        "Логи убийств:\n"
        f"{'\n'.join(player_info.log)}"
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
        "game_info": (
            f'Информация об игре "{game.name}" с айди {game_id}\n\n'
            f"Начало игры: {game.start_date}\n"
            f"Конец игры: {game.end_date}\n"
            f"\nКоличество участников: <b>{participants_count}</b>\n"
        )
    }


router.include_router(
    Dialog(
        Window(
            Const("Выбери, какую игру хочешь изменить:"),
            Column(
                Select(
                    Format("{item[name]}"),
                    id="select_game",
                    items="games",
                    item_id_getter=lambda x: x["id"],
                    on_click=on_game_selected,
                )
            ),
            Cancel(Const("Отмена")),
            state=EditGame.game_id,
            getter=get_games_data,
        ),
        Window(
            Format("Ну и что с ней делать будем?"),
            Format("Игра {game_name}", when="game_name"),
            Row(
                Button(
                    Const("Закончить игру"),
                    id="end_game",
                    on_click=on_action_clicked,
                    when="show_end_game",
                ),
            ),
            Row(
                Button(
                    Const("Посмотреть информацию"),
                    id="info",
                    on_click=lambda c, b, m: m.switch_to(EditGame.info),
                )
            ),
            Row(
                Button(
                    Const("Назад"),
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
                Const("Назад"),
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
            Const("Вы уверены что хотите завершить активную игру?"),
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
        msg = await message.answer("Сейчас нет активных игр чтобы завершать")
        await asyncio.sleep(1)
        await msg.delete()
        return
    await handle_end_game(bot, dispatcher, active_game)
    msg = await message.answer("Игра успешно завершена\nБот уходит на перезагрузку")
    await asyncio.sleep(1)
    await msg.delete()


@router.message(Command(commands=["cancel"]))
async def cancel(message: Message, dialog_manager: DialogManager):
    await dialog_manager.done()
