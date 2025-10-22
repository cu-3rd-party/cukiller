from aiogram.fsm.state import StatesGroup, State


class ParticipationForm(StatesGroup):
    confirm = State()
