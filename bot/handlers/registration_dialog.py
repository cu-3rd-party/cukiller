import logging

from aiogram import Router, Bot, types
from aiogram.enums import ContentType
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, Group, Column
from aiogram_dialog.widgets.text import Format, Const

from bot.filters.admin import AdminFilter
from bot.filters.confirmed import (
    ConfirmedFilter,
    PendingFilter,
    ProfileNonexistentFilter,
)
from bot.filters.debug import DebugFilter
from bot.misc.states import RegisterForm
from services.admin_chat import AdminChatService
from db.models import User
from settings import settings

logger = logging.getLogger(__name__)

router = Router()

# Constants for course types and numbers
COURSE_TYPES = {"bachelor": "Бакалавр", "master": "Магистр", "other": "Другое"}

COURSE_NUMBERS_RU = {
    "bachelor": ["1", "2", "3", "4"],
    "master": ["1", "2"],
    "other": ["сотрудник ЦУ", "аспирант"],
}

COURSE_NUMBERS_EN = {
    "bachelor": ["1", "2", "3", "4"],
    "master": ["1", "2"],
    "other": ["worker", "aspirant"],
}

GROUP_NAMES_RU = ["Разработка", "ИИ", "Бизнес-аналитика"]
GROUP_NAMES_EN = ["dev", "ai", "ba"]


async def on_name_input(
    message: Message, message_input: MessageInput, manager: DialogManager
):
    name = message.text.strip()

    manager.dialog_data["name"] = name
    await manager.next()


async def on_course_type_selected(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    course_type: str,
):
    manager.dialog_data["course_type"] = course_type
    if course_type == "bachelor":
        await manager.switch_to(RegisterForm.course_number_bachelor)
    elif course_type == "master":
        await manager.switch_to(RegisterForm.course_number_master)
    else:
        await manager.switch_to(RegisterForm.course_other)


async def on_course_number_selected(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    course_number: str,
):
    manager.dialog_data["course_number"] = course_number

    course_type = manager.dialog_data.get("course_type")
    if course_type == "bachelor":
        manager.dialog_data["db_course_number"] = int(course_number)
        manager.dialog_data["type"] = "bachelor"
        await manager.switch_to(RegisterForm.group_name)
    elif course_type == "master":
        manager.dialog_data["db_course_number"] = int(course_number)
        manager.dialog_data["type"] = "master"
        await manager.switch_to(RegisterForm.about)
    else:  # other
        manager.dialog_data["db_course_number"] = None
        manager.dialog_data["type"] = course_number
        await manager.switch_to(RegisterForm.about)


async def on_group_selected(
    callback: CallbackQuery,
    button: Button,
    manager: DialogManager,
    group_name: str,
):
    manager.dialog_data["group_name"] = group_name
    await manager.next()


async def on_about_input(
    message: Message, message_input: MessageInput, manager: DialogManager
):
    about_text = message.text.strip()

    # TODO: add validation

    manager.dialog_data["about_user"] = about_text
    await manager.next()


async def on_photo_input(
    message: Message, message_input: MessageInput, manager: DialogManager
):
    if not message.photo:
        await message.answer("Пожалуйста, отправь фотографию.")
        return

    # Get the highest quality photo
    photo_id = message.photo[-1].file_id
    manager.dialog_data["photo"] = photo_id
    await manager.next()


async def on_final_confirmation(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    bot: Bot = manager.middleware_data["bot"]
    user_data = manager.dialog_data

    # Save user to database
    telegram_user = callback.from_user
    user = await User.get_or_none(tg_id=telegram_user.id)

    if not user:
        user = User(tg_id=telegram_user.id)

    user.tg_username = telegram_user.username
    user.name = user_data.get("name")
    user.course_number = user_data.get("db_course_number")
    user.group_name = user_data.get("group_name")
    user.about_user = user_data.get("about_user")
    user.photo = user_data.get("photo")
    user.type = user_data.get("type")
    user.status = "pending"
    user.rating = settings.DEFAULT_RATING

    await user.save()

    # Prepare text for admin confirmation
    course_type_display = COURSE_TYPES.get(user_data.get("course_type"), "")
    course_number_display = user_data.get("course_number", "")

    text = (
        f"<b>Новый профиль для проверки:</b>\n\n"
        f"<b>Имя:</b> {user_data.get('name', 'Не указано')}\n"
        f"<b>Тип обучения:</b> {course_type_display}\n"
        f"<b>Курс/Статус:</b> {course_number_display}\n"
        f"<b>Поток:</b> {user_data.get('group_name', 'Не указано')}\n"
        f"<b>О себе:</b> {user_data.get('about_user', 'Не указано')}\n"
        f"<b>Username:</b> @{telegram_user.username if telegram_user.username else 'Не указан'}\n"
        f"<b>ID:</b> {telegram_user.id}"
    )

    # Send to admin for verification
    admin_chat = AdminChatService(bot=bot)
    await admin_chat.send_profile_confirmation_request(
        key="logs",
        photo=user_data.get("photo"),
        tg_id=telegram_user.id,
        text=text,
        tag="profile_confirm",
    )

    await callback.message.answer(
        "Твой профиль отправлен на проверку! "
        "Мы уведомим тебя, когда он будет одобрен."
    )

    await manager.done()


async def on_restart_registration(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    await manager.switch_to(RegisterForm.name)


# Widget factories
def create_course_type_buttons():
    return Column(
        *[
            Button(
                Const(display_name),
                id=f"type_{course_type}",
                on_click=lambda e,
                b,
                m,
                ct=course_type: on_course_type_selected(e, b, m, ct),
            )
            for course_type, display_name in COURSE_TYPES.items()
        ]
    )


def create_course_number_buttons(course_type: str):
    return Group(
        *[
            Button(
                Const(number_ru),
                id=f"course_{course_type}_{number_en.replace(' ', '_').replace('-', '_')}",
                on_click=lambda e,
                b,
                m,
                cn=number_ru: on_course_number_selected(e, b, m, cn),
            )
            for number_ru, number_en in zip(
                COURSE_NUMBERS_RU.get(course_type, []),
                COURSE_NUMBERS_EN.get(course_type, []),
            )
        ],
        width=2,
    )


def create_group_buttons():
    return Column(
        *[
            Button(
                Const(group_name_ru),
                id=f"group_{group_name_en.replace(' ', '_').replace('-', '_')}",
                on_click=lambda e, b, m, gn=group_name_ru: on_group_selected(
                    e, b, m, gn
                ),
            )
            for group_name_ru, group_name_en in zip(
                GROUP_NAMES_RU, GROUP_NAMES_EN
            )
        ]
    )


# Dialog windows
register_dialog = Dialog(
    # Name input
    Window(
        Format("Привет! Сейчас зарегистрируем тебя. Как тебя звать?"),
        Format(
            "Помни, что вся информация которую ты подашь будет проходить модерацию, так что не лукавь"
        ),
        MessageInput(on_name_input, content_types=ContentType.TEXT),
        state=RegisterForm.name,
    ),
    # Course type selection
    Window(
        Const("Выбери свою форму обучения:"),
        create_course_type_buttons(),
        Button(
            Const("Назад"),
            id="back",
            on_click=lambda c, b, m: m.switch_to(RegisterForm.name),
        ),
        state=RegisterForm.course_type,
    ),
    # Bachelor course number selection
    Window(
        Const("Выбери свой курс (бакалавриат):"),
        create_course_number_buttons("bachelor"),
        Button(
            Const("Назад"),
            id="back",
            on_click=lambda c, b, m: m.switch_to(RegisterForm.course_type),
        ),
        state=RegisterForm.course_number_bachelor,
    ),
    # Master course number selection
    Window(
        Const("Выбери свой курс (магистратура):"),
        create_course_number_buttons("master"),
        Button(
            Const("Назад"),
            id="back",
            on_click=lambda c, b, m: m.switch_to(RegisterForm.course_type),
        ),
        state=RegisterForm.course_number_master,
    ),
    # Other status selection
    Window(
        Const("Уточни свой статус:"),
        create_course_number_buttons("other"),
        Button(
            Const("Назад"),
            id="back",
            on_click=lambda c, b, m: m.switch_to(RegisterForm.course_type),
        ),
        state=RegisterForm.course_other,
    ),
    # Group selection
    Window(
        Const("Выбери свой поток:"),
        create_group_buttons(),
        Button(
            Const("Назад"),
            id="back",
            on_click=lambda c, b, m: m.switch_to(RegisterForm.course_type),
        ),
        state=RegisterForm.group_name,
    ),
    # About yourself
    Window(
        Const(
            "Теперь расскажи немного о себе:\n"
            "(Интересы, хобби, чем занимаешься - это поможет другим участникам познакомиться с тобой)"
        ),
        Button(
            Const("Назад"),
            id="back",
            on_click=lambda c, b, m: m.switch_to(RegisterForm.course_type),
        ),
        MessageInput(on_about_input, content_types=ContentType.TEXT),
        state=RegisterForm.about,
    ),
    # Photo upload
    Window(
        Const(
            "Отправь свою фотографию:\nЕё будут видеть другие участники игры"
        ),
        Button(
            Const("Назад"),
            id="back",
            on_click=lambda c, b, m: m.switch_to(RegisterForm.about),
        ),
        MessageInput(on_photo_input, content_types=ContentType.PHOTO),
        state=RegisterForm.photo,
    ),
    # Final confirmation
    Window(
        Const("Всё готово! Проверь свои данные и отправляй на проверку:"),
        Column(
            Button(
                Const("Отправить на проверку"),
                id="confirm_submit",
                on_click=on_final_confirmation,
            ),
            Button(
                Const("Начать заново"),
                id="restart",
                on_click=on_restart_registration,
            ),
        ),
        state=RegisterForm.confirm,
    ),
    name="user_registration_dialog",
)

router.include_router(register_dialog)


@router.message(CommandStart(), ProfileNonexistentFilter(), ~AdminFilter())
async def user_start(
    message: Message,
    dialog_manager: DialogManager,
    bot: Bot,
):
    await dialog_manager.reset_stack()
    await dialog_manager.start(RegisterForm.name)


@router.message(CommandStart(), PendingFilter(), ~AdminFilter())
async def user_start(
    message: Message,
    dialog_manager: DialogManager,
    bot: Bot,
):
    queue_len = len(await User.filter(status="pending").all())
    await message.reply(
        f"Пожалуйста, подождите. Ваш профиль находится на проверке\n\nВсего в очереди находится <b>{queue_len}</b> человек"
    )


@router.message(
    Command(commands=["fastreg"]),
    ProfileNonexistentFilter(),
    ~AdminFilter(),
    DebugFilter(),
)
async def user_fast_reg(
    message: Message,
    dialog_manager: DialogManager,
    bot: Bot,
    user: types.User,
):
    await dialog_manager.reset_stack()
    await User().update_or_create(
        tg_id=user.tg_id,
        tg_username=user.tg_username,
        defaults={
            "name": user.name,
            "course_number": 1,
            "group_name": "Разработка",
            "about_user": "test user",
            "photo": "fastreg",
            "type": "fastreg",
            "status": "confirmed",
            "rating": settings.DEFAULT_RATING,
        },
    )
    await message.answer("fastreg success")
