from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.filters import CommandObject
from aiogram.types import CallbackQuery, Message, User
from pydantic import SecretStr

import src.handlers.connection as connection_handlers
from src.config import BackendSettings
from src.handlers.connection import (
    code_command_handler,
    connection_mark_connected_callback_handler,
    connection_show_qr_callback_handler,
    open_connection_from_callback,
    open_connection_from_message,
)
from src.models.connection import ConnectionBootstrapResponse, MarkConnectedResponse
from src.services.api_client import APIError, CyberVPNAPIClient
from src.services.cache_service import CacheService
from src.services.connection_session import ConnectionSessionStore


class _I18nStub:
    def __call__(self, key: str, **kwargs: object) -> str:
        return self.get(key, **kwargs)

    def get(self, key: str, **kwargs: object) -> str:
        if kwargs:
            suffix = " ".join(f"{name}={value}" for name, value in sorted(kwargs.items()))
            return f"{key} {suffix}"
        return key


def _message(*, chat_type: str = "private", text: str = "/connect") -> Message:
    message = MagicMock(spec=Message)
    message.from_user = User(id=123456, is_bot=False, first_name="Test")
    message.chat = SimpleNamespace(id=123456 if chat_type == "private" else -100, type=chat_type)
    message.message_id = 777
    message.text = text
    message.answer = AsyncMock()
    return message


def _callback(data: str, *, user_id: int = 123456, chat_type: str = "private") -> CallbackQuery:
    callback = MagicMock(spec=CallbackQuery)
    callback.from_user = User(id=user_id, is_bot=False, first_name="Test")
    callback.data = data
    callback.message = MagicMock()
    callback.message.chat = SimpleNamespace(id=user_id if chat_type == "private" else -100, type=chat_type)
    callback.message.answer = AsyncMock()
    callback.message.edit_text = AsyncMock()
    callback.message.answer_photo = AsyncMock()
    callback.answer = AsyncMock()
    return callback


def _available_bootstrap(url: str = "vless://private-secret-config") -> ConnectionBootstrapResponse:
    return ConnectionBootstrapResponse(
        status="available",
        available=True,
        subscription_url=url,
        qr_payload=url,
        config_profile_name="Primary profile",
        flow_key="flow-123",
        version=7,
        connection_session_id="11111111-2222-4333-8444-555555555555",
        telegram_payload={"bot_connection_session_id": "11111111-2222-4333-8444-555555555555"},
    )


async def _cache(fake_redis: object) -> CacheService:
    return CacheService(fake_redis, key_prefix="test:")


def _callback_data(reply_markup: object) -> list[str]:
    keyboard = getattr(reply_markup, "inline_keyboard", [])
    return [button.callback_data for row in keyboard for button in row if getattr(button, "callback_data", None)]


def _answer_text(call: object) -> str:
    args = getattr(call, "args", ())
    kwargs = getattr(call, "kwargs", {})
    return str(kwargs.get("text") if "text" in kwargs else args[0])


def _assert_safe_telegram_log_context(warning: MagicMock) -> None:
    kwargs = warning.call_args.kwargs
    assert "user_id" not in kwargs
    assert kwargs["telegram_user_fingerprint"] == connection_handlers.telegram_user_fingerprint(123456)
    assert "123456" not in str(kwargs)


@pytest.mark.asyncio
async def test_connect_private_chat_creates_short_session_without_raw_config(fake_redis: object) -> None:
    cache = await _cache(fake_redis)
    api_client = SimpleNamespace(get_customer_connection_bootstrap=AsyncMock(return_value=_available_bootstrap()))
    message = _message()

    await open_connection_from_message(message, _I18nStub(), api_client, cache)

    api_client.get_customer_connection_bootstrap.assert_awaited_once_with(123456, platform_hint="unknown")
    message.answer.assert_awaited_once()
    reply_markup = message.answer.await_args.kwargs["reply_markup"]
    callback_data = _callback_data(reply_markup)
    assert callback_data
    assert all(len(value) <= 64 for value in callback_data)
    assert all("vless://private-secret-config" not in value for value in callback_data)

    raw_values = [str(value) for value in await fake_redis.mget(await fake_redis.keys("test:*"))]
    persisted = "\n".join(raw_values)
    assert "vless://private-secret-config" not in persisted
    assert "flow-123" in persisted


@pytest.mark.asyncio
async def test_connect_bootstrap_failure_logs_safe_telegram_reference(
    fake_redis: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = await _cache(fake_redis)
    api_client = SimpleNamespace(get_customer_connection_bootstrap=AsyncMock(side_effect=RuntimeError("backend down")))
    message = _message()
    warning = MagicMock()
    monkeypatch.setattr(connection_handlers, "logger", SimpleNamespace(warning=warning))

    await open_connection_from_message(message, _I18nStub(), api_client, cache)

    warning.assert_called_once()
    _assert_safe_telegram_log_context(warning)
    message.answer.assert_awaited_once_with("error-generic")


@pytest.mark.asyncio
async def test_callback_bootstrap_failure_logs_safe_telegram_reference(
    fake_redis: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = await _cache(fake_redis)
    api_client = SimpleNamespace(get_customer_connection_bootstrap=AsyncMock(side_effect=RuntimeError("backend down")))
    callback = _callback("connection:open")
    warning = MagicMock()
    monkeypatch.setattr(connection_handlers, "logger", SimpleNamespace(warning=warning))

    await open_connection_from_callback(callback, _I18nStub(), api_client, cache)

    warning.assert_called_once()
    _assert_safe_telegram_log_context(warning)
    callback.answer.assert_awaited_once_with("error-generic", show_alert=True)


@pytest.mark.asyncio
async def test_connect_group_chat_requires_private_chat_and_does_not_bootstrap(fake_redis: object) -> None:
    cache = await _cache(fake_redis)
    api_client = SimpleNamespace(get_customer_connection_bootstrap=AsyncMock(return_value=_available_bootstrap()))
    message = _message(chat_type="group")

    await open_connection_from_message(message, _I18nStub(), api_client, cache)

    api_client.get_customer_connection_bootstrap.assert_not_awaited()
    message.answer.assert_awaited_once()
    assert message.answer.await_args.kwargs["text"] == "bot-onboarding-connection-private-chat-required"
    assert "vless://" not in str(message.answer.await_args.kwargs)


@pytest.mark.asyncio
async def test_callback_without_message_requires_private_chat_and_does_not_bootstrap(fake_redis: object) -> None:
    cache = await _cache(fake_redis)
    api_client = SimpleNamespace(get_customer_connection_bootstrap=AsyncMock(return_value=_available_bootstrap()))
    callback = _callback("connection:open")
    callback.message = None

    await open_connection_from_callback(callback, _I18nStub(), api_client, cache)

    api_client.get_customer_connection_bootstrap.assert_not_awaited()
    callback.answer.assert_awaited_once_with("bot-onboarding-connection-private-chat-required", show_alert=True)


@pytest.mark.asyncio
async def test_callback_missing_chat_type_requires_private_chat_and_does_not_bootstrap(fake_redis: object) -> None:
    cache = await _cache(fake_redis)
    api_client = SimpleNamespace(get_customer_connection_bootstrap=AsyncMock(return_value=_available_bootstrap()))
    callback = _callback("connection:open")
    callback.message.chat = SimpleNamespace(id=123456)

    await open_connection_from_callback(callback, _I18nStub(), api_client, cache)

    api_client.get_customer_connection_bootstrap.assert_not_awaited()
    callback.answer.assert_awaited_once_with("bot-onboarding-connection-private-chat-required", show_alert=True)
    callback.message.answer.assert_awaited_once()
    assert callback.message.answer.await_args.kwargs["text"] == "bot-onboarding-connection-private-chat-required"


@pytest.mark.asyncio
async def test_show_qr_sends_photo_for_owned_private_session(
    fake_redis: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = await _cache(fake_redis)
    await ConnectionSessionStore(cache, id_factory=lambda: "sessABC123").create(
        telegram_id=123456,
        platform_hint="ios",
        flow_key="flow-123",
        version=7,
        backend_connection_session_id="11111111-2222-4333-8444-555555555555",
    )
    api_client = SimpleNamespace(get_customer_connection_bootstrap=AsyncMock(return_value=_available_bootstrap()))
    callback = _callback("connection:show_qr:sessABC123")
    seen_payloads: list[str] = []

    def _fake_qr(payload: str) -> BytesIO:
        seen_payloads.append(payload)
        return BytesIO(b"fake-png")

    monkeypatch.setattr("src.handlers.connection.generate_subscription_qr", _fake_qr)

    await connection_show_qr_callback_handler(callback, _I18nStub(), api_client, cache)

    assert seen_payloads == ["vless://private-secret-config"]
    callback.message.answer_photo.assert_awaited_once()
    callback.message.answer.assert_not_awaited()
    callback.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_show_qr_falls_back_to_private_link_when_qr_generation_fails(
    fake_redis: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = await _cache(fake_redis)
    await ConnectionSessionStore(cache, id_factory=lambda: "sessABC123").create(
        telegram_id=123456,
        platform_hint="android",
    )
    api_client = SimpleNamespace(get_customer_connection_bootstrap=AsyncMock(return_value=_available_bootstrap()))
    callback = _callback("connection:show_qr:sessABC123")

    def _raise_qr(payload: str) -> BytesIO:
        raise ValueError("qr unavailable")

    warning = MagicMock()
    monkeypatch.setattr(connection_handlers, "logger", SimpleNamespace(warning=warning))
    monkeypatch.setattr("src.handlers.connection.generate_subscription_qr", _raise_qr)

    await connection_show_qr_callback_handler(callback, _I18nStub(), api_client, cache)

    callback.message.answer_photo.assert_not_awaited()
    callback.message.answer.assert_awaited_once()
    assert "vless://private-secret-config" in callback.message.answer.await_args.kwargs["text"]
    warning.assert_called_once()
    _assert_safe_telegram_log_context(warning)


@pytest.mark.asyncio
async def test_callback_session_owner_mismatch_does_not_fetch_or_send_config(fake_redis: object) -> None:
    cache = await _cache(fake_redis)
    await ConnectionSessionStore(cache, id_factory=lambda: "sessABC123").create(telegram_id=999999)
    api_client = SimpleNamespace(get_customer_connection_bootstrap=AsyncMock(return_value=_available_bootstrap()))
    callback = _callback("connection:show_qr:sessABC123", user_id=123456)

    await connection_show_qr_callback_handler(callback, _I18nStub(), api_client, cache)

    api_client.get_customer_connection_bootstrap.assert_not_awaited()
    callback.message.answer_photo.assert_not_awaited()
    callback.message.answer.assert_not_awaited()
    callback.answer.assert_awaited_once_with("bot-onboarding-connection-session-expired", show_alert=True)


@pytest.mark.asyncio
async def test_mark_connected_calls_shared_backend_with_flow_metadata(fake_redis: object) -> None:
    cache = await _cache(fake_redis)
    await ConnectionSessionStore(cache, id_factory=lambda: "sessABC123").create(
        telegram_id=123456,
        platform_hint="ios",
        flow_key="flow-123",
        version=7,
        backend_connection_session_id="11111111-2222-4333-8444-555555555555",
    )
    api_client = SimpleNamespace(
        mark_customer_connection_connected=AsyncMock(return_value=MarkConnectedResponse(status="accepted"))
    )
    callback = _callback("connection:mark_connected:ios:sessABC123")

    await connection_mark_connected_callback_handler(callback, _I18nStub(), api_client, cache)

    api_client.mark_customer_connection_connected.assert_awaited_once_with(
        123456,
        platform="ios",
        source_surface="telegram_bot",
        flow_key="flow-123",
        version=7,
        connection_session_id="11111111-2222-4333-8444-555555555555",
    )
    callback.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_mark_connected_without_backend_session_id_fails_closed(fake_redis: object) -> None:
    cache = await _cache(fake_redis)
    await ConnectionSessionStore(cache, id_factory=lambda: "sessABC123").create(
        telegram_id=123456,
        platform_hint="ios",
        flow_key="flow-123",
        version=7,
    )
    api_client = SimpleNamespace(
        mark_customer_connection_connected=AsyncMock(return_value=MarkConnectedResponse(status="accepted"))
    )
    callback = _callback("connection:mark_connected:ios:sessABC123")

    await connection_mark_connected_callback_handler(callback, _I18nStub(), api_client, cache)

    api_client.mark_customer_connection_connected.assert_not_awaited()
    callback.answer.assert_awaited_once_with("bot-onboarding-connection-session-expired", show_alert=True)
    callback.message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_mark_connected_failure_logs_safe_telegram_reference(
    fake_redis: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = await _cache(fake_redis)
    await ConnectionSessionStore(cache, id_factory=lambda: "sessABC123").create(
        telegram_id=123456,
        platform_hint="ios",
        flow_key="flow-123",
        version=7,
        backend_connection_session_id="11111111-2222-4333-8444-555555555555",
    )
    api_client = SimpleNamespace(mark_customer_connection_connected=AsyncMock(side_effect=RuntimeError("backend down")))
    callback = _callback("connection:mark_connected:ios:sessABC123")
    warning = MagicMock()
    monkeypatch.setattr(connection_handlers, "logger", SimpleNamespace(warning=warning))

    await connection_mark_connected_callback_handler(callback, _I18nStub(), api_client, cache)

    warning.assert_called_once()
    _assert_safe_telegram_log_context(warning)
    callback.answer.assert_awaited_once_with("error-generic", show_alert=True)
    callback.message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_code_command_masks_user_visible_code_and_opens_connection(fake_redis: object) -> None:
    cache = await _cache(fake_redis)
    api_client = SimpleNamespace(
        apply_telegram_onboarding_code=AsyncMock(return_value={"status": "accepted"}),
        get_customer_connection_bootstrap=AsyncMock(return_value=_available_bootstrap()),
    )
    message = _message(text="/code GiftSecret42")

    await code_command_handler(
        message,
        CommandObject(prefix="/", command="code", mention=None, args="GiftSecret42"),
        _I18nStub(),
        api_client,
        cache,
    )

    api_client.apply_telegram_onboarding_code.assert_awaited_once()
    assert api_client.apply_telegram_onboarding_code.await_args.args == (123456, "GiftSecret42")
    first_answer = _answer_text(message.answer.await_args_list[0])
    assert "GiftSecret42" not in first_answer
    assert "Gi***42" in first_answer
    assert message.answer.await_count == 2


@pytest.mark.asyncio
async def test_code_apply_failure_logs_safe_telegram_reference(
    fake_redis: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = await _cache(fake_redis)
    api_client = SimpleNamespace(apply_telegram_onboarding_code=AsyncMock(side_effect=RuntimeError("backend down")))
    message = _message(text="/code GiftSecret42")
    warning = MagicMock()
    monkeypatch.setattr(connection_handlers, "logger", SimpleNamespace(warning=warning))

    await code_command_handler(
        message,
        CommandObject(prefix="/", command="code", mention=None, args="GiftSecret42"),
        _I18nStub(),
        api_client,
        cache,
    )

    warning.assert_called_once()
    _assert_safe_telegram_log_context(warning)
    assert warning.call_args.kwargs["code_fingerprint"] == connection_handlers.code_fingerprint("GiftSecret42")
    assert "GiftSecret42" not in str(warning.call_args.kwargs)
    message.answer.assert_awaited_once_with("code-not-found")


@pytest.mark.asyncio
async def test_code_command_uses_real_backend_apply_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = AsyncMock(return_value={"status": "completed"})
    idempotency_key = connection_handlers.onboarding_code_idempotency_key(
        telegram_id=123456,
        code="GiftSecret42",
        message_id=777,
    )
    client = CyberVPNAPIClient(
        BackendSettings(
            api_url="https://backend.example",
            api_key=SecretStr("backend-api-key"),
        )
    )
    monkeypatch.setattr(client, "_request_auth_backend_dict", request)
    try:
        await client.apply_telegram_onboarding_code(
            123456,
            "GiftSecret42",
            idempotency_key=idempotency_key,
        )
    finally:
        await client.close()

    request.assert_awaited_once()
    assert request.await_args.args == ("POST", "/customer/onboarding/growth-code/apply")
    payload = request.await_args.kwargs["json"]
    assert payload == {
        "telegram_id": 123456,
        "code": "GiftSecret42",
        "source_surface": "telegram_bot",
        "idempotency_key": idempotency_key,
    }
    assert "flow_token" not in payload


@pytest.mark.asyncio
async def test_code_apply_403_is_not_reported_as_not_found(fake_redis: object) -> None:
    cache = await _cache(fake_redis)
    api_client = SimpleNamespace(
        apply_telegram_onboarding_code=AsyncMock(
            side_effect=APIError(
                message="Forbidden",
                status_code=403,
                detail="CUSTOMER_ONBOARDING_FLOW_TOKEN_REQUIRED",
            )
        )
    )
    message = _message(text="/code GiftSecret42")

    await code_command_handler(
        message,
        CommandObject(prefix="/", command="code", mention=None, args="GiftSecret42"),
        _I18nStub(),
        api_client,
        cache,
    )

    message.answer.assert_awaited_once_with("bot-onboarding-code-apply-unavailable")


@pytest.mark.asyncio
async def test_promocode_text_entry_uses_onboarding_connection_flow_without_legacy_discount(
    fake_redis: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.handlers import promocode as promocode_handlers

    cache = await _cache(fake_redis)
    api_client = SimpleNamespace(
        apply_telegram_onboarding_code=AsyncMock(return_value={"status": "completed"}),
        get_customer_connection_bootstrap=AsyncMock(return_value=_available_bootstrap()),
    )
    message = _message(text="GiftSecret42")
    state = SimpleNamespace(clear=AsyncMock())
    warning = MagicMock()
    info = MagicMock()
    monkeypatch.setattr(connection_handlers, "logger", SimpleNamespace(warning=warning))
    monkeypatch.setattr(promocode_handlers, "logger", SimpleNamespace(info=info))

    await promocode_handlers.promocode_entered_handler(
        message,
        _I18nStub(),
        api_client,
        state,
        cache,
    )

    api_client.apply_telegram_onboarding_code.assert_awaited_once()
    assert api_client.apply_telegram_onboarding_code.await_args.args == (123456, "GiftSecret42")
    api_client.get_customer_connection_bootstrap.assert_awaited_once_with(123456, platform_hint="unknown")
    assert message.answer.await_count == 2
    rendered = "\n".join(_answer_text(call) for call in message.answer.await_args_list)
    assert "code-activated" not in rendered
    assert "discount" not in rendered.lower()
    assert "bot-onboarding-code-applied" in rendered
    assert "GiftSecret42" not in rendered
    assert "Gi***42" in rendered
    assert "vless://private-secret-config" not in rendered
    assert "GiftSecret42" not in str(info.call_args_list)
    assert "vless://private-secret-config" not in str(info.call_args_list)
    warning.assert_not_called()
    state.clear.assert_awaited_once()
