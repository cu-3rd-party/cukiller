import logging

from aiogram import Router
from aiogram.types import ChatJoinRequest

from db.models import User
from filters.group_key import GroupKeyFilter

logger = logging.getLogger(__name__)

router = Router()


@router.chat_join_request(GroupKeyFilter("discussion"))
async def chat_join_request(update: ChatJoinRequest):
    user_obj = await User().get_or_none(tg_id=update.from_user.id)
    if user_obj.status != "confirmed":
        await update.decline()
        return
    await update.approve()
