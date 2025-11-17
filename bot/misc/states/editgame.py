from aiogram.fsm.state import StatesGroup, State


class EditGame(StatesGroup):
    game_id = State()
    edit = State()
    info = State()
