from aiogram.fsm.state import StatesGroup, State


class RegisterForm(StatesGroup):
    name = State()
    course_type = State()
    course_number = State()
    course_number_bachelor = State()
    course_number_master = State()
    course_other = State()
    group_name = State()
    about = State()
    photo = State()
    confirm = State()
