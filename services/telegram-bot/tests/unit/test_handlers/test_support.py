from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, Message, User

from src.handlers.support import support_command, support_menu


class _I18nStub:
    def __call__(self, key: str, **kwargs: object) -> str:
        if key == "support-message":
            return f"Support contact: {kwargs['contact']}"
        return key


@pytest.mark.asyncio
async def test_support_command_handles_paysupport() -> None:
    message = MagicMock(spec=Message)
    message.from_user = User(id=123456, is_bot=False, first_name="Test")
    message.answer = AsyncMock()
    settings = SimpleNamespace(support_username="CyberVPNSupport")

    await support_command(message, _I18nStub(), settings)

    message.answer.assert_awaited_once_with("Support contact: @CyberVPNSupport")


@pytest.mark.asyncio
async def test_support_menu_uses_same_contact_format() -> None:
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = User(id=123456, is_bot=False, first_name="Test")
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    settings = SimpleNamespace(support_username="@CyberVPNSupport")

    await support_menu(callback, _I18nStub(), settings)

    callback.answer.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once_with("Support contact: @CyberVPNSupport")
