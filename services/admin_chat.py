import logging

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

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


def _pending_buttons(pending_id: str, tg_id: int, with_inspect: bool) -> InlineKeyboardMarkup:
    rows = []
    if with_inspect:
        rows.append([InlineKeyboardButton(text="inspect", url=f"tg://user?id={tg_id}")])
    else:
        logger.warning(f"User {tg_id} has forced us to disable inspect")
    rows.append(
        [
            InlineKeyboardButton(
                text="confirm",
                callback_data=f"confirm_pending:{pending_id}",
            ),
            InlineKeyboardButton(text="deny", callback_data=f"deny_pending:{pending_id}"),
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

    async def send_pending_profile_request(
        self,
        *,
        chat_key: str,
        pending_id: str,
        tg_id: int,
        text: str,
        photo: str | None = None,
        tag: str | None = None,
    ) -> Message:
        chat = await self._get_chat(chat_key)
        await User.get_or_create(tg_id=tg_id)

        body = _build_body(text, tag)
        reply_markup = _pending_buttons(pending_id, tg_id, with_inspect=True)

        try:
            if photo:
                return await self.bot.send_photo(
                    chat_id=chat.chat_id,
                    photo=photo,
                    caption=body,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
            return await self.bot.send_message(
                chat_id=chat.chat_id,
                text=body,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        except TelegramBadRequest as e:
            logger.warning(
                "Ошибка %s: %s. Пробуем отправить еще раз",
                chat.chat_id,
                e,
            )
            fallback_markup = _pending_buttons(pending_id, tg_id, with_inspect=False)
            try:
                return await self.bot.send_message(
                    chat_id=chat.chat_id,
                    text=body,
                    reply_markup=fallback_markup,
                    parse_mode="HTML",
                )
            except TelegramBadRequest as e2:
                logger.exception("Ошибка при отправке профиля: %s", e2)
                return None
        except Exception as e:
            logger.exception("Произошла ошибка: %s", e)
            return None
