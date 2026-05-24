"""Unit tests for email clients (Resend, Brevo)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.email.brevo_client import BrevoClient, BrevoError
from src.services.email.resend_client import ResendClient, ResendError


def _settings(*, environment: str = "test", resend_key: str | None = "re_test") -> MagicMock:
    settings = MagicMock()
    settings.environment = environment
    settings.resend_api_key.get_secret_value.return_value = resend_key
    if resend_key is None:
        settings.resend_api_key = None
    settings.resend_from_email = "CyberVPN <verify@email.cyber-vpn.net>"
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
        with patch("src.services.email.resend_client.get_settings", return_value=_settings()), patch(
            "httpx.AsyncClient"
        ) as mock_client_cls:
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
        with patch("src.services.email.resend_client.get_settings", return_value=_settings()), patch(
            "httpx.AsyncClient"
        ) as mock_client_cls:
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
        with patch(
            "src.services.email.resend_client.get_settings",
            return_value=_settings(environment="production", resend_key=None),
        ), patch("httpx.AsyncClient") as mock_client_cls:
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
        with patch(
            "src.services.email.resend_client.get_settings",
            return_value=_settings(environment="test", resend_key=None),
        ), patch("httpx.AsyncClient") as mock_client_cls:
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
        with patch("httpx.AsyncClient") as mock_client_cls:
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
        with patch("httpx.AsyncClient") as mock_client_cls:
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

    def test_brevo_template_contains_code(self):
        """Test that Brevo template includes OTP code."""
        client = BrevoClient()
        html = client._render_otp_template("654321", "3 hours", "en-EN")

        assert "654321" in html
        assert "CyberVPN" in html
