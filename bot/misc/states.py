from aiogram.fsm.state import State, StatesGroup


class RegisterForm(StatesGroup):
    name = State()
    course_type = State()
    course_number_bachelor = State()
    course_number_master = State()
    course_other = State()
    group_name = State()
    about = State()
    photo = State()
    confirm = State()

class ConfirmProfileForm(StatesGroup):
    user_id = State()


class MainLoop(StatesGroup):
    title = State()
