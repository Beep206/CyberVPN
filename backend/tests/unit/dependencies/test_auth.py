"""Unit tests for auth dependencies.

LOW-007: Test revocation check in optional_user.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from src.presentation.dependencies.auth import _validate_token, optional_user


class TestValidateToken:
    """Tests for _validate_token helper function."""

    @pytest.fixture
    def mock_auth_service(self):
        service = MagicMock()
        service.decode_token = MagicMock()
        return service

    @pytest.fixture
    def mock_redis(self):
        return AsyncMock()

    async def test_returns_none_for_non_access_token(self, mock_auth_service, mock_redis):
        """Non-access tokens should return None."""
        mock_auth_service.decode_token.return_value = {"type": "refresh", "sub": "user-123"}

        result = await _validate_token("token", mock_auth_service, mock_redis)

        assert result is None

    async def test_returns_none_for_missing_sub(self, mock_auth_service, mock_redis):
        """Tokens without sub claim should return None."""
        mock_auth_service.decode_token.return_value = {"type": "access"}

        result = await _validate_token("token", mock_auth_service, mock_redis)

        assert result is None

    async def test_returns_result_for_valid_token(self, mock_auth_service, mock_redis):
        """Valid tokens should return TokenValidationResult."""
        mock_auth_service.decode_token.return_value = {
            "type": "access",
            "sub": "user-123",
            "jti": "jti-456",
        }

        with patch(
            "src.presentation.dependencies.auth.JWTRevocationService"
        ) as mock_revocation_cls:
            mock_revocation = AsyncMock()
            mock_revocation.is_revoked.return_value = False
            mock_revocation_cls.return_value = mock_revocation

            result = await _validate_token("token", mock_auth_service, mock_redis)

        assert result is not None
        assert result.user_id == "user-123"
        assert result.jti == "jti-456"

    async def test_returns_none_for_revoked_token(self, mock_auth_service, mock_redis):
        """LOW-007: Revoked tokens should return None."""
        mock_auth_service.decode_token.return_value = {
            "type": "access",
            "sub": "user-123",
            "jti": "revoked-jti",
        }

        with patch(
            "src.presentation.dependencies.auth.JWTRevocationService"
        ) as mock_revocation_cls:
            mock_revocation = AsyncMock()
            mock_revocation.is_revoked.return_value = True
            mock_revocation_cls.return_value = mock_revocation

            result = await _validate_token("token", mock_auth_service, mock_redis)

        assert result is None

    async def test_skips_revocation_check_when_disabled(self, mock_auth_service, mock_redis):
        """Revocation check can be disabled."""
        mock_auth_service.decode_token.return_value = {
            "type": "access",
            "sub": "user-123",
            "jti": "jti-456",
        }

        # Should not call revocation service when check_revocation=False
        result = await _validate_token(
            "token",
            mock_auth_service,
            mock_redis,
            check_revocation=False,
        )

        assert result is not None
        assert result.user_id == "user-123"


class TestOptionalUserRevocation:
    """LOW-007: Tests for optional_user revocation check."""

    @pytest.fixture
    def mock_credentials(self):
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")

    async def test_optional_user_returns_none_for_revoked_token(self, mock_credentials):
        """LOW-007: optional_user should return None for revoked tokens."""
        mock_db = AsyncMock()
        mock_auth_service = MagicMock()
        mock_redis = AsyncMock()

        mock_auth_service.decode_token.return_value = {
            "type": "access",
            "sub": "user-123",
            "jti": "revoked-jti",
        }

        with patch(
            "src.presentation.dependencies.auth.JWTRevocationService"
        ) as mock_revocation_cls:
            mock_revocation = AsyncMock()
            mock_revocation.is_revoked.return_value = True
            mock_revocation_cls.return_value = mock_revocation

            result = await optional_user(
                credentials=mock_credentials,
                db=mock_db,
                auth_service=mock_auth_service,
                redis_client=mock_redis,
            )

        assert result is None, "optional_user should return None for revoked tokens"

    async def test_optional_user_returns_none_without_credentials(self):
        """optional_user should return None when no credentials provided."""
        mock_db = AsyncMock()
        mock_auth_service = MagicMock()
        mock_redis = AsyncMock()

        result = await optional_user(
            credentials=None,
            db=mock_db,
            auth_service=mock_auth_service,
            redis_client=mock_redis,
        )

        assert result is None
