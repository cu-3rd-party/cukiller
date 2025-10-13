from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from db.models.chat import Chat
from settings import Settings


class ChatServiceError(Exception):
    pass


class ChatNotFoundError(ChatServiceError):
    def __init__(self, key: str) -> None:
        super().__init__(f"Чат с ключом '{key}' не найден")


class AdminChatService:
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def send_message(
        self, key: str, text: str, tag: str | None = None
    ) -> None:
        body = text if not tag else f"#{tag}\n\n{text}"

        send_kwargs = {
            "chat_id": Settings.admin_chat_id,
            "text": body,
            "parse_mode": "HTML",
        }

        # if chat.thread is not None:
        #     send_kwargs["message_thread_id"] = chat.thread

        await self.bot.send_message(**send_kwargs)

    async def send_profile_confirmation_request(
        self,
        photo,
        key: str,
        user_id: int,
        text: str,
        tag: str | None = None,
    ):
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="confirm", callback_data=f"confirm {user_id}"
                    ),
                    InlineKeyboardButton(
                        text="deny", callback_data=f"deny {user_id}"
                    ),
                ]
            ]
        )

        body = text if not tag else f"#{tag}\n\n{text}"

        send_kwargs = {
            "chat_id": Settings.admin_chat_id,
            "photo": photo,
            "text": body,
            "reply_markup": keyboard,
            "parse_mode": "HTML",
        }

        # if chat.thread is not None:
        #     send_kwargs["message_thread_id"] = chat.thread

        await self.bot.send_photo(**send_kwargs)
