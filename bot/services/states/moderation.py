from aiogram.fsm.state import State, StatesGroup


class ProfileModeration(StatesGroup):
    waiting_reason = State()
