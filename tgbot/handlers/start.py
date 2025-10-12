from aiogram import Router, Dispatcher, Bot
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from tgbot.config import Config
from tgbot.models.commands import add_or_create_user, get_user_profile
from tgbot.services import admin_chat

router = Router()


@router.message(CommandStart())
async def user_start(
    message: Message, state: FSMContext, config, bot: Bot
):
    if message.chat.id != message.from_user.id:
        # TODO: import bot mention dynamically instead of hardcoding it into this message
        await message.answer("Этого бота можно использовать только в личных сообщениях. Перейди в @cukillerbot")

    await state.clear()
    await state.update_data(screen="Title")

    user, created = await add_or_create_user(user_id=message.from_user.id)
    profile = await get_user_profile(user_id=message.from_user.id)
    await state.update_data(profile=profile)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="register", callback_data="register")],
            [InlineKeyboardButton(text="overview", callback_data="overview")],
        ]
    )
    if profile:
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="play", callback_data="play")])
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="exit", callback_data="exit")])

    await message.answer(
        f"Тестовое приветственное сообщение для пользователя {message.from_user.mention_html()}",
        parse_mode="HTML",
        reply_markup=keyboard
    )

@router.callback_query()
async def handle_callback(callback_query, **kwargs):
    ...