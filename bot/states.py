from aiogram.fsm.state import State, StatesGroup


class ChatStates(StatesGroup):
    waiting_phone = State()
    waiting_address = State()
    waiting_reply = State()
    waiting_custom_label = State()