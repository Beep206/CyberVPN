from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Message, User

import src.handlers.promocode as promocode_handlers
from src.handlers.connection import code_fingerprint, onboarding_code_idempotency_key, telegram_user_fingerprint
from src.handlers.promocode import promocode_entered_handler
from src.models.connection import ConnectionBootstrapResponse
from src.services.cache_service import CacheService


class _I18nStub:
    def get(self, key: str, **kwargs: object) -> str:
        if kwargs:
            suffix = " ".join(f"{name}={value}" for name, value in sorted(kwargs.items()))
            return f"{key} {suffix}"
        return key


def _message(text: str) -> Message:
    message = MagicMock(spec=Message)
    message.from_user = User(id=123456, is_bot=False, first_name="Test")
    message.chat = SimpleNamespace(id=123456, type="private")
    message.message_id = 777
    message.text = text
    message.answer = AsyncMock()
    return message


def _answer_text(call: object) -> str:
    args = getattr(call, "args", ())
    kwargs = getattr(call, "kwargs", {})
    return str(kwargs.get("text") if "text" in kwargs else args[0])


@pytest.mark.asyncio
async def test_promocode_fsm_text_uses_connection_flow_without_discount_copy_or_secret_logs(
    fake_redis: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = CacheService(fake_redis, key_prefix="fsm:")
    private_url = "vless://fsm-private-config"
    api_client = SimpleNamespace(
        apply_telegram_onboarding_code=AsyncMock(
            return_value={
                "status": "completed",
                "discount_type": "percentage",
                "discount_value": 90,
            }
        ),
        get_customer_connection_bootstrap=AsyncMock(
            return_value=ConnectionBootstrapResponse(
                status="available",
                available=True,
                subscription_url=private_url,
                qr_payload=private_url,
                config_profile_name="FSM profile",
                flow_key="flow-fsm",
                version=11,
                connection_session_id="44444444-5555-4666-8777-888888888888",
                telegram_payload={"bot_connection_session_id": "44444444-5555-4666-8777-888888888888"},
            )
        ),
    )
    state = SimpleNamespace(clear=AsyncMock())
    message = _message("GiftSecret42")
    info = MagicMock()
    monkeypatch.setattr(promocode_handlers, "logger", SimpleNamespace(info=info))

    await promocode_entered_handler(message, _I18nStub(), api_client, state, cache)

    api_client.apply_telegram_onboarding_code.assert_awaited_once_with(
        123456,
        "GiftSecret42",
        idempotency_key=onboarding_code_idempotency_key(
            telegram_id=123456,
            code="GiftSecret42",
            message_id=777,
        ),
    )
    api_client.get_customer_connection_bootstrap.assert_awaited_once_with(123456, platform_hint="unknown")
    state.clear.assert_awaited_once()

    assert message.answer.await_count == 2
    first_answer = _answer_text(message.answer.await_args_list[0])
    assert first_answer.startswith("bot-onboarding-code-applied")
    assert "code-activated" not in first_answer
    assert "discount" not in first_answer.lower()
    assert "GiftSecret42" not in first_answer
    assert "Gi***42" in first_answer
    assert private_url not in first_answer

    second_answer = _answer_text(message.answer.await_args_list[1])
    assert second_answer.startswith("bot-onboarding-connection-ready")
    assert private_url not in second_answer
    assert private_url not in str(message.answer.await_args_list[1].kwargs["reply_markup"])

    raw_values = [str(value) for value in await fake_redis.mget(await fake_redis.keys("fsm:*"))]
    persisted = "\n".join(raw_values)
    assert "GiftSecret42" not in persisted
    assert private_url not in persisted
    assert "flow-fsm" in persisted

    info.assert_called_once()
    assert info.call_args.args == ("onboarding_code_text_submitted",)
    safe_log_context = info.call_args.kwargs
    assert safe_log_context["telegram_user_fingerprint"] == telegram_user_fingerprint(123456)
    assert safe_log_context["code_fingerprint"] == code_fingerprint("GiftSecret42")
    assert "user_id" not in safe_log_context
    assert "GiftSecret42" not in str(safe_log_context)
    assert private_url not in str(safe_log_context)
