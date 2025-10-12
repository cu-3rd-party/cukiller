"""
Сервис для генерирования изображений с превью профилей пользователей
"""

import io
from dataclasses import dataclass
from typing import Optional, List
from PIL import Image
import logging

logger = logging.getLogger(__name__)


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
    profile_photo: Optional[Image] = None


class ProfileImageGenerator:
    """
    Генерирует превью для профиля пользователя.

    В перспективе сюда надо прикрутить кэширование. Это не приоритетно, но если уж делать, то это должно быть сделано
    ПОСЛЕ того, как сделаем минимальный рабочий прототип
    """

    # здесь можно задавать любые метаданные
    image_width = 1000
    image_height = 1600
    background_color = (0, 0, 0)  # простой черный фон, в идеале его не видно

    @staticmethod
    def generate_wanted_single(
            user_info: ProfileInfo
    ) -> bytes:
        """
        Функция, которая генерирует одиночное превью цели
        :param user_info: Информация о цели, смотри описание датакласса
        :return:
        """
        logger.debug(f"Запросили генерацию превьюшки для пользователя {user_info.user_id}")
        try:
            # Создаем основной холст
            image = Image.new('RGB', (ProfileImageGenerator.image_width, ProfileImageGenerator.image_height),
                              ProfileImageGenerator.background_color)

            # Здесь должна идти логика рисования превьюхи на холсте
            ...

            img_buffer = io.BytesIO()
            image.save(img_buffer, format="PNG")
            img_buffer.seek(0)

            logger.debug(f"Превьюшка для пользователя {user_info.user_id} успешно сгенерирована")

            return img_buffer.getvalue()

        except Exception as e:
            logger.error(f"Error generating profile image for user {user_info.user_id}: {e}")
            return ProfileImageGenerator._generate_error_image(str(e))

    @staticmethod
    def generate_wanted_multiple(
           users: List[ProfileInfo],
    ):
        """
        По дизайну эта функция сделана, чтоб работать исключительно для 3-х профилей
        :param users: профили каждого из пользователей
        :return:
        """
        raise NotImplementedError()

    @staticmethod
    def _generate_error_image(error_message: str) -> bytes:
        """
        Вызывается в случае, если сгенерировать нормальное изображение не получилось
        :param error_message:
        :return:
        """
        raise NotImplementedError()
