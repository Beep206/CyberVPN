"""Unit tests for email clients (Resend, Brevo)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.email.resend_client import ResendClient, ResendError
from src.services.email.brevo_client import BrevoClient, BrevoError


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
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            async with ResendClient() as client:
                result = await client.send_otp(
                    email="test@example.com",
                    code="123456",
                    locale="en-EN",
                )

            assert result["id"] == "msg_123"

    async def test_send_otp_error(self, mock_error_response):
        """Test OTP email sending with API error."""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_error_response
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            async with ResendClient() as client:
                with pytest.raises(ResendError) as exc_info:
                    await client.send_otp(
                        email="test@example.com",
                        code="123456",
                        locale="en-EN",
                    )

                assert exc_info.value.status_code == 422

    def test_localized_subjects(self):
        """Test that localized subjects are available."""
        client = ResendClient()
        # Check some key locales exist
        assert "en-EN" in client._subjects
        assert "ru-RU" in client._subjects
        assert "uk-UA" in client._subjects
        assert "de-DE" in client._subjects


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
            mock_client_cls.return_value.__aenter__.return_value = mock_client

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
            mock_client_cls.return_value.__aenter__.return_value = mock_client

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
        # Brevo is used for resend, so subjects should indicate "new code"
        assert "en-EN" in client._subjects
        # The subject should be different from Resend's initial OTP subject
        assert "New" in client._subjects.get("en-EN", "") or "new" in client._subjects.get("en-EN", "")


class TestEmailTemplates:
    """Tests for email template generation."""

    def test_resend_template_contains_code(self):
        """Test that Resend template includes OTP code."""
        client = ResendClient()
        html = client._build_html_template("123456")

        assert "123456" in html
        assert "CyberVPN" in html
        assert "verification" in html.lower() or "code" in html.lower()

    def test_brevo_template_contains_code(self):
        """Test that Brevo template includes OTP code."""
        client = BrevoClient()
        html = client._build_html_template("654321")

        assert "654321" in html
        assert "CyberVPN" in html
