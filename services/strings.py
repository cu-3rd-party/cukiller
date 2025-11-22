import re
from dataclasses import dataclass
from html import unescape

SAFE_PATTERN = re.compile(r"^[\w\s\-\.,!()]+$", re.UNICODE)


@dataclass
class SafeStringConfig:
    allow_newline: bool = False
    max_len: int = 200
    allow_html: bool = False
    safe_pattern: bool = True


def is_safe(
    string: str, config: SafeStringConfig = SafeStringConfig()
) -> bool:
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
