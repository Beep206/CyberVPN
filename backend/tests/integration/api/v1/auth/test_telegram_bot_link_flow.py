"""Integration tests: bot-link generate -> exchange -> JWT response.

Tests the full flow through the use case layer with mocked dependencies.
"""

import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.use_cases.auth.telegram_bot_link import (
    TelegramBotLinkResult,
    TelegramBotLinkUseCase,
)
from src.infrastructure.cache.bot_link_tokens import (
    generate_bot_link_token,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel


def _make_user_model(
    telegram_id: int = 42,
    is_active: bool = True,
) -> AdminUserModel:
    model = MagicMock(spec=AdminUserModel)
    model.id = uuid.uuid4()
    model.login = "testuser"
    model.telegram_id = telegram_id
    model.email = None
    model.role = "viewer"
    model.is_active = is_active
    model.is_email_verified = True
    model.created_at = datetime.now(UTC)
    return model


class TestBotLinkHappyPath:
    """Integration: generate token -> exchange -> JWT tokens."""

    @pytest.mark.integration
    async def test_generate_then_exchange_returns_jwt(self):
        """Full flow: generate token, consume it, get JWT tokens."""
        mock_redis = AsyncMock()

        # Step 1: Generate token
        token = await generate_bot_link_token(mock_redis, telegram_id=42, ip="1.2.3.4")
        assert isinstance(token, str)
        assert len(token) > 20

        # Capture what was stored
        store_call = mock_redis.set.call_args
        _stored_key = store_call[0][0]
        stored_value = store_call[0][1]

        # Step 2: Set up consume to return the stored data
        mock_redis.getdel.return_value = stored_value

        user = _make_user_model(telegram_id=42)
        user_repo = AsyncMock()
        user_repo.get_by_telegram_id.return_value = user

        auth_service = MagicMock()
        access_exp = datetime.now(UTC) + timedelta(minutes=15)
        auth_service.create_access_token.return_value = ("access_tok", "jti1", access_exp)
        auth_service.create_refresh_token.return_value = ("refresh_tok", "jti2", datetime.now(UTC) + timedelta(days=7))

        use_case = TelegramBotLinkUseCase(
            user_repo=user_repo,
            auth_service=auth_service,
            redis_client=mock_redis,
        )

        result = await use_case.execute(token)

        assert isinstance(result, TelegramBotLinkResult)
        assert result.access_token == "access_tok"
        assert result.refresh_token == "refresh_tok"
        assert result.token_type == "bearer"
        assert result.user == user


class TestBotLinkExpiredToken:
    """Integration: exchange expired token -> 401."""

    @pytest.mark.integration
    async def test_expired_token_raises_value_error(self):
        """Token expired (Redis TTL expired) raises ValueError."""
        mock_redis = AsyncMock()
        mock_redis.getdel.return_value = None  # Token not in Redis = expired

        user_repo = AsyncMock()
        auth_service = MagicMock()

        use_case = TelegramBotLinkUseCase(
            user_repo=user_repo,
            auth_service=auth_service,
            redis_client=mock_redis,
        )

        with pytest.raises(ValueError, match="Invalid or expired"):
            await use_case.execute("expired_token_abc")


class TestBotLinkAlreadyUsedToken:
    """Integration: exchange already-used token -> 401."""

    @pytest.mark.integration
    async def test_second_use_of_token_fails(self):
        """Token consumed once; second attempt returns None from GETDEL."""
        mock_redis = AsyncMock()

        # First call: returns data
        mock_redis.getdel.side_effect = [
            json.dumps({"telegram_id": 42}),
            None,  # Second call: token already consumed
        ]

        user = _make_user_model(telegram_id=42)
        user_repo = AsyncMock()
        user_repo.get_by_telegram_id.return_value = user

        auth_service = MagicMock()
        access_exp = datetime.now(UTC) + timedelta(minutes=15)
        auth_service.create_access_token.return_value = ("access_tok", "jti1", access_exp)
        auth_service.create_refresh_token.return_value = ("refresh_tok", "jti2", datetime.now(UTC) + timedelta(days=7))

        use_case = TelegramBotLinkUseCase(
            user_repo=user_repo,
            auth_service=auth_service,
            redis_client=mock_redis,
        )

        # First exchange succeeds
        result = await use_case.execute("one_time_token")
        assert result.access_token == "access_tok"

        # Second exchange fails (token already consumed)
        with pytest.raises(ValueError, match="Invalid or expired"):
            await use_case.execute("one_time_token")


class TestBotLinkNonExistentUser:
    """Integration: exchange token for non-existent user -> error."""

    @pytest.mark.integration
    async def test_valid_token_but_no_user_raises(self):
        """Token is valid but telegram_id not in DB raises ValueError."""
        mock_redis = AsyncMock()
        mock_redis.getdel.return_value = json.dumps({"telegram_id": 999999})

        user_repo = AsyncMock()
        user_repo.get_by_telegram_id.return_value = None  # User not found

        auth_service = MagicMock()

        use_case = TelegramBotLinkUseCase(
            user_repo=user_repo,
            auth_service=auth_service,
            redis_client=mock_redis,
        )

        with pytest.raises(ValueError, match="User not found"):
            await use_case.execute("valid_token_no_user")

    @pytest.mark.integration
    async def test_deactivated_user_raises(self):
        """Token for deactivated user raises ValueError."""
        mock_redis = AsyncMock()
        mock_redis.getdel.return_value = json.dumps({"telegram_id": 42})

        user = _make_user_model(telegram_id=42, is_active=False)
        user_repo = AsyncMock()
        user_repo.get_by_telegram_id.return_value = user

        auth_service = MagicMock()

        use_case = TelegramBotLinkUseCase(
            user_repo=user_repo,
            auth_service=auth_service,
            redis_client=mock_redis,
        )

        with pytest.raises(ValueError, match="deactivated"):
            await use_case.execute("token_deactivated")
