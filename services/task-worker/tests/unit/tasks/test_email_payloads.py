"""Regression tests for auth email payload indirection."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tasks.email.payloads import (
    EMAIL_TASK_PAYLOAD_CLAIM_TTL_SECONDS,
    EMAIL_TASK_PAYLOAD_KEY_PREFIX,
    EmailTaskPayloadAlreadyClaimedError,
    EmailTaskPayloadError,
    claim_email_task_payload,
    consume_email_task_payload,
    release_email_task_payload,
    resolve_email_task_payload,
    validate_email_task_payload_ref,
)


def _payload_ref() -> str:
    return f"{EMAIL_TASK_PAYLOAD_KEY_PREFIX}{uuid.uuid4()}"


def test_validate_email_task_payload_ref_rejects_outside_namespace() -> None:
    with pytest.raises(EmailTaskPayloadError, match="outside_namespace"):
        validate_email_task_payload_ref("cybervpn:other:key")


def test_validate_email_task_payload_ref_rejects_non_uuid_suffix() -> None:
    with pytest.raises(EmailTaskPayloadError, match="invalid_id"):
        validate_email_task_payload_ref(f"{EMAIL_TASK_PAYLOAD_KEY_PREFIX}not-a-uuid")


@pytest.mark.asyncio
async def test_resolve_email_task_payload_decodes_expected_kind() -> None:
    payload_ref = _payload_ref()
    redis = AsyncMock()
    redis.get.return_value = json.dumps(
        {
            "version": 1,
            "kind": "magic_link",
            "email": "User@Example.com",
            "token": "magic-token",
            "otp_code": "654321",
            "locale": "ru-RU",
            "is_resend": True,
            "channel": "web",
        }
    )
    settings = MagicMock()
    settings.redis_url = "redis://unit-test"

    with (
        patch("src.tasks.email.payloads.get_settings", return_value=settings),
        patch("src.tasks.email.payloads.Redis.from_url", return_value=redis),
    ):
        payload = await resolve_email_task_payload(payload_ref, expected_kind="magic_link")

    assert payload.email == "User@Example.com"
    assert payload.token == "magic-token"  # noqa: S105 - synthetic test token
    assert payload.otp_code == "654321"
    assert payload.locale == "ru-RU"
    assert payload.is_resend is True
    redis.get.assert_awaited_once_with(payload_ref)
    redis.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_claim_email_task_payload_sets_short_claim_ttl() -> None:
    payload_ref = _payload_ref()
    redis = AsyncMock()
    redis.set.return_value = True
    settings = MagicMock()
    settings.redis_url = "redis://unit-test"

    with (
        patch("src.tasks.email.payloads.get_settings", return_value=settings),
        patch("src.tasks.email.payloads.Redis.from_url", return_value=redis),
    ):
        await claim_email_task_payload(payload_ref)

    redis.set.assert_awaited_once_with(
        f"{payload_ref}:claim",
        "1",
        ex=EMAIL_TASK_PAYLOAD_CLAIM_TTL_SECONDS,
        nx=True,
    )
    redis.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_claim_email_task_payload_rejects_duplicate_claim() -> None:
    payload_ref = _payload_ref()
    redis = AsyncMock()
    redis.set.return_value = None
    settings = MagicMock()
    settings.redis_url = "redis://unit-test"

    with (
        patch("src.tasks.email.payloads.get_settings", return_value=settings),
        patch("src.tasks.email.payloads.Redis.from_url", return_value=redis),
        pytest.raises(EmailTaskPayloadAlreadyClaimedError),
    ):
        await claim_email_task_payload(payload_ref)


@pytest.mark.asyncio
async def test_consume_email_task_payload_deletes_payload_and_claim() -> None:
    payload_ref = _payload_ref()
    redis = AsyncMock()
    settings = MagicMock()
    settings.redis_url = "redis://unit-test"

    with (
        patch("src.tasks.email.payloads.get_settings", return_value=settings),
        patch("src.tasks.email.payloads.Redis.from_url", return_value=redis),
    ):
        await consume_email_task_payload(payload_ref)

    redis.delete.assert_awaited_once_with(payload_ref, f"{payload_ref}:claim")


@pytest.mark.asyncio
async def test_release_email_task_payload_deletes_only_claim() -> None:
    payload_ref = _payload_ref()
    redis = AsyncMock()
    settings = MagicMock()
    settings.redis_url = "redis://unit-test"

    with (
        patch("src.tasks.email.payloads.get_settings", return_value=settings),
        patch("src.tasks.email.payloads.Redis.from_url", return_value=redis),
    ):
        await release_email_task_payload(payload_ref)

    redis.delete.assert_awaited_once_with(f"{payload_ref}:claim")
