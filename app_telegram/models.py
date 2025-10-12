from django.db import models


class TimeBasedModel(models.Model):
    class Meta:
        abstract = True
        ordering = ("-created",)

    created = models.DateTimeField(
        auto_now_add=True, verbose_name="дата создания"
    )
    updated = models.DateTimeField(
        auto_now=True, verbose_name="дата обновления"
    )


class UserProfile(TimeBasedModel):
    name = models.CharField(null=True)
    description = models.CharField(null=True)
    department = models.CharField()
    profile_picture = models.ImageField(
        upload_to="pfp"
    )  # TODO: make this upload location customizable
    verified = models.BooleanField(default=False)


class TGUser(TimeBasedModel):
    tg_id = models.BigIntegerField(
        unique=True, db_index=True, verbose_name="id Telegram"
    )
    profile = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name="профиль",
    )

    class Meta:
        verbose_name = "пользователь"
        verbose_name_plural = "пользователи"

    def __str__(self):
        return f"{self.tg_id}"
