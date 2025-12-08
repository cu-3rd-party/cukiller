from aiogram.fsm.state import State, StatesGroup


class EndGame(StatesGroup):
    confirm = State()
