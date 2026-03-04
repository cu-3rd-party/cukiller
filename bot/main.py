import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

import uvicorn
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage
from aiogram_dialog import setup_dialogs
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import Response
from redis.asyncio import Redis

from handlers.admin import router as admin_router
from handlers.join_request import router as join_request_router
from handlers.kills_confirmation import router as kills_confirmation_router
from handlers.leave_game import router as leave_game_router
from handlers.mainloop_dialog import router as mainloop_dialog_router
from handlers.matchmaking import router as matchmaking_router
from handlers.matchmaking import setup_matchmaking_routers
from handlers.metrics import metrics_updater, setup_metrics_routes
from handlers.my_profile import router as my_profile_router
from handlers.participation import router as participation_router
from handlers.profile_moderation import router as profile_moderation_router
from handlers.registration_dialog import router as registration_dialog_router
from handlers.reroll import router as reroll_router
from handlers.rules import router as rules_router
from middlewares.environment import EnvironmentMiddleware
from middlewares.game import GameMiddleware
from middlewares.logging import VerboseLoggingMiddleware
from middlewares.private_messages import PrivateMessagesMiddleware
from middlewares.register import RegisterUserMiddleware
from middlewares.user import UserMiddleware
from services import MatchmakingService, kill_timeout_monitor, settings
from services.backend_api import backend_api
from services.discussion_invite import (
    generate_discussion_invite_link,
    revoke_discussion_invite_link,
)
from services.metrics import metrics

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
    dp.include_router(admin_router)
    dp.include_router(join_request_router)
    dp.include_router(kills_confirmation_router)
    dp.include_router(leave_game_router)
    dp.include_router(mainloop_dialog_router)
    dp.include_router(matchmaking_router)
    dp.include_router(my_profile_router)
    dp.include_router(participation_router)
    dp.include_router(profile_moderation_router)
    dp.include_router(registration_dialog_router)
    dp.include_router(reroll_router)
    dp.include_router(rules_router)


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


async def on_startup(bot: Bot) -> None:
    if settings.skip_external_services:
        logger.warning("SKIP_EXTERNAL_SERVICES=1 -> skipping backend bootstrap, matchmaking checks, and timeouts")
        return
    admin_ids = []
    if settings.admin_ids_raw:
        admin_ids = [int(item.strip()) for item in settings.admin_ids_raw.split(",") if item.strip().isdigit()]
    await backend_api.start()
    await backend_api.bootstrap(settings.admin_chat_id, settings.discussion_chat_id, admin_ids)
    await generate_discussion_invite_link(bot)
    await metrics_updater.start()
    if settings.webhook_url:
        if settings.dispatcher is None:
            msg = "Dispatcher is not initialized for webhook setup"
            raise RuntimeError(msg)
        await bot.set_webhook(
            url=settings.webhook_url,
            allowed_updates=settings.dispatcher.resolve_used_update_types(),
            secret_token=settings.secret_key,
        )
    await MatchmakingService().healthcheck()
    await MatchmakingService().reset_queues()
    await kill_timeout_monitor.start(bot)


async def on_shutdown(bot: Bot) -> None:
    if settings.skip_external_services:
        return
    await kill_timeout_monitor.stop()
    await revoke_discussion_invite_link(bot)
    if settings.webhook_url:
        await bot.delete_webhook()
    await metrics_updater.stop()
    await backend_api.close()


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


def _build_storage() -> RedisStorage:
    logger.debug("build storage")
    return RedisStorage(
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


def _build_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    logger.debug("build bot and dispatcher")
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    metrics.instrument_bot(bot)
    dp = Dispatcher(storage=_build_storage())

    settings.bot = bot
    settings.dispatcher = dp

    register_all_middlewares(dp)
    register_all_handlers(dp)
    setup_dialogs(dp)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    return bot, dp


def _ensure_app_state(app: FastAPI) -> tuple[Bot, Dispatcher]:
    bot: Bot | None = getattr(app.state, "bot", None)
    dp: Dispatcher | None = getattr(app.state, "dp", None)
    if bot is not None and dp is not None:
        return bot, dp
    bot, dp = _build_bot_and_dispatcher()
    app.state.bot = bot
    app.state.dp = dp
    return bot, dp


async def run_bot() -> None:
    bot, dp = _build_bot_and_dispatcher()

    if settings.skip_polling:
        logger.warning("SKIP_POLLING=1 -> skipping Telegram polling/webhook setup")
        return

    try:
        logger.info("Starting polling...")
        logger.debug(bot)
        logger.debug(dp)
        await dp.start_polling(bot)
        logger.info("Stopped polling")
    finally:
        await dp.storage.close()
        await bot.session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=os.environ.get("LOGLEVEL", "DEBUG").upper(),
        format="%(levelname)s:\t[%(asctime)s] - %(message)s",
    )
    logger.debug("lifespan called")

    bot, dp = _ensure_app_state(app)
    setup_matchmaking_routers(app, bot)

    if settings.webhook_url:
        await bot.set_webhook(settings.webhook_url, secret_token=settings.secret_key)
        logger.info("Webhook set: %s", settings.webhook_url)
    else:
        await bot.delete_webhook()
        logger.info("Webhook deleted (polling mode)")

    await on_startup(bot)

    try:
        yield
    finally:
        await on_shutdown(bot)
        await dp.storage.close()
        await bot.session.close()


app = FastAPI(lifespan=lifespan)
api_router = APIRouter()
setup_metrics_routes(api_router)
app.include_router(api_router)

WEBHOOK_PATH = _normalize_webhook_path()


@app.post(WEBHOOK_PATH)
async def handle_webhook(request: Request) -> Response:
    if request.headers.get("X-Telegram-Bot-Api-Secret-Token") != settings.secret_key:
        raise HTTPException(status_code=403, detail="Forbidden")

    update = types.Update(**await request.json())
    await app.state.dp.feed_webhook_update(app.state.bot, update)
    return Response(status_code=200)


async def main() -> None:
    logger.debug("main called")
    logger.info("Запущен бот в проекте: %s", settings.project_name)

    _ensure_app_state(app)
    setup_matchmaking_routers(app, app.state.bot)

    server_config = uvicorn.Config(
        app,
        host=settings.web_server_host,
        port=settings.web_server_port,
        log_level=os.environ.get("LOGLEVEL", "debug").lower(),
    )
    server = uvicorn.Server(server_config)
    server_task = asyncio.create_task(server.serve())
    try:
        await run_bot()
    finally:
        server.should_exit = True
        await server_task


if __name__ == "__main__":
    logging.basicConfig(
        level=os.environ.get("LOGLEVEL", "debug").upper(),
        format="%(levelname)s:\t[%(asctime)s] - %(message)s",
    )
    try:
        if settings.webhook_url:
            uvicorn.run(
                app,
                host=settings.web_server_host,
                port=settings.web_server_port,
                log_level=os.environ.get("LOGLEVEL", "debug").lower(),
            )
        else:
            asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен!")
    logger.debug("cleanly shutting down")
