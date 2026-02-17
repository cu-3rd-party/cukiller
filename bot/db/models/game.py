from tortoise import fields

from .base import TimestampedModel


class Game(TimestampedModel):
    name = fields.CharField(max_length=255)

    start_date = fields.DatetimeField(null=True, index=True)
    end_date = fields.DatetimeField(null=True, index=True)

    class Meta:
        table = "games"
        table_description = "Игры"
        indexes = ("start_date",)

    def __str__(self) -> str:
        return f"<Game {self.name}>"
