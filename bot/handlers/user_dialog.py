from aiogram import Router, Bot, Dispatcher
from aiogram.enums import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram_dialog import Dialog, DialogManager, Window, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.text import Format, Const

from bot.misc.states import RegisterForm, MainLoop
from bot.services.admin_chat import AdminChatService
from db.models import User

router = Router()


async def on_name_input(
    message: Message, message_input: MessageInput, manager: DialogManager
):
    # TODO: add restrictions and validation
    manager.dialog_data["name"] = message.text
    await manager.next()


async def on_description_input(
    message: Message, message_input: MessageInput, manager: DialogManager
):
    # TODO: add restrictions and validation
    manager.dialog_data["description"] = message.text
    await manager.next()


async def set_department(event, button, manager, value):
    manager.dialog_data["departament"] = value
    await manager.next()  # or any next step if you have one


async def on_photo_input(
    message: Message, message_input: MessageInput, manager: DialogManager
):
    if not message.photo:
        await message.answer("Please send a photo.")
        return
    photo_id = message.photo[-1].file_id
    manager.dialog_data["photo"] = photo_id
    await manager.next()


async def on_finish(callback: CallbackQuery, button, manager: DialogManager):
    bot: Bot = manager.event.bot
    chat_id: int = callback.message.chat.id

    name = manager.dialog_data.get("name")
    desc = manager.dialog_data.get("description")
    dep = manager.dialog_data.get("departament")
    photo = manager.dialog_data.get("photo")

    text = (
        f"<b>Имя:</b> {name}\n<b>Поток:</b> {dep}\n<b>Описание:</b> {desc}\n\n"
    )

    admin_chat = AdminChatService(bot=bot)

    await admin_chat.send_profile_confirmation_request(
        key="logs",
        photo=photo,
        user_id=callback.from_user.id,
        text=text,
        tag="profile_confirm",
    )

    await bot.send_message(
        chat_id=chat_id, text="Все, отправил на проверку", parse_mode="HTML"
    )

    await manager.done()


register = [
    Window(
        Format("Привет! Сейчас зарегистрируем тебя. Как тебя звать?"),
        Format(
            "Помни, что вся информация которую ты подашь будет проходить модерацию, так что не лукавь"
        ),
        MessageInput(on_name_input, content_types=ContentType.TEXT),
        state=RegisterForm.name,
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
        state=RegisterForm.departament,
    ),
    Window(
        Format("А теперь напиши пару строк о себе"),
        MessageInput(on_description_input, content_types=ContentType.TEXT),
        state=RegisterForm.description,
    ),
    Window(
        Format("Отлично, теперь отправь мне свою фотку"),
        MessageInput(on_photo_input, content_types=ContentType.PHOTO),
        state=RegisterForm.photo,
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
                on_click=lambda e, b, m: m.switch_to(RegisterForm.name),
            ),
        ),
        state=RegisterForm.confirm,
    ),
]

register_dialog = Dialog(
    *register,
    name="user_dialog",
)
router.include_router(register_dialog)


@router.message(CommandStart())
async def user_start(
    message: Message,
    dialog_manager: DialogManager,
    bot: Bot,
    state: FSMContext,
):
    await state.clear()

    telegram_user = message.from_user

    if telegram_user is None:
        await message.answer("Не удалось определить пользователя.")
        return

    if message.from_user.id != message.chat.id:
        await message.answer(
            "этого бота можно использовать только в личных сообщениях"
        )
        return

    telegram_user = message.from_user
    user, created = await User().get_or_create(
        tg_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
    )
    await user.save()

    if created:
        mention_text = (
            f"@{message.from_user.username}"
            if message.from_user.username is not None
            else None
        )
        admin_chat = AdminChatService(bot=bot)
        await admin_chat.send_message(
            key="logs",
            text=f"Пользователь {message.from_user.mention_html(mention_text)} использовал команду /start в первый раз",
            tag="start",
        )

    if not user.profile:
        await dialog_manager.start(RegisterForm.name)
    else:
        await dialog_manager.start(MainLoop.title)
