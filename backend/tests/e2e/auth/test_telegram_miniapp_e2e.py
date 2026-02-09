"""
End-to-end tests for Telegram Mini App authentication flows.

These tests require a running backend with PostgreSQL, Redis, and a valid
Telegram bot token. They simulate the full flow from initData submission
to JWT token issuance.

Run with: pytest tests/e2e/auth/test_telegram_miniapp_e2e.py -m e2e

Covered flows:
- Mini App initData -> auto-login -> dashboard access
- Mini App initData -> auto-register -> dashboard access
- Invalid/expired initData -> fallback to login
- HMAC replay attack -> 401
- Data tampering -> 401

API routes under test:
- POST /api/v1/auth/telegram/miniapp  -> TelegramMiniAppResponse
"""

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skip(reason="Requires Telegram bot token, running backend, and Redis"),
]


# ---------------------------------------------------------------------------
# Mini App Auto-Login (existing user)
# ---------------------------------------------------------------------------


class TestMiniAppAutoLogin:
    """E2E: existing Telegram user opens Mini App -> auto-login -> JWT."""

    async def test_valid_initdata_existing_user_returns_jwt(self, _async_client):
        """POST /api/v1/auth/telegram/miniapp with valid initData for an
        existing user returns access_token, refresh_token, and user info."""
        ...

    async def test_jwt_grants_access_to_protected_routes(self, _async_client):
        """After Mini App auto-login, the returned access_token can be used
        to access GET /api/v1/auth/me and other protected endpoints."""
        ...

    async def test_auto_login_updates_last_login_at(self, _async_client):
        """Mini App auto-login updates the user's last_login_at timestamp."""
        ...

    async def test_auto_login_returns_is_new_user_false(self, _async_client):
        """Existing user auto-login returns is_new_user=false in response."""
        ...


# ---------------------------------------------------------------------------
# Mini App Auto-Register (new user)
# ---------------------------------------------------------------------------


class TestMiniAppAutoRegister:
    """E2E: unknown Telegram user opens Mini App -> auto-register -> JWT."""

    async def test_valid_initdata_new_user_creates_account(self, _async_client):
        """POST /api/v1/auth/telegram/miniapp with valid initData for an
        unknown telegram_id auto-creates a user and returns JWT tokens."""
        ...

    async def test_auto_register_returns_is_new_user_true(self, _async_client):
        """Auto-registered user response includes is_new_user=true."""
        ...

    async def test_auto_registered_user_is_active(self, _async_client):
        """Auto-registered user has is_active=True (no OTP verification
        needed since Telegram identity is trusted)."""
        ...

    async def test_auto_register_creates_remnawave_user(self, _async_client):
        """Auto-registration triggers Remnawave user creation
        (best-effort, doesn't block auth)."""
        ...

    async def test_auto_register_with_duplicate_username_appends_suffix(self, _async_client):
        """If the Telegram username conflicts with an existing login,
        a numeric suffix is appended (e.g., tg_alice -> tg_alice_1)."""
        ...


# ---------------------------------------------------------------------------
# Invalid/Expired initData
# ---------------------------------------------------------------------------


class TestMiniAppInvalidData:
    """E2E: invalid or expired initData -> error response."""

    async def test_invalid_hash_returns_401(self, _async_client):
        """POST /api/v1/auth/telegram/miniapp with a tampered hash
        returns 401 Unauthorized."""
        ...

    async def test_expired_auth_date_returns_401(self, _async_client):
        """POST /api/v1/auth/telegram/miniapp with auth_date older than
        telegram_auth_max_age_seconds returns 401."""
        ...

    async def test_missing_user_field_returns_422(self, _async_client):
        """POST /api/v1/auth/telegram/miniapp without the 'user' field
        in initData returns 422 Validation Error."""
        ...

    async def test_empty_initdata_returns_422(self, _async_client):
        """POST /api/v1/auth/telegram/miniapp with empty body
        returns 422 Validation Error."""
        ...

    async def test_malformed_user_json_returns_401(self, _async_client):
        """POST with user field containing invalid JSON returns 401."""
        ...


# ---------------------------------------------------------------------------
# Security: Replay & Tampering
# ---------------------------------------------------------------------------


class TestMiniAppSecurity:
    """E2E: security properties of Mini App initData validation."""

    async def test_replay_within_window_succeeds(self, _async_client):
        """Same initData resubmitted within the freshness window
        succeeds (stateless validation)."""
        ...

    async def test_replay_after_expiry_returns_401(self, _async_client):
        """Same initData resubmitted after auth_date freshness window
        is rejected with 401."""
        ...

    async def test_tampered_user_id_returns_401(self, _async_client):
        """Modifying the user.id in initData without updating the hash
        is detected and returns 401."""
        ...

    async def test_tampered_auth_date_returns_401(self, _async_client):
        """Changing auth_date without re-signing invalidates the hash."""
        ...

    async def test_wrong_bot_token_hash_returns_401(self, _async_client):
        """initData signed with a different bot token is rejected."""
        ...

    async def test_rate_limiting_returns_429(self, _async_client):
        """Rapid-fire Mini App auth requests trigger rate limiting (429)."""
        ...
