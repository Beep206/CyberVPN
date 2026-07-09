"""Auth service logging must use fingerprints instead of raw PII identifiers."""

import json
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.invite_service import InviteTokenService
from src.application.services.login_protection import LoginProtectionService
from src.application.services.magic_link_service import MagicLinkService, RateLimitExceededError


def _make_pipeline(execute_return):
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=execute_return)
    pipe.incr = MagicMock(return_value=pipe)
    pipe.ttl = MagicMock(return_value=pipe)
    pipe.get = MagicMock(return_value=pipe)
    pipe.delete = MagicMock(return_value=pipe)
    pipe.set = MagicMock(return_value=pipe)
    return pipe


def _assert_raw_value_not_logged(caplog, raw_value: str) -> None:
    assert raw_value not in caplog.text
    for record in caplog.records:
        record_values = record.__dict__
        assert record_values.get("email") != raw_value
        assert record_values.get("email_hint") != raw_value
        assert record_values.get("identifier") != raw_value
        assert raw_value not in str(record_values)


@pytest.mark.unit
async def test_magic_link_generate_rate_limit_and_validate_logs_do_not_expose_email(caplog):
    raw_email = "victim@example.com"
    caplog.set_level(logging.DEBUG, logger="src.application.services.magic_link_service")

    generate_pipe = _make_pipeline([1, -2])
    redis_for_generate = AsyncMock()
    redis_for_generate.pipeline = MagicMock(return_value=generate_pipe)
    redis_for_generate.get = AsyncMock(return_value=None)
    redis_for_generate.exists = AsyncMock(return_value=False)
    redis_for_generate.expire = AsyncMock()
    await MagicLinkService(redis_for_generate).generate(email=raw_email)

    rate_limit_pipe = _make_pipeline([MagicLinkService.MAX_REQUESTS_PER_HOUR + 1, 123])
    redis_for_rate_limit = AsyncMock()
    redis_for_rate_limit.pipeline = MagicMock(return_value=rate_limit_pipe)
    redis_for_rate_limit.expire = AsyncMock()
    with pytest.raises(RateLimitExceededError):
        await MagicLinkService(redis_for_rate_limit).generate(email=raw_email)

    payload = json.dumps({"email": raw_email, "ip_address": None, "created_at": "2026-01-01T00:00:00+00:00"})
    read_pipe = _make_pipeline([payload.encode(), 1])
    cleanup_pipe = _make_pipeline([1, 1, True, 1])
    redis_for_validate = AsyncMock()
    redis_for_validate.pipeline = MagicMock(side_effect=[read_pipe, cleanup_pipe])
    await MagicLinkService(redis_for_validate).validate_and_consume("magic-token")

    assert any(getattr(record, "email_fingerprint", None) for record in caplog.records)
    _assert_raw_value_not_logged(caplog, raw_email)


@pytest.mark.unit
async def test_magic_link_replay_and_otp_failure_logs_do_not_expose_email(caplog):
    raw_email = "otp-victim@example.com"
    payload = json.dumps({"email": raw_email, "ip_address": None, "created_at": "2026-01-01T00:00:00+00:00"})
    caplog.set_level(logging.INFO, logger="src.application.services.magic_link_service")

    replay_pipe = _make_pipeline([None, 0])
    redis_for_replay = AsyncMock()
    redis_for_replay.pipeline = MagicMock(return_value=replay_pipe)
    redis_for_replay.get = AsyncMock(return_value=payload.encode())
    await MagicLinkService(redis_for_replay).validate_and_consume("replayed-token")

    caplog.set_level(logging.WARNING, logger="src.application.services.magic_link_service")
    redis_for_missing_otp = AsyncMock()
    redis_for_missing_otp.get = AsyncMock(return_value=None)
    await MagicLinkService(redis_for_missing_otp).validate_otp(raw_email, "123456")

    redis_for_bad_otp = AsyncMock()
    redis_for_bad_otp.get = AsyncMock(return_value=b"654321")
    await MagicLinkService(redis_for_bad_otp).validate_otp(raw_email, "123456")

    assert any(getattr(record, "email_fingerprint", None) for record in caplog.records)
    _assert_raw_value_not_logged(caplog, raw_email)


@pytest.mark.unit
async def test_invite_token_generation_log_does_not_expose_email_hint(caplog):
    raw_email_hint = "invitee@example.com"
    caplog.set_level(logging.INFO, logger="src.application.services.invite_service")

    redis_client = AsyncMock()
    redis_client.set = AsyncMock(return_value=True)

    await InviteTokenService(redis_client).generate(
        created_by="admin-user-id",
        role="VIEWER",
        email_hint=raw_email_hint,
    )

    assert any(getattr(record, "email_hint_fingerprint", None) for record in caplog.records)
    assert any(getattr(record, "email_hint_present", None) is True for record in caplog.records)
    _assert_raw_value_not_logged(caplog, raw_email_hint)


@pytest.mark.unit
async def test_login_protection_logs_do_not_expose_identifier(caplog):
    raw_identifier = "login-victim@example.com"
    caplog.set_level(logging.DEBUG, logger="src.application.services.login_protection")

    redis_client = AsyncMock()
    redis_client.incr = AsyncMock(side_effect=[5, 20])
    redis_client.expire = AsyncMock()
    redis_client.set = AsyncMock(return_value=True)

    service = LoginProtectionService(redis_client)
    await service.record_failed_attempt(raw_identifier)
    await service.record_failed_attempt(raw_identifier)

    redis_for_reset = AsyncMock()
    redis_for_reset.get = AsyncMock(side_effect=[b"3", None])
    redis_for_reset.delete = AsyncMock(return_value=2)
    await LoginProtectionService(redis_for_reset).reset_on_success(raw_identifier)

    redis_for_permanent_reset = AsyncMock()
    redis_for_permanent_reset.get = AsyncMock(side_effect=[b"20", "permanent"])
    redis_for_permanent_reset.delete = AsyncMock(return_value=0)
    await LoginProtectionService(redis_for_permanent_reset).reset_on_success(raw_identifier)

    redis_for_admin_unlock = AsyncMock()
    redis_for_admin_unlock.delete = AsyncMock(return_value=2)
    await LoginProtectionService(redis_for_admin_unlock).admin_unlock(raw_identifier)

    assert any(getattr(record, "identifier_fingerprint", None) for record in caplog.records)
    _assert_raw_value_not_logged(caplog, raw_identifier)
