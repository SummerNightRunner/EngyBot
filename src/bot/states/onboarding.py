from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    choose_source_language = State()
    choose_target_language = State()
    choose_level = State()
