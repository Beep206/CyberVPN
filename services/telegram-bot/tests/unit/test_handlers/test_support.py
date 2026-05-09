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
        if key.startswith("support-first-line-") and key != "support-first-line-without-escalation":
            return f"{key} reference={kwargs['reference']} contact={kwargs['contact']}"
        if key == "support-first-line-without-escalation":
            return f"{kwargs['first_line']} no escalation"
        if key == "support-escalation-created":
            return f"Escalated reference={kwargs['reference']} contact={kwargs['contact']}"
        if key == "support-escalation-fallback":
            return f"Fallback reference={kwargs['reference']} contact={kwargs['contact']}"
        return key


@pytest.mark.asyncio
async def test_support_command_handles_paysupport() -> None:
    message = MagicMock(spec=Message)
    message.from_user = User(id=123456, is_bot=False, first_name="Test")
    message.text = "/paysupport"
    message.answer = AsyncMock()
    settings = SimpleNamespace(support_username="CyberVPNSupport")

    await support_command(message, _I18nStub(), settings)

    message.answer.assert_awaited_once_with("Support contact: @CyberVPNSupport")


@pytest.mark.asyncio
async def test_support_command_creates_escalation_for_paid_no_access() -> None:
    message = MagicMock(spec=Message)
    message.text = "/support I paid but got no access vless://secret-config"
    message.from_user = User(id=123456, is_bot=False, first_name="Test", username="tester")
    message.answer = AsyncMock()
    settings = SimpleNamespace(support_username="CyberVPNSupport")
    api_client = SimpleNamespace(create_support_escalation=AsyncMock(return_value={"status": "accepted"}))

    await support_command(message, _I18nStub(), settings, api_client=api_client)

    api_client.create_support_escalation.assert_awaited_once()
    telegram_id, payload = api_client.create_support_escalation.await_args.args
    assert telegram_id == 123456
    assert payload["category"] == "provisioning"
    assert payload["priority"] == "p1"
    assert "vless://" not in str(payload)
    assert "[vpn-config-url]" in payload["safe_summary"]
    assert "Escalated reference=tg-provisioning-p1-" in message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_support_command_returns_fallback_when_escalation_api_fails() -> None:
    message = MagicMock(spec=Message)
    message.text = "/support refund needed"
    message.from_user = User(id=123456, is_bot=False, first_name="Test", username="tester")
    message.answer = AsyncMock()
    settings = SimpleNamespace(support_username="@CyberVPNSupport")
    api_client = SimpleNamespace(create_support_escalation=AsyncMock(side_effect=RuntimeError("backend down")))

    await support_command(message, _I18nStub(), settings, api_client=api_client)

    api_client.create_support_escalation.assert_awaited_once()
    assert "Fallback reference=tg-payment-p1-" in message.answer.await_args.args[0]


@pytest.mark.asyncio
async def test_support_command_does_not_escalate_general_first_line_question() -> None:
    message = MagicMock(spec=Message)
    message.text = "/support What plans are available in beta?"
    message.from_user = User(id=123456, is_bot=False, first_name="Test", username="tester")
    message.answer = AsyncMock()
    settings = SimpleNamespace(support_username="CyberVPNSupport")
    api_client = SimpleNamespace(create_support_escalation=AsyncMock(return_value={"status": "accepted"}))

    await support_command(message, _I18nStub(), settings, api_client=api_client)

    api_client.create_support_escalation.assert_not_awaited()
    assert "support-first-line-general" in message.answer.await_args.args[0]


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
