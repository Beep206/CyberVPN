from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, User

from src.handlers.account import show_subscriptions_handler
from src.handlers.menu import connect_menu_handler


class _I18nStub:
    def __call__(self, key: str, **kwargs: object) -> str:
        return self.get(key, **kwargs)

    def get(self, key: str, **kwargs: object) -> str:
        if key == "subscription-active":
            return f"Plan: {kwargs.get('plan')} | Expires: {kwargs.get('expires')}"
        if key == "subscription-none":
            return "No subscription"
        if key == "subscriptions-title":
            return "Order History"
        if key == "subscriptions-none":
            return "No history"
        if key == "status":
            return "Status"
        if key == "error-generic":
            return "Error"
        return key


def _callback(user_id: int = 123456) -> CallbackQuery:
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = User(id=user_id, is_bot=False, first_name="Test")
    callback.message = MagicMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


@pytest.mark.asyncio
async def test_connect_menu_handler_uses_entitlements_and_service_state() -> None:
    callback = _callback()
    api_client = MagicMock()
    api_client.get_current_entitlements = AsyncMock(
        return_value={
            "status": "active",
            "display_name": "Pro Plan",
            "expires_at": "2026-05-01T12:00:00Z",
        }
    )
    api_client.get_current_service_state = AsyncMock(
        return_value={
            "provider_name": "remnawave",
            "access_delivery_channel": {"channel_type": "telegram_bot"},
            "purchase_context": {"source_type": "order"},
        }
    )

    await connect_menu_handler(callback, _I18nStub(), api_client)

    rendered_text = callback.message.edit_text.await_args.kwargs["text"]
    assert "Pro Plan" in rendered_text
    assert "remnawave" in rendered_text
    assert "telegram_bot" in rendered_text
    api_client.get_current_entitlements.assert_awaited_once_with(123456)
    api_client.get_current_service_state.assert_awaited_once_with(123456)


@pytest.mark.asyncio
async def test_show_subscriptions_handler_uses_canonical_order_history() -> None:
    callback = _callback()
    api_client = MagicMock()
    api_client.get_user_orders = AsyncMock(
        return_value=[
            {
                "id": "order-1",
                "settlement_status": "paid",
                "created_at": "2026-04-18T10:00:00Z",
                "items": [{"display_name": "Pro Plan"}],
            }
        ]
    )

    await show_subscriptions_handler(callback, _I18nStub(), api_client)

    rendered_text = callback.message.edit_text.await_args.kwargs["text"]
    assert "Order History" in rendered_text
    assert "Pro Plan" in rendered_text
    assert "paid" in rendered_text
    api_client.get_user_orders.assert_awaited_once_with(123456, limit=10, offset=0)
