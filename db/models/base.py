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
    # имя фамилия вместе
    name = fields.CharField(max_length=511, null=True)
    # тип: студент/сотрудник/абитуриент
    type = fields.CharField(max_length=32, null=True)
    # номер курса
    course_number = fields.SmallIntField(null=True, validators=[MinValueValidator(1), MaxValueValidator(8)])
    # название направления
    group_name = fields.CharField(max_length=255, null=True)
    # строчка айди файла в тг - мы даже не храним аватарки у себя
    photo = fields.TextField(null=True)
    # описание пользователя (о себе)
    about_user = fields.TextField(null=True)
    # согласие на объятия при убийстве
    allow_hugging_on_kill = fields.BooleanField(default=False)

    class Meta:
        abstract = True
