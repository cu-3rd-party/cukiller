import asyncio
import contextlib
import html
import re
from datetime import datetime, timedelta
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
from services import settings, texts
from services.states import MainLoop, ProfileModeration

router = Router(name="profile_moderation")

_CONFIRM_PREFIX = "confirm_pending:"
_DENY_PREFIX = "deny_pending:"
_TAG = "profile_confirm"


FIELD_LABELS = texts.PROFILE_FIELD_LABELS


def _moderator_name(tg_user) -> str:
    if tg_user.username:
        return f"@{tg_user.username}"
    full_name = tg_user.full_name or str(tg_user.id)
    return html.escape(full_name)


def _extract_pending_id_from_text(text: str) -> UUID | None:
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


def _extract_pending_id_from_message(message: Message) -> UUID | None:
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


def _extract_pending_id(data: str, prefix: str) -> UUID | None:
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
    if field == "allow_hugging_on_kill":
        return texts.get("profile.hugs_allowed_yes") if value else texts.get("profile.hugs_allowed_no")
    return str(value)


def _build_new_profile_body(pending: PendingProfile) -> str:
    return texts.render(
        "moderation.new_profile_body",
        pending_id=pending.id,
        name=html.escape(_format_value("name", pending.name)),
        type=html.escape(_format_value("type", pending.type)),
        course_number=html.escape(_format_value("course_number", pending.course_number)),
        group_name=html.escape(_format_value("group_name", pending.group_name)),
        about_user=html.escape(_format_value("about_user", pending.about_user)),
        allow_hugging_on_kill=html.escape(_format_value("allow_hugging_on_kill", pending.allow_hugging_on_kill)),
        submitted_username=pending.submitted_username or texts.get("common.username_unknown"),
        user_id=pending.user.tg_id,
    )


def _build_changes_body(pending: PendingProfile, current_user: User) -> str:
    lines = [
        texts.get("moderation.change_header"),
        texts.render("moderation.change_meta_id", pending_id=pending.id),
        texts.render("moderation.change_meta_user_id", user_id=pending.user.tg_id),
        texts.render(
            "moderation.change_meta_username",
            username=pending.submitted_username or texts.get("common.username_unknown"),
        ),
    ]
    for field in pending.changed_fields:
        if field == "photo":
            lines.append(
                texts.render("moderation.change_photo", field_label=FIELD_LABELS["photo"])
            )
            continue
        old_value = getattr(current_user, field)
        new_value = getattr(pending, field)
        lines.append(
            texts.render(
                "moderation.change_line",
                field_label=FIELD_LABELS[field],
                old_value=html.escape(_format_value(field, old_value)),
                new_value=html.escape(_format_value(field, new_value)),
            )
        )
    return "\n\n".join(lines)


def _build_admin_body(pending: PendingProfile, user: User) -> str:
    if pending.is_new_profile:
        return _build_new_profile_body(pending)
    return _build_changes_body(pending, user)


def _build_user_denied_text(pending: PendingProfile, reason: str | None) -> str:
    if pending.is_new_profile:
        if reason:
            return texts.render("moderation.user_denied_new_reason", reason=html.escape(reason))
        return texts.get("moderation.user_denied_new")
    if reason:
        return texts.render("moderation.user_denied_update_reason", reason=html.escape(reason))
    return texts.get("moderation.user_denied_update")


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
) -> None:
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


async def _notify_user_rejection(bot: Bot, pending: PendingProfile, reason: str | None) -> None:
    text = _build_user_denied_text(pending, reason)
    try:
        await bot.send_message(chat_id=pending.user.tg_id, text=text)
    except TelegramForbiddenError:
        return


def _disabled_keyboard(label_left: str, label_right: str) -> InlineKeyboardMarkup:
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
) -> None:
    if pending.status != "rejected":
        await message.answer(texts.get("moderation.request_already_processed"))
        if state:
            await state.clear()
        return

    updated_at = pending.updated_at
    updated_at_local = updated_at if updated_at.tzinfo else updated_at.replace(tzinfo=settings.timezone)
    now_local = datetime.now(updated_at_local.tzinfo)
    if now_local - updated_at_local > timedelta(minutes=10):
        await message.answer(texts.get("moderation.reason_timeout"))
        if state:
            await state.clear()
        return

    reason = None if reason_text.lower() == "none" else reason_text
    pending.reason = reason
    pending.moderator = moderator
    await pending.save()

    body = _build_admin_body(pending, pending.user)
    reason_part = (
        texts.get("moderation.ask_reason_placeholder")
        if reason is None
        else texts.render("moderation.ask_reason_prefix", reason=html.escape(reason))
    )
    status_line = texts.render(
        "moderation.status_denied",
        moderator=_moderator_name(message.from_user),
        reason_part=reason_part,
    )
    await _edit_admin_message(
        bot,
        pending,
        body=body,
        status_line=status_line,
    )

    await _notify_user_rejection(bot, pending, reason)
    await message.answer(texts.get("moderation.reason_saved"))

    if state:
        await state.clear()


@router.callback_query(F.data.startswith("noop"))
async def _disabled_keyboard_callback(callback: CallbackQuery, bot: Bot) -> None:
    await callback.answer(
        texts.get("moderation.noop"),
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
        await callback.answer(texts.get("moderation.no_rights"), show_alert=True)
        return True
    return False


@router.callback_query(F.data.startswith(_CONFIRM_PREFIX))
async def on_confirm_profile(callback: CallbackQuery, bot: Bot, state: FSMContext):
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
        await callback.answer(texts.get("moderation.invalid_payload"), show_alert=True)
        return

    pending = await PendingProfile.filter(id=pending_id).prefetch_related("user").first()
    if pending is None:
        await callback.answer(texts.get("moderation.request_not_found"), show_alert=True)
        return
    if pending.status != "pending":
        await callback.answer(texts.get("moderation.request_done"), show_alert=True)
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
        status_line=texts.render(
            "moderation.status_confirmed",
            moderator=_moderator_name(callback.from_user),
        ),
        message=callback.message,
    )

    await callback.answer(texts.get("moderation.confirmed_alert"), show_alert=False)

    notify_text = (
        texts.get("moderation.confirm_notify_new")
        if pending.is_new_profile
        else texts.get("moderation.confirm_notify_update")
    )

    try:
        await bot.send_message(chat_id=approved_user.tg_id, text=notify_text)
        if pending.is_new_profile:
            user_dialog_manager = BgManagerFactoryImpl(router=mainloop_dialog.router).bg(
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
                show_mode=ShowMode.AUTO,
            )
    except TelegramForbiddenError as e:
        if callback.message:
            await callback.message.reply(
                texts.render(
                    "moderation.cannot_notify_user",
                    user_id=approved_user.tg_id,
                    error=e,
                )
            )


@router.callback_query(F.data.startswith(_DENY_PREFIX))
async def on_deny_profile(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """
    Admin pressed 'deny {user_id}'.
    - Notifies the user about denial.
    - Locks the admin message keyboard to a non-interactive state.
    """
    if await _block_if_not_admin(callback):
        return
    pending_id = _extract_pending_id(callback.data, _DENY_PREFIX)
    if pending_id is None:
        await callback.answer(texts.get("moderation.invalid_payload"), show_alert=True)
        return

    pending = await PendingProfile.filter(id=pending_id).prefetch_related("user").first()
    if pending is None:
        await callback.answer(texts.get("moderation.request_not_found"), show_alert=True)
        return
    if pending.status != "pending":
        await callback.answer(texts.get("moderation.request_done"), show_alert=True)
        return

    try:
        if callback.message:
            await callback.message.edit_reply_markup(reply_markup=_disabled_keyboard("—", "denied"))
    except TelegramBadRequest:
        pass

    await callback.answer(texts.get("moderation.denied_alert"), show_alert=False)

    moderator = await User.get_or_none(tg_id=callback.from_user.id)
    pending.status = "rejected"
    pending.moderator = moderator
    pending.reason = None
    await pending.save()

    status_line = texts.render(
        "moderation.status_denied_waiting", moderator=_moderator_name(callback.from_user)
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

    with contextlib.suppress(TelegramForbiddenError):
        await bot.send_message(
            chat_id=callback.from_user.id,
            text=texts.render("moderation.notify_reason", pending_id=pending.id),
        )

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

    async def _timeout_notify() -> None:
        await asyncio.sleep(600)
        fresh = await PendingProfile.filter(id=pending.id).prefetch_related("user").first()
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
async def on_rejection_reason_state(message: Message, bot: Bot, state: FSMContext):
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
        await message.answer(texts.get("moderation.reason_missing_pending"))
        return

    pending = await PendingProfile.filter(id=pending_id).prefetch_related("user").first()
    if not pending:
        await message.answer(texts.get("moderation.pending_not_found"))
        await state.clear()
        return

    reason_text = (message.text or message.caption or "").strip()
    if not reason_text:
        await message.answer(texts.get("moderation.reason_empty"))
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

    pending = await PendingProfile.filter(id=pending_id).prefetch_related("user").first()
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
