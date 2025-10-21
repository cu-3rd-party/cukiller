from typing import TYPE_CHECKING

from tortoise import fields

from .base import TimestampedModel
from .constants import GAME_VISIBILITY

if TYPE_CHECKING:
    from .kill_event import KillEvent
    from .player import Player


class Game(TimestampedModel):
    name = fields.CharField(max_length=255)

    start_date = fields.DatetimeField(null=True)
    end_date = fields.DatetimeField(null=True)

    class Meta:
        table = "games"
        table_description = "Игры"
        indexes = ("start_date", )

    def __str__(self) -> str:
        return f"<Game {self.name}>"
