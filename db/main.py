import logging

from tortoise import Tortoise

from db.models import Chat, User
from settings import Settings

logger = logging.getLogger(__name__)


async def init_db(settings: Settings) -> None:
    """Инициализация подключения к Tortoise ORM"""

    await Tortoise.init(config=settings.tortoise_config)
    logger.info("Tortoise ORM инициализирована")
    if settings.tortoise_generate_schemas:
        await Tortoise.generate_schemas()
        logger.info("Генерация схем Tortoise ORM выполнена")
    await _ensure_default_admin_chat(settings)
    await _ensure_default_discussion_group(settings)
    await _ensure_default_admins(settings)


async def close_db() -> None:
    """Закрываем все соединения с базой данных для Tortoise ORM"""

    await Tortoise.close_connections()
    logger.info("Tortoise ORM соединения закрыты")


async def _ensure_default_admin_chat(settings: Settings) -> None:
    defaults = {
        "chat_id": settings.admin_chat_id,
        "name": "Admin Logs",
        "type": "group",
        "purpose": "Логи админов",
    }

    _, created = await Chat.get_or_create(key="logs", defaults=defaults)
    if created:
        logger.info(
            f"Создан системный чат 'logs' c айди {settings.admin_chat_id}",
        )

async def _ensure_default_discussion_group(settings: Settings) -> None:
    defaults = {
        "chat_id": settings.discussion_chat_id,
        "name": "Discussion Group",
        "type": "group",
        "purpose": "Чат игры",
    }

    _, created = await Chat.get_or_create(key="discussion", defaults=defaults)
    if created:
        logger.info(
            f"Создан системный чат 'discussion' c айди {settings.discussion_chat_id}",
        )


async def _ensure_default_admins(settings: Settings) -> None:
    # Выдаем админки тем, кто указан
    admins = [int(i) for i in settings.admin_ids_raw.split(",")]
    for admin_id in admins:
        user, created = await User.get_or_create(
            tg_id=admin_id,
        )
        if not user.is_admin:
            user.is_admin = True
            await user.save()
            logger.info(
                f"Админ {admin_id} получил права администратора!",
            )
    # Забираем админки у тех, кто больше не указан
    for user in await User.filter(is_admin=True).all():
        if user.tg_id in admins:
            continue
        user.is_admin = False
        logger.info(
            f"Админ {user.tg_id} лишился права администратора!",
        )
        await user.save()
    assert len(admins) == await User.filter(is_admin=True).count()
