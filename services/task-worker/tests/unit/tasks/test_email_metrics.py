"""Unit tests for auth email delivery metrics emitted by worker tasks."""

from unittest.mock import MagicMock, patch

import pytest

from src.metrics import EMAIL_SEND_CONTEXT_TOTAL, EMAIL_SEND_ERRORS, EMAIL_SEND_TOTAL, OTP_EMAILS_SENT
from src.tasks.email.send_magic_link import send_magic_link_email
from src.tasks.email.send_otp import send_otp_email
from src.tasks.email.send_password_reset import send_password_reset_email


def _counter_value(counter, **labels) -> float:
    return counter.labels(**labels)._value.get()


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

    with patch("src.tasks.email.send_otp.get_settings", return_value=settings), patch(
        "src.tasks.email.send_otp.SmtpClient",
        _SuccessfulSmtpClient,
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

    with patch("src.tasks.email.send_magic_link.get_settings", return_value=settings), patch(
        "src.tasks.email.send_magic_link.SmtpClient",
        _SuccessfulSmtpClient,
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

    with patch("src.tasks.email.send_password_reset.get_settings", return_value=settings), patch(
        "src.tasks.email.send_password_reset.SmtpClient",
        _SuccessfulSmtpClient,
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
