import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from db.models import User
from db.models.chat import Chat

logger = logging.getLogger(__name__)


class ChatServiceError(Exception):
    pass


class ChatNotFoundError(ChatServiceError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Чат с ключом '{key}' не найден")


def _build_body(text: str, tag: str | None) -> str:
    return f"#{tag}\n\n{text}" if tag else text


def _buttons(tg_id: int, with_inspect: bool) -> InlineKeyboardMarkup:
    rows = []
    if with_inspect:
        rows.append([InlineKeyboardButton(text="inspect", url=f"tg://user?id={tg_id}")])
    else:
        logger.warning(f"User {tg_id} has forced us to disable inspect")
    rows.append(
        [
            InlineKeyboardButton(text="confirm", callback_data=f"confirm {tg_id}"),
            InlineKeyboardButton(text="deny", callback_data=f"deny {tg_id}"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


class AdminChatService:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @staticmethod
    async def _get_chat(key: str) -> Chat:
        chat = await Chat.get_or_none(key=key)
        if chat is None:
            raise ChatNotFoundError(key)
        return chat

    async def send_message(self, key: str, text: str, tag: str | None = None) -> None:
        """Send a text message to a chat by key"""
        chat = await self._get_chat(key)
        await self.bot.send_message(
            chat_id=chat.chat_id,
            text=_build_body(text, tag),
            parse_mode="HTML",
        )

    async def send_message_photo(self, photo, tg_id: int, key: str, text: str, tag: str | None = None):
        chat = await self._get_chat(key)
        body = _build_body(text, tag)

        await self.bot.send_photo(
            chat_id=chat.chat_id,
            photo=photo,
            caption=body,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="inspect", url=f"tg://user?id={tg_id}")]]
            ),
            parse_mode="HTML",
        )

    async def send_profile_confirmation_request(
        self,
        photo,
        key: str,
        tg_id: int,
        text: str,
        tag: str | None = None,
    ):
        """Send a profile confirmation request with fallback keyboard"""
        chat = await self._get_chat(key)
        await User.get_or_create(tg_id=tg_id)

        body = _build_body(text, tag)

        try:
            reply_markup = _buttons(tg_id, with_inspect=True)
            await self.bot.send_photo(
                chat_id=chat.chat_id,
                photo=photo,
                caption=body,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        except:
            reply_markup = _buttons(tg_id, with_inspect=False)
            await self.bot.send_photo(
                chat_id=chat.chat_id,
                photo=photo,
                caption=body,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
