from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from tgbot.models.commands import add_or_create_user

router = Router()


@router.message(CommandStart())
async def user_start(message: Message, state: FSMContext):
    await state.clear()

    await state.update_data(last_command="start")

    user = await add_or_create_user(user_id=message.from_user.id)
    await message.answer(f"Привет. Вы в базе с id {user.tg_id}")

    states = await state.get_data()
    await message.answer(f"вы ввели команду, {states.get('last_command')}")
