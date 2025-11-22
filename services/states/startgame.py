from aiogram.fsm.state import StatesGroup, State


class StartGame(StatesGroup):
    name = State()
    confirm = State()
