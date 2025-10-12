# Не оптимизировать импорты и не менять их порядок

import os, django
from typing import Tuple, Optional

from PIL import Image as PILImage
from PIL.Image import Image

from tgbot.services.profile_info import ProfileInfo

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dj_ac.settings")
os.environ.update({"DJANGO_ALLOW_ASYNC_UNSAFE": "true"})
django.setup()

import logging

from asgiref.sync import sync_to_async

from app_telegram.models import TGUser

logger = logging.getLogger(__name__)


@sync_to_async
def add_or_create_user(user_id: int) -> Tuple[TGUser, bool]:
    user, created = TGUser.objects.get_or_create(tg_id=user_id)
    if created:
        logger.info(f"user {user.tg_id} was added to DB")
    else:
        logger.info(f"User {user.tg_id} is already exist")
    return user, created


@sync_to_async
def get_user_profile(user_id: int) -> Optional[ProfileInfo]:
    """
    Если пользователь с таким айди есть в базе данных, то мы возвращаем информацию о его профиле. Если нет, то None
    """
    user_obj = TGUser.objects.filter(tg_id=user_id)
    if not user_obj.exists():
        return None

    return ProfileInfo(
        user_id,
        "Вася Пупкин",
        "Hello, world",
        "Разработка",
        PILImage.open("assets/mock-pfp.jpg"),
    )
