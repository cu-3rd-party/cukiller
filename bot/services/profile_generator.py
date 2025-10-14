"""
Сервис для генерирования изображений с превью профилей пользователей
"""

import io
from dataclasses import dataclass
from typing import Optional, List
from PIL import Image
import logging

logger = logging.getLogger(__name__)

global PATH_TO_IMAGES 
PATH_TO_IMAGES= "bot/services/images" # Вынесено в отдельную переменную

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
    department: str | None = None
    profile_photo: Image.Image | None = None # добавил Image.Image


class ProfileImageGenerator:
    """
    Генерирует превью для профиля пользователя.

    Настраиваемые параметры:
    - image_width, image_height - размеры рабочей области в пикселях
    - area_X, area_Y - координаты левого верхнего угла рабочей области относительно левого верхнего угла фона

    В перспективе сюда надо прикрутить кэширование. Это не приоритетно, но если уж делать, то это должно быть сделано
    ПОСЛЕ того, как сделаем минимальный рабочий прототип
    """
    background = Image.open(f'{PATH_TO_IMAGES}/background.png') # Фон для превьюшки
    background_width, background_height = background.size # Получаем размеры фона

    image_width = 1191 
    image_height = 1588
    working_area = (image_width, image_height)  # Размеры рабочей области (должны быть 3:4)
   
    area_X = 250
    area_Y = 488
    area_cord = (area_X, area_Y)


    @staticmethod
    def generate_wanted_single(user_info: ProfileInfo) -> bytes:
        """
        Функция, которая генерирует одиночное превью цели
        :param user_info: Информация о цели, смотри описание датакласса
        :return:
        """
        logger.debug(
            f"Запросили генерацию превьюшки для пользователя {user_info.user_id}"
        )
        try:
            user_image = user_info.profile_photo 
            preview = ProfileImageGenerator.background.copy()
            user_image_width, user_image_height = user_image.size
            if round(user_image_width / user_image_height, 2) == 0.75: 
                #Если фото 3:4 то просто подгоняем его под размеры рабочей области
                user_image = user_image.resize(ProfileImageGenerator.working_area)
            elif user_image_width / user_image_height > 1: # Если фотка горизонтальная
                if user_image_height > ProfileImageGenerator.image_height \
                  and user_image_width > ProfileImageGenerator.image_width: # Проверяем что из фотки можно вырезать область
                    left = (user_image_width - ProfileImageGenerator.image_width) / 2
                    right = left + ProfileImageGenerator.image_width
                    top = (user_image_height - ProfileImageGenerator.image_height) / 2
                    bottom = top + ProfileImageGenerator.image_height
                    user_image = user_image.crop((left, top, right, bottom)) #вырезаем нужный нам кусок из центра
                else:
                    # Тут надо что-ли логи вывести, что фотка горизонтальная и не может быть использована
                    pass
            else: 
                # Если фотка все-таки корявая, просто тянем ее под нужный нам размер
                user_image = user_image.resize(ProfileImageGenerator.working_area)
            preview.paste(user_image, ProfileImageGenerator.area_cord)
            """
            TODO: 
               - исправить ошибки ревью
               - написать readme.md файл по использованию
            """
            # preview.show() # Чтобы глянуть при запуске, откроется просмотрщик по умолчанию
            img_buffer = io.BytesIO()
            preview.save(img_buffer, format="PNG")
            img_buffer.seek(0)

            logger.debug(
                f"Превьюшка для пользователя {user_info.user_id} успешно сгенерирована"
            )

            return img_buffer.getvalue()

        except Exception as e:
            logger.error(
                f"Ошибка генерации превью для пользователя {user_info.user_id}: {e}"
            )
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
        preview = Image.new('RGB', (ProfileImageGenerator.background_width * 3, ProfileImageGenerator.background_height))
        if len(users) == 3:
            user_images = [ProfileImageGenerator.generate_wanted_single(user) for user in users]
            widht = 0
            for image in user_images:
                image_for_paste = io.BytesIO(image)
                image_for_paste = Image.open(image_for_paste) # Преобразуем из байтов в Image
                preview.paste(image_for_paste, (widht, 0))
                widht += ProfileImageGenerator.background_width
        else:
            ProfileImageGenerator._generate_error_image 
        img_buffer = io.BytesIO()
        preview.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        
        users_id = [user.user_id for user in users]
        logger.debug(
            f"Превьюшка для пользователей {users_id} успешно сгенерирована"
        )

        return img_buffer.getvalue()

        

    @staticmethod
    def _generate_error_image(error_message: str) -> bytes:
        """
        Вызывается в случае, если сгенерировать нормальное изображение не получилось
        :param error_message:
        :return:
        """
        raise NotImplementedError()


# Тестовый код для запуска
if __name__ == "__main__":
    myImage1_path = f"{PATH_TO_IMAGES}/myImage.jpg" 
    myImage2_path = f"{PATH_TO_IMAGES}/myBigImage.jpg"
    myImage3_path = f"{PATH_TO_IMAGES}/gorizontalImage.jpg"
    with Image.open(myImage1_path) as myImage1:
        myImage1.load()
    with Image.open(myImage2_path) as myImage2:
        myImage2.load()
    with Image.open(myImage3_path) as myImage3:
        myImage3.load()
    
    user1 = ProfileInfo(
        user_id=1435771278, 
        name="Artem", 
        description='Хочу выучить питон', 
        profile_photo=myImage1)
    user2 = ProfileInfo(
        user_id=1435771278, 
        name="Artem", 
        description='Хочу выучить питон', 
        profile_photo=myImage2)
    user3 = ProfileInfo(
        user_id=1435771278, 
        name="Artem", 
        description='Хочу выучить питон', 
        profile_photo=myImage3)
    test = ProfileImageGenerator.generate_wanted_multiple([user1, user2, user3])
    # test = ProfileImageGenerator.generate_wanted_single(user1)
    image = io.BytesIO(test)
    image = Image.open(image)
    image.show()