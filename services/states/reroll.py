from aiogram.fsm.state import StatesGroup, State


class Reroll(StatesGroup):
    confirm = State()
