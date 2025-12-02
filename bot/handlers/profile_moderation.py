import asyncio
import html
import re
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from aiogram import Bot, F, Router
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
)
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram_dialog import ShowMode
from aiogram_dialog.manager.bg_manager import BgManagerFactoryImpl

from bot.handlers import mainloop_dialog
from bot.handlers.registration_dialog import COURSE_TYPES
from db.models import Game, PendingProfile, User
from services import settings
from services.states import MainLoop, ProfileModeration

router = Router(name="profile_moderation")

_CONFIRM_PREFIX = "confirm_pending:"
_DENY_PREFIX = "deny_pending:"
_TAG = "profile_confirm"


FIELD_LABELS = {
    "name": "Имя",
    "type": "Тип",
    "course_number": "Курс",
    "group_name": "Поток",
    "about_user": "О себе",
    "photo": "Фото",
}


def _moderator_name(tg_user) -> str:
    if tg_user.username:
        return f"@{tg_user.username}"
    full_name = tg_user.full_name or str(tg_user.id)
    return html.escape(full_name)


def _extract_pending_id_from_text(text: str) -> Optional[UUID]:
    match = re.search(
        r"(?P<uuid>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
        text or "",
    )
    if not match:
        return None
    try:
        return UUID(match.group("uuid"))
    except ValueError:
        return None


def _extract_pending_id_from_message(message: Message) -> Optional[UUID]:
    reply = message.reply_to_message
    if reply:
        for payload in (reply.text, reply.caption):
            pending_id = _extract_pending_id_from_text(payload or "")
            if pending_id:
                return pending_id

    for payload in (message.text, message.caption):
        pending_id = _extract_pending_id_from_text(payload or "")
        if pending_id:
            return pending_id
    return None


def _has_pending_id(message: Message) -> bool:
    return _extract_pending_id_from_message(message) is not None


def _extract_pending_id(data: str, prefix: str) -> Optional[UUID]:
    if not data.startswith(prefix):
        return None
    raw = data[len(prefix) :]
    try:
        return UUID(raw)
    except ValueError:
        return None


def _wrap_with_tag(text: str) -> str:
    return f"#{_TAG}\n\n{text}"


def _format_value(field: str, value) -> str:
    if value is None:
        return "-"
    if field == "type":
        return COURSE_TYPES.get(value, value)
    return str(value)


def _build_new_profile_body(pending: PendingProfile) -> str:
    return (
        "<b>Новый профиль:</b>\n\n"
        f"<b>ID заявки:</b> {pending.id}\n"
        f"<b>Имя:</b> {html.escape(_format_value('name', pending.name))}\n"
        f"<b>Тип:</b> {html.escape(_format_value('type', pending.type))}\n"
        f"<b>Курс:</b> {html.escape(_format_value('course_number', pending.course_number))}\n"
        f"<b>Поток:</b> {html.escape(_format_value('group_name', pending.group_name))}\n"
        f"<b>О себе:</b> {html.escape(_format_value('about_user', pending.about_user))}\n"
        f"<b>Username:</b> @{pending.submitted_username or 'не указан'}\n"
        f"<b>ID:</b> {pending.user.tg_id}"
    )


def _build_changes_body(pending: PendingProfile, current_user: User) -> str:
    lines = [
        "<b>Изменение профиля:</b>",
        f"<b>ID заявки:</b> {pending.id}",
        f"<b>ID:</b> {pending.user.tg_id}",
        f"<b>Username:</b> @{pending.submitted_username or 'не указан'}",
    ]
    for field in pending.changed_fields:
        if field == "photo":
            lines.append(f"<b>{FIELD_LABELS['photo']}:</b> обновлено")
            continue
        old_value = getattr(current_user, field)
        new_value = getattr(pending, field)
        lines.append(
            f"<b>{FIELD_LABELS[field]}:</b>\n"
            f"— было: {html.escape(_format_value(field, old_value))}\n"
            f"— стало: {html.escape(_format_value(field, new_value))}"
        )
    return "\n\n".join(lines)


def _build_admin_body(pending: PendingProfile, user: User) -> str:
    if pending.is_new_profile:
        return _build_new_profile_body(pending)
    return _build_changes_body(pending, user)


def _build_user_denied_text(
    pending: PendingProfile, reason: str | None
) -> str:
    if pending.is_new_profile:
        base = "К сожалению, нам пришлось отклонить вашу заявку"
        if reason:
            return f"{base}, причина: {html.escape(reason)}"
        return base + "."
    else:
        base = "Ваши изменения не соответствуют нашим правилам"
        if reason:
            return f"{base} по причине {html.escape(reason)}."
        return base + "."


async def _apply_pending_profile(pending: PendingProfile) -> User:
    await pending.fetch_related("user")
    user = pending.user
    for field in pending.changed_fields:
        setattr(user, field, getattr(pending, field))
    if pending.submitted_username is not None:
        user.tg_username = pending.submitted_username
    if pending.is_new_profile:
        user.status = "confirmed"
    await user.save()
    return user


async def _edit_admin_message(
    bot: Bot,
    pending: PendingProfile,
    body: str,
    status_line: str,
    message: Message | None = None,
):
    chat_id = pending.chat_id or (message and message.chat.id)
    message_id = pending.message_id or (message and message.message_id)
    if not chat_id or not message_id:
        return

    full_body = f"{status_line}\n\n{_wrap_with_tag(body)}"

    try:
        await bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=full_body,
            reply_markup=None,
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=full_body,
            reply_markup=None,
            parse_mode="HTML",
        )


async def _notify_user_rejection(
    bot: Bot, pending: PendingProfile, reason: str | None
):
    text = _build_user_denied_text(pending, reason)
    try:
        await bot.send_message(chat_id=pending.user.tg_id, text=text)
    except TelegramForbiddenError:
        return


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


async def _process_rejection(
    *,
    message: Message,
    bot: Bot,
    pending: PendingProfile,
    moderator: User,
    reason_text: str,
    state: FSMContext | None = None,
):
    if pending.status != "rejected":
        await message.answer("Эта заявка уже обработана")
        if state:
            await state.clear()
        return

    updated_at = pending.updated_at
    updated_at_local = (
        updated_at
        if updated_at.tzinfo
        else updated_at.replace(tzinfo=settings.timezone)
    )
    now_local = datetime.now(updated_at_local.tzinfo)
    if now_local - updated_at_local > timedelta(minutes=10):
        await message.answer("Время на указание причины истекло")
        if state:
            await state.clear()
        return

    reason = None if reason_text.lower() == "none" else reason_text
    pending.reason = reason
    pending.moderator = moderator
    await pending.save()

    body = _build_admin_body(pending, pending.user)
    status_line = (
        f"❌ Отклонено {_moderator_name(message.from_user)} "
        f"{'(без причины)' if reason is None else f'по причине {html.escape(reason)}'}"
    )
    await _edit_admin_message(
        bot,
        pending,
        body=body,
        status_line=status_line,
    )

    await _notify_user_rejection(bot, pending, reason)
    await message.answer("Причина сохранена")

    if state:
        await state.clear()


@router.callback_query(F.data.startswith("noop"))
async def _disabled_keyboard_callback(callback: CallbackQuery, bot: Bot):
    await callback.answer(
        "Никаких действий не требуется, это выключенная кнопка, не видно?",
        show_alert=True,
    )


async def _block_if_not_admin(callback: CallbackQuery) -> bool:
    """
    Returns True if processing should stop (user is not admin).
    Shows an alert popup to the user.
    """
    user_id = callback.from_user.id
    user_obj = await User.get_or_none(tg_id=user_id)
    if not user_obj or not user_obj.is_admin:
        await callback.answer(
            "У вас нет прав для модерации профилей.", show_alert=True
        )
        return True
    return False


@router.callback_query(F.data.startswith(_CONFIRM_PREFIX))
async def on_confirm_profile(
    callback: CallbackQuery, bot: Bot, state: FSMContext
):
    """
    Admin pressed 'confirm {user_id}'.
    - Notifies the user about approval.
    - Locks the admin message keyboard to a non-interactive state.
    """
    if await _block_if_not_admin(callback):
        return
    await state.clear()
    pending_id = _extract_pending_id(callback.data, _CONFIRM_PREFIX)
    if pending_id is None:
        await callback.answer("Invalid payload", show_alert=True)
        return

    pending = (
        await PendingProfile.filter(id=pending_id)
        .prefetch_related("user")
        .first()
    )
    if pending is None:
        await callback.answer("Запрос не найден", show_alert=True)
        return
    if pending.status != "pending":
        await callback.answer("Заявка уже обработана", show_alert=True)
        return

    body = _build_admin_body(pending, pending.user)

    moderator = await User.get_or_none(tg_id=callback.from_user.id)
    approved_user = await _apply_pending_profile(pending)
    pending.status = "approved"
    pending.moderator = moderator
    pending.reason = None
    await pending.save()

    await _edit_admin_message(
        bot,
        pending,
        body=body,
        status_line=f"✅ Подтверждено {_moderator_name(callback.from_user)}",
        message=callback.message,
    )

    await callback.answer("Profile confirmed", show_alert=False)

    notify_text = (
        "Ваш профиль подтвержден, скорее изучайте возможности бота"
        if pending.is_new_profile
        else "Изменения приняты"
    )

    try:
        await bot.send_message(chat_id=approved_user.tg_id, text=notify_text)
        if pending.is_new_profile:
            user_dialog_manager = BgManagerFactoryImpl(
                router=mainloop_dialog.router
            ).bg(
                bot=bot,
                user_id=approved_user.tg_id,
                chat_id=approved_user.tg_id,
            )
            game = await Game().filter(end_date=None).first()
            await user_dialog_manager.start(
                MainLoop.title,
                data={
                    "user_tg_id": approved_user.tg_id,
                    "game_id": (game and game.id) or None,
                },
                show_mode=ShowMode.DELETE_AND_SEND,
            )
    except TelegramForbiddenError as e:
        if callback.message:
            await callback.message.reply(
                f"Не удалось отправить уведомление пользователю {approved_user.tg_id}: {e}"
            )


@router.callback_query(F.data.startswith(_DENY_PREFIX))
async def on_deny_profile(
    callback: CallbackQuery, bot: Bot, state: FSMContext
):
    """
    Admin pressed 'deny {user_id}'.
    - Notifies the user about denial.
    - Locks the admin message keyboard to a non-interactive state.
    """
    if await _block_if_not_admin(callback):
        return
    pending_id = _extract_pending_id(callback.data, _DENY_PREFIX)
    if pending_id is None:
        await callback.answer("Invalid payload", show_alert=True)
        return

    pending = (
        await PendingProfile.filter(id=pending_id)
        .prefetch_related("user")
        .first()
    )
    if pending is None:
        await callback.answer("Запрос не найден", show_alert=True)
        return
    if pending.status != "pending":
        await callback.answer("Заявка уже обработана", show_alert=True)
        return

    try:
        if callback.message:
            await callback.message.edit_reply_markup(
                reply_markup=_disabled_keyboard("—", "denied")
            )
    except TelegramBadRequest:
        pass

    await callback.answer("Profile denied", show_alert=False)

    moderator = await User.get_or_none(tg_id=callback.from_user.id)
    pending.status = "rejected"
    pending.moderator = moderator
    pending.reason = None
    await pending.save()

    status_line = (
        f"❌ Отклонено {_moderator_name(callback.from_user)} (ожидаем причину)"
    )
    body = _build_admin_body(pending, pending.user)
    await _edit_admin_message(
        bot,
        pending,
        body=body,
        status_line=status_line,
        message=callback.message,
    )

    if pending.is_new_profile:
        pending.user.status = "rejected"
        await pending.user.save(update_fields=["status"])

    try:
        await bot.send_message(
            chat_id=callback.from_user.id,
            text=(
                "Укажи причину отклонения заявки.\n"
                f"ID заявки: {pending.id}\n"
                "Ответь на это сообщение текстом причины или словом None"
            ),
        )
    except TelegramForbiddenError:
        pass

    user_state = FSMContext(
        storage=state.storage,
        key=StorageKey(
            bot_id=bot.id,
            chat_id=callback.from_user.id,
            user_id=callback.from_user.id,
        ),
    )
    await user_state.set_state(ProfileModeration.waiting_reason)
    await user_state.update_data(pending_id=str(pending.id))

    initial_updated = pending.updated_at

    async def _timeout_notify():
        await asyncio.sleep(600)
        fresh = (
            await PendingProfile.filter(id=pending.id)
            .prefetch_related("user")
            .first()
        )
        if not fresh:
            return
        if fresh.status != "rejected":
            return
        if fresh.reason is not None:
            return
        if fresh.updated_at != initial_updated:
            return
        await _notify_user_rejection(bot, fresh, None)

    asyncio.create_task(_timeout_notify())


@router.message(
    StateFilter(ProfileModeration.waiting_reason),
    flags={"block": True, "dialog": False},
)
async def on_rejection_reason_state(
    message: Message, bot: Bot, state: FSMContext
):
    moderator = await User.get_or_none(tg_id=message.from_user.id)
    if not moderator or not moderator.is_admin:
        return

    data = await state.get_data()
    pending_id_raw = data.get("pending_id")
    pending_id = _extract_pending_id_from_message(message)
    if pending_id is None and pending_id_raw:
        try:
            pending_id = UUID(pending_id_raw)
        except ValueError:
            pending_id = None

    if pending_id is None:
        await message.answer(
            "Не удалось определить заявку. Ответь на сообщение с ID заявки"
        )
        return

    pending = (
        await PendingProfile.filter(id=pending_id)
        .prefetch_related("user")
        .first()
    )
    if not pending:
        await message.answer("Заявка не найдена")
        await state.clear()
        return

    reason_text = (message.text or message.caption or "").strip()
    if not reason_text:
        await message.answer("Пришли текст причины или слово None")
        return

    await _process_rejection(
        message=message,
        bot=bot,
        pending=pending,
        moderator=moderator,
        reason_text=reason_text,
        state=state,
    )


@router.message(_has_pending_id, flags={"block": True, "dialog": False})
async def on_rejection_reason(message: Message, bot: Bot, state: FSMContext):
    moderator = await User.get_or_none(tg_id=message.from_user.id)
    if not moderator or not moderator.is_admin:
        return

    pending_id = _extract_pending_id_from_message(message)
    if not pending_id:
        return

    pending = (
        await PendingProfile.filter(id=pending_id)
        .prefetch_related("user")
        .first()
    )
    if not pending:
        return

    reason_text = (message.text or message.caption or "").strip()
    if not reason_text:
        return

    await _process_rejection(
        message=message,
        bot=bot,
        pending=pending,
        moderator=moderator,
        reason_text=reason_text,
        state=state,
    )
