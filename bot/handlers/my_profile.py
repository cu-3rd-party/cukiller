import logging

from aiogram import Router, Bot
from aiogram.enums import ContentType
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Cancel, Button
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_dialog.widgets.text import Format, Const

from bot.handlers.mainloop.getters import get_advanced_info, get_user
from bot.handlers.registration_dialog import (
    btns_course_types,
    course_buttons,
    btns_groups,
    reg_getter,
    course_number_required,
    group_required,
    COURSE_TYPES,
)
from db.models import User
from services import settings
from services.admin_chat import AdminChatService
from services.logging import log_dialog_action
from services.states.my_profile import MyProfile, EditProfile
from services.strings import is_safe, SafeStringConfig

logger = logging.getLogger(__name__)

router = Router()


async def get_profile_info(dialog_manager: DialogManager, **kwargs):
    user = await get_user(dialog_manager)
    return {
        "name": user.name,
        "photo": MediaAttachment(
            type=ContentType.PHOTO, file_id=MediaId(file_id=user.photo)
        ),
        "advanced_info": get_advanced_info(user),
        "profile_link": user.tg_id and f"tg://user?id={user.tg_id}",
    }


@log_dialog_action("EDIT_PROFILE")
async def on_edit(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    await manager.start(
        EditProfile.main, data={"user_tg_id": callback.from_user.id}
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
async def on_type_selected(
    c: CallbackQuery, _, manager: DialogManager, course_type: str
):
    manager.dialog_data["academics_edited"] = True
    manager.dialog_data["course_type"] = course_type

    if course_number_required(course_type):
        await manager.switch_to(EditProfile.course)
    else:
        await manager.switch_to(EditProfile.confirm)


@log_dialog_action("EDIT_COURSE_NUMBER_SELECTED")
async def on_course_number_selected(
    c: CallbackQuery, _, manager: DialogManager, num: str
):
    manager.dialog_data["course_number"] = int(num)

    if group_required(manager.dialog_data["course_type"]):
        await manager.switch_to(EditProfile.group)
    else:
        await manager.switch_to(EditProfile.confirm)


@log_dialog_action("EDIT_GROUP_SELECTED")
async def on_group_selected(
    c: CallbackQuery, _, manager: DialogManager, group: str
):
    manager.dialog_data["group_name"] = group
    await manager.switch_to(EditProfile.confirm)


@log_dialog_action("EDIT_NAME")
async def on_name(
    message: Message, message_input: MessageInput, manager: DialogManager
):
    if not is_safe(message.text):
        return
    manager.dialog_data["name"] = message.text
    await manager.switch_to(EditProfile.confirm)


@log_dialog_action("EDIT_ABOUT")
async def on_about(
    message: Message, message_input: MessageInput, manager: DialogManager
):
    if not is_safe(
        message.text, SafeStringConfig(allow_newline=True, max_len=500)
    ):
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
async def on_final_confirmation(
    c: CallbackQuery, b: Button, manager: DialogManager
):
    bot: Bot = c.bot
    d = manager.dialog_data
    tg_user = c.from_user

    # DB save
    user = await User.get_or_none(tg_id=tg_user.id) or User(tg_id=tg_user.id)

    user.name = d.get("name") or user.name
    user.tg_username = tg_user.username
    if d.get("academics_edited"):
        user.type = d.get("course_type")
        user.course_number = d.get("course_number")
        user.group_name = d.get("group_name")
    user.about_user = d.get("about") or user.about_user
    user.photo = d.get("photo") or user.photo
    user.status = "pending"
    user.rating = settings.DEFAULT_RATING

    await user.save()

    # Notify admin
    text = (
        f"<b>Измененный профиль:</b>\n\n"
        f"<b>Имя:</b> {user.name}\n"
        f"<b>Тип:</b> {COURSE_TYPES[user.type]}\n"
        f"<b>Курс:</b> {user.course_number or '-'}\n"
        f"<b>Поток:</b> {user.group_name or '-'}\n"
        f"<b>О себе:</b> {user.about_user}\n"
        f"<b>Username:</b> @{tg_user.username or 'не указан'}\n"
        f"<b>ID:</b> {tg_user.id}"
    )

    await AdminChatService(bot).send_message_photo(
        key="logs",
        photo=user.photo,
        tg_id=tg_user.id,
        text=text,
        tag="profile_confirm",
    )

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
        # одиночные изменения
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
            Const("Подтверждаешь корректность изменений?"),
            Button(
                Const("Да, отправляй"),
                id="confirmed",
                on_click=on_final_confirmation,
            ),
            Cancel(Const("Отмена")),
            state=EditProfile.confirm,
        ),
    )
)
