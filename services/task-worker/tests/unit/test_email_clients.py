"""Unit tests for email clients (Resend, Brevo)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.email.brevo_client import BrevoClient, BrevoError
from src.services.email.resend_client import ResendClient, ResendError
from src.services.email.smtp_client import SmtpClient


def _settings(*, environment: str = "test", resend_key: str | None = "re_test") -> MagicMock:
    settings = MagicMock()
    settings.environment = environment
    settings.resend_api_key.get_secret_value.return_value = resend_key
    if resend_key is None:
        settings.resend_api_key = None
    settings.resend_from_email = "CyberVPN <verify@email.cyber-vpn.net>"
    return settings


def _brevo_settings(*, brevo_key: str | None = "brevo_test") -> MagicMock:
    settings = MagicMock()
    settings.brevo_api_key.get_secret_value.return_value = brevo_key
    if brevo_key is None:
        settings.brevo_api_key = None
    settings.brevo_from_email = "CyberVPN <noreply@email.cyber-vpn.net>"
    return settings


def _smtp_settings() -> MagicMock:
    settings = MagicMock()
    settings.email_dev_mode = False
    settings.smtp_servers = ["localhost:1025"]
    settings.smtp_host = "mail.cyber-vpn.net"
    settings.smtp_port = 587
    settings.smtp_starttls = True
    settings.smtp_use_ssl = False
    settings.smtp_auth_username = "noreply@cyber-vpn.net"
    settings.smtp_auth_password.get_secret_value.return_value = "smtp-password"
    settings.smtp_system_from_email = "CyberVPN <noreply@cyber-vpn.net>"
    settings.smtp_from_email = "CyberVPN <verify@cybervpn.local>"
    settings.redis_url = "redis://unit-test"
    return settings


def _dev_smtp_settings() -> MagicMock:
    settings = _smtp_settings()
    settings.email_dev_mode = True
    settings.smtp_from_email = "CyberVPN <verify@cybervpn.local>"
    settings.smtp_servers = ["mailpit-1:1025"]
    return settings


class TestResendClient:
    """Tests for ResendClient."""

    @pytest.fixture
    def mock_response(self):
        """Create mock successful response."""
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"id": "msg_123"}
        return response

    @pytest.fixture
    def mock_error_response(self):
        """Create mock error response."""
        response = MagicMock()
        response.status_code = 422
        response.text = "Validation error"
        response.json.return_value = {"message": "Invalid email"}
        return response

    async def test_send_otp_success(self, mock_response):
        """Test successful OTP email sending."""
        with (
            patch("src.services.email.resend_client.get_settings", return_value=_settings()),
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            async with ResendClient() as client:
                result = await client.send_otp(
                    email="test@example.com",
                    code="123456",
                    locale="en-EN",
                )

            assert result["id"] == "msg_123"

    async def test_send_otp_error(self, mock_error_response):
        """Test OTP email sending with API error."""
        with (
            patch("src.services.email.resend_client.get_settings", return_value=_settings()),
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_error_response
            mock_client_cls.return_value = mock_client

            async with ResendClient() as client:
                with pytest.raises(ResendError) as exc_info:
                    await client.send_otp(
                        email="test@example.com",
                        code="123456",
                        locale="en-EN",
                    )

                assert exc_info.value.status_code == 422

    async def test_missing_api_key_fails_in_production(self):
        """Production must not mark registration email delivery as successful without Resend credentials."""
        with (
            patch(
                "src.services.email.resend_client.get_settings",
                return_value=_settings(environment="production", resend_key=None),
            ),
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client

            async with ResendClient() as client:
                with pytest.raises(ResendError, match="RESEND_API_KEY"):
                    await client.send_otp(
                        email="test@example.com",
                        code="123456",
                        locale="en-EN",
                    )

            mock_client.post.assert_not_called()

    async def test_missing_api_key_can_skip_outside_production(self):
        """Local/test environments may still skip real email delivery without hiding production defects."""
        with (
            patch(
                "src.services.email.resend_client.get_settings",
                return_value=_settings(environment="test", resend_key=None),
            ),
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client

            async with ResendClient() as client:
                result = await client.send_otp(
                    email="test@example.com",
                    code="123456",
                    locale="en-EN",
                )

            assert result == {"id": "mock_no_key", "status": "skipped"}
            mock_client.post.assert_not_called()


class TestBrevoClient:
    """Tests for BrevoClient."""

    @pytest.fixture
    def mock_response(self):
        """Create mock successful response."""
        response = MagicMock()
        response.status_code = 201
        response.json.return_value = {"messageId": "brevo_msg_456"}
        return response

    @pytest.fixture
    def mock_error_response(self):
        """Create mock error response."""
        response = MagicMock()
        response.status_code = 400
        response.text = "Bad request"
        response.json.return_value = {"message": "Invalid recipient"}
        return response

    async def test_send_otp_success(self, mock_response):
        """Test successful OTP email sending via Brevo."""
        with (
            patch("src.services.email.brevo_client.get_settings", return_value=_brevo_settings()),
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value = mock_client

            async with BrevoClient() as client:
                result = await client.send_otp(
                    email="test@example.com",
                    code="654321",
                    locale="en-EN",
                )

            assert result["messageId"] == "brevo_msg_456"

    async def test_send_otp_error(self, mock_error_response):
        """Test OTP email sending with Brevo API error."""
        with (
            patch("src.services.email.brevo_client.get_settings", return_value=_brevo_settings()),
            patch("httpx.AsyncClient") as mock_client_cls,
        ):
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_error_response
            mock_client_cls.return_value = mock_client

            async with BrevoClient() as client:
                with pytest.raises(BrevoError) as exc_info:
                    await client.send_otp(
                        email="test@example.com",
                        code="654321",
                        locale="en-EN",
                    )

                assert exc_info.value.status_code == 400

    def test_localized_subjects_differ_from_initial(self):
        """Test that Brevo uses different subject for resend."""
        client = BrevoClient()
        subject = client._get_subject("en-EN")
        # Brevo is used for resend, so subject should indicate a new code.
        assert "new" in subject.lower()


class TestEmailTemplates:
    """Tests for email template generation."""

    def test_resend_template_contains_code(self):
        """Test that Resend template includes OTP code."""
        with patch("src.services.email.resend_client.get_settings", return_value=_settings()):
            client = ResendClient()
        html = client._render_otp_template("123456", "3 hours", "en-EN")

        assert "123456" in html
        assert "CyberVPN" in html
        assert "verification" in html.lower() or "code" in html.lower()

    def test_resend_template_contains_activation_link_when_provided(self):
        """Registration OTP emails should support one-click account verification links."""
        with patch("src.services.email.resend_client.get_settings", return_value=_settings()):
            client = ResendClient()
        html = client._render_otp_template(
            "123456",
            "3 hours",
            "en-EN",
            activation_url="https://cyber-vpn.net/en-EN/verify",
        )

        assert "VERIFY ACCOUNT" in html
        assert "https://cyber-vpn.net/en-EN/verify" in html
        assert "test%40example.com" not in html
        assert "code=123456" not in html

    def test_brevo_template_contains_code(self):
        """Test that Brevo template includes OTP code."""
        client = BrevoClient()
        html = client._render_otp_template("654321", "3 hours", "en-EN")

        assert "654321" in html
        assert "CyberVPN" in html


class TestSmtpClient:
    """Tests for SMTP primary delivery behavior."""

    async def test_production_smtp_uses_starttls_login_and_safe_headers(self):
        smtp_connection = MagicMock()
        smtp_context = MagicMock()
        smtp_context.__enter__.return_value = smtp_connection

        with (
            patch("src.services.email.smtp_client.get_settings", return_value=_smtp_settings()),
            patch(
                "src.services.email.smtp_client.smtplib.SMTP",
                return_value=smtp_context,
            ) as smtp_cls,
        ):
            async with SmtpClient() as client:
                result = await client.send_otp(
                    email="test@example.com",
                    code="123456",
                    locale="en-EN",
                    activation_url="https://cyber-vpn.net/en-EN/verify",
                )

        smtp_cls.assert_called_once_with("mail.cyber-vpn.net", 587, timeout=10)
        smtp_connection.starttls.assert_called_once()
        smtp_connection.ehlo.assert_called_once()
        smtp_connection.login.assert_called_once_with("noreply@cyber-vpn.net", "smtp-password")
        sendmail_args = smtp_connection.sendmail.call_args.args
        assert sendmail_args[0] == "noreply@cyber-vpn.net"
        assert sendmail_args[1] == ["test@example.com"]
        assert "X-OTP-Code" not in sendmail_args[2]
        assert result["server"] == "smtp-primary"

    async def test_dev_smtp_does_not_use_production_tls_or_login(self):
        smtp_connection = MagicMock()
        smtp_context = MagicMock()
        smtp_context.__enter__.return_value = smtp_connection
        redis_client = AsyncMock()
        redis_client.incr.return_value = 1

        with (
            patch("src.services.email.smtp_client.get_settings", return_value=_dev_smtp_settings()),
            patch("src.services.email.smtp_client.aioredis.from_url", return_value=redis_client),
            patch(
                "src.services.email.smtp_client.smtplib.SMTP",
                return_value=smtp_context,
            ) as smtp_cls,
        ):
            async with SmtpClient() as client:
                result = await client.send_otp(
                    email="test@example.com",
                    code="123456",
                    locale="en-EN",
                )

        smtp_cls.assert_called_once_with("mailpit-1", 1025, timeout=10)
        smtp_connection.starttls.assert_not_called()
        smtp_connection.login.assert_not_called()
        assert smtp_connection.sendmail.call_args.args[0] == "verify@cybervpn.local"
        assert result["server"] == "mailpit-1"
        redis_client.aclose.assert_awaited_once()
