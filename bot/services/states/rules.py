from aiogram.fsm.state import State, StatesGroup


class RulesStates(StatesGroup):
    rules = State()
    profile_rules = State()
    gameplay = State()
