"""Unit tests for VerifyOtpUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.otp_service import OtpVerificationResult
from src.application.use_cases.auth.verify_otp import VerifyOtpResult, VerifyOtpUseCase


@pytest.fixture
def mock_user_repo():
    """Create mock user repository."""
    return AsyncMock()


@pytest.fixture
def mock_auth_service():
    """Create mock auth service."""
    service = MagicMock()
    service.create_access_token.return_value = "access_token_123"
    service.create_refresh_token.return_value = "refresh_token_456"
    return service


@pytest.fixture
def mock_otp_service():
    """Create mock OTP service."""
    return AsyncMock()


@pytest.fixture
def mock_session():
    """Create mock database session."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_remnawave():
    """Create mock Remnawave gateway."""
    gateway = AsyncMock()
    gateway.create_user.return_value = {"uuid": str(uuid4()), "username": "testuser"}
    return gateway


@pytest.fixture
def verify_use_case(mock_user_repo, mock_auth_service, mock_otp_service, mock_session, mock_remnawave):
    """Create VerifyOtpUseCase with mocks."""
    return VerifyOtpUseCase(
        user_repo=mock_user_repo,
        auth_service=mock_auth_service,
        otp_service=mock_otp_service,
        session=mock_session,
        remnawave_gateway=mock_remnawave,
    )


@pytest.fixture
def test_user():
    """Create mock test user."""
    user = MagicMock()
    user.id = uuid4()
    user.login = "testuser"
    user.email = "test@example.com"
    user.telegram_id = None
    user.role = "viewer"
    user.is_active = False
    user.is_email_verified = False
    return user


@pytest.fixture
def verified_user(test_user):
    """Create mock already-verified user."""
    test_user.is_email_verified = True
    test_user.is_active = True
    return test_user


class TestVerifyOtpSuccess:
    """Tests for successful OTP verification."""

    async def test_verify_otp_activates_user(
        self, verify_use_case, mock_user_repo, mock_otp_service, mock_session, test_user
    ):
        """Test that successful verification activates user."""
        mock_user_repo.get_by_email.return_value = test_user
        mock_otp_service.validate_otp.return_value = OtpVerificationResult(success=True)

        result = await verify_use_case.execute(email="test@example.com", code="123456")

        assert result.success is True
        assert test_user.is_active is True
        assert test_user.is_email_verified is True

    async def test_verify_otp_returns_tokens(
        self, verify_use_case, mock_user_repo, mock_auth_service, mock_otp_service, test_user
    ):
        """Test that successful verification returns access and refresh tokens."""
        mock_user_repo.get_by_email.return_value = test_user
        mock_otp_service.validate_otp.return_value = OtpVerificationResult(success=True)

        result = await verify_use_case.execute(email="test@example.com", code="123456")

        assert result.success is True
        assert result.access_token == "access_token_123"
        assert result.refresh_token == "refresh_token_456"
        assert result.token_type == "bearer"

    async def test_verify_otp_creates_remnawave_user(
        self, verify_use_case, mock_user_repo, mock_otp_service, mock_remnawave, test_user
    ):
        """Test that successful verification creates user in Remnawave."""
        mock_user_repo.get_by_email.return_value = test_user
        mock_otp_service.validate_otp.return_value = OtpVerificationResult(success=True)

        await verify_use_case.execute(email="test@example.com", code="123456")

        mock_remnawave.create_user.assert_called_once_with(
            username=test_user.login,
            email=test_user.email,
            telegram_id=test_user.telegram_id,
        )

    async def test_verify_otp_continues_on_remnawave_error(
        self, verify_use_case, mock_user_repo, mock_otp_service, mock_remnawave, test_user
    ):
        """Test that verification succeeds even if Remnawave fails."""
        mock_user_repo.get_by_email.return_value = test_user
        mock_otp_service.validate_otp.return_value = OtpVerificationResult(success=True)
        mock_remnawave.create_user.side_effect = Exception("Remnawave unavailable")

        result = await verify_use_case.execute(email="test@example.com", code="123456")

        assert result.success is True
        assert result.access_token is not None


class TestVerifyOtpFailure:
    """Tests for failed OTP verification."""

    async def test_verify_otp_user_not_found(self, verify_use_case, mock_user_repo):
        """Test verification fails for non-existent user."""
        mock_user_repo.get_by_email.return_value = None

        result = await verify_use_case.execute(email="unknown@example.com", code="123456")

        assert result.success is False
        assert result.error_code == "OTP_INVALID"

    async def test_verify_otp_already_verified(self, verify_use_case, mock_user_repo, verified_user):
        """Test verification fails if user already verified."""
        mock_user_repo.get_by_email.return_value = verified_user

        result = await verify_use_case.execute(email="test@example.com", code="123456")

        assert result.success is False
        assert result.error_code == "ALREADY_VERIFIED"

    async def test_verify_otp_invalid_code(
        self, verify_use_case, mock_user_repo, mock_otp_service, test_user
    ):
        """Test verification fails with invalid code."""
        mock_user_repo.get_by_email.return_value = test_user
        mock_otp_service.validate_otp.return_value = OtpVerificationResult(
            success=False,
            error_code="OTP_INVALID",
            message="Invalid verification code",
            attempts_remaining=4,
        )

        result = await verify_use_case.execute(email="test@example.com", code="000000")

        assert result.success is False
        assert result.error_code == "OTP_INVALID"
        assert result.attempts_remaining == 4

    async def test_verify_otp_expired(
        self, verify_use_case, mock_user_repo, mock_otp_service, test_user
    ):
        """Test verification fails with expired code."""
        mock_user_repo.get_by_email.return_value = test_user
        mock_otp_service.validate_otp.return_value = OtpVerificationResult(
            success=False,
            error_code="OTP_EXPIRED",
            message="Verification code has expired",
        )

        result = await verify_use_case.execute(email="test@example.com", code="123456")

        assert result.success is False
        assert result.error_code == "OTP_EXPIRED"

    async def test_verify_otp_exhausted(
        self, verify_use_case, mock_user_repo, mock_otp_service, test_user
    ):
        """Test verification fails when max attempts reached."""
        mock_user_repo.get_by_email.return_value = test_user
        mock_otp_service.validate_otp.return_value = OtpVerificationResult(
            success=False,
            error_code="OTP_EXHAUSTED",
            message="Maximum verification attempts reached",
            attempts_remaining=0,
        )

        result = await verify_use_case.execute(email="test@example.com", code="123456")

        assert result.success is False
        assert result.error_code == "OTP_EXHAUSTED"
        assert result.attempts_remaining == 0


class TestVerifyOtpWithoutRemnawave:
    """Tests for verification without Remnawave integration."""

    async def test_verify_otp_without_remnawave_gateway(
        self, mock_user_repo, mock_auth_service, mock_otp_service, mock_session, test_user
    ):
        """Test verification works without Remnawave gateway."""
        use_case = VerifyOtpUseCase(
            user_repo=mock_user_repo,
            auth_service=mock_auth_service,
            otp_service=mock_otp_service,
            session=mock_session,
            remnawave_gateway=None,
        )
        mock_user_repo.get_by_email.return_value = test_user
        mock_otp_service.validate_otp.return_value = OtpVerificationResult(success=True)

        result = await use_case.execute(email="test@example.com", code="123456")

        assert result.success is True
        assert result.access_token is not None
