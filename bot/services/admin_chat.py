from dataclasses import dataclass
from typing import Any

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from db.models import User
from db.models.chat import Chat


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
        chat: Chat | None = await Chat.get_or_none(key=key)
        if chat is None:
            raise ChatNotFoundError(key)

        body = text if not tag else f"#{tag}\n\n{text}"

        send_kwargs = {
            "chat_id": chat.chat_id,
            "text": body,
            "parse_mode": "HTML",
        }

        if chat.thread is not None:
            send_kwargs["message_thread_id"] = chat.thread

        await self.bot.send_message(**send_kwargs)

    async def send_profile_confirmation_request(
        self,
        photo,
        key: str,
        update_data: dict[str, Any],
        text: str,
        tag: str | None = None,
    ):
        chat: Chat | None = await Chat.get_or_none(key=key)
        if chat is None:
            raise ChatNotFoundError(key)

        user_obj, _ = await User.get_or_create(tg_id=update_data["tg_id"])

        # Split the name safely
        name_parts = update_data["name"].split(maxsplit=1)
        update_data["given_name"] = name_parts[0]
        update_data["family_name"] = (
            name_parts[1] if len(name_parts) > 1 else ""
        )

        # update_data = {
        #     "tg_username": update_data.tg_username,
        #     "given_name": given_name,
        #     "family_name": family_name,
        #     "course_number": update_data.course_number,
        #     "group_name": update_data.group_name,
        #     "about_user": update_data.about_user,
        #     "photo": update_data.photo,
        #     "status": "pending",
        # }

        await user_obj.update_from_dict(update_data)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="confirm",
                        callback_data=f"confirm {update_data['tg_id']}",
                    ),
                    InlineKeyboardButton(
                        text="deny",
                        callback_data=f"deny {update_data['tg_id']}",
                    ),
                ]
            ]
        )

        body = text if not tag else f"#{tag}\n\n{text}"

        send_kwargs = {
            "chat_id": chat.chat_id,
            "photo": photo,
            "caption": body,
            "reply_markup": keyboard,
            "parse_mode": "HTML",
        }

        if chat.thread is not None:
            send_kwargs["message_thread_id"] = chat.thread

        await self.bot.send_photo(**send_kwargs)
