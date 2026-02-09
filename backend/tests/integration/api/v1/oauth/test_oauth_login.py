"""Integration tests for OAuth login routes.

These tests verify the full HTTP request/response cycle for:
- GET /api/v1/oauth/{provider}/login (authorize URL)
- POST /api/v1/oauth/{provider}/login/callback (token exchange)

Requires: TestClient, test database, fakeredis.
"""

import pytest

# TODO: Import TestClient setup when integration test infrastructure is available
# from tests.conftest import async_client, test_db


class TestOAuthLoginRoutes:
    """Integration tests for OAuth login HTTP endpoints."""

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_google_authorize_returns_url_and_state(self):
        """GET /api/v1/oauth/google/login returns authorize_url and state."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_discord_authorize_returns_url_and_state(self):
        """GET /api/v1/oauth/discord/login returns authorize_url and state."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_callback_with_valid_code_returns_tokens(self):
        """POST /api/v1/oauth/google/login/callback with mocked provider returns tokens."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_callback_creates_new_user_when_no_match(self):
        """Callback for unknown email creates a new user account."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_callback_auto_links_existing_email_user(self):
        """Callback auto-links when email matches existing user."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_callback_returns_2fa_when_totp_enabled(self):
        """Callback returns requires_2fa=true for users with TOTP."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_unsupported_provider_returns_404(self):
        """Request to unsupported provider returns 404."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_rate_limiting_on_callback(self):
        """Rapid callback requests trigger rate limiting."""
        pass


class TestTelegramOAuthRegistrationFlow:
    """Integration tests for Telegram OAuth registration flow.

    Tests the full flow: Telegram callback -> new user created ->
    is_email_verified=True -> JWT issued -> no OTP dispatch.
    """

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_telegram_new_user_created_with_verified_email(self):
        """Telegram callback for new user creates user with is_email_verified=True, is_active=True."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_telegram_new_user_gets_jwt_tokens(self):
        """Telegram new user registration returns valid JWT access and refresh tokens."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_telegram_existing_user_login_returns_tokens(self):
        """Telegram callback for existing linked user returns JWT tokens."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_telegram_email_match_auto_links_account(self):
        """Telegram user with matching email auto-links to existing user."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_telegram_remnawave_user_created_on_registration(self):
        """Telegram registration triggers Remnawave user creation."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_telegram_new_user_returns_is_new_user_true(self):
        """Telegram callback for new registration returns is_new_user=true in response."""
        pass

    @pytest.mark.integration
    @pytest.mark.skip(reason="Integration test infrastructure not yet available")
    async def test_telegram_existing_user_returns_is_new_user_false(self):
        """Telegram callback for existing user returns is_new_user=false."""
        pass
