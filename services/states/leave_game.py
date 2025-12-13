from aiogram.fsm.state import State, StatesGroup


class LeaveGame(StatesGroup):
    confirm = State()
