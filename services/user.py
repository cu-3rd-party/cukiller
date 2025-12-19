from aiogram import types

from db.models import User
from services.strings import normalize_name_component


async def get_or_create_user(user: types.User):
    return await User.get_or_create(
        tg_id=user.id,
        defaults={
            "tg_id": user.id,
            "tg_username": user.username if user.username else None,
            "given_name": normalize_name_component(user.first_name),
            "family_name": normalize_name_component(user.last_name),
        },
    )
