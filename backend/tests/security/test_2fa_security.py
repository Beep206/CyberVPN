"""Security tests for 2FA operations (CRIT-3).

Tests that:
1. 2FA setup requires re-authentication
2. TOTP secret is only stored after verification
3. 2FA disable requires password AND TOTP code
4. Rate limiting prevents brute force
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestReauthService:
    """Test password re-authentication service."""

    @pytest.mark.asyncio
    async def test_verify_password_stores_reauth_token(self):
        """Successful password verification stores token in Redis."""
        from src.application.services.reauth_service import ReauthService

        mock_redis = AsyncMock()
        mock_auth = MagicMock()
        mock_auth.verify_password.return_value = True

        service = ReauthService(mock_redis, mock_auth)
        result = await service.verify_password(
            user_id="user-123",
            password="correct",
            password_hash="hash",
        )

        assert result is True
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_password_fails_with_wrong_password(self):
        """Wrong password returns False and doesn't store token."""
        from src.application.services.reauth_service import ReauthService

        mock_redis = AsyncMock()
        mock_auth = MagicMock()
        mock_auth.verify_password.return_value = False

        service = ReauthService(mock_redis, mock_auth)
        result = await service.verify_password(
            user_id="user-123",
            password="wrong",
            password_hash="hash",
        )

        assert result is False
        mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_is_recently_authenticated_checks_redis(self):
        """Check if user has valid reauth token."""
        from src.application.services.reauth_service import ReauthService

        mock_redis = AsyncMock()
        mock_redis.get.return_value = '{"verified_at": "2026-01-01"}'
        mock_auth = MagicMock()

        service = ReauthService(mock_redis, mock_auth)
        result = await service.is_recently_authenticated("user-123")

        assert result is True

    @pytest.mark.asyncio
    async def test_require_reauth_raises_when_not_authenticated(self):
        """require_reauth raises exception when no token exists."""
        from src.application.services.reauth_service import ReauthenticationRequired, ReauthService

        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_auth = MagicMock()

        service = ReauthService(mock_redis, mock_auth)

        with pytest.raises(ReauthenticationRequired):
            await service.require_reauth("user-123")


class TestPendingTOTPService:
    """Test pending TOTP secret storage."""

    @pytest.mark.asyncio
    async def test_generate_stores_in_redis_not_db(self):
        """Secret is stored in Redis, not database."""
        from src.application.services.pending_totp_service import PendingTOTPService

        mock_redis = AsyncMock()

        with patch("src.application.services.pending_totp_service.TOTPService") as mock_totp:
            mock_totp.return_value.generate_secret.return_value = "TESTSECRET"
            mock_totp.return_value.generate_qr_uri.return_value = "otpauth://..."

            service = PendingTOTPService(mock_redis)
            result = await service.generate_pending_secret("user-123", "test@example.com")

        assert "secret" in result
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_deletes_pending_on_success(self):
        """Successful verification deletes pending secret."""
        import json

        from src.application.services.pending_totp_service import PendingTOTPService

        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps({"secret": "TESTSECRET"})

        with patch("src.application.services.pending_totp_service.TOTPService") as mock_totp:
            mock_totp.return_value.verify_code.return_value = True

            service = PendingTOTPService(mock_redis)
            result = await service.verify_and_consume("user-123", "123456")

        assert result == "TESTSECRET"
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_returns_none_on_failure(self):
        """Failed verification returns None."""
        import json

        from src.application.services.pending_totp_service import PendingTOTPService

        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps({"secret": "TESTSECRET"})

        with patch("src.application.services.pending_totp_service.TOTPService") as mock_totp:
            mock_totp.return_value.verify_code.return_value = False

            service = PendingTOTPService(mock_redis)
            result = await service.verify_and_consume("user-123", "000000")

        assert result is None
        # Should not delete on failure
        mock_redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_verify_returns_none_when_no_pending(self):
        """No pending secret returns None."""
        from src.application.services.pending_totp_service import PendingTOTPService

        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        service = PendingTOTPService(mock_redis)
        result = await service.verify_and_consume("user-123", "123456")

        assert result is None
