import asyncio
import importlib
import logging
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog import setup_dialogs
from aiohttp import web

from bot.handlers.metrics import metrics_updater, setup_metrics_routes
from bot.middlewares.environment import EnvironmentMiddleware
from bot.middlewares.register import RegisterUserMiddleware
from bot.services.discussion_invite import generate_discussion_invite_link
from db.main import close_db, init_db
from settings import Settings, get_settings

logger = logging.getLogger(__name__)

HANDLERS_PACKAGE = "bot.handlers"
HANDLERS_PATH = Path(__file__).parent / "handlers"


def register_all_middlewares(dp: Dispatcher, settings: Settings) -> None:
    environment = EnvironmentMiddleware(config=settings, dp=dp)
    dp.update.middleware(environment)
    register = RegisterUserMiddleware()
    dp.message.middleware(register)


def _iter_handler_modules() -> Iterable[ModuleType]:
    for module in HANDLERS_PATH.rglob("*.py"):
        if module.name == "__init__.py":
            continue
        relative = module.relative_to(HANDLERS_PATH).with_suffix("")
        dotted = ".".join((HANDLERS_PACKAGE, *relative.parts))
        yield importlib.import_module(dotted)


def register_all_handlers(dp: Dispatcher) -> None:
    routers = []
    for module in _iter_handler_modules():
        router = getattr(module, "router", None)
        if router is None:
            continue
        routers.append(router)

    if routers:
        dp.include_routers(*routers)
    else:
        logger.warning("Не найдено ни одного роутера для регистрации")


# Global web server instance
_web_server: web.AppRunner | None = None


async def start_web_server() -> None:
    """Start the HTTP web server for metrics endpoint."""
    global _web_server

    app = web.Application()
    setup_metrics_routes(app)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", 8000)
    await site.start()

    _web_server = runner
    logger.info("HTTP web server started on port 8000 for metrics endpoint")


async def stop_web_server() -> None:
    """Stop the HTTP web server."""
    global _web_server

    if _web_server:
        await _web_server.cleanup()
        _web_server = None
        logger.info("HTTP web server stopped")


async def on_startup(bot: Bot, settings: Settings) -> None:
    await init_db(settings)
    await generate_discussion_invite_link(bot, settings)
    await metrics_updater.start()
    await start_web_server()


async def on_shutdown(bot: Bot, settings: Settings) -> None:
    await stop_web_server()
    await metrics_updater.stop()
    await close_db()


async def run_bot(settings: Settings) -> None:
    storage = MemoryStorage()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)
    dp["settings"] = settings

    register_all_middlewares(dp, settings)
    register_all_handlers(dp)
    setup_dialogs(dp)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(bot)
    finally:
        await dp.storage.close()
        await bot.session.close()


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s",
    )
    settings = get_settings()
    logger.info("Запущен бот в проекте: %s", settings.project_name)

    await run_bot(settings)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен!")
