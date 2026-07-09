"""Unit tests for auth email delivery metrics emitted by worker tasks."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from src.metrics import EMAIL_SEND_CONTEXT_TOTAL, EMAIL_SEND_ERRORS, EMAIL_SEND_TOTAL, OTP_EMAILS_SENT
from src.tasks.email.payloads import EMAIL_TASK_PAYLOAD_KEY_PREFIX, EmailTaskPayload
from src.tasks.email.send_magic_link import _build_magic_link_url, send_magic_link_email
from src.tasks.email.send_otp import _build_activation_url, send_otp_email
from src.tasks.email.send_password_reset import send_password_reset_email


def _counter_value(counter, **labels) -> float:
    return counter.labels(**labels)._value.get()


def test_build_activation_url_targets_locale_verify_page():
    url = _build_activation_url(
        base_url="https://cyber-vpn.net/",
        email="new.user@example.com",
        otp_code="123456",
        locale="ru-RU",
    )

    assert url == "https://cyber-vpn.net/ru-RU/verify"
    assert "new.user@example.com" not in url
    assert "123456" not in url
    assert "?" not in url


def test_build_magic_link_url_uses_fragment_token_not_query_string():
    url = _build_magic_link_url(
        base_url="https://cyber-vpn.net/",
        locale="en-EN",
        token="magic/token+value",  # noqa: S106 - synthetic test token
    )

    assert url == "https://cyber-vpn.net/en-EN/magic-link/verify#token=magic%2Ftoken%2Bvalue"
    assert "magic-link/verify?token" not in url


class _SuccessfulSmtpClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def send_otp(self, **kwargs):
        return {"id": "msg-otp-1", "server": "mailpit-1"}

    async def send_magic_link(self, **kwargs):
        return {"id": "msg-magic-1", "server": "mailpit-2"}

    async def send_password_reset(self, **kwargs):
        return {"id": "msg-reset-1", "server": "mailpit-3"}


class _FailingSmtpClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def send_otp(self, **kwargs):
        raise TimeoutError("smtp timed out")


class _SuccessfulResendClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def send_otp(self, **kwargs):
        return {"id": "msg-resend-fallback-1"}


class _UnexpectedApiClient:
    async def __aenter__(self):
        raise AssertionError("unexpected provider selected")

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_send_otp_email_emits_success_metrics():
    """OTP task should emit success counters for auth delivery dashboards."""
    settings = MagicMock()
    settings.email_dev_mode = True

    before_email_total = _counter_value(
        EMAIL_SEND_TOTAL,
        provider="smtp",
        email_type="otp",
        status="success",
    )
    before_otp_total = _counter_value(
        OTP_EMAILS_SENT,
        provider="smtp",
        action="initial",
        status="success",
    )
    before_context_total = _counter_value(
        EMAIL_SEND_CONTEXT_TOTAL,
        channel="web",
        provider="smtp",
        email_type="otp",
        locale="en-EN",
        status="success",
    )

    with (
        patch("src.tasks.email.send_otp.get_settings", return_value=settings),
        patch(
            "src.tasks.email.send_otp.SmtpClient",
            _SuccessfulSmtpClient,
        ),
    ):
        result = await send_otp_email.original_func(
            email="metrics@example.com",
            otp_code="123456",
            locale="en-EN",
            is_resend=False,
            channel="web",
        )

    assert result["success"] is True
    assert (
        _counter_value(
            EMAIL_SEND_TOTAL,
            provider="smtp",
            email_type="otp",
            status="success",
        )
        == before_email_total + 1
    )
    assert (
        _counter_value(
            OTP_EMAILS_SENT,
            provider="smtp",
            action="initial",
            status="success",
        )
        == before_otp_total + 1
    )
    assert (
        _counter_value(
            EMAIL_SEND_CONTEXT_TOTAL,
            channel="web",
            provider="smtp",
            email_type="otp",
            locale="en-EN",
            status="success",
        )
        == before_context_total + 1
    )


@pytest.mark.asyncio
async def test_send_otp_uses_resend_only_for_explicit_fallback_policy():
    """A resend request may use Resend only when fallback policy is explicitly enabled."""
    settings = MagicMock()
    settings.email_dev_mode = False
    settings.email_resend_fallback_enabled = True
    settings.resend_api_key.get_secret_value.return_value = "ValidResendProviderToken"
    settings.magic_link_base_url = "https://cyber-vpn.net"

    with (
        patch("src.tasks.email.send_otp.get_settings", return_value=settings),
        patch(
            "src.tasks.email.send_otp.ResendClient",
            _SuccessfulResendClient,
        ),
        patch("src.tasks.email.send_otp.SmtpClient", _UnexpectedApiClient),
    ):
        result = await send_otp_email.original_func(
            email="metrics@example.com",
            otp_code="123456",
            locale="en-EN",
            is_resend=True,
            channel="web",
        )

    assert result["success"] is True
    assert result["provider"] == "resend"
    assert result["message_id"] == "msg-resend-fallback-1"


@pytest.mark.asyncio
async def test_send_otp_resend_request_stays_on_smtp_without_fallback_policy():
    """A resend-code user action is not enough to route through Resend by itself."""
    settings = MagicMock()
    settings.email_dev_mode = False
    settings.email_resend_fallback_enabled = False
    settings.magic_link_base_url = "https://cyber-vpn.net"

    with (
        patch("src.tasks.email.send_otp.get_settings", return_value=settings),
        patch(
            "src.tasks.email.send_otp.SmtpClient",
            _SuccessfulSmtpClient,
        ),
        patch("src.tasks.email.send_otp.ResendClient", _UnexpectedApiClient),
    ):
        result = await send_otp_email.original_func(
            email="metrics@example.com",
            otp_code="123456",
            locale="en-EN",
            is_resend=True,
            channel="web",
        )

    assert result["success"] is True
    assert result["provider"] == "smtp"
    assert result["message_id"] == "msg-otp-1"


@pytest.mark.asyncio
async def test_send_otp_email_consumes_payload_ref_after_success():
    settings = MagicMock()
    settings.email_dev_mode = True
    settings.magic_link_base_url = "https://cyber-vpn.net"
    payload_ref = f"{EMAIL_TASK_PAYLOAD_KEY_PREFIX}{uuid.uuid4()}"
    payload = EmailTaskPayload(
        kind="otp",
        email="metrics@example.com",
        otp_code="123456",
        locale="en-EN",
        channel="web",
    )

    with (
        patch("src.tasks.email.send_otp.get_settings", return_value=settings),
        patch("src.tasks.email.send_otp.SmtpClient", _SuccessfulSmtpClient),
        patch("src.tasks.email.send_otp.claim_email_task_payload") as claim_payload,
        patch("src.tasks.email.send_otp.resolve_email_task_payload", return_value=payload) as resolve_payload,
        patch("src.tasks.email.send_otp.consume_email_task_payload") as consume_payload,
        patch("src.tasks.email.send_otp.release_email_task_payload") as release_payload,
    ):
        result = await send_otp_email.original_func(payload_ref=payload_ref)

    assert result["success"] is True
    claim_payload.assert_awaited_once_with(payload_ref)
    resolve_payload.assert_awaited_once_with(payload_ref, expected_kind="otp")
    consume_payload.assert_awaited_once_with(payload_ref)
    release_payload.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_otp_email_releases_payload_ref_after_provider_failure():
    settings = MagicMock()
    settings.email_dev_mode = True
    settings.magic_link_base_url = "https://cyber-vpn.net"
    payload_ref = f"{EMAIL_TASK_PAYLOAD_KEY_PREFIX}{uuid.uuid4()}"
    payload = EmailTaskPayload(
        kind="otp",
        email="metrics@example.com",
        otp_code="123456",
        locale="en-EN",
        channel="web",
    )

    with (
        patch("src.tasks.email.send_otp.get_settings", return_value=settings),
        patch("src.tasks.email.send_otp.SmtpClient", _FailingSmtpClient),
        patch("src.tasks.email.send_otp.claim_email_task_payload") as claim_payload,
        patch("src.tasks.email.send_otp.resolve_email_task_payload", return_value=payload),
        patch("src.tasks.email.send_otp.consume_email_task_payload") as consume_payload,
        patch("src.tasks.email.send_otp.release_email_task_payload") as release_payload,
        pytest.raises(TimeoutError),
    ):
        await send_otp_email.original_func(payload_ref=payload_ref)

    claim_payload.assert_awaited_once_with(payload_ref)
    consume_payload.assert_not_awaited()
    release_payload.assert_awaited_once_with(payload_ref)


@pytest.mark.asyncio
async def test_send_otp_email_emits_failure_metrics():
    """OTP task should emit failure counters with low-cardinality error labels."""
    settings = MagicMock()
    settings.email_dev_mode = True

    before_email_total = _counter_value(
        EMAIL_SEND_TOTAL,
        provider="smtp",
        email_type="otp",
        status="failed",
    )
    before_email_errors = _counter_value(
        EMAIL_SEND_ERRORS,
        provider="smtp",
        error_type="timeout",
    )
    before_otp_total = _counter_value(
        OTP_EMAILS_SENT,
        provider="smtp",
        action="resend",
        status="failed",
    )
    before_context_total = _counter_value(
        EMAIL_SEND_CONTEXT_TOTAL,
        channel="web",
        provider="smtp",
        email_type="otp",
        locale="en-EN",
        status="failed",
    )

    with (
        patch("src.tasks.email.send_otp.get_settings", return_value=settings),
        patch("src.tasks.email.send_otp.SmtpClient", _FailingSmtpClient),
        pytest.raises(TimeoutError),
    ):
        await send_otp_email.original_func(
            email="metrics@example.com",
            otp_code="123456",
            locale="en-EN",
            is_resend=True,
            channel="web",
        )

    assert (
        _counter_value(
            EMAIL_SEND_TOTAL,
            provider="smtp",
            email_type="otp",
            status="failed",
        )
        == before_email_total + 1
    )
    assert (
        _counter_value(
            EMAIL_SEND_ERRORS,
            provider="smtp",
            error_type="timeout",
        )
        == before_email_errors + 1
    )
    assert (
        _counter_value(
            OTP_EMAILS_SENT,
            provider="smtp",
            action="resend",
            status="failed",
        )
        == before_otp_total + 1
    )
    assert (
        _counter_value(
            EMAIL_SEND_CONTEXT_TOTAL,
            channel="web",
            provider="smtp",
            email_type="otp",
            locale="en-EN",
            status="failed",
        )
        == before_context_total + 1
    )


@pytest.mark.asyncio
async def test_send_magic_link_email_emits_success_metrics():
    """Magic link task should emit generic email delivery counters."""
    settings = MagicMock()
    settings.email_dev_mode = True
    settings.magic_link_base_url = "http://localhost:3000"

    before_email_total = _counter_value(
        EMAIL_SEND_TOTAL,
        provider="smtp",
        email_type="magic_link",
        status="success",
    )
    before_context_total = _counter_value(
        EMAIL_SEND_CONTEXT_TOTAL,
        channel="web",
        provider="smtp",
        email_type="magic_link",
        locale="en-EN",
        status="success",
    )

    magic_link_value = "magic-" + "token"

    with (
        patch("src.tasks.email.send_magic_link.get_settings", return_value=settings),
        patch(
            "src.tasks.email.send_magic_link.SmtpClient",
            _SuccessfulSmtpClient,
        ),
    ):
        result = await send_magic_link_email.original_func(
            email="metrics@example.com",
            token=magic_link_value,
            locale="en-EN",
            otp_code="654321",
            channel="web",
        )

    assert result["success"] is True
    assert (
        _counter_value(
            EMAIL_SEND_TOTAL,
            provider="smtp",
            email_type="magic_link",
            status="success",
        )
        == before_email_total + 1
    )
    assert (
        _counter_value(
            EMAIL_SEND_CONTEXT_TOTAL,
            channel="web",
            provider="smtp",
            email_type="magic_link",
            locale="en-EN",
            status="success",
        )
        == before_context_total + 1
    )


@pytest.mark.asyncio
async def test_send_password_reset_email_emits_success_metrics():
    """Password reset task should emit generic email delivery counters."""
    settings = MagicMock()
    settings.email_dev_mode = True

    before_email_total = _counter_value(
        EMAIL_SEND_TOTAL,
        provider="smtp",
        email_type="password_reset",
        status="success",
    )
    before_context_total = _counter_value(
        EMAIL_SEND_CONTEXT_TOTAL,
        channel="web",
        provider="smtp",
        email_type="password_reset",
        locale="en-EN",
        status="success",
    )

    with (
        patch("src.tasks.email.send_password_reset.get_settings", return_value=settings),
        patch(
            "src.tasks.email.send_password_reset.SmtpClient",
            _SuccessfulSmtpClient,
        ),
    ):
        result = await send_password_reset_email.original_func(
            email="metrics@example.com",
            otp_code="123456",
            locale="en-EN",
            channel="web",
        )

    assert result["success"] is True
    assert (
        _counter_value(
            EMAIL_SEND_TOTAL,
            provider="smtp",
            email_type="password_reset",
            status="success",
        )
        == before_email_total + 1
    )
    assert (
        _counter_value(
            EMAIL_SEND_CONTEXT_TOTAL,
            channel="web",
            provider="smtp",
            email_type="password_reset",
            locale="en-EN",
            status="success",
        )
        == before_context_total + 1
    )


@pytest.mark.asyncio
async def test_send_password_reset_email_uses_smtp_primary_outside_dev():
    settings = MagicMock()
    settings.email_dev_mode = False

    with (
        patch("src.tasks.email.send_password_reset.get_settings", return_value=settings),
        patch(
            "src.tasks.email.send_password_reset.SmtpClient",
            _SuccessfulSmtpClient,
        ),
    ):
        result = await send_password_reset_email.original_func(
            email="metrics@example.com",
            otp_code="123456",
            locale="en-EN",
            channel="web",
        )

    assert result["success"] is True
    assert result["provider"] == "smtp"
