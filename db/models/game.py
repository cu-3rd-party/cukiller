from typing import TYPE_CHECKING

from tortoise import fields

from .base import TimestampedModel
from .constants import GAME_VISIBILITY

if TYPE_CHECKING:
    from .kill_event import KillEvent
    from .player import Player


class Game(TimestampedModel):
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)

    start_date = fields.DatetimeField(null=True)
    end_date = fields.DatetimeField(null=True)

    end_message = fields.TextField(null=True)
    max_players = fields.IntField(null=True, validators=[])

    registration_start_date = fields.DatetimeField(null=True)
    registration_end_date = fields.DatetimeField(null=True)

    n_candidates = fields.IntField(default=0)

    visibility = fields.CharField(
        max_length=16,
        default="private",
        choices=tuple((v, v) for v in GAME_VISIBILITY),
        index=True,
    )

    players: fields.ReverseRelation["Player"]
    kill_events: fields.ReverseRelation["KillEvent"]

    class Meta:
        table = "games"
        table_description = "Игры"
        indexes = (("start_date",), ("visibility",))

    def __str__(self) -> str:
        return f"<Game {self.name}>"
