import logging

from aiogram import Router, Bot, Dispatcher
from aiogram.enums import ContentType
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Group, Column, Url
from aiogram_dialog.widgets.text import Format, Const

from bot.filters.confirmed import ConfirmedFilter
from bot.filters.private_messages import PrivateMessagesFilter
from bot.filters.user import UserFilter
from bot.handlers import participation
from bot.misc.states import RegisterForm, MainLoop
from bot.misc.states.participation import ParticipationForm
from services.admin_chat import AdminChatService
from db.models import User, Game, Player, KillEvent
from settings import Settings

logger = logging.getLogger(__name__)

router = Router()


async def parse_target_info(game: Game | None, user: User):
    player = await Player.filter(user=user, game=game).first()
    if not player:
        return {"no_target": False, "has_target": False, "is_hunted": False}

    victim_event = await KillEvent.filter(
        killer=player, status="pending"
    ).first()
    killer_event = await KillEvent.filter(
        victim=player, status="pending"
    ).first()

    target_name = "Неизвестно"
    if victim_event:
        await victim_event.fetch_related("victim__user")
        target_name = victim_event.victim.user.name

    return {
        "has_target": victim_event is not None,
        "no_target": victim_event is None,
        "is_hunted": killer_event is not None,
        "target_name": target_name,
    }


async def get_main_menu_info(
    dialog_manager: DialogManager,
    settings: Settings,
    **kwargs,
):
    game = dialog_manager.start_data["game"]
    user = dialog_manager.start_data["user"]

    return {
        "game": game,
        "user": user,
        "discussion_link": settings.discussion_chat_invite_link.invite_link,
        "next_game_link": settings.game_info_link,
        "game_running": game is not None,
        "game_not_running": game is None,
        "user_not_participating": not user.is_in_game and game is not None,
        "user_participating": user.is_in_game and game is not None,
        **await parse_target_info(game, user),
    }


async def get_target_info(dialog_manager: DialogManager, **kwargs):
    """Getter for target info window"""
    settings: Settings = dialog_manager.middleware_data["settings"]
    game = dialog_manager.start_data.get("game")

    return {
        "report_link": settings.report_link,
        **await parse_target_info(game, dialog_manager.start_data["user"]),
    }


# Button handlers
async def on_get_target(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Handle 'Get Target' button click"""
    # TODO: Implement get target functionality
    await callback.answer("Получение цели...")


async def on_i_was_killed(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Handle 'I was killed' button click"""
    # TODO: Implement kill confirmation functionality
    await callback.answer("Подтверждение убийства...")


async def on_target_info(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Handle 'Your Target' button click - go to target info window"""
    await manager.switch_to(MainLoop.target_info)


# async def on_write_report(callback: CallbackQuery, button: Button, manager: DialogManager):
#     """Handle 'Write Report' button click"""
#     # TODO: Implement report functionality
#     await callback.answer("Написание репорта...")


async def on_i_killed(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Handle 'I killed' button click"""
    # TODO: Implement kill report functionality
    await callback.answer("Репорт об убийстве...")


async def on_back_to_menu(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Handle 'Back to menu' button click"""
    await manager.switch_to(MainLoop.title)


async def confirm_participation(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    # info about user and about game is stored in getter, how to access it?
    game = manager.start_data.get("game")
    user = manager.start_data.get("user")
    user_dialog_manager = BgManagerFactoryImpl(router=participation.router).bg(
        bot=manager.event.bot,
        user_id=user.tg_id,
        chat_id=user.tg_id,
    )
    await user_dialog_manager.start(
        ParticipationForm.confirm, data={"game": game, "user": user}
    )


main_menu_dialog = Dialog(
    Window(
        Const("главное меню"),
        Column(
            Url(
                Const("Перейти в чат обсуждения"),
                id="discussion_group_link",
                url=Format("{discussion_link}"),
            ),
            Url(
                Const("Когда следующая игра?"),
                id="next_game_link",
                url=Format("{next_game_link}"),
                when="game_not_running",
            ),
            Button(
                Const("Присоединиться к игре"),
                id="join_game",
                on_click=confirm_participation,
                when="user_not_participating",
            ),
            # Game-related buttons
            Button(
                Const("Получить цель"),
                id="get_target",
                on_click=on_get_target,
                when="no_target",
            ),
            Button(
                Const("Меня убили"),
                id="i_was_killed",
                on_click=on_i_was_killed,
                when="is_hunted",
            ),
            Button(
                Format("Ваша цель: {target_name}"),
                id="target_info",
                on_click=on_target_info,
                when="has_target",
            ),
        ),
        getter=get_main_menu_info,
        state=MainLoop.title,
    ),
    Window(
        Const("Информация о цели"),
        Column(
            Url(
                Const("Написать репорт"),
                id="write_report",
                url=Format("{report_link}"),
            ),
            Button(
                Const("Я убил"),
                id="i_killed",
                on_click=on_i_killed,
            ),
            Button(
                Const("Назад"),
                id="back_to_menu",
                on_click=on_back_to_menu,
            ),
        ),
        getter=get_target_info,
        state=MainLoop.target_info,
    ),
)

router.include_router(main_menu_dialog)


@router.message(
    CommandStart(), ConfirmedFilter(), PrivateMessagesFilter(), UserFilter()
)
async def user_start(
    message: Message,
    dialog_manager: DialogManager,
    bot: Bot,
    user: User,
):
    await dialog_manager.reset_stack()
    game = await Game().filter(end_date=None).first()
    user = await User().get(tg_id=user.tg_id)
    await dialog_manager.start(
        MainLoop.title, data={"user": user, "game": game}
    )
