from tortoise import fields
from tortoise.validators import MaxValueValidator, MinValueValidator

from .base import TimestampedModel

from .constants import PLAYER_STATUS


class User(TimestampedModel):
    tg_id = fields.BigIntField(unique=True)
    tg_username = fields.CharField(max_length=32, null=True, unique=True)

    # имя фамилия вместе
    name = fields.CharField(max_length=511, null=True)
    # тип: студент/сотрудник/абитуриент
    type = fields.CharField(max_length=32, null=True)
    # номер курса
    course_number = fields.SmallIntField(
        null=True, validators=[MinValueValidator(1), MaxValueValidator(8)]
    )
    # название направления
    group_name = fields.CharField(max_length=255, null=True)

    is_in_game = fields.BooleanField(default=False)
    is_admin = fields.BooleanField(default=False)
    rating = fields.IntField(
        default=0, validators=[MinValueValidator(0)]
    )

    photo = fields.TextField(null=True)
    about_user = fields.TextField(null=True)

    status = fields.CharField(
        max_length=32,
        default="active",
        choices=tuple((s, s) for s in PLAYER_STATUS),
        index=True
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
