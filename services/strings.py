import re
from dataclasses import dataclass
from datetime import timedelta
from html import unescape

SAFE_PATTERN = re.compile(r"^[\w\s\-\.,!()]+$", re.UNICODE)


@dataclass
class SafeStringConfig:
    allow_newline: bool = False
    max_len: int = 200
    allow_html: bool = False
    safe_pattern: bool = True


def is_safe(string: str, config: SafeStringConfig = SafeStringConfig()) -> bool:
    raw = unescape(string)
    if not config.allow_newline and ("\n" in raw or "\r" in raw):
        return False
    if len(raw) > config.max_len:
        return False
    if not config.allow_html and ("<" in raw or ">" in raw):
        return False
    if config.safe_pattern and not SAFE_PATTERN.match(raw):
        return False

    return True


def trim_name(string: str, max_len: int) -> str:
    """Trim string and add ellipsis if too long."""
    if len(string) > max_len:
        return string[: max_len - 3] + "..."
    return string


def format_timedelta(delta: timedelta) -> str:
    """Format timedelta into a human-readable string."""
    total_seconds = int(delta.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days}д")
    if hours > 0:
        parts.append(f"{hours}ч")
    if minutes > 0:
        parts.append(f"{minutes}м")
    if seconds > 0 or not parts:  # Always show at least seconds if nothing else
        parts.append(f"{seconds}с")

    return " ".join(parts)
