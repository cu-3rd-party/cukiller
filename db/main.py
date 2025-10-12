import logging

from tortoise import Tortoise

from settings import Settings

logger = logging.getLogger(__name__)


async def init_db(settings: Settings) -> None:
    """Инициализация подключения к Tortoise ORM"""

    await Tortoise.init(config=settings.tortoise_config)
    logger.info("Tortoise ORM инициализирована")
    if settings.tortoise_generate_schemas:
        await Tortoise.generate_schemas()
        logger.info("Генерация схем Tortoise ORM выполнена")


async def close_db() -> None:
    """Закрываем все соединения с базой данных для Tortoise ORM"""

    await Tortoise.close_connections()
    logger.info("Tortoise ORM соединения закрыты")
