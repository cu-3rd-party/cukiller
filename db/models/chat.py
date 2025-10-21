from tortoise import fields

from .base import TimestampedModel


class Chat(TimestampedModel):
    chat_id = fields.BigIntField()
    key = fields.CharField(max_length=1024)

    class Meta:
        table = "chats"
        table_description = "Админ-чаты Telegram"
        unique_together = (("chat_id", "thread"),)
        indexes = (("chat_id",),)

    def __str__(self) -> str:
        return f"<Chat {self.chat_id}:{self.key}>"
