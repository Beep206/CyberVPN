from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, Message, User

from src.handlers.connection import (
    connection_mark_connected_callback_handler,
    connection_open_link_callback_handler,
    open_connection_from_message,
)
from src.models.connection import ConnectionBootstrapResponse, MarkConnectedResponse
from src.services.cache_service import CacheService


class _I18nStub:
    def __call__(self, key: str, **kwargs: object) -> str:
        return self.get(key, **kwargs)

    def get(self, key: str, **kwargs: object) -> str:
        if kwargs:
            suffix = " ".join(f"{name}={value}" for name, value in sorted(kwargs.items()))
            return f"{key} {suffix}"
        return key


def _message() -> Message:
    message = MagicMock(spec=Message)
    message.from_user = User(id=123456, is_bot=False, first_name="Test")
    message.chat = SimpleNamespace(id=123456, type="private")
    message.answer = AsyncMock()
    return message


def _callback(data: str) -> CallbackQuery:
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = User(id=123456, is_bot=False, first_name="Test")
    callback.data = data
    callback.message = MagicMock()
    callback.message.chat = SimpleNamespace(id=123456, type="private")
    callback.message.answer = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


def _callback_data(reply_markup: object) -> set[str]:
    keyboard = getattr(reply_markup, "inline_keyboard", [])
    return {button.callback_data for row in keyboard for button in row if getattr(button, "callback_data", None)}


@pytest.mark.asyncio
async def test_connection_session_survives_link_callback_and_mark_connected(fake_redis: object) -> None:
    cache = CacheService(fake_redis, key_prefix="integration:")
    bootstrap = ConnectionBootstrapResponse(
        status="available",
        available=True,
        subscription_url="vless://integration-private-config",
        qr_payload="vless://integration-private-config",
        config_profile_name="Integration profile",
        flow_key="flow-integration",
        version=3,
        connection_session_id="22222222-3333-4444-8555-666666666666",
        telegram_payload={"bot_connection_session_id": "22222222-3333-4444-8555-666666666666"},
    )
    api_client = SimpleNamespace(
        get_customer_connection_bootstrap=AsyncMock(return_value=bootstrap),
        mark_customer_connection_connected=AsyncMock(return_value=MarkConnectedResponse(status="accepted")),
    )
    message = _message()

    await open_connection_from_message(message, _I18nStub(), api_client, cache)

    callbacks = _callback_data(message.answer.await_args.kwargs["reply_markup"])
    open_link_callback = next(value for value in callbacks if value.startswith("connection:open_link:"))
    mark_callback = open_link_callback.replace("connection:open_link:", "connection:mark_connected:ios:")

    link_callback = _callback(open_link_callback)
    await connection_open_link_callback_handler(link_callback, _I18nStub(), api_client, cache)

    assert "vless://integration-private-config" in link_callback.message.answer.await_args.kwargs["text"]

    mark_connected_callback = _callback(mark_callback)
    await connection_mark_connected_callback_handler(mark_connected_callback, _I18nStub(), api_client, cache)

    api_client.mark_customer_connection_connected.assert_awaited_once_with(
        123456,
        platform="ios",
        source_surface="telegram_bot",
        flow_key="flow-integration",
        version=3,
        connection_session_id="22222222-3333-4444-8555-666666666666",
    )
    mark_connected_callback.message.edit_text.assert_awaited_once()
