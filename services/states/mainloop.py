from aiogram.fsm.state import State, StatesGroup


class MainLoop(StatesGroup):
    title = State()
    target_info = State()
