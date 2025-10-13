from aiogram import Router, Bot, Dispatcher
from aiogram.enums import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram_dialog import Dialog, DialogManager, Window, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row
from aiogram_dialog.widgets.text import Format, Const

from bot.filters.ingame import NotInGameFilter
from bot.misc.states import RegisterForm, MainLoop
from bot.services.admin_chat import AdminChatService
from db.models import User

router = Router()

COURSE_NUMBERS = ["бак1", "бак2", "бак3", "бак4", "маг1", "маг2", "другое"]


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


async def set_group_name(event, button, manager, value):
    manager.dialog_data["group_name"] = value
    await manager.next()


async def set_course_number(event, button, manager: DialogManager, value: str):
    if value not in COURSE_NUMBERS:
        await event.answer(
            "Пожалуйста, выбери один из предложенных вариантов."
        )
        return
    manager.dialog_data["course_number"] = COURSE_NUMBERS.index(value) + 1
    await manager.next()


def make_course_button(value: str):
    safe_id = f"reg_course_{COURSE_NUMBERS.index(value)}"  # e.g., reg_course_0
    return Button(
        Const(value),
        id=safe_id,
        on_click=lambda e, b, m, v=value: set_course_number(e, b, m, v),
    )


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
    dep = manager.dialog_data.get("group_name")
    photo = manager.dialog_data.get("photo")
    course_number = manager.dialog_data.get("course_number")

    text = (
        f"<b>Имя:</b> {name}\n"
        f"<b>Курс:</b> {COURSE_NUMBERS[course_number - 1]}\n"
        f"<b>Поток:</b> {dep}\n"
        f"<b>Описание:</b> {desc}\n\n"
    )

    admin_chat = AdminChatService(bot=bot)

    await admin_chat.send_profile_confirmation_request(
        key="logs",
        photo=photo,
        update_data={
            "tg_id": callback.message.from_user.id,
            "tg_username": callback.message.from_user.username,
            "name": name,
            "about_user": desc,
            "group_name": dep,
            "photo": photo,
            "course_number": course_number,
        },
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
        Format("С какого ты курса?"),
        Row(
            *(make_course_button(i) for i in ["бак1", "бак2", "бак3", "бак4"])
        ),
        Row(*(make_course_button(i) for i in ["маг1", "маг2"])),
        Row(make_course_button("другое")),
        state=RegisterForm.course_number,
    ),
    Window(
        Format("С какого ты потока? (разработка / ИИ / бизнес-аналитика)"),
        Row(
            Button(
                Const("разработка"),
                id="reg_dep_dev",
                on_click=lambda e, b, m: set_group_name(e, b, m, "Разработка"),
            ),
            Button(
                Const("ИИ"),
                id="reg_dep_ai",
                on_click=lambda e, b, m: set_group_name(e, b, m, "ИИ"),
            ),
            Button(
                Const("бизнес-аналитика"),
                id="reg_dep_ba",
                on_click=lambda e, b, m: set_group_name(
                    e, b, m, "Бизнес-аналитика"
                ),
            ),
        ),
        state=RegisterForm.group_name,
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


@router.message(CommandStart(), NotInGameFilter())
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
        tg_username=telegram_user.username,
        given_name=telegram_user.first_name,
        family_name=telegram_user.last_name,
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

    await dialog_manager.start(RegisterForm.name)
