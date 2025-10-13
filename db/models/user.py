from typing import TYPE_CHECKING

from tortoise import fields
from tortoise.validators import MaxValueValidator, MinValueValidator

from .base import TimestampedModel

if TYPE_CHECKING:
    from .kill_event import KillEvent
    from .player import Player


class User(TimestampedModel):
    tg_id = fields.BigIntField(unique=True)
    tg_username = fields.CharField(max_length=32, null=True, unique=True)

    given_name = fields.CharField(max_length=255, null=True)
    family_name = fields.CharField(max_length=255, null=True)
    course_number = fields.SmallIntField(
        null=True, validators=[MinValueValidator(1), MaxValueValidator(8)]
    )
    group_name = fields.CharField(max_length=255, null=True)

    is_in_game = fields.BooleanField(default=False)
    is_admin = fields.BooleanField(default=False)
    global_rating = fields.IntField(
        default=0, validators=[MinValueValidator(0)]
    )

    photo = fields.TextField(null=True)
    about_user = fields.TextField(null=True)

    status = fields.CharField(max_length=32, default="active", index=True)
    type = fields.CharField(max_length=32, null=True)

    players: fields.ReverseRelation["Player"]
    kills_as_killer: fields.ReverseRelation["KillEvent"]
    kills_as_victim: fields.ReverseRelation["KillEvent"]
    moderated_events: fields.ReverseRelation["KillEvent"]

    class Meta:
        table = "users"
        table_description = "Пользователи"
        indexes = (
            ("status",),
            ("tg_id",),
        )

    def __str__(self) -> str:
        base = self.tg_username or f"user:{self.tg_id}"
        return f"<User {base}>"
