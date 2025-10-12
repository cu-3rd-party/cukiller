from aiogram import Router, Dispatcher, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from tgbot.config import Config
from tgbot.models.commands import add_or_create_user
from tgbot.services.admin_chat import send_admin_chat_message

router = Router()


@router.message(CommandStart())
async def user_start(
    message: Message, state: FSMContext, config: Config, bot: Bot
):
    await state.clear()

    await state.update_data(last_command="start")

    user, created = await add_or_create_user(user_id=message.from_user.id)
    await message.answer(f"Привет. Вы в базе с id {user.tg_id}")

    states = await state.get_data()
    await message.answer(f"вы ввели команду, {states.get('last_command')}")

    if created:
        await send_admin_chat_message(
            f"Пользователь {message.from_user.mention_html()} использовал команду /start в первый раз",
            bot,
            config,
        )
    else:
        await send_admin_chat_message(
            f"Пользователь {message.from_user.mention_html()} использовал команду /start не в первый раз",
            bot,
            config,
        )
