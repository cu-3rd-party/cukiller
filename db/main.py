import logging

from tortoise import Tortoise

from db.models import Chat
from settings import Settings

logger = logging.getLogger(__name__)


async def init_db(settings: Settings) -> None:
    """Инициализация подключения к Tortoise ORM"""

    await Tortoise.init(config=settings.tortoise_config)
    logger.info("Tortoise ORM инициализирована")
    if settings.tortoise_generate_schemas:
        await Tortoise.generate_schemas()
        logger.info("Генерация схем Tortoise ORM выполнена")
    await _ensure_default_admin_chat()


async def close_db() -> None:
    """Закрываем все соединения с базой данных для Tortoise ORM"""

    await Tortoise.close_connections()
    logger.info("Tortoise ORM соединения закрыты")


async def _ensure_default_admin_chat() -> None:
    defaults = {
        "chat_id": -1003148190868,
        "name": "Admin Logs",
        "type": "supergroup",
        "purpose": "Логи админов",
    }

    _, created = await Chat.get_or_create(key="logs", defaults=defaults)
    if created:
        logger.info(
            "Создан системный чат 'logs'",
        )
