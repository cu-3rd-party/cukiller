import logging

from aiogram import Router
from aiogram.enums import ContentType
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from aiogram_dialog.widgets.kbd import Cancel
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_dialog.widgets.text import Format, Const

from bot.handlers.mainloop.getters import get_advanced_info, get_user
from bot.misc.states.my_profile import MyProfile
from services.logging import log_dialog_action

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


router.include_router(
    Dialog(
        Window(
            Format("\nИмя: <b>{name}</b>\n", when="name"),
            Format("{advanced_info}", when="advanced_info"),
            DynamicMedia("photo", when="photo"),
            Cancel(Const("Назад")),
            getter=get_profile_info,
            state=MyProfile.profile,
        )
    )
)
