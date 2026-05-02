from aiogram.fsm.state import State, StatesGroup


class QuizStates(StatesGroup):
    in_progress = State()
