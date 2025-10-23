import logging

from aiogram import Router, Bot
from aiohttp import web

from db.models import KillEvent, Game
from services.admin_chat import AdminChatService
from settings import Settings

router = Router()
logger = logging.getLogger(__name__)


def setup_matchmaking_routers(
    app: web.Application, bot: Bot, settings: Settings
) -> None:
    app["bot"] = bot
    app["admin_chat"] = AdminChatService(bot)
    app["settings"] = settings
    app.router.add_post("/match", handler=handle_match)


async def handle_match(request: web.Request) -> web.StreamResponse:
    data = await request.json()

    if data["secret_key"] != request.app["settings"].secret_key:
        return web.StreamResponse(status=403)

    killer = data["killer"]
    victim = data["victim"]
    match_quality = data["quality"]

    await request.app["admin_chat"].send_message(
        "logs",
        f"Match found: {killer} vs {victim} (quality: {match_quality:.2f})",
    )

    return web.StreamResponse(status=200)
