"""Unit tests for OtpService."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.otp_service import (
    OtpRateLimitError,
    OtpService,
)
from src.infrastructure.database.models.otp_code_model import OtpCodeModel


@pytest.fixture
def mock_otp_repo():
    """Create mock OTP repository."""
    return AsyncMock()


@pytest.fixture
def otp_service(mock_otp_repo):
    """Create OTP service with mock repository."""
    return OtpService(mock_otp_repo)


@pytest.fixture
def user_id():
    """Create test user ID."""
    return uuid4()


@pytest.fixture
def valid_otp(user_id):
    """Create valid OTP code model."""
    otp = OtpCodeModel(
        user_id=user_id,
        code="123456",
        purpose="email_verification",
        attempts_used=0,
        max_attempts=5,
        resend_count=0,
        max_resends=3,
        expires_at=datetime.now(UTC) + timedelta(hours=3),
    )
    otp.created_at = datetime.now(UTC) - timedelta(minutes=5)
    otp.last_resend_at = None
    otp.verified_at = None
    return otp


@pytest.fixture
def expired_otp(valid_otp):
    """Create mock expired OTP."""
    valid_otp.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    return valid_otp


@pytest.fixture
def exhausted_otp(valid_otp):
    """Create mock exhausted OTP (max attempts reached)."""
    valid_otp.attempts_used = valid_otp.max_attempts
    return valid_otp


class TestGenerateOtp:
    """Tests for OtpService.generate_otp."""

    async def test_generate_otp_creates_new_code(self, otp_service, mock_otp_repo, user_id):
        """Test that generate_otp creates a 6-digit code."""
        mock_otp_repo.invalidate_all_for_user.return_value = None
        mock_otp_repo.create.return_value = MagicMock(
            code="654321",
            expires_at=datetime.now(UTC) + timedelta(hours=3),
        )

        result = await otp_service.generate_otp(user_id, purpose="email_verification")

        assert result.code == "654321"
        mock_otp_repo.invalidate_all_for_user.assert_called_once()
        mock_otp_repo.create.assert_called_once()

    async def test_generate_otp_respects_is_resend_flag(self, otp_service, mock_otp_repo, user_id, valid_otp):
        """Test that generate_otp increments resend count when is_resend=True."""
        valid_otp.resend_count = 1
        mock_otp_repo.get_active_by_user_id.return_value = valid_otp
        mock_otp_repo.update.return_value = valid_otp
        mock_otp_repo.invalidate_all_for_user.return_value = None
        mock_otp_repo.create.return_value = OtpCodeModel(
            user_id=user_id,
            code="654321",
            purpose="email_verification",
            attempts_used=0,
            max_attempts=5,
            resend_count=1,
            max_resends=3,
            expires_at=datetime.now(UTC) + timedelta(hours=3),
        )

        result = await otp_service.generate_otp(user_id, purpose="email_verification", is_resend=True)

        assert result.code == "654321"
        assert valid_otp.resend_count == 2
        assert valid_otp.last_resend_at is not None
        mock_otp_repo.update.assert_called_once_with(valid_otp)

    async def test_generate_otp_rate_limits_resends(self, otp_service, mock_otp_repo, user_id, valid_otp):
        """Test that generate_otp raises error when resend limit reached."""
        valid_otp.resend_count = 3
        valid_otp.max_resends = 3
        mock_otp_repo.get_active_by_user_id.return_value = valid_otp

        with pytest.raises(OtpRateLimitError):
            await otp_service.generate_otp(user_id, purpose="email_verification", is_resend=True)


class TestValidateOtp:
    """Tests for OtpService.validate_otp."""

    async def test_validate_otp_success(self, otp_service, mock_otp_repo, user_id, valid_otp):
        """Test successful OTP validation."""
        mock_otp_repo.get_by_user_id_and_code.return_value = valid_otp
        mock_otp_repo.update.return_value = valid_otp

        result = await otp_service.validate_otp(user_id, "123456", "email_verification")

        assert result.success is True
        assert result.error_code is None
        mock_otp_repo.update.assert_called()

    async def test_validate_otp_invalid_code(self, otp_service, mock_otp_repo, user_id, valid_otp):
        """Test validation with wrong code."""
        mock_otp_repo.get_by_user_id_and_code.return_value = None
        mock_otp_repo.get_active_by_user_id.return_value = valid_otp
        mock_otp_repo.update.return_value = valid_otp

        result = await otp_service.validate_otp(user_id, "000000", "email_verification")

        assert result.success is False
        assert result.error_code == "OTP_INVALID"
        assert result.attempts_remaining == 4  # 5 - 1
        assert valid_otp.attempts_used == 1

    async def test_validate_otp_expired(self, otp_service, mock_otp_repo, user_id, expired_otp):
        """Test validation with expired OTP."""
        mock_otp_repo.get_by_user_id_and_code.return_value = expired_otp

        result = await otp_service.validate_otp(user_id, "123456", "email_verification")

        assert result.success is False
        assert result.error_code == "OTP_EXPIRED"

    async def test_validate_otp_exhausted(self, otp_service, mock_otp_repo, user_id, exhausted_otp):
        """Test validation when max attempts reached."""
        mock_otp_repo.get_by_user_id_and_code.return_value = exhausted_otp

        result = await otp_service.validate_otp(user_id, "123456", "email_verification")

        assert result.success is False
        assert result.error_code == "OTP_EXHAUSTED"

    async def test_validate_otp_no_active_otp(self, otp_service, mock_otp_repo, user_id):
        """Test validation when no OTP exists."""
        mock_otp_repo.get_by_user_id_and_code.return_value = None
        mock_otp_repo.get_active_by_user_id.return_value = None

        result = await otp_service.validate_otp(user_id, "123456", "email_verification")

        assert result.success is False
        assert result.error_code == "OTP_NOT_FOUND"


class TestInvalidateOtp:
    """Tests for OtpService.invalidate_otp."""

    async def test_invalidate_otp(self, otp_service, mock_otp_repo, user_id):
        """Test invalidating all OTPs for user."""
        mock_otp_repo.invalidate_all_for_user.return_value = None

        await otp_service.invalidate_otp(user_id, "email_verification")

        mock_otp_repo.invalidate_all_for_user.assert_called_once_with(user_id, "email_verification")


class TestCanResend:
    """Tests for OtpService.can_resend."""

    async def test_can_resend_when_allowed(self, otp_service, mock_otp_repo, user_id, valid_otp):
        """Test can_resend returns True when resends available."""
        valid_otp.resend_count = 1
        mock_otp_repo.get_active_by_user_id.return_value = valid_otp

        can_resend, remaining, next_available = await otp_service.can_resend(user_id, "email_verification")

        assert can_resend is True
        assert remaining == 2  # 3 - 1

    async def test_can_resend_when_limit_reached(self, otp_service, mock_otp_repo, user_id, valid_otp):
        """Test can_resend returns False when max resends reached."""
        valid_otp.resend_count = 3
        valid_otp.max_resends = 3
        mock_otp_repo.get_active_by_user_id.return_value = valid_otp

        can_resend, remaining, next_available = await otp_service.can_resend(user_id, "email_verification")

        assert can_resend is False
        assert remaining == 0

    async def test_can_resend_when_no_active_otp(self, otp_service, mock_otp_repo, user_id):
        """Test can_resend when no active OTP exists."""
        mock_otp_repo.get_active_by_user_id.return_value = None

        can_resend, remaining, next_available = await otp_service.can_resend(user_id, "email_verification")

        assert can_resend is True
        assert remaining == 3


class TestGetActiveOtp:
    """Tests for OtpService.get_active_otp."""

    async def test_get_active_otp_exists(self, otp_service, mock_otp_repo, user_id, valid_otp):
        """Test getting active OTP when one exists."""
        mock_otp_repo.get_active_by_user_id.return_value = valid_otp

        result = await otp_service.get_active_otp(user_id, "email_verification")

        assert result == valid_otp

    async def test_get_active_otp_none(self, otp_service, mock_otp_repo, user_id):
        """Test getting active OTP when none exists."""
        mock_otp_repo.get_active_by_user_id.return_value = None

        result = await otp_service.get_active_otp(user_id, "email_verification")

        assert result is None
