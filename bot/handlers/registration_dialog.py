import logging

from aiogram import Bot, Router
from aiogram.enums import ContentType
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, ShowMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Column, Group
from aiogram_dialog.widgets.text import Const, Format

from bot.filters.confirmed import PendingFilter, ProfileNonexistentFilter
from db.models import PendingProfile, User
from services.admin_chat import AdminChatService
from services.logging import log_dialog_action
from services.states import RegisterForm
from services.strings import SafeStringConfig, is_safe

logger = logging.getLogger(__name__)

router = Router()

# ---------------------------------------------
# CONSTANTS
# ---------------------------------------------

COURSE_TYPES = {
    "bachelor": "Бакалавр",
    "master": "Магистр",
    "worker": "Сотрудник ЦУ",
}

COURSE_NUMBERS = {
    "bachelor": ["1", "2", "3", "4"],
    "master": ["1", "2"],
}

GROUP_NAMES = ["Разработка", "ИИ", "Бизнес-аналитика"]


# ---------------------------------------------
# HELPERS
# ---------------------------------------------


def course_number_required(course_type: str) -> bool:
    return course_type in ("bachelor", "master")


def group_required(course_type: str) -> bool:
    return course_type == "bachelor"


# ---------------------------------------------
# HANDLERS
# ---------------------------------------------


@log_dialog_action("REG_NAME_INPUT")
async def on_name_input(m: Message, _, manager: DialogManager):
    if not is_safe(m.text):
        return
    manager.dialog_data["name"] = m.text.strip()
    await manager.next()


@log_dialog_action("REG_TYPE_SELECTED")
async def on_type_selected(c: CallbackQuery, _, manager: DialogManager, course_type: str):
    manager.dialog_data["course_type"] = course_type

    if course_number_required(course_type):
        await manager.switch_to(RegisterForm.course_number)
    else:
        await manager.switch_to(RegisterForm.photo)


@log_dialog_action("REG_COURSE_NUMBER_SELECTED")
async def on_course_number_selected(c: CallbackQuery, _, manager: DialogManager, num: str):
    manager.dialog_data["course_number"] = int(num)

    if group_required(manager.dialog_data["course_type"]):
        await manager.switch_to(RegisterForm.group_name)
    else:
        await manager.switch_to(RegisterForm.photo)


@log_dialog_action("REG_GROUP_SELECTED")
async def on_group_selected(c: CallbackQuery, _, manager: DialogManager, group: str):
    manager.dialog_data["group_name"] = group
    await manager.next()


@log_dialog_action("REG_ABOUT_INPUT")
async def on_about_input(m: Message, _, manager: DialogManager):
    if not is_safe(m.text, SafeStringConfig(allow_newline=True, max_len=0)):
        return
    manager.dialog_data["about"] = m.text.strip()
    await manager.next()


@log_dialog_action("REG_PHOTO_INPUT")
async def on_photo_input(m: Message, _, manager: DialogManager):
    if not m.photo:
        return await m.answer("Пожалуйста, отправь фото.")
    manager.dialog_data["photo"] = m.photo[-1].file_id
    await manager.next()
    return None


async def reg_confirm_getter(dialog_manager: DialogManager, **_):
    d = dialog_manager.dialog_data
    return {
        "name": d.get("name"),
        "course_type_label": COURSE_TYPES.get(d.get("course_type"), "-"),
        "course_number": d.get("course_number") or "-",
        "group_name": d.get("group_name") or "-",
        "about": d.get("about") or "-",
        "photo": d.get("photo"),
        "has_photo": bool(d.get("photo")),
    }


@log_dialog_action("REG_FINAL_CONFIRM")
async def on_final_confirmation(c: CallbackQuery, b: Button, manager: DialogManager):
    bot: Bot = manager.middleware_data["bot"]
    d = manager.dialog_data
    tg_user = c.from_user

    user_obj, _ = await User.get_or_create(tg_id=tg_user.id)
    user_obj.tg_username = tg_user.username
    user_obj.status = "pending"
    await user_obj.save()

    pending = await PendingProfile.create(
        user=user_obj,
        status="pending",
        is_new_profile=True,
        name=d["name"],
        type=d["course_type"],
        course_number=d.get("course_number"),
        group_name=d.get("group_name"),
        about_user=d["about"],
        photo=d["photo"],
        changed_fields=[
            "name",
            "type",
            "course_number",
            "group_name",
            "about_user",
            "photo",
        ],
        submitted_username=tg_user.username,
    )

    # Notify admin
    text = (
        f"<b>Новый профиль:</b>\n\n"
        f"<b>Имя:</b> {d['name']}\n"
        f"<b>Тип:</b> {COURSE_TYPES[d['course_type']]}\n"
        f"<b>Курс:</b> {d.get('course_number') or '-'}\n"
        f"<b>Поток:</b> {d.get('group_name') or '-'}\n"
        f"<b>О себе:</b> {d['about']}\n"
        f"<b>Username:</b> @{tg_user.username or 'не указан'}\n"
        f"<b>ID:</b> {tg_user.id}\n"
        f"<b>ID заявки:</b> {pending.id}"
    )

    admin_service = AdminChatService(bot)
    admin_message = await admin_service.send_pending_profile_request(
        chat_key="logs",
        pending_id=str(pending.id),
        tg_id=tg_user.id,
        text=text,
        photo=d["photo"],
        tag="profile_confirm",
    )
    if admin_message:
        pending.chat_id = admin_message.chat.id
        pending.message_id = admin_message.message_id
        await pending.save()

    await c.message.answer("Твой профиль отправлен на проверку!")
    await manager.done()


# ---------------------------------------------
# BUTTON FACTORIES
# ---------------------------------------------


def btns_course_types(callback=on_type_selected):
    return Column(
        *[
            Button(
                Const(title),
                id=f"type_{t}",
                on_click=lambda c, b, m, x=t: callback(c, b, m, x),
            )
            for t, title in COURSE_TYPES.items()
        ]
    )


def btns_groups(callback=on_group_selected):
    return Column(
        *[
            Button(
                Const(name),
                id=f"group_{i}",
                on_click=lambda c, b, m, x=name: callback(c, b, m, x),
            )
            for i, name in enumerate(GROUP_NAMES)
        ]
    )


def course_buttons(callback=on_course_number_selected):
    # bachelor: 1–4
    bachelor_btns = [
        Button(
            Const(num),
            id=f"course_bachelor_{num}",
            when="is_bachelor",
            on_click=lambda c, b, m, x=num: callback(c, b, m, x),
        )
        for num in ["1", "2", "3", "4"]
    ]

    # master: 1–2
    master_btns = [
        Button(
            Const(num),
            id=f"course_master_{num}",
            when="is_master",
            on_click=lambda c, b, m, x=num: callback(c, b, m, x),
        )
        for num in ["1", "2"]
    ]

    return Group(*bachelor_btns, *master_btns, width=2)


async def reg_getter(dialog_manager: DialogManager, **_):
    course_type = dialog_manager.dialog_data.get("course_type")
    return {
        "course_type": course_type,
        "is_bachelor": course_type == "bachelor",
        "is_master": course_type == "master",
    }


# ---------------------------------------------
# DIALOG
# ---------------------------------------------

router.include_router(
    Dialog(
        Window(
            Const("Привет! Как тебя зовут?"),
            MessageInput(on_name_input),
            state=RegisterForm.name,
        ),
        Window(
            Const("Выбери тип обучения:"),
            btns_course_types(),
            Button(
                Const("Назад"),
                id="back",
                on_click=lambda c, b, m: m.switch_to(RegisterForm.name),
            ),
            state=RegisterForm.course_type,
        ),
        Window(
            Const("Выбери курс:"),
            course_buttons(),
            Button(
                Const("Назад"),
                id="back",
                on_click=lambda c, b, m: m.switch_to(RegisterForm.course_type),
            ),
            getter=reg_getter,
            state=RegisterForm.course_number,
        ),
        Window(
            Const("Выбери свой поток:"),
            btns_groups(),
            Button(
                Const("Назад"),
                id="back",
                on_click=lambda c, b, m: m.switch_to(RegisterForm.course_type),
            ),
            state=RegisterForm.group_name,
        ),
        Window(
            Const("Теперь отправь фото:"),
            Button(
                Const("Назад"),
                id="back",
                on_click=lambda c, b, m: m.switch_to(RegisterForm.about),
            ),
            MessageInput(on_photo_input, content_types=ContentType.PHOTO),
            state=RegisterForm.photo,
        ),
        Window(
            Const("Расскажи о себе:"),
            Button(
                Const("Назад"),
                id="back",
                on_click=lambda c, b, m: m.switch_to(RegisterForm.course_type),
            ),
            MessageInput(on_about_input, content_types=ContentType.TEXT),
            state=RegisterForm.about,
        ),
        Window(
            Const("Проверь данные и отправь на проверку:"),
            Format("<b>Имя:</b> {name}", when="name"),
            Format("<b>Тип:</b> {course_type_label}"),
            Format("<b>Курс:</b> {course_number}"),
            Format("<b>Поток:</b> {group_name}"),
            Format("<b>О себе:</b>\n{about}"),
            Format("Фото прикреплено", when="has_photo"),
            Column(
                Button(Const("Отправить"), id="go", on_click=on_final_confirmation),
                Button(
                    Const("Начать заново"),
                    id="restart",
                    on_click=lambda c, b, m: m.switch_to(RegisterForm.name),
                ),
            ),
            getter=reg_confirm_getter,
            state=RegisterForm.confirm,
        ),
    )
)


@router.message(CommandStart(), ProfileNonexistentFilter())
async def registration_start(
    message: Message,
    dialog_manager: DialogManager,
    bot: Bot,
):
    await dialog_manager.reset_stack()
    await dialog_manager.start(RegisterForm.name, show_mode=ShowMode.AUTO)


@router.message(CommandStart(), PendingFilter())
async def registration_pending(message: Message):
    await message.answer("Твой профиль на модерации. Мы сообщим, как только его проверят")
