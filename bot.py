import asyncio, django, logging, os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog import setup_dialogs

from tgbot.config import load_config
import os
import importlib
from tgbot.middlewares.environment import EnvironmentMiddleware

logger = logging.getLogger(__name__)


def register_all_middlewares(dp, config):
    dp.message.middleware(EnvironmentMiddleware(config=config, dp=dp))


def register_all_handlers(dp):
    """
    Очень сложная (нет) логика для автоматического импорта хэндлеров.
    Каждый хэндлер ОБЯЗАН содержать в себе router = Router(), который уже и будет подвязываться к нашему диспетчеру
    :param dp:
    :return:
    """
    base_package = "tgbot.handlers"
    base_path = os.path.join("tgbot", "handlers")
    routers = []

    for root, dirs, files in os.walk(base_path):
        for file in files:
            if not file.endswith(".py") or file == "__init__.py":
                continue

            rel_path = os.path.relpath(root, base_path).replace(os.sep, ".")
            module_name = file[:-3]

            if rel_path == ".":
                full_module_name = f"{base_package}.{module_name}"
            else:
                full_module_name = f"{base_package}.{rel_path}.{module_name}"

            module = importlib.import_module(full_module_name)
            routers.append(module.router)

    dp.include_routers(*routers)
    setup_dialogs(dp)


def setup_django():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dj_ac.settings")
    os.environ.update({"DJANGO_ALLOW_ASYNC_UNSAFE": "true"})
    django.setup()


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s",
    )
    logger.info("Starting bot")
    setup_django()
    config = load_config(".env")

    storage = MemoryStorage()

    bot = Bot(
        token=config.tg_bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    dp["config"] = config

    register_all_middlewares(dp, config)
    register_all_handlers(dp)

    # start
    try:
        await dp.start_polling(bot)
    finally:
        await dp.storage.close()
        session = bot.session
        await session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")
