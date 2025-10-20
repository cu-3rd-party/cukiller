import logging

from aiogram import Router, Bot
from aiogram.enums import ContentType
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram_dialog import Dialog, DialogManager, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Group, Column, Url
from aiogram_dialog.widgets.text import Format, Const

from bot.filters.confirmed import ConfirmedFilter
from bot.filters.private_messages import PrivateMessagesFilter
from bot.filters.user import UserFilter
from bot.misc.states import RegisterForm, MainLoop
from services.admin_chat import AdminChatService
from db.models import User, Game, Player, KillEvent
from settings import Settings

logger = logging.getLogger(__name__)

router = Router()


async def get_main_menu_info(dialog_manager: DialogManager, **kwargs):
    settings: Settings = dialog_manager.middleware_data["settings"]
    game = await Game().filter(end_date=None).first()

    # TODO: database queries
    has_target = True
    is_hunted = True
    is_in_game = True
    target_name = "test"

    return {
        "discussion_link": settings.discussion_chat_invite_link.invite_link,
        "next_game_link": settings.game_info_link,
        "game_running": game is not None,
        "game_not_running": game is None,
        "has_target": has_target,
        "is_hunted": is_hunted,
        "no_target": game is not None and is_in_game and not has_target,
        "target_name": target_name or "Неизвестно",
    }


async def get_target_info(dialog_manager: DialogManager, **kwargs):
    """Getter for target info window"""
    # Get current user from event context
    current_user = None
    user_tg_id = None
    
    # Try to get user from different possible sources
    if "user" in kwargs:
        current_user = kwargs["user"]
    elif "event" in kwargs and hasattr(kwargs["event"], 'from_user'):
        user_tg_id = kwargs["event"].from_user.id
    elif "start_data" in kwargs and "user_tg_id" in kwargs["start_data"]:
        user_tg_id = kwargs["start_data"]["user_tg_id"]
    else:
        # Fallback: try dialog_data if available
        try:
            user_tg_id = dialog_manager.dialog_data.get("user_tg_id")
        except:
            pass

    target_name = "test"

    return {
        "target_name": target_name or "Цель не найдена",
    }


# Button handlers
async def on_get_target(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Handle 'Get Target' button click"""
    # TODO: Implement get target functionality
    await callback.answer("Получение цели...")

async def on_i_was_killed(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Handle 'I was killed' button click"""
    # TODO: Implement kill confirmation functionality  
    await callback.answer("Подтверждение убийства...")

async def on_target_info(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Handle 'Your Target' button click - go to target info window"""
    # Ensure user information is preserved in dialog_data
    if callback.from_user and "user_tg_id" not in manager.dialog_data:
        manager.dialog_data["user_tg_id"] = callback.from_user.id
    await manager.switch_to(MainLoop.target_info)

async def on_write_report(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Handle 'Write Report' button click"""
    # TODO: Implement report functionality
    await callback.answer("Написание репорта...")

async def on_i_killed(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Handle 'I killed' button click"""
    # TODO: Implement kill report functionality
    await callback.answer("Репорт об убийстве...")

async def on_back_to_menu(callback: CallbackQuery, button: Button, manager: DialogManager):
    """Handle 'Back to menu' button click"""
    # Ensure user information is preserved when going back
    if callback.from_user and "user_tg_id" not in manager.dialog_data:
        manager.dialog_data["user_tg_id"] = callback.from_user.id
    await manager.switch_to(MainLoop.title)


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
            Button(
                Const("Написать репорт"),
                id="write_report",
                on_click=on_write_report,
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
    # Start dialog first, then set user data to avoid NoContextError
    await dialog_manager.start(MainLoop.title, data={"user_tg_id": user.tg_id})
