from datetime import datetime

from aiogram import Router, Bot
from aiogram.enums import ContentType
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    BotCommand,
    BotCommandScope,
    BotCommandScopeChat, CallbackQuery,
)
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Column, Button
from aiogram_dialog.widgets.text import Format, Const

from bot.filters.admin import AdminFilter
from bot.misc.states.startgame import StartGame
from db.models import User, Game

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
                command="/startgame",
                description="Начать новую игру",
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
    game_status = f"Сейчас игра <b>идет</b>, она началась {current_game.start_date}" if current_game else "Сейчас игра <b>не идет</b>"
    await message.reply(
        text=(
            "Держи краткую статистику по боту\n\n"
            f"В базе данных сейчас находится {user_count} уникальных пользователей\n"
            f"Из них {user_confirmed_count} имеют подтвержденные профили, что составляет {user_confirmed_count / user_count * 100}%\n"
            f"{game_status}\n"
            "\nДругие статистики будут добавляться по ходу дела, хозяин"
        )
    )


async def on_name_input(
        message: Message, message_input: MessageInput, manager: DialogManager
):
    manager.dialog_data["name"] = message.text.strip()
    await manager.next()


async def on_description_input(
        message: Message, message_input: MessageInput, manager: DialogManager
):
    manager.dialog_data["description"] = message.text.strip()
    await manager.next()

async def on_final_confirmation(
        callback: CallbackQuery, button: Button, manager: DialogManager
):
    manager.dialog_data["confirm"] = True

    await Game().create(
        name=manager.dialog_data["name"],
        description=manager.dialog_data["description"],
        start_date=datetime.now(),
        visibility="public", # ну сорян, пока что свои лобби не в планах делать
    )

    # TODO: notify everyone about the new game

    await manager.done()

create_game_dialog = Dialog(
    Window(
        Const("Ну вот ты хочешь начать новую игру, как назовем ее?"),
        MessageInput(on_name_input, content_types=ContentType.TEXT),
        state=StartGame.name,
    ),
    Window(
        Const("Супер, какое описание сделаем ей?"),
        MessageInput(on_description_input, content_types=ContentType.TEXT),
        state=StartGame.description,
    ),
    Window(
        Const("Ну в принципе я получил все что мне надо было, стартуем?"),
        Column(
            Button(Const("Да, погнали"), on_click=on_final_confirmation, id="startgame_confirm")
        ),
        state=StartGame.confirm,
    ),
)
router.include_router(create_game_dialog)

@router.message(AdminFilter(), Command(commands=["startgame"]))
async def startgame(message: Message, bot: Bot, dialog_manager: DialogManager):
    if await Game().filter(end_date=None).exists():
        await message.reply(
            text=(
                "Ты уверен, что хочешь начать новую игру, не закончив старую?\n\n"
                "Даже если уверен, то ты меня не научил так делать, так "
                "что начала закончи текущую активную игру\n"
            )
        )
        return
    await dialog_manager.start(StartGame.name)
