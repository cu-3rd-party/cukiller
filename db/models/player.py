from tortoise import fields
from tortoise.validators import MinValueValidator

from .base import TimestampedModel


class Player(TimestampedModel):
    user = fields.ForeignKeyField(
        "models.User",
        related_name="players",
        on_delete=fields.CASCADE,
    )
    game = fields.ForeignKeyField(
        "models.Game",
        related_name="players",
        on_delete=fields.CASCADE,
    )

    player_rating = fields.IntField(
        default=0, validators=[MinValueValidator(0)]
    )

    class Meta:
        table = "players"
        table_description = "Игроки в игре"
        unique_together = (("user", "game"),)
        indexes = (("user",), ("game",))

    def __str__(self) -> str:
        return f"<Player u={self.user.id} g={self.game.id}>"
