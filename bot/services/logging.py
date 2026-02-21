import contextlib
import logging
from collections.abc import Awaitable, Callable

from aiogram.types import CallbackQuery, Message

from services.metrics import metrics
logger = logging.getLogger("dialog_actions")


_MANAGER_ARG_INDEX = 2


def log_dialog_action(
    action_name: str,
) -> Callable[[Callable[..., Awaitable[object]]], Callable[..., Awaitable[object]]]:
    def decorator(func: Callable[..., Awaitable[object]]) -> Callable[..., Awaitable[object]]:
        async def wrapper(*args: object, **kwargs: object) -> object:
            event = args[0] if args else None
            manager = args[_MANAGER_ARG_INDEX] if len(args) > _MANAGER_ARG_INDEX else kwargs.get("manager")

            user_id = None
            if isinstance(event, CallbackQuery):
                user_id = event.from_user.id
                data = event.data
            elif isinstance(event, Message):
                user_id = event.from_user.id
                data = event.text
            else:
                data = None

            state = None
            if manager:
                with contextlib.suppress(Exception):
                    state = manager.current_context().state

            logger.info(
                "DIALOG ACTION: user=%s state=%s action=%s data=%s",
                user_id,
                state,
                action_name,
                data,
            )

            metrics.increment_action(action_name)
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def log_filter(call_name: str) -> Callable[[Callable[..., Awaitable[object]]], Callable[..., Awaitable[object]]]:
    def decorator(func: Callable[..., Awaitable[object]]) -> Callable[..., Awaitable[object]]:
        async def wrapper(*args: object, **kwargs: object) -> object:
            ret = await func(*args, **kwargs)
            logger.debug(
                "FILTER: %s called on user=%s and returned %s",
                call_name,
                args[1].from_user.id,
                ret,
            )
            return ret

        return wrapper

    return decorator


def log_getter(call_name: str) -> Callable[[Callable[..., Awaitable[object]]], Callable[..., Awaitable[object]]]:
    def decorator(func: Callable[..., Awaitable[object]]) -> Callable[..., Awaitable[object]]:
        async def wrapper(*args: object, **kwargs: object) -> object:
            ret = await func(*args, **kwargs)
            logger.debug(
                "GETTER: %s called and returned %s",
                call_name,
                ret,
            )
            return ret

        return wrapper

    return decorator
