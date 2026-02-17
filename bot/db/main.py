import logging

from tortoise import Tortoise

from db.models import Chat, User
from services import settings

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Initialize Tortoise ORM connection."""

    await Tortoise.init(config=settings.tortoise_config)
    if settings.tortoise_generate_schemas:
        await Tortoise.generate_schemas()
        logger.info("Генерация схем Tortoise ORM выполнена")
    await _ensure_default_admin_chat()
    await _ensure_default_discussion_group()
    await _ensure_default_admins()
    logger.info("Tortoise ORM инициализирована")


async def close_db() -> None:
    """Close all Tortoise ORM connections."""

    await Tortoise.close_connections()
    logger.info("Tortoise ORM соединения закрыты")


async def _ensure_default_admin_chat() -> None:
    defaults = {
        "chat_id": settings.admin_chat_id,
        "name": "Admin Logs",
        "type": "group",
        "purpose": "Логи админов",
    }

    _, created = await Chat.get_or_create(key="logs", defaults=defaults)
    if created:
        logger.info(
            "Created system chat 'logs' with id %s",
            settings.admin_chat_id,
        )


async def _ensure_default_discussion_group() -> None:
    defaults = {
        "chat_id": settings.discussion_chat_id,
        "name": "Discussion Group",
        "type": "group",
        "purpose": "Чат игры",
    }

    _, created = await Chat.get_or_create(key="discussion", defaults=defaults)
    if created:
        logger.info(
            "Created system chat 'discussion' with id %s",
            settings.discussion_chat_id,
        )


async def _ensure_default_admins() -> None:
    # Grant admin role to configured users.
    admins = [int(i) for i in settings.admin_ids_raw.split(",")]
    for admin_id in admins:
        user, _created = await User.get_or_create(
            tg_id=admin_id,
        )
        if not user.is_admin:
            user.is_admin = True
            await user.save()
            logger.info(
                "Admin %s granted admin rights.",
                admin_id,
            )
    # Revoke admin role from users not listed anymore.
    for user in await User.filter(is_admin=True).all():
        if user.tg_id in admins:
            continue
        user.is_admin = False
        logger.info(
            "Admin %s lost admin rights.",
            user.tg_id,
        )
        await user.save()
    admin_count = await User.filter(is_admin=True).count()
    if len(admins) != admin_count:
        msg = "Admin sync mismatch: expected %s, got %s"
        raise RuntimeError(msg % (len(admins), admin_count))
