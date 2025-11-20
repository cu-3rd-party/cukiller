import logging

from aiogram import Router, Bot
from aiogram_dialog.api.entities import ShowMode
from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl
from aiohttp import web

from bot.handlers import mainloop_dialog
from bot.misc.states import MainLoop
from db.models import KillEvent, Game, User
from services import settings
from services.admin_chat import AdminChatService

router = Router()
logger = logging.getLogger(__name__)


def setup_matchmaking_routers(app: web.Application, bot: Bot) -> None:
    app["bot"] = bot
    app["admin_chat"] = AdminChatService(bot)
    app["settings"] = settings
    app.router.add_post("/match", handler=handle_match)
    app.router.add_get("/restore", handler=get_queue_info)


async def get_queue_info(request: web.Request) -> web.StreamResponse:
    # по сути все игроки которые is_in_game, но у которых нету цели/нет убийцы подлежат помещению в очередь на матчмейкинг
    # можно сделать уебищную логику через все кто не в KillEvent, но надо TODO: добавить схему очереди в дб
    game = await Game.filter(end_date=None).first()
    found_victims = set()
    found_killers = set()
    for ke in await KillEvent.filter(game=game).all():
        found_killers.add(ke.killer)
        found_victims.add(ke.victim)
    potential_killers = await User.filter(
        is_in_game=True, id__not_in=found_killers
    ).all()
    potential_victims = await User.filter(
        is_in_game=True, id__not_in=found_victims
    ).all()
    return web.json_response(
        status=200,
        data={
            "killers_queue": [i.tg_id for i in potential_killers],
            "victims_queue": [i.tg_id for i in potential_victims],
        },
    )


async def handle_match(request: web.Request) -> web.StreamResponse:
    data = await request.json()
    bot: Bot = request.app["bot"]

    if request.headers.get("secret-key") != request.app["settings"].secret_key:
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
        text=f"Вам была выдана цель, посмотрите",
        parse_mode="HTML",
    )

    await bot.send_message(
        chat_id=victim_user.tg_id,
        text="На вас открыта охота!",
        parse_mode="HTML",
    )

    victim_dialog_manager = BgManagerFactoryImpl(
        router=mainloop_dialog.router
    ).bg(
        bot=bot,
        user_id=victim_user.tg_id,
        chat_id=victim_user.tg_id,
    )
    killer_dialog_manager = BgManagerFactoryImpl(
        router=mainloop_dialog.router
    ).bg(
        bot=bot,
        user_id=killer_user.tg_id,
        chat_id=killer_user.tg_id,
    )

    await victim_dialog_manager.start(
        MainLoop.title,
        data={"game_id": game.id, "user_tg_id": victim_user.tg_id},
        show_mode=ShowMode.DELETE_AND_SEND,
    )
    await killer_dialog_manager.start(
        MainLoop.title,
        data={"game_id": game.id, "user_tg_id": killer_user.tg_id},
        show_mode=ShowMode.DELETE_AND_SEND,
    )

    return web.StreamResponse(status=200)
