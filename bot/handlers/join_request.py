import logging

from aiogram import Router
from aiogram.types import ChatJoinRequest

from filters.group_key import GroupKeyFilter
from services.backend_api import backend_api

logger = logging.getLogger(__name__)

router = Router()


@router.chat_join_request(GroupKeyFilter("discussion"))
async def chat_join_request(update: ChatJoinRequest):
    user_obj = await backend_api.get_user_by_tg_id(update.from_user.id)
    if user_obj.status != "confirmed":
        await update.decline()
        return
    await update.approve()
