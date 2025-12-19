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
    hugging_allowed_label,
)
from db.models import PendingProfile, User
from services import texts
from services.admin_chat import AdminChatService
from services.logging import log_dialog_action
from services.states.my_profile import EditProfile, MyProfile
from services.strings import SafeStringConfig, is_safe

logger = logging.getLogger(__name__)

router = Router()


FIELD_LABELS = texts.PROFILE_FIELD_LABELS


def _format_value(field: str, value):
    if value is None:
        return "-"
    if field == "type":
        return COURSE_TYPES.get(value, value)
    if field == "allow_hugging_on_kill":
        return texts.get("profile.hugs_allowed_yes") if value else texts.get("profile.hugs_allowed_no")
    return str(value)


def _format_change_arrow(field: str, old, new) -> str:
    return texts.render(
        "profile.change_arrow",
        field_label=FIELD_LABELS[field],
        old_value=html.escape(_format_value(field, old)),
        new_value=html.escape(_format_value(field, new)),
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
        return texts.get("profile.changes_empty")

    lines = [texts.get("profile.changes_title")]
    for field in changed_fields:
        if field == "photo":
            lines.append(
                texts.render("profile.photo_will_be_updated", field_label=FIELD_LABELS["photo"])
            )
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
    hugging_value = html.escape(
        _format_value(
            "allow_hugging_on_kill",
            changes.get("allow_hugging_on_kill", user.allow_hugging_on_kill),
        )
    )

    return texts.get("profile.draft_title") + texts.render(
        "profile.draft_body",
        name=name,
        type_value=type_value,
        course_value=course_value,
        group_value=group_value,
        about_value=about_value,
        hugging_value=hugging_value,
    )


async def get_profile_info(dialog_manager: DialogManager, **kwargs):
    user = await get_user(dialog_manager)
    return {
        "name": user.name,
        "photo": MediaAttachment(type=ContentType.PHOTO, file_id=MediaId(file_id=user.photo)),
        "advanced_info": get_advanced_info(user),
        "profile_link": user.tg_id and f"tg://user?id={user.tg_id}",
        "hugs_allowed_label": hugging_allowed_label(user.allow_hugging_on_kill),
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
        show_mode=ShowMode.AUTO,
    )


@log_dialog_action("TOGGLE_HUGGING_SETTING")
async def toggle_hugging_setting(callback: CallbackQuery, button: Button, manager: DialogManager):
    user = await get_user(manager)
    user.allow_hugging_on_kill = not bool(user.allow_hugging_on_kill)
    await user.save(update_fields=["allow_hugging_on_kill"])
    await callback.answer(texts.get("profile.toggle_hugs_updated"))
    await manager.switch_to(MyProfile.profile)


router.include_router(
    Dialog(
        Window(
            Format(texts.get("profile.name_line"), when="name"),
            Format("{advanced_info}", when="advanced_info"),
            DynamicMedia("photo", when="photo"),
            Button(
                Format(texts.get("profile.hugs_label")),
                id="toggle_hugs",
            on_click=toggle_hugging_setting,
        ),
        Button(Const(texts.get("buttons.edit")), id="edit", on_click=on_edit),
        Cancel(Const(texts.get("buttons.back"))),
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
        await c.answer(texts.get("profile.no_user_found"), show_alert=True)
        await manager.done()
        return

    if user.tg_username != tg_user.username:
        user.tg_username = tg_user.username
        await user.save(update_fields=["tg_username"])

    changes, changed_fields = _collect_changes(d, user)

    if not changed_fields:
        await c.answer(texts.get("profile.no_changes"), show_alert=True)
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
        texts.get("moderation.change_header"),
        texts.render("moderation.change_meta_id", pending_id=pending.id),
        texts.render("moderation.change_meta_user_id", user_id=tg_user.id),
        texts.render(
            "moderation.change_meta_username",
            username=tg_user.username or texts.get("common.username_unknown"),
        ),
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

    await c.message.answer(texts.get("profile.change_sent"))
    await manager.done()


router.include_router(
    Dialog(
        Window(
            Const(texts.get("profile.edit_prompt")),
            Button(
                Const(texts.get("buttons.profile_name")),
                id="name",
                on_click=lambda c, b, m: m.switch_to(EditProfile.name),
            ),
            Button(
                Const(texts.get("buttons.profile_academic")),
                id="academic",
                on_click=lambda c, b, m: m.switch_to(EditProfile.type),
            ),
            Button(
                Const(texts.get("buttons.profile_description")),
                id="description",
                on_click=lambda c, b, m: m.switch_to(EditProfile.about),
            ),
            Button(
                Const(texts.get("buttons.profile_photo")),
                id="profile_photo",
                on_click=lambda c, b, m: m.switch_to(EditProfile.photo),
            ),
            Cancel(Const(texts.get("buttons.back"))),
            state=EditProfile.main,
        ),
        Window(
            Const(texts.get("profile.ask_type")),
            btns_course_types(on_type_selected),
            Cancel(Const(texts.get("buttons.back"))),
            state=EditProfile.type,
        ),
        Window(
            Const(texts.get("profile.ask_course")),
            course_buttons(on_course_number_selected),
            Cancel(Const(texts.get("buttons.back"))),
            getter=reg_getter,
            state=EditProfile.course,
        ),
        Window(
            Const(texts.get("profile.ask_group")),
            btns_groups(on_group_selected),
            Cancel(Const(texts.get("buttons.back"))),
            state=EditProfile.group,
        ),
        Window(
            Const(texts.get("profile.ask_name")),
            MessageInput(on_name, content_types=ContentType.TEXT),
            Cancel(Const(texts.get("buttons.back"))),
            state=EditProfile.name,
        ),
        Window(
            Const(texts.get("profile.ask_about")),
            MessageInput(on_about, content_types=ContentType.TEXT),
            Cancel(Const(texts.get("buttons.back"))),
            state=EditProfile.about,
        ),
        Window(
            Const(texts.get("profile.ask_photo")),
            MessageInput(on_photo, content_types=ContentType.PHOTO),
            Cancel(Const(texts.get("buttons.back"))),
            state=EditProfile.photo,
        ),
        Window(
            Format("{preview_text}"),
            DynamicMedia("preview_photo", when="preview_photo"),
            Format(texts.get("profile.preview_changes")),
            Button(
                Const(texts.get("profile.add_more_fields")),
                id="edit_more",
                on_click=lambda c, b, m: m.switch_to(EditProfile.main),
            ),
            Button(
                Const(texts.get("profile.send_to_moderation")),
                id="confirmed",
                on_click=on_final_confirmation,
                when="has_changes",
            ),
            Cancel(Const(texts.get("buttons.cancel"))),
            getter=confirm_preview_getter,
            state=EditProfile.confirm,
        ),
    )
)
