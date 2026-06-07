from aiogram.fsm.state import State, StatesGroup


class DialogueStates(StatesGroup):
    awaiting_gap_answer = State()
