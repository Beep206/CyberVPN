"""FSM states for account flow."""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AccountState(StatesGroup):
    changing_language = State()
