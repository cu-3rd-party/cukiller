from aiogram.fsm.state import StatesGroup, State


class EndGame(StatesGroup):
    confirm = State()
