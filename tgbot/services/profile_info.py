from dataclasses import dataclass
from typing import Optional

from PIL import Image


@dataclass
class ProfileInfo:
    """
    Информация о пользователе

    :param name: Имя фамилия цели
    :param description: Описание цели, пара строчек
    :param department: На каком потоке учится цель (значение может быть разработка/ИИ/бизнес-аналитика). Может быть None, тогда просто поток не указывается
    :param profile_photo: Фотка цели. Может быть None, тогда вместо нее должен идти знак вопроса
    """

    user_id: int
    name: str
    description: str = ""
    department: Optional[str] = None
    photo_id: Optional[int] = None
