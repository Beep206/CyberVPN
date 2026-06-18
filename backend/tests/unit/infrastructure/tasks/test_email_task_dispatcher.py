"""Regression tests for auth email TaskIQ payload hardening."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.infrastructure.tasks.email_task_dispatcher import (
    EMAIL_TASK_PAYLOAD_KEY_PREFIX,
    EmailTaskDispatcher,
)


@pytest.mark.asyncio
async def test_dispatch_otp_email_queues_only_payload_reference() -> None:
    redis_client = AsyncMock()
    redis_client.set.return_value = True
    dispatcher = EmailTaskDispatcher(redis_url="redis://unit-test", payload_ttl_seconds=900)

    with (
        patch.object(dispatcher, "_get_broker", new=AsyncMock()),
        patch("src.infrastructure.tasks.email_task_dispatcher.redis.from_url", return_value=redis_client),
    ):
        task_id = await dispatcher.dispatch_otp_email(
            "new.user@example.com",
            "123456",
            locale="ru-RU",
            is_resend=True,
            channel="web",
        )

    payload_ref = f"{EMAIL_TASK_PAYLOAD_KEY_PREFIX}{task_id}"
    redis_client.set.assert_awaited_once()
    set_args = redis_client.set.await_args.args
    set_kwargs = redis_client.set.await_args.kwargs
    assert set_args[0] == payload_ref
    assert set_kwargs == {"ex": 900, "nx": True}

    stored_payload = json.loads(set_args[1])
    assert stored_payload["kind"] == "otp"
    assert stored_payload["email"] == "new.user@example.com"
    assert stored_payload["otp_code"] == "123456"

    redis_client.xadd.assert_awaited_once()
    _, xadd_fields = redis_client.xadd.await_args.args
    taskiq_payload = json.loads(xadd_fields["data"].decode("utf-8"))
    assert taskiq_payload["task_name"] == "send_otp_email"
    assert taskiq_payload["kwargs"] == {"payload_ref": payload_ref}
    assert "email" not in taskiq_payload["kwargs"]
    assert "otp_code" not in taskiq_payload["kwargs"]


@pytest.mark.asyncio
async def test_dispatch_magic_link_email_cleans_payload_when_enqueue_fails() -> None:
    redis_client = AsyncMock()
    redis_client.set.return_value = True
    redis_client.xadd.side_effect = RuntimeError("redis stream unavailable")
    dispatcher = EmailTaskDispatcher(redis_url="redis://unit-test", payload_ttl_seconds=900)

    with (
        patch.object(dispatcher, "_get_broker", new=AsyncMock()),
        patch("src.infrastructure.tasks.email_task_dispatcher.redis.from_url", return_value=redis_client),
        pytest.raises(RuntimeError, match="redis stream unavailable"),
    ):
        await dispatcher.dispatch_magic_link_email(
            "new.user@example.com",
            "magic-token",
            otp_code="654321",
            locale="en-EN",
        )

    payload_ref = redis_client.set.await_args.args[0]
    assert payload_ref.startswith(EMAIL_TASK_PAYLOAD_KEY_PREFIX)
    redis_client.delete.assert_awaited_once_with(payload_ref)
    redis_client.aclose.assert_awaited_once()
