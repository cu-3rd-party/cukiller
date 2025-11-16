import json
from uuid import UUID
import asyncio
import importlib
import logging
import os
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage
from aiogram_dialog import setup_dialogs
from aiohttp import web

from bot.handlers.matchmaking import setup_matchmaking_routers
from bot.handlers.metrics import metrics_updater, setup_metrics_routes
from bot.middlewares.environment import EnvironmentMiddleware
from bot.middlewares.private_messages import PrivateMessagesMiddleware
from bot.middlewares.register import RegisterUserMiddleware
from services.discussion_invite import (
    generate_discussion_invite_link,
    revoke_discussion_invite_link,
)
from db.main import close_db, init_db
from services.matchmaking import MatchmakingService
from settings import settings

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

HANDLERS_PACKAGE = "bot.handlers"
HANDLERS_PATH = Path(__file__).parent / "handlers"


def register_all_middlewares(dp: Dispatcher) -> None:
    dp.update.middleware(EnvironmentMiddleware(dispatcher=dp))
    dp.message.middleware(RegisterUserMiddleware())
    dp.message.middleware(PrivateMessagesMiddleware())


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


async def start_web_server(bot: Bot) -> None:
    """Start the HTTP web server for metrics endpoint."""
    global _web_server

    app = web.Application()
    setup_metrics_routes(app)
    setup_matchmaking_routers(app, bot)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", settings.web_server_port)
    await site.start()

    _web_server = runner
    logger.info(
        "HTTP web server started on port %d for metrics endpoint",
        settings.web_server_port,
    )


async def stop_web_server() -> None:
    """Stop the HTTP web server."""
    global _web_server

    if _web_server:
        await _web_server.cleanup()
        _web_server = None
        logger.info("HTTP web server stopped")


async def on_startup(bot: Bot) -> None:
    await init_db()
    await generate_discussion_invite_link(bot)
    await metrics_updater.start()
    await start_web_server(bot)
    await MatchmakingService(
        settings,
        logging.getLogger(__name__),
    ).healthcheck()


async def on_shutdown(bot: Bot) -> None:
    await revoke_discussion_invite_link(bot)
    await stop_web_server()
    await metrics_updater.stop()
    await close_db()


class EnhancedJSONEncoder(json.JSONEncoder):
    """JSON encoder that supports UUID."""

    def default(self, obj):
        if isinstance(obj, UUID):
            return {"__uuid__": str(obj)}
        return super().default(obj)


def enhanced_json_loader(data: str):
    """JSON loader that restores UUIDs."""

    def object_hook(obj):
        if "__uuid__" in obj:
            return UUID(obj["__uuid__"])
        return obj

    return json.loads(data, object_hook=object_hook)


def enhanced_json_dumper(obj) -> str:
    """JSON dumper that serializes UUIDs."""
    return json.dumps(obj, cls=EnhancedJSONEncoder)


async def run_bot() -> None:
    storage = RedisStorage(
        redis=Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
        ),
        key_builder=DefaultKeyBuilder(
            with_destiny=True,
        ),
        json_dumps=enhanced_json_dumper,
        json_loads=enhanced_json_loader,
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    register_all_middlewares(dp)
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
        level=os.environ.get("LOGLEVEL", "INFO").upper(),
        format="%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s",
    )
    logger.info("Запущен бот в проекте: %s", settings.project_name)

    await run_bot()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен!")
