from aiogram.fsm.state import State, StatesGroup


class RegisterForm(StatesGroup):
    name = State()
    description = State()
    photo = State()
    course_number = State()
    group_name = State()
    confirm = State()


class ConfirmProfileForm(StatesGroup):
    user_id = State()


class MainLoop(StatesGroup):
    title = State()
