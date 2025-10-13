from tortoise import fields

from .base import TimestampedModel


class MessageTemplate(TimestampedModel):
    key = fields.CharField(max_length=120, unique=True)
    text = fields.TextField()

    class Meta:
        table = "message_templates"
        table_description = "Шаблоны сообщений"
        indexes = (("key",),)

    def __str__(self) -> str:
        return f"<MsgTpl {self.key}>"
