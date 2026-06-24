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
from sqlalchemy import select

from src.application.services.auth_service import AuthService
from src.application.use_cases.auth.telegram_miniapp import (
    TelegramMiniAppResult,
    TelegramMiniAppUseCase,
)
from src.config.settings import settings
from src.infrastructure.database.models.admin_user_model import AdminUserModel
from src.infrastructure.database.models.principal_session_model import PrincipalSessionModel
from src.infrastructure.database.models.refresh_token_model import RefreshToken
from src.infrastructure.remnawave.adapters import get_remnawave_adapter
from src.main import app
from src.presentation.api.v1.mobile_auth.routes import _get_subscription_client
from src.presentation.dependencies.database import get_db

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


def _make_replay_guard() -> AsyncMock:
    guard = AsyncMock()
    guard.accept.return_value = None
    return guard


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
            replay_guard=_make_replay_guard(),
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
            replay_guard=_make_replay_guard(),
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
            replay_guard=_make_replay_guard(),
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
            replay_guard=_make_replay_guard(),
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
            replay_guard=_make_replay_guard(),
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
            replay_guard=_make_replay_guard(),
            remnawave_gateway=remnawave,
        )

        init_data = _build_init_data(BOT_TOKEN)
        result = await use_case.execute(init_data)

        # Auth succeeds despite Remnawave failure
        assert result.access_token == "access_tok"
        assert result.is_new_user is True


@pytest.mark.integration
async def test_miniapp_route_persists_returned_customer_session_and_revokes_access_on_logout(
    async_client,
    db,
    monkeypatch: pytest.MonkeyPatch,
):
    telegram_id = 900_000_000 + int(uuid.uuid4().hex[:6], 16) % 100_000_000
    username = f"miniapp_{uuid.uuid4().hex[:8]}"
    init_data = _build_init_data(
        BOT_TOKEN,
        user={"id": telegram_id, "first_name": "Mini", "username": username},
    )
    device_key = "123e4567-e89b-12d3-a456-426614174000"

    async def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_remnawave_adapter] = lambda: None
    app.dependency_overrides[_get_subscription_client] = lambda: None
    monkeypatch.setattr(settings, "registration_enabled", True)

    try:
        with patch("src.infrastructure.oauth.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token.get_secret_value.return_value = BOT_TOKEN
            mock_settings.telegram_bot_username = "test_bot"
            mock_settings.telegram_auth_max_age_seconds = 86400

            async_client.cookies.set(settings.web_device_cookie_name, device_key)
            response = await async_client.post(
                "/api/v1/auth/telegram/miniapp",
                json={"init_data": init_data},
            )

        assert response.status_code == 200
        payload = response.json()
        access_token = payload["access_token"]
        refresh_token = payload["refresh_token"]

        token_payload = AuthService().decode_token(access_token, audience="cybervpn:customer")
        refresh_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        refresh_record = (
            await db.execute(select(RefreshToken).where(RefreshToken.token_hash == refresh_hash))
        ).scalar_one()
        assert refresh_record.principal_session_id is not None
        principal_session = await db.get(PrincipalSessionModel, refresh_record.principal_session_id)
        assert principal_session is not None
        assert principal_session.access_token_jti == token_payload["jti"]
        assert principal_session.principal_class == "customer"
        assert principal_session.principal_subject == token_payload["sub"]
        assert principal_session.revoked_at is None

        logout_response = await async_client.post(
            "/api/v1/mobile/auth/logout",
            json={"refresh_token": refresh_token, "device_id": device_key},
        )
        assert logout_response.status_code == 204

        stale_access_response = await async_client.get(
            "/api/v1/mobile/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert stale_access_response.status_code == 401

        await db.refresh(principal_session)
        await db.refresh(refresh_record)
        assert principal_session.status == "revoked"
        assert refresh_record.revoked_at is not None
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_remnawave_adapter, None)
        app.dependency_overrides.pop(_get_subscription_client, None)
