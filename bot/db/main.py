import logging

from tortoise import Tortoise

from db.models import Chat, User
from services import settings

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Initialize Tortoise ORM connection."""
    # TODO: API CALL
    return


async def close_db() -> None:
    """Close all Tortoise ORM connections."""
    # TODO: API CALL
    return


async def _ensure_default_admin_chat() -> None:
    # TODO: API CALL
    return


async def _ensure_default_discussion_group() -> None:
    # TODO: API CALL
    return


async def _ensure_default_admins() -> None:
    # TODO: API CALL
    return
