from aiogram import types

from services.backend_api import backend_api


async def get_or_create_user(user: types.User):
    payload = {
        "tg_id": user.id,
        "tg_username": user.username,
    }
    return await backend_api.get_or_create_user(payload)
