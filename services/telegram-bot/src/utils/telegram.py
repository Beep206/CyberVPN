"""Typed helpers for aiogram update objects."""

from __future__ import annotations

from aiogram.types import CallbackQuery, InaccessibleMessage, Message


def callback_message(callback: CallbackQuery) -> Message:
    """Return the accessible message behind a callback query."""

    message = callback.message
    if message is not None and not isinstance(message, InaccessibleMessage):
        return message
    msg = "Callback query does not include an accessible message"
    raise RuntimeError(msg)


def callback_data(callback: CallbackQuery) -> str:
    """Return callback data when a route filter has already matched it."""

    data = callback.data
    if data is not None:
        return data
    msg = "Callback query does not include callback data"
    raise RuntimeError(msg)


def message_text(message: Message) -> str:
    """Return message text when an aiogram text filter has already matched it."""

    text = message.text
    if text is not None:
        return text
    msg = "Message does not include text"
    raise RuntimeError(msg)


def message_user_id(message: Message) -> int:
    """Return the Telegram sender id when a user-originated message matched."""

    user = message.from_user
    if user is not None:
        return user.id
    msg = "Message does not include a sender"
    raise RuntimeError(msg)
