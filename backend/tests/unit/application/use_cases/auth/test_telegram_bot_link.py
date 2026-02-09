"""Unit tests for TelegramBotLinkUseCase."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.application.use_cases.auth.telegram_bot_link import (
    TelegramBotLinkResult,
    TelegramBotLinkUseCase,
)


class TestTelegramBotLinkUseCase:
    """Tests for TelegramBotLinkUseCase.execute()."""

    @pytest.fixture
    def mock_user_repo(self):
        return AsyncMock()

    @pytest.fixture
    def mock_auth_service(self):
        service = MagicMock()
        access_exp = datetime.now(UTC) + timedelta(minutes=15)
        refresh_exp = datetime.now(UTC) + timedelta(days=7)
        service.create_access_token.return_value = ("access_tok", "jti_a", access_exp)
        service.create_refresh_token.return_value = ("refresh_tok", "jti_r", refresh_exp)
        return service

    @pytest.fixture
    def mock_redis(self):
        return AsyncMock()

    @pytest.fixture
    def make_user(self):
        def _make(user_id=None, telegram_id=123456789, is_active=True, role="viewer"):
            user = MagicMock()
            user.id = user_id or uuid4()
            user.login = "testuser"
            user.email = None
            user.telegram_id = telegram_id
            user.role = role
            user.is_active = is_active
            user.is_email_verified = True
            user.created_at = datetime.now(UTC)
            return user
        return _make

    @pytest.fixture
    def use_case(self, mock_user_repo, mock_auth_service, mock_redis):
        return TelegramBotLinkUseCase(
            user_repo=mock_user_repo,
            auth_service=mock_auth_service,
            redis_client=mock_redis,
        )

    @pytest.mark.unit
    @patch("src.application.use_cases.auth.telegram_bot_link.consume_bot_link_token")
    async def test_valid_token_returns_jwt(self, mock_consume, use_case, mock_user_repo, make_user):
        mock_consume.return_value = 123456789
        existing_user = make_user()
        mock_user_repo.get_by_telegram_id.return_value = existing_user

        result = await use_case.execute("valid_token")

        assert isinstance(result, TelegramBotLinkResult)
        assert result.access_token == "access_tok"
        assert result.refresh_token == "refresh_tok"
        assert result.user == existing_user

    @pytest.mark.unit
    @patch("src.application.use_cases.auth.telegram_bot_link.consume_bot_link_token")
    async def test_expired_token_raises(self, mock_consume, use_case):
        mock_consume.return_value = None

        with pytest.raises(ValueError, match="Invalid or expired"):
            await use_case.execute("expired_token")

    @pytest.mark.unit
    @patch("src.application.use_cases.auth.telegram_bot_link.consume_bot_link_token")
    async def test_user_not_found_raises(self, mock_consume, use_case, mock_user_repo):
        mock_consume.return_value = 999999
        mock_user_repo.get_by_telegram_id.return_value = None

        with pytest.raises(ValueError, match="User not found"):
            await use_case.execute("valid_token")

    @pytest.mark.unit
    @patch("src.application.use_cases.auth.telegram_bot_link.consume_bot_link_token")
    async def test_inactive_user_raises(self, mock_consume, use_case, mock_user_repo, make_user):
        mock_consume.return_value = 123456789
        mock_user_repo.get_by_telegram_id.return_value = make_user(is_active=False)

        with pytest.raises(ValueError, match="deactivated"):
            await use_case.execute("valid_token")

    @pytest.mark.unit
    @patch("src.application.use_cases.auth.telegram_bot_link.consume_bot_link_token")
    async def test_token_consumed_atomically(self, mock_consume, use_case, mock_user_repo, make_user, mock_redis):
        mock_consume.return_value = 123456789
        mock_user_repo.get_by_telegram_id.return_value = make_user()

        await use_case.execute("my_token")

        mock_consume.assert_called_once_with(mock_redis, "my_token")
