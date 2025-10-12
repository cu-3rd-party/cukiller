from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.text import Format, Const
from tgbot.misc.states import UsersStates


async def on_register(c, button, manager: DialogManager):
    await manager.switch_to(UsersStates.register)


async def on_play(c, button, manager: DialogManager):
    await manager.switch_to(UsersStates.play)


async def on_exit(c, button, manager: DialogManager):
    await c.message.answer("Пока 👋")
    await manager.done()


main_window = Window(
    Format("Привет, {event.from_user.first_name}!"),
    Row(
        Button(Const("📋 Register"), id="register", on_click=on_register),
        Button(
            Const("👤 Profile"),
            id="profile",
            on_click=lambda c, b, m: m.switch_to(UsersStates.profile),
        ),
    ),
    Row(
        Button(Const("🎮 Play"), id="play", on_click=on_play),
        Button(Const("🚪 Exit"), id="exit", on_click=on_exit),
    ),
    state=UsersStates.start,
)

register_window = Window(
    Format("📋 Регистрация пользователя..."),
    Button(
        Const("⬅️ Назад"),
        id="back",
        on_click=lambda c, b, m: m.switch_to(UsersStates.start),
    ),
    state=UsersStates.register,
)

play_window = Window(
    Format("🎮 Игра начинается..."),
    Button(
        Const("⬅️ Назад"),
        id="back",
        on_click=lambda c, b, m: m.switch_to(UsersStates.start),
    ),
    state=UsersStates.play,
)

profile_window = Window(
    Format("👤 Ваш профиль (здесь можно вывести данные из БД)"),
    Button(
        Const("⬅️ Назад"),
        id="back",
        on_click=lambda c, b, m: m.switch_to(UsersStates.start),
    ),
    state=UsersStates.profile,
)

router = Router()
router.include_router(
    Dialog(main_window, register_window, play_window, profile_window)
)


@router.message(CommandStart())
async def user_start(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(UsersStates.start)
