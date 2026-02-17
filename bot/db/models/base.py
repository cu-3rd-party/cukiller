import uuid

from tortoise import fields, models
from tortoise.validators import MaxValueValidator, MinValueValidator


class TimestampedModel(models.Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True


class ProfileBase(models.Model):
    given_name = fields.CharField(max_length=255, null=True)
    family_name = fields.CharField(max_length=255, null=True)
    type = fields.CharField(max_length=32, null=True)
    course_number = fields.SmallIntField(null=True, validators=[MinValueValidator(1), MaxValueValidator(8)])
    group_name = fields.CharField(max_length=255, null=True)
    photo = fields.TextField(null=True)
    about_user = fields.TextField(null=True)
    allow_hugging_on_kill = fields.BooleanField(default=False)

    class Meta:
        abstract = True

    @property
    def full_name(self) -> str:
        parts = [p.strip() for p in (self.family_name, self.given_name) if p]
        return " ".join(parts).strip()
