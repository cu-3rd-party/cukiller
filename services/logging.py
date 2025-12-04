import logging

from aiogram.types import CallbackQuery, Message

logger = logging.getLogger("dialog_actions")


def log_dialog_action(action_name: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            event = args[0] if args else None
            manager = args[2] if len(args) > 2 else kwargs.get("manager")

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
                try:
                    state = manager.current_context().state
                except Exception:
                    pass

            logger.info(
                "DIALOG ACTION: user=%s state=%s action=%s data=%s",
                user_id,
                state,
                action_name,
                data,
            )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def log_filter(call_name: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
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


def log_getter(call_name: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            ret = await func(*args, **kwargs)
            logger.debug(
                "GETTER: %s called and returned %s",
                call_name,
                ret,
            )
            return ret

        return wrapper

    return decorator
