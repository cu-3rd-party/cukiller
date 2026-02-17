from aiogram.fsm.state import State, StatesGroup


class ConfirmProfileForm(StatesGroup):
    user_id = State()
