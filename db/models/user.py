import html

from tortoise import fields

from services.strings import trim_name
from .base import TimestampedModel, ProfileBase
from .constants import PLAYER_STATUS


class User(TimestampedModel, ProfileBase):
    tg_id = fields.BigIntField(unique=True)
    tg_username = fields.CharField(max_length=32, null=True, unique=True)

    is_in_game = fields.BooleanField(default=False)
    is_admin = fields.BooleanField(default=False)

    status = fields.CharField(
        max_length=32,
        default="active",
        choices=tuple((s, s) for s in PLAYER_STATUS),
        index=True,
    )

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

    def profile_link(self):
        return f"tg://user?id={self.tg_id}"

    def mention_html(self, max_len=25) -> str:
        return f'<a href="{self.profile_link()}">{trim_name(html.escape(self.name), max_len)}</a>'
