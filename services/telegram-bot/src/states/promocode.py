"""FSM states for promocode activation."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class PromoCodeState(StatesGroup):
    entering_code = State()
