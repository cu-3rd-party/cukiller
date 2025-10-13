from typing import Optional

from aiogram import Bot, Router, F
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

from tgbot.config import Config


async def send_message(
    text: str, bot: Bot, config: Config, tag: Optional[str] = None
):
    await bot.send_message(
        chat_id=config.tg_bot.admin_chat_id,
        text=text if not tag else f"#{tag}\n\n{text}",
        parse_mode="HTML",
    )


async def send_profile_confirmation_request(
    photo,
    user_id: int,
    text: str,
    bot: Bot,
    config: Config,
    tag: Optional[str] = None,
):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="confirm", callback_data=f"confirm {user_id}"
                ),
                InlineKeyboardButton(
                    text="deny", callback_data=f"deny {user_id}"
                ),
            ]
        ]
    )
    await bot.send_photo(
        chat_id=config.tg_bot.admin_chat_id,
        photo=photo,
        caption=text if not tag else f"#{tag}\n\n{text}",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


router = Router(name="profile_moderation")

_CONFIRM_PREFIX = "confirm "
_DENY_PREFIX = "deny "


def _disabled_keyboard(
    label_left: str, label_right: str
) -> InlineKeyboardMarkup:
    """Return a non-interactive keyboard to indicate final state."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=label_left, callback_data="noop"),
                InlineKeyboardButton(text=label_right, callback_data="noop"),
            ]
        ]
    )


def _extract_user_id(data: str, prefix: str) -> Optional[int]:
    if not data.startswith(prefix):
        return None
    raw = data[len(prefix) :].strip()
    try:
        return int(raw)
    except ValueError:
        return None


async def _block_if_not_admin(callback: CallbackQuery, config: Config) -> bool:
    """
    Returns True if processing should stop (user is not admin).
    Shows an alert popup to the user.
    """
    user_id = callback.from_user.id
    if user_id not in getattr(config.tg_bot, "admin_ids", []):
        await callback.answer(
            "У вас нет прав для модерации профилей.", show_alert=True
        )
        return True
    return False


@router.callback_query(F.data.startswith(_CONFIRM_PREFIX))
async def on_confirm_profile(
    callback: CallbackQuery, bot: Bot, config: Config
):
    """
    Admin pressed 'confirm {user_id}'.
    - Notifies the user about approval.
    - Locks the admin message keyboard to a non-interactive state.
    """
    if await _block_if_not_admin(callback, config):
        return
    target_user_id = _extract_user_id(callback.data, _CONFIRM_PREFIX)
    if target_user_id is None:
        await callback.answer("Invalid payload", show_alert=True)
        return

    # Update admin message UI (disable buttons)
    try:
        if callback.message:
            await callback.message.edit_reply_markup(
                reply_markup=_disabled_keyboard("confirmed", "—")
            )
    except TelegramBadRequest:
        # Message could be already edited/deleted; ignore
        pass

    # Notify admin with a toast
    await callback.answer("Profile confirmed", show_alert=False)

    # Notify the user
    try:
        await bot.send_message(
            chat_id=target_user_id,
            text=("<b>Ваш профиль подтверждён модератором.</b>\n\n"),
            parse_mode="HTML",
        )
    except TelegramForbiddenError:
        # The user might have blocked the bot or never started it
        if callback.message:
            await callback.message.reply(
                f"Не удалось отправить уведомление пользователю {target_user_id}: Forbidden"
            )


@router.callback_query(F.data.startswith(_DENY_PREFIX))
async def on_deny_profile(callback: CallbackQuery, bot: Bot, config: Config):
    """
    Admin pressed 'deny {user_id}'.
    - Notifies the user about denial.
    - Locks the admin message keyboard to a non-interactive state.
    """
    if await _block_if_not_admin(callback, config):
        return
    target_user_id = _extract_user_id(callback.data, _DENY_PREFIX)
    if target_user_id is None:
        await callback.answer("Invalid payload", show_alert=True)
        return

    # Update admin message UI (disable buttons)
    try:
        if callback.message:
            await callback.message.edit_reply_markup(
                reply_markup=_disabled_keyboard("—", "denied")
            )
    except TelegramBadRequest:
        pass

    await callback.answer("Profile denied", show_alert=False)

    # Notify the user
    try:
        await bot.send_message(
            chat_id=target_user_id,
            text=(
                "<b>Ваш профиль не прошёл модерацию.</b>\n\n"
                "Пожалуйста, обновите информацию и отправьте повторно."
                "Если нужна помощь — ответьте этому сообщению."
            ),
            parse_mode="HTML",
        )
    except TelegramForbiddenError:
        if callback.message:
            await callback.message.reply(
                f"Не удалось отправить уведомление пользователю {target_user_id}: Forbidden"
            )
