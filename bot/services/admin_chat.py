from aiogram import Bot

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
