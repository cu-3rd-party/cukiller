import logging

from aiogram import Router, Bot
from aiohttp import web

from services.admin_chat import AdminChatService

router = Router()
logger = logging.getLogger(__name__)


def setup_matchmaking_routers(app: web.Application, bot: Bot) -> None:
    app["bot"] = bot
    app["admin_chat"] = AdminChatService(bot)
    app.router.add_post("/match", handler=handle_match)


async def handle_match(request: web.Request) -> web.StreamResponse:
    data = await request.json()

    player1 = data["player1"]
    player2 = data["player2"]
    match_quality = data["quality"]

    await request.app["admin_chat"].send_message(
        "logs",
        (
            f"Match found: {player1} vs {player2} "
            f"(quality: {match_quality:.2f})"
        ),
    )

    return web.StreamResponse(status=200)
