import logging

from aiogram.filters import BaseFilter
from aiogram.types import Message

from db.models import Chat

logger = logging.getLogger(__name__)


class GroupKeyFilter(BaseFilter):
    def __init__(self, key):
        self.key = key

    async def __call__(self, update, **kwargs) -> bool:
        chat_obj = await Chat().get_or_none(chat_id=update.chat.id)
        if not chat_obj:
            logger.error("Update from unknown chat with id %d", update.chat.id)
            return False
        return chat_obj.key == self.key
