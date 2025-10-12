from tortoise import fields

from .base import TimestampedModel


class Chat(TimestampedModel):
    chat_id = fields.BigIntField()
    name = fields.CharField(max_length=255, null=True)
    slug = fields.CharField(max_length=255, null=True)
    type = fields.CharField(max_length=32, null=True)
    thread = fields.IntField(null=True)
    purpose = fields.TextField(null=True)

    class Meta:
        table = "chats"
        table_description = "Админ-чаты Telegram"
        unique_together = (("chat_id", "thread"),)
        indexes = (("chat_id",),)

    def __str__(self) -> str:
        return f"<Chat {self.chat_id}:{self.thread or 0}>"
