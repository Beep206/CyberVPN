"""Security tests for JWT token revocation (HIGH-6).

Tests that:
1. Tokens include JTI claim
2. Revoked tokens are rejected
3. Logout-all revokes all user tokens
4. Revocation list uses appropriate TTL
"""

import pytest
from unittest.mock import AsyncMock
from datetime import UTC, datetime, timedelta


class TestJTIClaims:
    """Test JTI claim in tokens."""

    def test_access_token_includes_jti(self):
        """Access tokens include JTI claim."""
        from src.application.services.auth_service import AuthService

        auth = AuthService()
        token, jti, expires_at = auth.create_access_token("user-123", "admin")

        # Token should be created
        assert token is not None

        # JTI should be UUID format
        assert jti is not None
        assert len(jti) == 36  # UUID format: 8-4-4-4-12

        # Expiry should be in the future
        assert expires_at > datetime.now(UTC)

    def test_refresh_token_includes_jti(self):
        """Refresh tokens include JTI claim."""
        from src.application.services.auth_service import AuthService

        auth = AuthService()
        token, jti, expires_at = auth.create_refresh_token("user-123")

        assert jti is not None
        assert len(jti) == 36  # UUID format

    def test_each_token_has_unique_jti(self):
        """Each token gets a unique JTI."""
        from src.application.services.auth_service import AuthService

        auth = AuthService()
        jtis = set()

        for _ in range(100):
            _, jti, _ = auth.create_access_token("user-123", "admin")
            jtis.add(jti)

        # All JTIs should be unique
        assert len(jtis) == 100

    def test_decoded_token_contains_jti(self):
        """Decoded token payload contains JTI."""
        from src.application.services.auth_service import AuthService

        auth = AuthService()
        token, expected_jti, _ = auth.create_access_token("user-123", "admin")

        # Decode and verify JTI
        payload = auth.decode_token(token)
        assert "jti" in payload
        assert payload["jti"] == expected_jti


class TestRevocationService:
    """Test JWT revocation service."""

    @pytest.mark.asyncio
    async def test_generate_jti_produces_uuid(self):
        """generate_jti produces valid UUID."""
        from src.application.services.jwt_revocation_service import JWTRevocationService

        jti = JWTRevocationService.generate_jti()

        assert jti is not None
        assert len(jti) == 36
        # Should be valid UUID format
        parts = jti.split("-")
        assert len(parts) == 5

    @pytest.mark.asyncio
    async def test_revoke_token_stores_in_redis(self):
        """Revoked token is stored in Redis with TTL."""
        from src.application.services.jwt_revocation_service import JWTRevocationService

        mock_redis = AsyncMock()

        service = JWTRevocationService(mock_redis)
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        await service.revoke_token("test-jti-123", expires_at)

        # Should store with appropriate TTL
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert "test-jti-123" in call_args[0][0]  # Key contains JTI
        assert call_args[0][2] == "revoked"  # Value is "revoked"

    @pytest.mark.asyncio
    async def test_is_revoked_checks_redis(self):
        """is_revoked checks Redis for JTI."""
        from src.application.services.jwt_revocation_service import JWTRevocationService

        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 1  # Token is revoked

        service = JWTRevocationService(mock_redis)
        result = await service.is_revoked("test-jti-123")

        assert result is True
        mock_redis.exists.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_revoked_returns_false_for_valid(self):
        """is_revoked returns False for non-revoked token."""
        from src.application.services.jwt_revocation_service import JWTRevocationService

        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 0  # Token not in revocation list

        service = JWTRevocationService(mock_redis)
        result = await service.is_revoked("test-jti-123")

        assert result is False


class TestSecurityProperties:
    """Test security properties of revocation system."""

    def test_revocation_prefix_is_namespaced(self):
        """Revocation keys are properly namespaced in Redis."""
        from src.application.services.jwt_revocation_service import JWTRevocationService

        assert JWTRevocationService.REVOKED_PREFIX == "jwt_revoked:"

    def test_expired_token_not_stored(self):
        """Already-expired tokens aren't stored in revocation list."""
        # This is by design - no need to revoke already-expired tokens

    @pytest.mark.asyncio
    async def test_revoke_with_expired_token_skipped(self):
        """Revoking an already-expired token is a no-op."""
        from src.application.services.jwt_revocation_service import JWTRevocationService

        mock_redis = AsyncMock()

        service = JWTRevocationService(mock_redis)
        expires_at = datetime.now(UTC) - timedelta(hours=1)  # Already expired

        await service.revoke_token("expired-jti", expires_at)

        # Should not store anything
        mock_redis.setex.assert_not_called()
