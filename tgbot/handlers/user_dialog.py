from aiogram import Router, Bot
from aiogram.enums import ContentType
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.text import Format, Const
from aiogram_dialog.widgets.media import Media

from tgbot.config import Config
from tgbot.misc.states import UserState
from tgbot.models.commands import add_or_create_user
from tgbot.services import admin_chat


async def on_name_input(
    message: Message, message_input: MessageInput, manager: DialogManager
):
    # TODO: add restrictions and validation
    manager.dialog_data["register_name"] = message.text
    await manager.next()


async def on_description_input(
    message: Message, message_input: MessageInput, manager: DialogManager
):
    # TODO: add restrictions and validation
    manager.dialog_data["register_description"] = message.text
    await manager.next()


async def set_department(event, button, manager, value):
    manager.dialog_data["register_departament"] = value
    await manager.next()  # or any next step if you have one


async def on_photo_input(
    message: Message, message_input: MessageInput, manager: DialogManager
):
    if not message.photo:
        await message.answer("Please send a photo.")
        return
    photo_id = message.photo[-1].file_id
    manager.dialog_data["register_photo"] = photo_id
    await manager.next()


async def on_finish(callback, button, manager: DialogManager):
    name = manager.dialog_data.get("register_name")
    desc = manager.dialog_data.get("register_description")
    dep = manager.dialog_data.get("register_departament")
    photo = manager.dialog_data.get("register_photo")

    # text = (
    #     f"<b>Имя:</b> {name}\n"
    #     f"<b>Поток:</b> {dep}\n"
    #     f"<b>Описание:</b> {desc}\n\n"
    # )
    #
    # await callback.message.answer_photo(photo=photo, caption=text, parse_mode="HTML")

    await manager.done()


register = [
    Window(
        Format("Привет! Сейчас зарегистрируем тебя. Как тебя звать?"),
        Format(
            "Помни, что вся информация которую ты подашь будет проходить модерацию, так что не лукавь"
        ),
        MessageInput(on_name_input, content_types=ContentType.TEXT),
        state=UserState.register_name,
    ),
    Window(
        Format("С какого ты потока? (разработка / ИИ / бизнес-аналитика)"),
        Row(
            Button(
                Const("разработка"),
                id="reg_dep_dev",
                on_click=lambda e, b, m: set_department(e, b, m, "Разработка"),
            ),
            Button(
                Const("ИИ"),
                id="reg_dep_ai",
                on_click=lambda e, b, m: set_department(e, b, m, "ИИ"),
            ),
            Button(
                Const("бизнес-аналитика"),
                id="reg_dep_ba",
                on_click=lambda e, b, m: set_department(
                    e, b, m, "Бизнес-аналитика"
                ),
            ),
        ),
        state=UserState.register_departament,
    ),
    Window(
        Format("А теперь напиши пару строк о себе"),
        MessageInput(on_description_input, content_types=ContentType.TEXT),
        state=UserState.register_description,
    ),
    Window(
        Format("Отлично, теперь отправь мне свою фотку"),
        MessageInput(on_photo_input, content_types=ContentType.PHOTO),
        state=UserState.register_photo,
    ),
    Window(
        Format("Все, шик, отправляю твой профиль на проверку?"),
        Row(
            Button(
                Format("Да, пожалуйста"), id="verification", on_click=on_finish
            ),
            Button(
                Format("Нет, давай сначала"),
                id="waiting_room",
                on_click=lambda e, b, m: m.switch_to(UserState.register_name),
            ),
        ),
        state=UserState.register_confirm,
    ),
]

router = Router()
user_dialog = Dialog(
    *register,
    name="user_dialog",
)
router.include_router(user_dialog)


@router.message(CommandStart())
async def user_start(
    message: Message, dialog_manager: DialogManager, bot: Bot, config: Config
):
    if message.from_user.id != message.chat.id:
        await message.answer(
            "этого бота можно использовать только в личных сообщениях"
        )
        return

    user, created = await add_or_create_user(message.from_user.id)
    if created:
        await admin_chat.send_message(
            f"user {user.tg_id} used the bot first time",
            bot=bot,
            config=config,
            tag="start",
        )

    if not user.profile:
        await dialog_manager.start(UserState.register_name)
    else:
        await dialog_manager.start(UserState.title)
