import logging
from datetime import datetime

from aiogram import Router, Bot, types
from aiogram.enums import ContentType
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    BotCommand,
    BotCommandScopeChat,
    CallbackQuery,
)
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.api.entities import StartMode, ShowMode
from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Column, Button, Select, Row
from aiogram_dialog.widgets.text import Format, Const

from bot.filters.admin import AdminFilter
from bot.misc.states.editgame import EditGame
from bot.misc.states.participation import ParticipationForm
from bot.misc.states.startgame import StartGame
from db.models import User, Game, Player
from services.logging import log_dialog_action

logger = logging.getLogger(__name__)

router = Router()


@router.message(AdminFilter(), CommandStart())
async def admin_start(message: Message, bot: Bot):
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
        scope=BotCommandScopeChat(chat_id=message.chat.id),
    )
    await message.reply(
        text=(
            "Привет, админ!\n"
            "Добавил тебе список команд в менюшку, полюбуйся)\n"
        )
    )


@router.message(AdminFilter(), Command(commands=["stats"]))
async def stats(message: Message, bot: Bot):
    user_count = await User().all().count()
    user_confirmed_count = await User().filter(status="confirmed").count()
    current_game = await Game().filter(end_date=None).first()
    game_status = (
        f"Сейчас игра <b>идет</b>, она началась {current_game.start_date}"
        if current_game
        else "Сейчас игра <b>не идет</b>"
    )
    await message.reply(
        text=(
            "Держи краткую статистику по боту\n\n"
            f"В базе данных сейчас находится {user_count} уникальных пользователей\n"
            f"Из них {user_confirmed_count} имеют подтвержденные профили, что составляет {user_confirmed_count / user_count * 100}%\n"
            f"{game_status}\n"
            "\nДругие статистики будут добавляться по ходу дела, хозяин"
        )
    )


@log_dialog_action("ADMIN_CAMPAIGN_NAME_INPUT")
async def on_name_input(
    message: Message, message_input: MessageInput, manager: DialogManager
):
    manager.dialog_data["name"] = message.text.strip()
    await manager.next()


@log_dialog_action("ADMIN_CAMPAIGN_DESCRIPTION_INPUT")
async def on_description_input(
    message: Message, message_input: MessageInput, manager: DialogManager
):
    manager.dialog_data["description"] = message.text.strip()
    await manager.next()


@log_dialog_action("ADMIN_CAMPAIGN_FINAL_CONFIRMATION")
async def on_final_confirmation(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    **kwargs,
):
    bot = manager.event.bot
    manager.dialog_data["confirm"] = True

    creation_date = datetime.now()
    game = await Game().create(
        name=manager.dialog_data.get("name") or "test",
        start_date=creation_date,
    )

    users = await User().filter(is_in_game=False, status="confirmed").all()
    logger.debug(f"Notifying {len(users)} about new game {game.id}")
    for user in users:
        await bot.send_message(
            user.tg_id,
            text=f"Внимание, {types.User(id=user.tg_id, is_bot=False, first_name=user.name).mention_html()}!!",
            parse_mode="HTML",
        )
        user_dialog_manager = BgManagerFactoryImpl(router=router).bg(
            bot=bot,
            user_id=user.tg_id,
            chat_id=user.tg_id,
        )
        await user_dialog_manager.start(
            ParticipationForm.confirm,
            data={
                "game_id": (game and game.id) or None,
                "user_tg_id": user.tg_id,
            },
            mode=StartMode.NEW_STACK,
            show_mode=ShowMode.DELETE_AND_SEND,
        )

    await manager.done()
    await callback.message.reply(
        f"Новая игра создана. Дата создания: {creation_date}"
    )


@log_dialog_action("ADMIN_RESET_GAME_CREATION")
async def on_reset_game_creation(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    manager.dialog_data["confirm"] = False

    await manager.switch_to(StartGame.name)


create_game_dialog = Dialog(
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
router.include_router(create_game_dialog)


@router.message(AdminFilter(), Command(commands=["creategame"]))
async def creategame(
    message: Message, bot: Bot, dialog_manager: DialogManager
):
    if await Game().filter(end_date=None).exists():
        await message.reply(
            text=(
                "Ты уверен, что хочешь начать новую игру, не закончив старую?\n\n"
                "Даже если уверен, то ты меня не научил так делать, так "
                "что начала закончи текущую активную игру\n"
                "Для этого можешь воспользоваться /endgame\n"
            )
        )
        return
    await dialog_manager.start(StartGame.confirm)


@router.message(AdminFilter(), Command(commands=["getservertime"]))
async def getservertime(message: Message):
    await message.reply(f"Сейчас на сервере: {datetime.now()}")


def parse_game_stage(game: Game) -> str:
    if game.end_date:
        return "Завершена"
    elif game.start_date:
        return "Начата"
    else:
        logger.warn("start: %s; end: %s", game.start_date, game.end_date)
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
async def on_game_selected(
    callback: CallbackQuery, widget, manager: DialogManager, item_id: str
):
    await callback.answer(f"Вы выбрали игру {item_id}")
    manager.dialog_data["game_id"] = item_id
    await manager.next()


@log_dialog_action("ADMIN_GAME_ACTION_CLICKED")
async def on_action_clicked(
    callback: CallbackQuery, widget, manager: DialogManager
):
    action = widget.widget_id
    game = await Game.get(id=manager.dialog_data["game_id"])
    logger.info(action)
    if action == "start_game":
        game.start_date = datetime.now()
    elif action == "end_game":
        game.end_date = datetime.now()
        await User().all().update(is_in_game=False)
    await game.save()
    logger.info(game.start_date)
    await callback.message.delete()
    await manager.switch_to(EditGame.edit)


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


game_edit_dialog = Dialog(
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
router.include_router(game_edit_dialog)


@router.message(AdminFilter(), Command(commands=["editgame"]))
async def editgame(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(EditGame.game_id)
