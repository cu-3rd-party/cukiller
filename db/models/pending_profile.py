from tortoise import fields

from .base import ProfileBase, TimestampedModel
from .constants import PENDING_PROFILE_STATUS


class PendingProfile(TimestampedModel, ProfileBase):
    user = fields.ForeignKeyField("models.User", related_name="pending_profiles")
    status = fields.CharField(
        max_length=32,
        default="pending",
        choices=tuple((s, s) for s in PENDING_PROFILE_STATUS),
        index=True,
    )
    is_new_profile = fields.BooleanField(default=False)
    moderator = fields.ForeignKeyField(
        "models.User",
        related_name="moderated_profiles",
        null=True,
    )
    reason = fields.TextField(null=True)
    changed_fields = fields.JSONField(default=list)
    chat_id = fields.BigIntField(null=True)
    message_id = fields.BigIntField(null=True)
    submitted_username = fields.CharField(max_length=32, null=True)

    class Meta:
        table = "pending_profiles"
        table_description = "Профили, ожидающие модерации"
        indexes = (("status",), ("user_id",))
