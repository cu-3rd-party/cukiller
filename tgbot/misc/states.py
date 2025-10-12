from aiogram.fsm.state import StatesGroup, State


class UsersStates(StatesGroup):
    """
    Класс реализует состояние пользователя внутри сценария.
    Атрибуты заполняются во время опроса пользователя.

    :param last_command команда, которую ввёл пользователь.

    :param screen может быть:
    - Title
    - Registration
    - Edit
    - Overview
    - Play
    - TargetInfo
    - TargetPick
    - TargetQueue
    - SubmitDeath
    - SubmitKill

    """

    screen = State()
    profile = State()
