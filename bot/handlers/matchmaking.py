import logging

from aiogram import Router, Bot
from aiohttp import web

from db.models import KillEvent, Game, User
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
    bot: Bot = request.app["bot"]

    if data["secret_key"] != request.app["settings"].secret_key:
        return web.StreamResponse(status=403)

    match_quality = data.get("quality", 0.0)

    killer_user, _ = await User.get_or_create(tg_id=int(data["killer"]))
    victim_user, _ = await User.get_or_create(tg_id=int(data["victim"]))

    game = await Game.filter(end_date=None).first()

    ke = await KillEvent.create(
        game=game,
        killer=killer_user,
        victim=victim_user,
        status="pending",
        is_approved=False,
    )

    await request.app["admin_chat"].send_message(
        key="logs",
        text=f"Match found: {killer_user.tg_id} vs {victim_user.tg_id} (quality: {match_quality:.2f}), created KillEvent id={ke.id}",
    )

    await bot.send_message(
        chat_id=killer_user.tg_id,
        text=f"Вам была выдана цель: @{victim_user.tg_username or victim_user.tg_id}",  # TODO: player preview
        parse_mode="HTML",
    )

    await bot.send_message(
        chat_id=victim_user.tg_id,
        text="На вас открыта охота",
        parse_mode="HTML",
    )

    return web.StreamResponse(status=200)
