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

    start = State()
    title = State()
    register = State()
    edit = State()
    overview = State()
    play = State()
    target_info = State()
    target_queue = State()
    submit_death = State()
    submit_kill = State()
    profile = State()
