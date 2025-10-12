from aiogram.fsm.state import State, StatesGroup


class UsersStates(StatesGroup):
    """
    Класс реализует состояние пользователя внутри сценария.
    Атрибуты заполняются во время опроса пользователя.

    Attributes:
        last_command (str): команда, которую ввёл пользователь.
    """

    last_command = State()
