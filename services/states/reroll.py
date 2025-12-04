from aiogram.fsm.state import State, StatesGroup


class Reroll(StatesGroup):
    confirm = State()
