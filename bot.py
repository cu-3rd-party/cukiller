import asyncio, django, logging, os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from tgbot.config import load_config
# TODO: переписать на importlib
from tgbot.handlers.admin import router as admin_router
from tgbot.handlers.echo import router as echo_router
from tgbot.handlers.start import router as start_router
from tgbot.middlewares.environment import EnvironmentMiddleware

logger = logging.getLogger(__name__)


def register_all_middlewares(dp, config):
    dp.message.middleware(EnvironmentMiddleware(config=config, dp=dp))


def register_all_handlers(dp):
    dp.include_routers(
        admin_router,
        echo_router,
        start_router
    )


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

    bot = Bot(token=config.tg_bot.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
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
