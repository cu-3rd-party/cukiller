from aiogram.fsm.state import State, StatesGroup


class EditGame(StatesGroup):
    game_id = State()
    edit = State()
    info = State()
