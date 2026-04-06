"""Integration tests for OAuth login HTTP routes."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.application.use_cases.auth.oauth_login import OAuthLoginResult
from src.config.settings import settings
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.oauth.errors import OAuthProviderUnavailableError
from src.infrastructure.remnawave.adapters import get_remnawave_adapter
from src.main import app
from src.presentation.dependencies.database import get_db
from src.presentation.dependencies.services import get_auth_service
from src.presentation.middleware.rate_limit import RateLimitMiddleware


@pytest.fixture
def oauth_route_dependencies():
    """Override OAuth route dependencies with in-memory doubles."""
    redis_client = AsyncMock()
    db = AsyncMock()
    auth_service = MagicMock()
    remnawave_adapter = MagicMock()

    async def override_db():
        yield db

    def override_redis():
        return redis_client

    def override_auth_service():
        return auth_service

    def override_remnawave_adapter():
        return remnawave_adapter

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_redis] = override_redis
    app.dependency_overrides[get_auth_service] = override_auth_service
    app.dependency_overrides[get_remnawave_adapter] = override_remnawave_adapter

    yield {
        "redis_client": redis_client,
        "db": db,
        "auth_service": auth_service,
        "remnawave_adapter": remnawave_adapter,
    }

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True, scope="session")
def _rate_limit_fail_open():
    """Keep route integration tests focused on OAuth contract, not Redis availability."""
    original = settings.rate_limit_fail_open
    object.__setattr__(settings, "rate_limit_fail_open", True)

    current = getattr(app, "middleware_stack", None)
    while current is not None:
        if isinstance(current, RateLimitMiddleware):
            current.fail_open = True
        current = getattr(current, "app", None)

    yield
    object.__setattr__(settings, "rate_limit_fail_open", original)


@pytest.fixture(autouse=True)
def _disable_rate_limit_middleware_for_route_contract_tests(monkeypatch):
    """Keep these tests focused on OAuth contract assertions, not Redis event-loop quirks."""

    async def passthrough(self, request, call_next):
        return await call_next(request)

    monkeypatch.setattr(RateLimitMiddleware, "dispatch", passthrough)


@pytest.fixture(autouse=True)
def _reset_circuit_breaker():
    """Avoid cross-test leakage from the shared rate-limit circuit breaker."""
    cb = RateLimitMiddleware._circuit_breaker
    if cb is not None:
        cb._failure_count = 0
        cb._state = cb.CLOSED
    yield


def _make_oauth_user(**overrides):
    payload = {
        "id": uuid4(),
        "login": "neo",
        "email": "neo@cybervpn.io",
        "is_active": True,
        "is_email_verified": True,
        "created_at": datetime.now(UTC),
        "role": "viewer",
        "totp_enabled": False,
    }
    payload.update(overrides)
    return SimpleNamespace(**payload)


class TestOAuthLoginRoutes:
    """Current route-level integration coverage for OAuth login."""

    @pytest.mark.integration
    async def test_google_authorize_returns_provider_url_and_state(
        self,
        async_client: AsyncClient,
        oauth_route_dependencies,
    ):
        with (
            patch("src.presentation.api.v1.oauth.routes.settings.oauth_web_base_url", "https://vpn.ozoxy.ru"),
            patch(
                "src.application.services.oauth_state_service.OAuthStateService.generate",
                new=AsyncMock(return_value=("csrf_state_123", "pkce_challenge_123")),
            ),
            patch(
                "src.infrastructure.oauth.google.GoogleOAuthProvider.authorize_url",
                return_value="https://accounts.google.com/o/oauth2/v2/auth?state=csrf_state_123",
            ) as mock_authorize_url,
        ):
            response = await async_client.get("/api/v1/oauth/google/login")

        assert response.status_code == 200
        assert response.json() == {
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth?state=csrf_state_123",
            "state": "csrf_state_123",
        }
        mock_authorize_url.assert_called_once_with(
            "https://vpn.ozoxy.ru/api/oauth/callback/google",
            state="csrf_state_123",
            code_challenge="pkce_challenge_123",
            code_challenge_method="S256",
        )

    @pytest.mark.integration
    async def test_google_callback_returns_tokens_and_sets_auth_cookies(
        self,
        async_client: AsyncClient,
        oauth_route_dependencies,
    ):
        user = _make_oauth_user()
        oauth_result = OAuthLoginResult(
            access_token="access_token_value",
            refresh_token="refresh_token_value",
            token_type="bearer",
            expires_in=3600,
            user=user,
            is_new_user=False,
        )

        with (
            patch("src.presentation.api.v1.oauth.routes.settings.oauth_web_base_url", "https://vpn.ozoxy.ru"),
            patch(
                "src.application.services.oauth_state_service.OAuthStateService.validate_and_consume",
                new=AsyncMock(return_value={"code_verifier": "verifier_123"}),
            ),
            patch(
                "src.infrastructure.oauth.google.GoogleOAuthProvider.exchange_code",
                new=AsyncMock(
                    return_value={
                        "id": "google_sub_123",
                        "email": "neo@cybervpn.io",
                        "username": "neo",
                        "access_token": "provider_access",
                    }
                ),
            ) as mock_exchange_code,
            patch(
                "src.presentation.api.v1.oauth.routes.OAuthLoginUseCase.execute",
                new=AsyncMock(return_value=oauth_result),
            ),
        ):
            response = await async_client.post(
                "/api/v1/oauth/google/login/callback",
                json={"code": "google_code_123", "state": "csrf_state_123"},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["access_token"] == "access_token_value"
        assert payload["refresh_token"] == "refresh_token_value"
        assert payload["requires_2fa"] is False
        assert payload["user"]["login"] == "neo"
        assert "access_token=access_token_value" in "\n".join(response.headers.get_list("set-cookie"))
        mock_exchange_code.assert_awaited_once_with(
            code="google_code_123",
            redirect_uri="https://vpn.ozoxy.ru/api/oauth/callback/google",
            code_verifier="verifier_123",
        )

    @pytest.mark.integration
    async def test_callback_returns_2fa_without_establishing_full_session(
        self,
        async_client: AsyncClient,
        oauth_route_dependencies,
    ):
        user = _make_oauth_user(totp_enabled=True)
        oauth_result = OAuthLoginResult(
            access_token="",
            refresh_token="",
            token_type="bearer",
            expires_in=0,
            user=user,
            is_new_user=False,
            requires_2fa=True,
            tfa_token="pending_2fa_token",
        )

        with (
            patch("src.presentation.api.v1.oauth.routes.settings.oauth_web_base_url", "https://vpn.ozoxy.ru"),
            patch(
                "src.application.services.oauth_state_service.OAuthStateService.validate_and_consume",
                new=AsyncMock(return_value={"code_verifier": "verifier_123"}),
            ),
            patch(
                "src.infrastructure.oauth.github.GitHubOAuthProvider.exchange_code",
                new=AsyncMock(
                    return_value={
                        "id": "github_123",
                        "email": "neo@cybervpn.io",
                        "username": "neo",
                        "access_token": "provider_access",
                    }
                ),
            ),
            patch(
                "src.presentation.api.v1.oauth.routes.OAuthLoginUseCase.execute",
                new=AsyncMock(return_value=oauth_result),
            ),
        ):
            response = await async_client.post(
                "/api/v1/oauth/github/login/callback",
                json={"code": "github_code_123", "state": "csrf_state_123"},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["requires_2fa"] is True
        assert payload["tfa_token"] == "pending_2fa_token"
        assert response.headers.get_list("set-cookie") == []

    @pytest.mark.integration
    async def test_callback_rejects_invalid_state(
        self,
        async_client: AsyncClient,
        oauth_route_dependencies,
    ):
        with (
            patch("src.presentation.api.v1.oauth.routes.settings.oauth_web_base_url", "https://vpn.ozoxy.ru"),
            patch(
                "src.application.services.oauth_state_service.OAuthStateService.validate_and_consume",
                new=AsyncMock(return_value=None),
            ),
        ):
            response = await async_client.post(
                "/api/v1/oauth/google/login/callback",
                json={"code": "google_code_123", "state": "tampered_state"},
            )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid or expired OAuth state."

    @pytest.mark.integration
    async def test_callback_returns_collision_for_untrusted_auto_link(
        self,
        async_client: AsyncClient,
        oauth_route_dependencies,
    ):
        with (
            patch("src.presentation.api.v1.oauth.routes.settings.oauth_web_base_url", "https://vpn.ozoxy.ru"),
            patch(
                "src.presentation.api.v1.oauth.routes.settings.oauth_enabled_login_providers",
                ["google", "github", "discord", "facebook"],
            ),
            patch(
                "src.application.services.oauth_state_service.OAuthStateService.validate_and_consume",
                new=AsyncMock(return_value={"validated": True}),
            ),
            patch(
                "src.infrastructure.oauth.facebook.FacebookOAuthProvider.exchange_code",
                new=AsyncMock(
                    return_value={
                        "id": "facebook_123",
                        "email": "existing@example.com",
                        "username": "neo",
                        "access_token": "provider_access",
                    }
                ),
            ),
            patch(
                "src.presentation.api.v1.oauth.routes.OAuthLoginUseCase.execute",
                new=AsyncMock(
                    side_effect=ValueError(
                        "Automatic account linking is disabled for this provider email. "
                        "Sign in with your existing account and link the provider manually."
                    )
                ),
            ),
        ):
            response = await async_client.post(
                "/api/v1/oauth/facebook/login/callback",
                json={"code": "facebook_code_123", "state": "csrf_state_123"},
            )

        assert response.status_code == 409
        assert "Automatic account linking is disabled" in response.json()["detail"]

    @pytest.mark.integration
    async def test_callback_returns_503_when_google_is_temporarily_unavailable(
        self,
        async_client: AsyncClient,
        oauth_route_dependencies,
    ):
        with (
            patch("src.presentation.api.v1.oauth.routes.settings.oauth_web_base_url", "https://vpn.ozoxy.ru"),
            patch(
                "src.application.services.oauth_state_service.OAuthStateService.validate_and_consume",
                new=AsyncMock(return_value={"code_verifier": "verifier_123"}),
            ),
            patch(
                "src.infrastructure.oauth.google.GoogleOAuthProvider.exchange_code",
                new=AsyncMock(side_effect=OAuthProviderUnavailableError("Google OAuth provider is temporarily unavailable")),
            ),
        ):
            response = await async_client.post(
                "/api/v1/oauth/google/login/callback",
                json={"code": "google_code_123", "state": "csrf_state_123"},
            )

        assert response.status_code == 503
        assert response.json()["detail"] == "Google OAuth provider is temporarily unavailable"
