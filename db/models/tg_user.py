from tortoise import fields
from tortoise.models import Model


class TGUser(Model):
    id = fields.IntField(pk=True)
    tg_id = fields.BigIntField(unique=True, index=True)
    username = fields.CharField(max_length=64, null=True)
    first_name = fields.CharField(max_length=255, null=True)
    last_name = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "tg_users"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"TGUser (tg_id={self.tg_id})"
