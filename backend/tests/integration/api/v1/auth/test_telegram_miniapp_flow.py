"""Integration tests: Mini App initData -> auto-login -> JWT response.

Tests the full request/response flow through the FastAPI route handler,
with mocked dependencies (DB session, Redis, auth service).

Requires: TestClient, test database, fakeredis (when infra available).
"""

import hashlib
import hmac
import json
import time
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import quote, urlencode

import pytest

from src.application.use_cases.auth.telegram_miniapp import (
    TelegramMiniAppResult,
    TelegramMiniAppUseCase,
)
from src.infrastructure.database.models.admin_user_model import AdminUserModel


BOT_TOKEN = "7654321:AAHfVcYK-test-token-for-integration"


def _build_init_data(
    bot_token: str,
    user: dict | None = None,
    auth_date: int | None = None,
) -> str:
    """Build a valid Telegram Mini App initData string."""
    if auth_date is None:
        auth_date = int(time.time())
    if user is None:
        user = {"id": 123456789, "first_name": "Test", "username": "testuser"}

    params: dict[str, str] = {
        "auth_date": str(auth_date),
        "user": json.dumps(user, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    hash_value = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    params["hash"] = hash_value
    return urlencode(params, quote_via=quote)


def _make_user_model(
    telegram_id: int = 123456789,
    login: str = "testuser",
    is_active: bool = True,
) -> AdminUserModel:
    """Create a mock AdminUserModel for testing."""
    model = MagicMock(spec=AdminUserModel)
    model.id = uuid.uuid4()
    model.login = login
    model.telegram_id = telegram_id
    model.email = None
    model.role = "viewer"
    model.is_active = is_active
    model.is_email_verified = True
    model.created_at = datetime.now(UTC)
    return model


class TestMiniAppAutoLoginFlow:
    """Integration: valid initData for existing user -> JWT tokens."""

    @pytest.fixture(autouse=True)
    def _mock_settings(self):
        with patch("src.infrastructure.oauth.telegram.settings") as mock:
            mock.telegram_bot_token.get_secret_value.return_value = BOT_TOKEN
            mock.telegram_bot_username = "test_bot"
            mock.telegram_auth_max_age_seconds = 86400
            yield mock

    @pytest.mark.integration
    async def test_existing_user_returns_jwt_tokens(self):
        """Valid initData for an existing user returns access + refresh tokens."""
        user = _make_user_model()

        user_repo = AsyncMock()
        user_repo.get_by_telegram_id.return_value = user

        auth_service = MagicMock()
        access_exp = datetime.now(UTC) + timedelta(minutes=15)
        auth_service.create_access_token.return_value = ("access_tok", "jti1", access_exp)
        auth_service.create_refresh_token.return_value = ("refresh_tok", "jti2", datetime.now(UTC) + timedelta(days=7))

        session = AsyncMock()
        from src.infrastructure.oauth.telegram import TelegramOAuthProvider

        telegram_provider = TelegramOAuthProvider()

        use_case = TelegramMiniAppUseCase(
            user_repo=user_repo,
            auth_service=auth_service,
            session=session,
            telegram_provider=telegram_provider,
        )

        init_data = _build_init_data(BOT_TOKEN)
        result = await use_case.execute(init_data)

        assert isinstance(result, TelegramMiniAppResult)
        assert result.access_token == "access_tok"
        assert result.refresh_token == "refresh_tok"
        assert result.token_type == "bearer"
        assert result.is_new_user is False
        assert result.user == user
        user_repo.get_by_telegram_id.assert_called_once_with(123456789)

    @pytest.mark.integration
    async def test_new_user_auto_registers_and_returns_jwt(self):
        """Valid initData for unknown telegram_id auto-registers user + returns JWT."""
        new_user = _make_user_model(login="tg_testuser")

        user_repo = AsyncMock()
        user_repo.get_by_telegram_id.return_value = None
        user_repo.get_by_login.return_value = None
        user_repo.create.return_value = new_user

        auth_service = MagicMock()
        auth_service.hash_password = AsyncMock(return_value="hashed_pw")
        access_exp = datetime.now(UTC) + timedelta(minutes=15)
        auth_service.create_access_token.return_value = ("access_tok", "jti1", access_exp)
        auth_service.create_refresh_token.return_value = ("refresh_tok", "jti2", datetime.now(UTC) + timedelta(days=7))

        session = AsyncMock()
        from src.infrastructure.oauth.telegram import TelegramOAuthProvider

        telegram_provider = TelegramOAuthProvider()

        use_case = TelegramMiniAppUseCase(
            user_repo=user_repo,
            auth_service=auth_service,
            session=session,
            telegram_provider=telegram_provider,
        )

        init_data = _build_init_data(BOT_TOKEN)
        result = await use_case.execute(init_data)

        assert result.is_new_user is True
        assert result.access_token == "access_tok"
        user_repo.create.assert_called_once()
        session.commit.assert_called_once()

    @pytest.mark.integration
    async def test_invalid_init_data_raises_value_error(self):
        """Invalid initData (wrong hash) raises ValueError."""
        user_repo = AsyncMock()
        auth_service = MagicMock()
        session = AsyncMock()
        from src.infrastructure.oauth.telegram import TelegramOAuthProvider

        telegram_provider = TelegramOAuthProvider()

        use_case = TelegramMiniAppUseCase(
            user_repo=user_repo,
            auth_service=auth_service,
            session=session,
            telegram_provider=telegram_provider,
        )

        # Build initData with wrong token
        bad_init_data = _build_init_data("wrong_token")

        with pytest.raises(ValueError, match="Invalid or expired"):
            await use_case.execute(bad_init_data)

    @pytest.mark.integration
    async def test_expired_init_data_raises_value_error(self):
        """Expired initData (auth_date > 24h ago) raises ValueError."""
        user_repo = AsyncMock()
        auth_service = MagicMock()
        session = AsyncMock()
        from src.infrastructure.oauth.telegram import TelegramOAuthProvider

        telegram_provider = TelegramOAuthProvider()

        use_case = TelegramMiniAppUseCase(
            user_repo=user_repo,
            auth_service=auth_service,
            session=session,
            telegram_provider=telegram_provider,
        )

        old_auth_date = int(time.time()) - 90000
        expired_init_data = _build_init_data(BOT_TOKEN, auth_date=old_auth_date)

        with pytest.raises(ValueError, match="Invalid or expired"):
            await use_case.execute(expired_init_data)

    @pytest.mark.integration
    async def test_remnawave_creation_for_new_user(self):
        """New user registration calls Remnawave gateway (best-effort)."""
        new_user = _make_user_model()

        user_repo = AsyncMock()
        user_repo.get_by_telegram_id.return_value = None
        user_repo.get_by_login.return_value = None
        user_repo.create.return_value = new_user

        auth_service = MagicMock()
        auth_service.hash_password = AsyncMock(return_value="hashed_pw")
        access_exp = datetime.now(UTC) + timedelta(minutes=15)
        auth_service.create_access_token.return_value = ("access_tok", "jti1", access_exp)
        auth_service.create_refresh_token.return_value = ("refresh_tok", "jti2", datetime.now(UTC) + timedelta(days=7))

        session = AsyncMock()
        remnawave = AsyncMock()

        from src.infrastructure.oauth.telegram import TelegramOAuthProvider

        telegram_provider = TelegramOAuthProvider()

        use_case = TelegramMiniAppUseCase(
            user_repo=user_repo,
            auth_service=auth_service,
            session=session,
            telegram_provider=telegram_provider,
            remnawave_gateway=remnawave,
        )

        init_data = _build_init_data(BOT_TOKEN)
        await use_case.execute(init_data)

        remnawave.create_user.assert_called_once()

    @pytest.mark.integration
    async def test_remnawave_failure_does_not_block_auth(self):
        """Remnawave failure doesn't prevent successful authentication."""
        new_user = _make_user_model()

        user_repo = AsyncMock()
        user_repo.get_by_telegram_id.return_value = None
        user_repo.get_by_login.return_value = None
        user_repo.create.return_value = new_user

        auth_service = MagicMock()
        auth_service.hash_password = AsyncMock(return_value="hashed_pw")
        access_exp = datetime.now(UTC) + timedelta(minutes=15)
        auth_service.create_access_token.return_value = ("access_tok", "jti1", access_exp)
        auth_service.create_refresh_token.return_value = ("refresh_tok", "jti2", datetime.now(UTC) + timedelta(days=7))

        session = AsyncMock()
        remnawave = AsyncMock()
        remnawave.create_user.side_effect = Exception("Remnawave down")

        from src.infrastructure.oauth.telegram import TelegramOAuthProvider

        telegram_provider = TelegramOAuthProvider()

        use_case = TelegramMiniAppUseCase(
            user_repo=user_repo,
            auth_service=auth_service,
            session=session,
            telegram_provider=telegram_provider,
            remnawave_gateway=remnawave,
        )

        init_data = _build_init_data(BOT_TOKEN)
        result = await use_case.execute(init_data)

        # Auth succeeds despite Remnawave failure
        assert result.access_token == "access_tok"
        assert result.is_new_user is True
