import logging

from db.models import TGUser

logger = logging.getLogger(__name__)


async def add_or_create_user(
    user_id: int,
    *,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    language_code: str | None = None,
) -> tuple[TGUser, bool]:

    defaults = {
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
        "language_code": language_code,
    }
    create_defaults = defaults | {"is_active": True}
    user, created = await TGUser.get_or_create(
        tg_id=user_id, defaults=create_defaults
    )

    if created:
        logger.info("Пользователь %s добавлен в базу", user_id)
        return user, True

    updated_fields: dict[str, str] = {}
    for field_name, value in defaults.items():
        if value is None:
            continue
        current_value = getattr(user, field_name, None)
        if current_value != value:
            setattr(user, field_name, value)
            updated_fields[field_name] = value

    if updated_fields:
        await user.save(update_fields=list(updated_fields))
        logger.info(
            "Для пользователя с ID: %s информация обновлена (%s)",
            user_id,
            ", ".join(updated_fields),
        )
    else:
        logger.info("Пользователь с ID: %s, уже существует", user_id)

    return user, False
