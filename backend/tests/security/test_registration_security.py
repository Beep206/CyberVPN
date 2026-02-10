"""Security tests for registration endpoint (CRIT-1).

Tests that:
1. Registration is blocked when REGISTRATION_ENABLED=false
2. Registration requires invite token when enabled with invite-only mode
"""

from unittest.mock import AsyncMock, patch

import pytest


class TestRegistrationDisabled:
    """Test registration when REGISTRATION_ENABLED=false (default)."""

    @pytest.mark.asyncio
    async def test_registration_blocked_when_disabled(self):
        """Registration returns 403 when disabled."""
        from fastapi import HTTPException

        from src.presentation.api.v1.auth.registration import register
        from src.presentation.api.v1.auth.schemas import RegisterRequest

        # Mock settings with registration disabled
        with patch("src.presentation.api.v1.auth.registration.settings") as mock_settings:
            mock_settings.registration_enabled = False
            mock_settings.registration_invite_required = True

            request = RegisterRequest(
                login="testuser",
                email="test@example.com",
                password="SecurePass123!",
                locale="en-EN",
            )

            mock_db = AsyncMock()
            mock_dispatcher = AsyncMock()
            mock_redis = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await register(
                    request=request,
                    invite_token=None,
                    db=mock_db,
                    email_dispatcher=mock_dispatcher,
                    redis_client=mock_redis,
                )

            assert exc_info.value.status_code == 403
            assert "disabled" in exc_info.value.detail.lower()


class TestInviteTokenValidation:
    """Test invite token validation."""

    @pytest.mark.asyncio
    async def test_registration_requires_invite_token(self):
        """Registration fails without invite token when required."""
        from fastapi import HTTPException

        from src.presentation.api.v1.auth.registration import register
        from src.presentation.api.v1.auth.schemas import RegisterRequest

        with patch("src.presentation.api.v1.auth.registration.settings") as mock_settings:
            mock_settings.registration_enabled = True
            mock_settings.registration_invite_required = True

            request = RegisterRequest(
                login="testuser",
                email="test@example.com",
                password="SecurePass123!",
                locale="en-EN",
            )

            mock_db = AsyncMock()
            mock_dispatcher = AsyncMock()
            mock_redis = AsyncMock()

            with pytest.raises(HTTPException) as exc_info:
                await register(
                    request=request,
                    invite_token=None,  # No invite token
                    db=mock_db,
                    email_dispatcher=mock_dispatcher,
                    redis_client=mock_redis,
                )

            assert exc_info.value.status_code == 403
            assert "invite" in exc_info.value.detail.lower()


class TestInviteTokenService:
    """Test InviteTokenService functionality."""

    @pytest.mark.asyncio
    async def test_generate_token_stores_in_redis(self):
        """Token generation stores data in Redis."""
        from src.application.services.invite_service import InviteTokenService

        mock_redis = AsyncMock()
        service = InviteTokenService(mock_redis)

        token = await service.generate(
            created_by="admin-id",
            role="VIEWER",
            email_hint="test@example.com",
        )

        # Verify token was stored
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert f"invite_token:{token}" == call_args[0][0]

    @pytest.mark.asyncio
    async def test_validate_returns_data_for_valid_token(self):
        """Validating valid token returns data."""
        import json

        from src.application.services.invite_service import InviteTokenService

        mock_redis = AsyncMock()
        token_data = {"created_by": "admin", "role": "VIEWER", "created_at": "2026-01-01"}
        mock_redis.get = AsyncMock(return_value=json.dumps(token_data))

        service = InviteTokenService(mock_redis)
        result = await service.validate("test-token")

        assert result is not None
        assert result["role"] == "VIEWER"

    @pytest.mark.asyncio
    async def test_validate_returns_none_for_missing_token(self):
        """Validating non-existent token returns None."""
        from src.application.services.invite_service import InviteTokenService

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)

        service = InviteTokenService(mock_redis)
        result = await service.validate("nonexistent-token")

        assert result is None

    @pytest.mark.asyncio
    async def test_revoke_token_deletes_from_redis(self):
        """Revoking token deletes it from Redis."""
        from src.application.services.invite_service import InviteTokenService

        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=1)

        service = InviteTokenService(mock_redis)
        result = await service.revoke("test-token")

        assert result is True
        mock_redis.delete.assert_called_once_with("invite_token:test-token")

    @pytest.mark.asyncio
    async def test_revoke_returns_false_for_missing_token(self):
        """Revoking non-existent token returns False."""
        from src.application.services.invite_service import InviteTokenService

        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=0)

        service = InviteTokenService(mock_redis)
        result = await service.revoke("nonexistent-token")

        assert result is False
