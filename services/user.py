from aiogram import types

from db.models import User


async def get_or_create_user(user: types.User):
    return await User.get_or_create(
        tg_id=user.id,
        defaults={
            "tg_id": user.id,
            "tg_username": user.username if user.username else None,
        },
    )
