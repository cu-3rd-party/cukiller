from aiogram import types

from services.backend_api import backend_api
from services.strings import normalize_name_component


async def get_or_create_user(user: types.User):
    payload = {
        "tg_id": user.id,
        "tg_username": user.username,
        "given_name": normalize_name_component(user.first_name),
        "family_name": normalize_name_component(user.last_name),
    }
    return await backend_api.get_or_create_user(payload)
