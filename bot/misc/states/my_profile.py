from aiogram.fsm.state import StatesGroup, State


class MyProfile(StatesGroup):
    profile = State()


class EditProfile(StatesGroup):
    main = State()
    name = State()
    type = State()
    course = State()
    group = State()
    description = State()
    photo = State()
    confirm = State()
