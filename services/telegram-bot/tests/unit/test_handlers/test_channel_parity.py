from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, User

from src.handlers.account import show_subscriptions_handler
from src.handlers.menu import connect_menu_handler
from src.models.connection import ConnectionBootstrapResponse
from src.services.cache_service import CacheService


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
    callback.message.chat = type("Chat", (), {"id": user_id, "type": "private"})()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


def _available_bootstrap(url: str = "vless://private-secret-config") -> ConnectionBootstrapResponse:
    return ConnectionBootstrapResponse(
        status="available",
        available=True,
        subscription_url=url,
        qr_payload=url,
        config_profile_name="Primary profile",
        flow_key="flow-channel",
        version=7,
        connection_session_id="11111111-2222-4333-8444-555555555555",
        telegram_payload={"bot_connection_session_id": "11111111-2222-4333-8444-555555555555"},
    )


@pytest.mark.asyncio
async def test_connect_menu_handler_uses_connection_bootstrap(fake_redis: object) -> None:
    callback = _callback()
    cache = CacheService(fake_redis, key_prefix="channel:")
    api_client = MagicMock()
    api_client.get_customer_connection_bootstrap = AsyncMock(return_value=_available_bootstrap())

    await connect_menu_handler(callback, _I18nStub(), api_client, cache)

    rendered_text = callback.message.edit_text.await_args.kwargs["text"]
    assert rendered_text.startswith("bot-onboarding-connection-ready")
    api_client.get_customer_connection_bootstrap.assert_awaited_once_with(123456, platform_hint="unknown")


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
