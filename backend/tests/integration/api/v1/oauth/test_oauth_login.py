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
