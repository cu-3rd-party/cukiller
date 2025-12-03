from tortoise import fields

from .base import TimestampedModel
from .constants import KILL_STATUS


class KillEvent(TimestampedModel):
    game = fields.ForeignKeyField(
        "models.Game",
        related_name="kill_events",
        on_delete=fields.CASCADE,
        index=True,
    )

    killer = fields.ForeignKeyField(
        "models.User",
        related_name="kills_as_killer",
        on_delete=fields.RESTRICT,
        index=True,
    )
    victim = fields.ForeignKeyField(
        "models.User",
        related_name="kills_as_victim",
        on_delete=fields.RESTRICT,
        index=True,
    )

    killer_confirmed = fields.BooleanField(default=False)
    killer_confirmed_at = fields.DatetimeField(null=True)

    victim_confirmed = fields.BooleanField(default=False)
    victim_confirmed_at = fields.DatetimeField(null=True)

    status = fields.CharField(
        max_length=16,
        default="pending",
        choices=tuple((s, s) for s in KILL_STATUS),
        index=True,
    )

    moderator = fields.ForeignKeyField(
        "models.User",
        related_name="moderated_events",
        null=True,
        on_delete=fields.SET_NULL,
        source_field="moderator_id",
    )
    moderated_at = fields.DatetimeField(null=True)

    is_approved = fields.BooleanField(default=False)

    class Meta:
        table = "kill_events"
        table_description = "События «киллов»"

    def __str__(self) -> str:
        return f"<KillEvent with id={self.id}>"
