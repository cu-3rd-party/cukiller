import html
import logging

from aiogram import Bot, Router
from aiogram.enums import ContentType
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, DialogManager, ShowMode, Window
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Cancel
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_dialog.widgets.text import Const, Format

from bot.handlers.mainloop.getters import get_advanced_info, get_user
from bot.handlers.registration_dialog import (
    COURSE_TYPES,
    btns_course_types,
    btns_groups,
    course_buttons,
    course_number_required,
    group_required,
    reg_getter,
)
from db.models import PendingProfile, User
from services.admin_chat import AdminChatService
from services.logging import log_dialog_action
from services.states.my_profile import EditProfile, MyProfile
from services.strings import SafeStringConfig, is_safe

logger = logging.getLogger(__name__)

router = Router()


FIELD_LABELS = {
    "name": "Имя",
    "type": "Тип",
    "course_number": "Курс",
    "group_name": "Поток",
    "about_user": "О себе",
    "photo": "Фото",
}


def _format_value(field: str, value):
    if value is None:
        return "-"
    if field == "type":
        return COURSE_TYPES.get(value, value)
    return str(value)


def _format_change_arrow(field: str, old, new) -> str:
    return (
        f"<b>{FIELD_LABELS[field]}:</b> "
        f"{html.escape(_format_value(field, old))} -> "
        f"{html.escape(_format_value(field, new))}"
    )


def _collect_changes(dialog_data: dict, user: User) -> tuple[dict, list[str]]:
    changes: dict[str, object] = {}
    changed_fields: list[str] = []

    if "name" in dialog_data and dialog_data.get("name") != user.name:
        changes["name"] = dialog_data.get("name")
        changed_fields.append("name")

    if dialog_data.get("academics_edited"):
        if "course_type" in dialog_data and dialog_data.get("course_type") != user.type:
            changes["type"] = dialog_data.get("course_type")
            changed_fields.append("type")
        if "course_number" in dialog_data and dialog_data.get("course_number") != user.course_number:
            changes["course_number"] = dialog_data.get("course_number")
            changed_fields.append("course_number")
        if "group_name" in dialog_data and dialog_data.get("group_name") != user.group_name:
            changes["group_name"] = dialog_data.get("group_name")
            changed_fields.append("group_name")

    if "about" in dialog_data and dialog_data.get("about") != user.about_user:
        changes["about_user"] = dialog_data.get("about")
        changed_fields.append("about_user")

    if "photo" in dialog_data and dialog_data.get("photo") and dialog_data.get("photo") != user.photo:
        changes["photo"] = dialog_data.get("photo")
        changed_fields.append("photo")

    return changes, changed_fields


def _build_changes_preview(user: User, changes: dict, changed_fields: list[str]) -> str:
    if not changed_fields:
        return "Изменения пока не выбраны. Добавьте поля и вернитесь к подтверждению."

    lines = ["<b>Изменения:</b>"]
    for field in changed_fields:
        if field == "photo":
            lines.append(f"<b>{FIELD_LABELS['photo']}:</b> фото будет обновлено")
            continue
        old_value = getattr(user, field)
        new_value = changes[field]
        lines.append(_format_change_arrow(field, old_value, new_value))

    return "\n".join(lines)


def _build_profile_preview(user: User, changes: dict) -> str:
    """Как профиль будет выглядеть после сохранения изменений."""
    name = html.escape(changes.get("name", user.name))
    type_value = html.escape(_format_value("type", changes.get("type", user.type)))
    course_value = html.escape(_format_value("course_number", changes.get("course_number", user.course_number)))
    group_value = html.escape(_format_value("group_name", changes.get("group_name", user.group_name)))
    about_value = html.escape(changes.get("about_user", user.about_user) or "-")

    return (
        "<b>Черновик профиля:</b>\n"
        f"Имя: <b>{name}</b>\n"
        f"Тип: {type_value}\n"
        f"Курс: {course_value}\n"
        f"Поток: {group_value}\n"
        f"О себе: {about_value}"
    )


async def get_profile_info(dialog_manager: DialogManager, **kwargs):
    user = await get_user(dialog_manager)
    return {
        "name": user.name,
        "photo": MediaAttachment(type=ContentType.PHOTO, file_id=MediaId(file_id=user.photo)),
        "advanced_info": get_advanced_info(user),
        "profile_link": user.tg_id and f"tg://user?id={user.tg_id}",
    }


async def confirm_preview_getter(dialog_manager: DialogManager, **kwargs):
    user = await get_user(dialog_manager)
    changes, changed_fields = _collect_changes(dialog_manager.dialog_data, user)
    preview_photo_id = changes.get("photo") or user.photo

    preview_photo = (
        MediaAttachment(type=ContentType.PHOTO, file_id=MediaId(file_id=preview_photo_id)) if preview_photo_id else None
    )

    return {
        "preview_text": _build_profile_preview(user, changes),
        "changes_preview": _build_changes_preview(user, changes, changed_fields),
        "has_changes": bool(changed_fields),
        "preview_photo": preview_photo,
    }


@log_dialog_action("EDIT_PROFILE")
async def on_edit(callback: CallbackQuery, button: Button, manager: DialogManager):
    await manager.start(
        EditProfile.main,
        data={"user_tg_id": callback.from_user.id},
        show_mode=ShowMode.SEND,
    )


router.include_router(
    Dialog(
        Window(
            Format("\nИмя: <b>{name}</b>\n", when="name"),
            Format("{advanced_info}", when="advanced_info"),
            DynamicMedia("photo", when="photo"),
            Button(Const("Редактировать"), id="edit", on_click=on_edit),
            Cancel(Const("Назад")),
            getter=get_profile_info,
            state=MyProfile.profile,
        )
    )
)


@log_dialog_action("EDIT_TYPE_SELECTED")
async def on_type_selected(c: CallbackQuery, _, manager: DialogManager, course_type: str):
    manager.dialog_data["academics_edited"] = True
    manager.dialog_data["course_type"] = course_type

    if course_number_required(course_type):
        await manager.switch_to(EditProfile.course)
    else:
        await manager.switch_to(EditProfile.confirm)


@log_dialog_action("EDIT_COURSE_NUMBER_SELECTED")
async def on_course_number_selected(c: CallbackQuery, _, manager: DialogManager, num: str):
    manager.dialog_data["course_number"] = int(num)

    if group_required(manager.dialog_data["course_type"]):
        await manager.switch_to(EditProfile.group)
    else:
        await manager.switch_to(EditProfile.confirm)


@log_dialog_action("EDIT_GROUP_SELECTED")
async def on_group_selected(c: CallbackQuery, _, manager: DialogManager, group: str):
    manager.dialog_data["group_name"] = group
    await manager.switch_to(EditProfile.confirm)


@log_dialog_action("EDIT_NAME")
async def on_name(message: Message, message_input: MessageInput, manager: DialogManager):
    if not is_safe(message.text):
        return
    manager.dialog_data["name"] = message.text
    await manager.switch_to(EditProfile.confirm)


@log_dialog_action("EDIT_ABOUT")
async def on_about(message: Message, message_input: MessageInput, manager: DialogManager):
    if not is_safe(message.text, SafeStringConfig(allow_newline=True, max_len=0)):
        return
    manager.dialog_data["about"] = message.text
    await manager.switch_to(EditProfile.confirm)


@log_dialog_action("EDIT_PHOTO_INPUT")
async def on_photo(m: Message, _, manager: DialogManager):
    if not m.photo:
        return
    manager.dialog_data["photo"] = m.photo[-1].file_id
    await manager.switch_to(EditProfile.confirm)


@log_dialog_action("EDIT_FINAL_CONFIRMATION")
async def on_final_confirmation(c: CallbackQuery, b: Button, manager: DialogManager):
    bot: Bot = c.bot
    d = manager.dialog_data
    tg_user = c.from_user

    user = await User.get_or_none(tg_id=tg_user.id)
    if user is None:
        await c.answer("Не удалось найти пользователя.", show_alert=True)
        await manager.done()
        return

    if user.tg_username != tg_user.username:
        user.tg_username = tg_user.username
        await user.save(update_fields=["tg_username"])

    changes, changed_fields = _collect_changes(d, user)

    if not changed_fields:
        await c.answer("Нет изменений для отправки", show_alert=True)
        await manager.done()
        return

    pending = await PendingProfile.create(
        user=user,
        is_new_profile=False,
        changed_fields=changed_fields,
        submitted_username=tg_user.username,
        **changes,
    )

    changes_preview = _build_changes_preview(user, changes, changed_fields)
    profile_preview = _build_profile_preview(user, changes)

    lines = [
        "<b>Изменение профиля:</b>",
        f"<b>ID заявки:</b> {pending.id}",
        f"<b>ID:</b> {tg_user.id}",
        f"<b>Username:</b> @{tg_user.username or 'не указан'}",
        changes_preview,
        profile_preview,
    ]

    text = "\n\n".join(lines)
    photo_to_send = changes.get("photo") or user.photo

    admin_service = AdminChatService(bot)
    admin_message = await admin_service.send_pending_profile_request(
        chat_key="logs",
        pending_id=str(pending.id),
        tg_id=tg_user.id,
        text=text,
        photo=photo_to_send,
        tag="profile_edit",
    )
    if admin_message:
        pending.chat_id = admin_message.chat.id
        pending.message_id = admin_message.message_id
        await pending.save()

    await c.message.answer("Изменения отправлены на модерацию. Пока используется старая версия профиля")
    await manager.done()


router.include_router(
    Dialog(
        Window(
            Const("Что хотите изменить?"),
            Button(
                Const("Имя"),
                id="name",
                on_click=lambda c, b, m: m.switch_to(EditProfile.name),
            ),
            Button(
                Const("Обучение"),
                id="academic",
                on_click=lambda c, b, m: m.switch_to(EditProfile.type),
            ),
            Button(
                Const("Описание"),
                id="description",
                on_click=lambda c, b, m: m.switch_to(EditProfile.about),
            ),
            Button(
                Const("Фото профиля"),
                id="profile_photo",
                on_click=lambda c, b, m: m.switch_to(EditProfile.photo),
            ),
            Cancel(Const("Назад")),
            state=EditProfile.main,
        ),
        Window(
            Const("Выбери тип обучения:"),
            btns_course_types(on_type_selected),
            Cancel(Const("Назад")),
            state=EditProfile.type,
        ),
        Window(
            Const("Выбери курс:"),
            course_buttons(on_course_number_selected),
            Cancel(Const("Назад")),
            getter=reg_getter,
            state=EditProfile.course,
        ),
        Window(
            Const("Выбери свой поток:"),
            btns_groups(on_group_selected),
            Cancel(Const("Назад")),
            state=EditProfile.group,
        ),
        Window(
            Const("Введите измененное имя:"),
            MessageInput(on_name, content_types=ContentType.TEXT),
            Cancel(Const("Назад")),
            state=EditProfile.name,
        ),
        Window(
            Const("Введите измененное описание:"),
            MessageInput(on_about, content_types=ContentType.TEXT),
            Cancel(Const("Назад")),
            state=EditProfile.about,
        ),
        Window(
            Const("Отправь мне новое фото:"),
            MessageInput(on_photo, content_types=ContentType.PHOTO),
            Cancel(Const("Назад")),
            state=EditProfile.photo,
        ),
        Window(
            Format("{preview_text}"),
            DynamicMedia("preview_photo", when="preview_photo"),
            Format("\n{changes_preview}"),
            Button(
                Const("Добавить ещё поля"),
                id="edit_more",
                on_click=lambda c, b, m: m.switch_to(EditProfile.main),
            ),
            Button(
                Const("Отправить на модерацию"),
                id="confirmed",
                on_click=on_final_confirmation,
                when="has_changes",
            ),
            Cancel(Const("Отмена")),
            getter=confirm_preview_getter,
            state=EditProfile.confirm,
        ),
    )
)
