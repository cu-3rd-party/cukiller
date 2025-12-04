from aiogram.fsm.state import State, StatesGroup


class StartGame(StatesGroup):
    name = State()
    confirm = State()
