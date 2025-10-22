from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl
from aiogram_dialog.widgets.kbd import Button

from bot.handlers import participation
from bot.misc.states import MainLoop
from bot.misc.states.participation import ParticipationForm
from db.models import User
from services.matchmaking import MatchmakingService


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

# async def on_write_report(callback: CallbackQuery, button: Button, manager: DialogManager):
#     """Handle 'Write Report' button click"""
#     # TODO: Implement report functionality
#     await callback.answer("Написание репорта...")
async def on_get_target(
    callback: CallbackQuery, button: Button, manager: DialogManager
):
    """Handle 'Get Target' button click"""
    matchmaking: MatchmakingService = manager.middleware_data.get(
        "matchmaking"
    )
    user: User = manager.start_data.get("user")
    await matchmaking.add_player_to_queue(
        user.tg_id,
        {
            "player_id": user.tg_id,
            "rating": user.rating,
            "type": user.type,
            "course_number": user.course_number,
            "group_name": user.group_name,
        },
    )
    await callback.answer("Вы были поставлены в очередь, ожидайте...")


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
