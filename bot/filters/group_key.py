import logging

from aiogram.filters import BaseFilter
from aiogram.types import Update

from services.backend_api import backend_api

logger = logging.getLogger(__name__)


class GroupKeyFilter(BaseFilter):
    def __init__(self, key: str) -> None:
        self.key = key

    async def __call__(self, update: Update, **kwargs: object) -> bool:
        chat_obj = await backend_api.get_chat_by_id(update.chat.id)
        if not chat_obj:
            logger.error("Update from unknown chat with id %d", update.chat.id)
            return False
        return chat_obj.key == self.key
