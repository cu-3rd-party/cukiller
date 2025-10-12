from aiogram import Bot, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.services.admin_chat import AdminChatService
from db.models.user import User

router = Router()


@router.message(CommandStart())
async def user_start(
    message: Message,
    state: FSMContext,
    bot: Bot,
):
    await state.clear()

    await state.update_data(last_command="start")

    telegram_user = message.from_user
    if telegram_user is None:
        await message.answer("Не удалось определить пользователя.")
        return

    user, created = await User().get_or_create(
        tg_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
    )
    await user.save()

    await message.answer(f"Привет. Вы в базе с id {user.tg_id}")

    states = await state.get_data()
    await message.answer(f"Вы ввели команду, {states.get('last_command')}")

    mention_text = (
        f"@{message.from_user.username}"
        if message.from_user.username is not None
        else None
    )
    if created:
        admin_chat = AdminChatService(bot=bot)
        await admin_chat.send_message(
            key="logs",
            text=f"Пользователь {message.from_user.mention_html(mention_text)} использовал команду /start в первый раз",
            tag="start",
        )
