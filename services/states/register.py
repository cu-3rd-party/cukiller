from aiogram.fsm.state import State, StatesGroup


class RegisterForm(StatesGroup):
    name = State()
    course_type = State()
    course_number = State()
    course_number_bachelor = State()
    course_number_master = State()
    course_other = State()
    group_name = State()
    about = State()
    allow_hugging_on_kill = State()
    photo = State()
    confirm = State()
