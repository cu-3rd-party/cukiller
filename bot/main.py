import asyncio
import importlib
import json
import logging
import os
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType
from urllib.parse import urlparse
from uuid import UUID

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram_dialog import setup_dialogs
from aiohttp import web
from redis.asyncio import Redis

from db.main import close_db, init_db
from handlers import router as handlers_router
from handlers.matchmaking import setup_matchmaking_routers
from handlers.metrics import metrics_updater, setup_metrics_routes
from middlewares.environment import EnvironmentMiddleware
from middlewares.game import GameMiddleware
from middlewares.logging import VerboseLoggingMiddleware
from middlewares.private_messages import PrivateMessagesMiddleware
from middlewares.register import RegisterUserMiddleware
from middlewares.user import UserMiddleware
from services import MatchmakingService, kill_timeout_monitor, settings
from services.discussion_invite import (
    generate_discussion_invite_link,
    revoke_discussion_invite_link,
)

logger = logging.getLogger(__name__)

HANDLERS_PACKAGE = "handlers"
HANDLERS_PATH = Path(__file__).parent / "handlers"


def register_all_middlewares(dp: Dispatcher) -> None:
    dp.update.middleware(UserMiddleware())
    dp.update.middleware(VerboseLoggingMiddleware())
    dp.callback_query.middleware(UserMiddleware())
    dp.callback_query.middleware(GameMiddleware())
    dp.update.middleware(EnvironmentMiddleware(dispatcher=dp))
    dp.message.middleware(RegisterUserMiddleware())
    dp.message.middleware(PrivateMessagesMiddleware("/stats", "/rollbackkill"))


def register_all_handlers(dp: Dispatcher) -> None:
    routers = []

    dp.include_router(handlers_router)

    if routers:
        dp.include_routers(*routers)
    else:
        logger.warning("Не найдено ни одного роутера для регистрации")


# Global web server instance
_web_server_state: dict[str, web.AppRunner | None] = {"runner": None}


def _normalize_webhook_path() -> str:
    if settings.webhook_path:
        path = settings.webhook_path
    elif settings.webhook_url:
        path = urlparse(settings.webhook_url).path
    else:
        path = "/webhook"
    if not path:
        path = "/webhook"
    if not path.startswith("/"):
        path = f"/{path}"
    return path


async def start_web_server(bot: Bot, dp: Dispatcher) -> None:
    """Start the HTTP web server for metrics/matchmaking and webhook endpoints."""
    app = web.Application()
    setup_metrics_routes(app)
    setup_matchmaking_routers(app, bot)
    if settings.webhook_url:
        webhook_path = _normalize_webhook_path()
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=webhook_path)
        setup_application(app, dp, bot=bot)
        logger.info("Webhook endpoint registered on %s", webhook_path)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, settings.web_server_host, settings.web_server_port)
    await site.start()

    _web_server_state["runner"] = runner
    logger.info(
        "HTTP web server started on port %d for metrics endpoint",
        settings.web_server_port,
    )


async def stop_web_server() -> None:
    """Stop the HTTP web server."""
    runner = _web_server_state["runner"]
    if runner:
        await runner.cleanup()
        _web_server_state["runner"] = None
        logger.info("HTTP web server stopped")


async def on_startup(bot: Bot) -> None:
    await init_db()
    await generate_discussion_invite_link(bot)
    await metrics_updater.start()
    if settings.webhook_url:
        if settings.dispatcher is None:
            msg = "Dispatcher is not initialized for webhook setup"
            raise RuntimeError(msg)
        await bot.set_webhook(
            url=settings.webhook_url,
            allowed_updates=settings.dispatcher.resolve_used_update_types(),
        )
    else:
        if settings.dispatcher is None:
            msg = "Dispatcher is not initialized for polling setup"
            raise RuntimeError(msg)
        await start_web_server(bot, settings.dispatcher)
    await MatchmakingService().healthcheck()
    await MatchmakingService().reset_queues()
    await kill_timeout_monitor.start(bot)


async def on_shutdown(bot: Bot) -> None:
    await kill_timeout_monitor.stop()
    await revoke_discussion_invite_link(bot)
    if settings.webhook_url:
        await bot.delete_webhook()
    else:
        await stop_web_server()
    await metrics_updater.stop()
    await close_db()


class EnhancedJSONEncoder(json.JSONEncoder):
    """JSON encoder that supports UUID."""

    def default(self, obj: object) -> object:
        if isinstance(obj, UUID):
            return {"__uuid__": str(obj)}
        return super().default(obj)


def enhanced_json_loader(data: str) -> object:
    """JSON loader that restores UUIDs."""

    def object_hook(obj: dict[str, object]) -> object:
        if "__uuid__" in obj:
            return UUID(str(obj["__uuid__"]))
        return obj

    return json.loads(data, object_hook=object_hook)


def enhanced_json_dumper(obj: object) -> str:
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

    settings.bot = bot
    settings.dispatcher = dp

    register_all_middlewares(dp)
    register_all_handlers(dp)
    setup_dialogs(dp)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    if settings.webhook_url:
        try:
            await start_web_server(bot, dp)
            await asyncio.Event().wait()
        finally:
            await stop_web_server()
            await dp.storage.close()
            await bot.session.close()
    else:
        try:
            await dp.start_polling(bot)
        finally:
            await dp.storage.close()
            await bot.session.close()


async def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOGLEVEL", "INFO").upper(),
        format="%(levelname)s:\t[%(asctime)s] - %(message)s",
    )
    logger.info("Запущен бот в проекте: %s", settings.project_name)

    await run_bot()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен!")
