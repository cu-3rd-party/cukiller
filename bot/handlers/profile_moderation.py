from typing import Optional

from aiogram import Bot, Router, F
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

from db.models import User

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


@router.callback_query(F.data.startswith("noop"))
async def _disabled_keyboard_callback(callback: CallbackQuery, bot: Bot):
    await callback.answer(
        "Никаких действий не требуется, это выключенная кнопка, не видно?",
        show_alert=True,
    )


def _extract_user_id(data: str, prefix: str) -> Optional[int]:
    if not data.startswith(prefix):
        return None
    raw = data[len(prefix) :].strip()
    try:
        return int(raw)
    except ValueError:
        return None


async def _block_if_not_admin(callback: CallbackQuery) -> bool:
    """
    Returns True if processing should stop (user is not admin).
    Shows an alert popup to the user.
    """
    user_id = callback.from_user.id
    user_obj = await User().get(tg_id=user_id)
    if not user_obj.is_admin:
        await callback.answer(
            "У вас нет прав для модерации профилей.", show_alert=True
        )
        return True
    return False


@router.callback_query(F.data.startswith(_CONFIRM_PREFIX))
async def on_confirm_profile(callback: CallbackQuery, bot: Bot):
    """
    Admin pressed 'confirm {user_id}'.
    - Notifies the user about approval.
    - Locks the admin message keyboard to a non-interactive state.
    """
    if await _block_if_not_admin(callback):
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
            text="<b>Ваш профиль подтверждён модератором.</b>\n\n",
            parse_mode="HTML",
        )
        # TODO: start main menu dialog
    except TelegramForbiddenError:
        # The user might have blocked the bot or never started it
        if callback.message:
            await callback.message.reply(
                f"Не удалось отправить уведомление пользователю {target_user_id}: Forbidden"
            )


@router.callback_query(F.data.startswith(_DENY_PREFIX))
async def on_deny_profile(callback: CallbackQuery, bot: Bot):
    """
    Admin pressed 'deny {user_id}'.
    - Notifies the user about denial.
    - Locks the admin message keyboard to a non-interactive state.
    """
    if await _block_if_not_admin(callback):
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
