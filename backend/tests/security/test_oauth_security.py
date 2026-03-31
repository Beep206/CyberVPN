"""Security tests for OAuth validation (CRIT-2).

Tests that:
1. Telegram HMAC validation rejects forged data
2. State parameter protects against CSRF
"""

import hashlib
import hmac
import time
from unittest.mock import AsyncMock, patch

import pytest


class TestTelegramHMACValidation:
    """Test Telegram HMAC-SHA256 signature validation."""

    def test_valid_hmac_signature_passes(self):
        """Valid HMAC signature passes validation."""
        from src.infrastructure.oauth.telegram import TelegramOAuthProvider

        with patch("src.infrastructure.oauth.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token.get_secret_value.return_value = "test_token"
            mock_settings.telegram_bot_username = "testbot"
            mock_settings.telegram_auth_max_age_seconds = 86400

            provider = TelegramOAuthProvider()

            # Create valid auth data
            auth_data = {
                "id": "123456",
                "first_name": "Test",
                "auth_date": str(int(time.time())),
            }

            # Calculate valid hash
            data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(auth_data.items()))
            secret_key = hashlib.sha256(b"test_token").digest()
            valid_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

            auth_data["hash"] = valid_hash

            assert provider._verify_telegram_auth(auth_data) is True

    def test_invalid_hmac_signature_fails(self):
        """Forged HMAC signature fails validation."""
        from src.infrastructure.oauth.telegram import TelegramOAuthProvider

        with patch("src.infrastructure.oauth.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token.get_secret_value.return_value = "test_token"
            mock_settings.telegram_bot_username = "testbot"
            mock_settings.telegram_auth_max_age_seconds = 86400

            provider = TelegramOAuthProvider()

            auth_data = {
                "id": "123456",
                "first_name": "Test",
                "auth_date": str(int(time.time())),
                "hash": "invalid_forged_hash_that_should_not_work",
            }

            assert provider._verify_telegram_auth(auth_data) is False

    def test_missing_hash_fails(self):
        """Missing hash fails validation."""
        from src.infrastructure.oauth.telegram import TelegramOAuthProvider

        with patch("src.infrastructure.oauth.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token.get_secret_value.return_value = "test_token"
            mock_settings.telegram_bot_username = "testbot"
            mock_settings.telegram_auth_max_age_seconds = 86400

            provider = TelegramOAuthProvider()

            auth_data = {
                "id": "123456",
                "first_name": "Test",
                "auth_date": str(int(time.time())),
                # No hash field
            }

            assert provider._verify_telegram_auth(auth_data) is False

    def test_old_auth_date_fails(self):
        """Auth date older than max age fails."""
        from src.infrastructure.oauth.telegram import TelegramOAuthProvider

        with patch("src.infrastructure.oauth.telegram.settings") as mock_settings:
            mock_settings.telegram_bot_token.get_secret_value.return_value = "test_token"
            mock_settings.telegram_bot_username = "testbot"
            mock_settings.telegram_auth_max_age_seconds = 86400  # 24 hours

            provider = TelegramOAuthProvider()

            # Auth date from 2 days ago
            old_auth_date = str(int(time.time()) - (2 * 86400))

            auth_data = {
                "id": "123456",
                "first_name": "Test",
                "auth_date": old_auth_date,
            }

            assert provider._verify_auth_date(auth_data) is False


class TestOAuthStateService:
    """Test OAuth state service for CSRF protection."""

    @pytest.mark.asyncio
    async def test_generate_creates_state_in_redis(self):
        """State generation stores data in Redis."""
        from src.application.services.oauth_state_service import OAuthStateService

        mock_redis = AsyncMock()
        service = OAuthStateService(mock_redis)

        state, code_challenge = await service.generate(
            provider="github",
            user_id="user-123",
            ip_address="1.2.3.4",
        )

        assert len(state) > 20  # Should be a secure random token
        assert code_challenge is None  # No PKCE by default
        mock_redis.setex.assert_called_once()


class TestOAuthLoginRedirectContract:
    """Test server-owned redirect resolution for OAuth login flow."""

    def test_builds_canonical_web_callback_from_configured_base_url(self):
        """Web login flow must use the configured same-origin callback path."""
        from src.presentation.api.v1.oauth.routes import _build_oauth_web_callback_uri

        with patch("src.presentation.api.v1.oauth.routes.settings") as mock_settings:
            mock_settings.oauth_web_base_url = "https://vpn.ozoxy.ru"

            assert _build_oauth_web_callback_uri("google") == "https://vpn.ozoxy.ru/api/oauth/callback/google"

    def test_allows_exact_native_redirect_uri_override(self):
        """Explicit native/universal callback URIs are allowed only by exact match."""
        from src.presentation.api.v1.oauth.routes import _resolve_oauth_login_redirect_uri

        with patch("src.presentation.api.v1.oauth.routes.settings") as mock_settings:
            mock_settings.oauth_web_base_url = "https://vpn.ozoxy.ru"
            mock_settings.oauth_allowed_redirect_uris = ["cybervpn://oauth/callback"]

            assert (
                _resolve_oauth_login_redirect_uri("github", "cybervpn://oauth/callback")
                == "cybervpn://oauth/callback"
            )

    def test_rejects_browser_supplied_web_redirect_uri_override(self):
        """Arbitrary browser-supplied web callback URIs must not be trusted."""
        from src.presentation.api.v1.oauth.routes import _resolve_oauth_login_redirect_uri

        with patch("src.presentation.api.v1.oauth.routes.settings") as mock_settings:
            mock_settings.oauth_web_base_url = "https://vpn.ozoxy.ru"
            mock_settings.oauth_allowed_redirect_uris = ["cybervpn://oauth/callback"]

            with pytest.raises(Exception) as exc_info:
                _resolve_oauth_login_redirect_uri("google", "https://vpn.ozoxy.ru/en-EN/oauth/callback")

            assert getattr(exc_info.value, "status_code", None) == 400

    def test_rejects_web_flow_when_canonical_origin_is_not_configured(self):
        """Server-owned web flow must fail closed if callback origin is missing."""
        from src.presentation.api.v1.oauth.routes import _resolve_oauth_login_redirect_uri

        with patch("src.presentation.api.v1.oauth.routes.settings") as mock_settings:
            mock_settings.oauth_web_base_url = ""
            mock_settings.oauth_allowed_redirect_uris = ["cybervpn://oauth/callback"]

            with pytest.raises(Exception) as exc_info:
                _resolve_oauth_login_redirect_uri("discord", None)

            assert getattr(exc_info.value, "status_code", None) == 503


class TestOAuthLoginProviderAvailability:
    """Test active login provider gating."""

    def test_apple_provider_stays_in_code_but_is_disabled_for_login(self):
        """Apple remains supported in code but is blocked from the active login flow."""
        from src.presentation.api.v1.oauth.routes import _is_oauth_login_provider_enabled

        assert _is_oauth_login_provider_enabled("apple") is False

    def test_facebook_provider_is_enabled_for_login(self):
        """Facebook is part of the active login provider set."""
        from src.presentation.api.v1.oauth.routes import _is_oauth_login_provider_enabled

        assert _is_oauth_login_provider_enabled("facebook") is True


class TestOAuthTokenRetentionPolicy:
    """Test minimum-retention policy for provider secrets."""

    def test_login_only_flow_does_not_persist_provider_tokens_by_default(self):
        """Access/refresh tokens are dropped unless a provider is explicitly allowlisted."""
        from src.shared.security.oauth_token_store import build_stored_oauth_tokens

        with patch("src.shared.security.oauth_token_store.settings") as mock_settings:
            mock_settings.oauth_retained_access_token_providers = []
            mock_settings.oauth_retained_refresh_token_providers = []

            stored = build_stored_oauth_tokens(
                provider="google",
                access_token="provider_access",
                refresh_token="provider_refresh",
            )

        assert stored.access_token is None
        assert stored.refresh_token is None

    def test_allowlisted_refresh_token_is_retained_for_future_product_use(self):
        """Refresh retention is opt-in and isolated by provider name."""
        from src.shared.security.oauth_token_store import build_stored_oauth_tokens

        with patch("src.shared.security.oauth_token_store.settings") as mock_settings:
            mock_settings.oauth_retained_access_token_providers = []
            mock_settings.oauth_retained_refresh_token_providers = ["microsoft"]

            stored = build_stored_oauth_tokens(
                provider="microsoft",
                access_token="provider_access",
                refresh_token="provider_refresh",
            )

        assert stored.access_token is None
        assert stored.refresh_token == "provider_refresh"
