from aiogram.types import TelegramObject


def extract_user(event: TelegramObject):
    return (
        (event.message and event.message.from_user)
        or (event.callback_query and event.callback_query.from_user)
        or (event.my_chat_member and event.my_chat_member.from_user)
        or (event.chat_join_request and event.chat_join_request.from_user)
    )
