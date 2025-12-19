from aiogram.fsm.state import State, StatesGroup


class MyProfile(StatesGroup):
    profile = State()


class EditProfile(StatesGroup):
    main = State()
    family_name = State()
    given_name = State()
    type = State()
    course = State()
    group = State()
    about = State()
    photo = State()
    confirm = State()
