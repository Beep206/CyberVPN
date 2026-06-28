from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import CallbackQuery, User

from src.handlers.config import (
    config_menu_handler,
    send_config_link_handler,
    send_config_qr_handler,
    send_selected_config_handler,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class _I18nStub:
    def __call__(self, key: str, **kwargs: object) -> str:
        return self.get(key, **kwargs)

    def get(self, key: str, **kwargs: object) -> str:
        if kwargs:
            suffix = " ".join(f"{name}={value}" for name, value in sorted(kwargs.items()))
            return f"{key} {suffix}"
        return key


def _group_callback(data: str) -> CallbackQuery:
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = User(id=123456, is_bot=False, first_name="Test")
    callback.data = data
    callback.message = MagicMock()
    callback.message.chat = SimpleNamespace(id=-100123, type="group")
    callback.message.answer = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.message.answer_photo = AsyncMock()
    callback.answer = AsyncMock()
    return callback


def _api_client() -> SimpleNamespace:
    return SimpleNamespace(
        get_user_config=AsyncMock(return_value={"subscription_url": "https://vpn.example/subscription/private-token"}),
        get_user_subscriptions=AsyncMock(return_value=[{"status": "active", "subscription_key": "sub-private"}]),
    )


def _assert_private_chat_gate(callback: CallbackQuery, api_client: SimpleNamespace | None = None) -> None:
    callback.answer.assert_awaited_once_with(
        "bot-onboarding-connection-private-chat-required",
        show_alert=True,
    )
    callback.message.answer.assert_awaited_once()
    assert callback.message.answer.await_args.kwargs["text"] == "bot-onboarding-connection-private-chat-required"
    callback.message.edit_text.assert_not_awaited()
    callback.message.answer_photo.assert_not_awaited()
    assert "vpn.example" not in str(callback.message.answer.await_args)
    if api_client is not None:
        api_client.get_user_config.assert_not_awaited()
        api_client.get_user_subscriptions.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("data", ["config:menu"])
async def test_config_menu_requires_private_chat_before_showing_delivery_options(data: str) -> None:
    callback = _group_callback(data)

    await config_menu_handler(callback, _I18nStub())

    _assert_private_chat_gate(callback)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("data", "handler"),
    [
        ("config:link", send_config_link_handler),
        ("config:qr", send_config_qr_handler),
        ("config:pick:link:0", send_selected_config_handler),
        ("config:pick:qr:0", send_selected_config_handler),
    ],
)
async def test_config_delivery_requires_private_chat_before_fetching_config(
    data: str,
    handler: Callable[..., Awaitable[None]],
) -> None:
    callback = _group_callback(data)
    api_client = _api_client()

    await handler(callback, _I18nStub(), api_client)

    _assert_private_chat_gate(callback, api_client)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("data", "handler"),
    [
        ("config:link", send_config_link_handler),
        ("config:qr", send_config_qr_handler),
    ],
)
async def test_config_delivery_fails_closed_when_callback_message_is_missing(
    data: str,
    handler: Callable[..., Awaitable[None]],
) -> None:
    callback = _group_callback(data)
    callback.message = None
    api_client = _api_client()

    await handler(callback, _I18nStub(), api_client)

    callback.answer.assert_awaited_once_with(
        "bot-onboarding-connection-private-chat-required",
        show_alert=True,
    )
    api_client.get_user_config.assert_not_awaited()
    api_client.get_user_subscriptions.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("data", "handler"),
    [
        ("config:link", send_config_link_handler),
        ("config:qr", send_config_qr_handler),
    ],
)
async def test_config_delivery_fails_closed_when_chat_type_is_missing(
    data: str,
    handler: Callable[..., Awaitable[None]],
) -> None:
    callback = _group_callback(data)
    callback.message.chat = SimpleNamespace(id=123456)
    api_client = _api_client()

    await handler(callback, _I18nStub(), api_client)

    _assert_private_chat_gate(callback, api_client)
