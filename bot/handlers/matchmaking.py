from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram_dialog.api.entities import ShowMode
from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl
from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from handlers import mainloop_dialog
from services import AdminChatService, MainLoop, texts
from services.backend_api import backend_api
from services.settings import settings

router = Router()
api_router = APIRouter()
logger = logging.getLogger(__name__)


def setup_matchmaking_routers(app: FastAPI, bot: Bot) -> None:
    app.state.bot = bot
    app.state.admin_chat = AdminChatService(bot)
    app.state.settings = settings
    api_router.add_api_route("/match", handle_match, methods=["POST"])
    api_router.add_api_route("/restore", get_queue_info, methods=["GET"])
    app.include_router(api_router)


async def get_queue_info(request: Request) -> JSONResponse:
    # All players that are is_in_game but have no target/killer should be queued.
    # A dedicated DB queue schema would be more reliable than filtering by KillEvent.
    if request.headers.get("secret-key") != request.app.state.settings.secret_key:
        raise HTTPException(status_code=403)
    game = await backend_api.get_active_game()
    found_victims: set[str] = set()
    found_killers: set[str] = set()
    events = await backend_api.list_kill_events(game_id=game.id, status="pending") if game else []
    for ke in events:
        found_killers.add(ke.killer_id)
        found_victims.add(ke.victim_id)
    participants = await backend_api.list_game_participants(game.id) if game else []
    potential_killers = [u for u in participants if u.id not in found_killers]
    potential_victims = [u for u in participants if u.id not in found_victims]
    return JSONResponse(
        {
            "killers_queue": [i.tg_id for i in potential_killers],
            "victims_queue": [i.tg_id for i in potential_victims],
        }
    )


async def handle_match(request: Request) -> Response:
    data = await request.json()
    bot: Bot = request.app.state.bot

    if request.headers.get("secret-key") != request.app.state.settings.secret_key:
        raise HTTPException(status_code=403)

    match_quality = data.get("quality", 0.0)

    killer_id = data.get("killer_id")
    victim_id = data.get("victim_id")
    killer_user = await backend_api.get_user_by_tg_id(killer_id)
    victim_user = await backend_api.get_user_by_tg_id(victim_id)

    game = await backend_api.get_active_game()
    if not killer_user or not victim_user or not game:
        return Response(status_code=200)

    ke = await backend_api.create_kill_event(
        {"game_id": game.id, "killer_id": killer_user.id, "victim_id": victim_user.id, "status": "pending"}
    )

    try:
        await request.app.state.admin_chat.send_message(
            key="logs",
            text=texts.render(
                "matchmaking.admin_log",
                killer=killer_user.profile_link(),
                victim=victim_user.profile_link(),
                quality=match_quality,
                kill_event_id=ke.id,
            ),
        )

        await bot.send_message(
            chat_id=killer_user.tg_id,
            text=texts.get("matchmaking.killer_message"),
            parse_mode="HTML",
        )

        victim_dialog_manager = BgManagerFactoryImpl(router=mainloop_dialog.router).bg(
            bot=bot,
            user_id=victim_user.tg_id,
            chat_id=victim_user.tg_id,
        )
        killer_dialog_manager = BgManagerFactoryImpl(router=mainloop_dialog.router).bg(
            bot=bot,
            user_id=killer_user.tg_id,
            chat_id=killer_user.tg_id,
        )

        await victim_dialog_manager.start(
            MainLoop.title,
            data={"game_id": game.id, "user_tg_id": victim_user.tg_id},
            show_mode=ShowMode.AUTO,
        )
        await killer_dialog_manager.start(
            MainLoop.title,
            data={"game_id": game.id, "user_tg_id": killer_user.tg_id},
            show_mode=ShowMode.AUTO,
        )
    except Exception:
        logger.exception("Failed to process matchmaking notification")
    finally:
        return Response(status_code=200)  # noqa: B012
