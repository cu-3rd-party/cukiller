from aiogram.fsm.state import State, StatesGroup


class ParticipationForm(StatesGroup):
    confirm = State()
