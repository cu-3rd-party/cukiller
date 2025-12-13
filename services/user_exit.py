from __future__ import annotations

from datetime import datetime, timedelta

from db.models import User
from services import settings

# !!! Сколько пользователь не может участвовать в играх
EXIT_COOLDOWN_DURATION = timedelta(days=7)


def compute_exit_cooldown_until(now: datetime | None = None) -> datetime:
    now = now or datetime.now(settings.timezone)
    return now + EXIT_COOLDOWN_DURATION


def is_exit_cooldown_active(user: User, now: datetime | None = None) -> bool:
    if user.exit_cooldown_until is None:
        return False
    now = now or datetime.now(settings.timezone)
    return user.exit_cooldown_until > now


def format_exit_cooldown(user: User, fmt: str = "%d.%m.%Y %H:%M") -> str | None:
    if not user.exit_cooldown_until:
        return None

    until = user.exit_cooldown_until
    if until.tzinfo is None:
        until = until.replace(tzinfo=settings.timezone)
    return until.astimezone(settings.timezone).strftime(fmt)


def calculate_leave_penalty(current_rating: int, opponent_rating: int | None = None) -> int:
    """Тут возвращаем дельту для рейтинга"""
    opponent_rating = opponent_rating or settings.DEFAULT_RATING
    expected_victim = 1 / (1 + 10 ** ((opponent_rating - current_rating) / settings.ELO_SCALE))
    victim_delta = settings.K_VICTIM * (0 - expected_victim)
    return round(victim_delta)
