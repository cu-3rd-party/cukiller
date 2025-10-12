from aiogram.fsm.state import StatesGroup, State


class RegisterForm(StatesGroup):
    name = State()
    description = State()
    photo = State()
    departament = State()
    confirm = State()

class ConfirmProfileForm(StatesGroup):
    user_id = State()

class MainLoop(StatesGroup):
    title = State()
