from aiogram.fsm.state import StatesGroup, State


class ConfirmProfileForm(StatesGroup):
    user_id = State()
