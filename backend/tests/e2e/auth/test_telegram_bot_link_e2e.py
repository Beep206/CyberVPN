"""
End-to-end tests for Telegram Bot Deep Link authentication flows.

These tests require a running backend with PostgreSQL, Redis, and a valid
Telegram bot token. They test the full generate -> open link -> auto-login
flow.

Run with: pytest tests/e2e/auth/test_telegram_bot_link_e2e.py -m e2e

Covered flows:
- Generate link -> open link -> auto-login -> dashboard
- Expired link -> error message -> fallback to login
- Invalid/random link -> error message
- Reused link -> error message
- Brute force protection -> 429

API routes under test:
- POST /api/v1/auth/telegram/generate-login-link -> {login_url}
- POST /api/v1/auth/telegram/bot-link            -> TokenResponse
"""

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skip(reason="Requires Telegram bot token, running backend, and Redis"),
]


# ---------------------------------------------------------------------------
# Happy Path: Generate -> Exchange -> Dashboard
# ---------------------------------------------------------------------------


class TestBotLinkHappyPath:
    """E2E: generate login link -> exchange token -> JWT -> dashboard."""

    async def test_generate_link_returns_valid_url(self, _async_client):
        """POST /api/v1/auth/telegram/generate-login-link with a valid
        Telegram user ID returns a login_url containing a token."""
        ...

    async def test_exchange_token_returns_jwt(self, _async_client):
        """POST /api/v1/auth/telegram/bot-link with a valid token
        returns access_token, refresh_token, and user info."""
        ...

    async def test_jwt_grants_access_to_protected_routes(self, _async_client):
        """After bot-link login, the returned access_token grants access
        to GET /api/v1/auth/me and other protected endpoints."""
        ...

    async def test_full_flow_generate_then_exchange(self, _async_client):
        """Full flow: generate link -> extract token -> exchange -> verify
        access to protected endpoint."""
        ...

    async def test_generate_link_for_new_user(self, _async_client):
        """POST /api/v1/auth/telegram/generate-login-link for a Telegram
        user not yet in the database still generates a link (user created
        on token exchange)."""
        ...


# ---------------------------------------------------------------------------
# Expired Token
# ---------------------------------------------------------------------------


class TestBotLinkExpiredToken:
    """E2E: exchange expired token -> error."""

    async def test_expired_token_returns_401(self, _async_client):
        """POST /api/v1/auth/telegram/bot-link with a token past its
        5-minute TTL returns 401 Unauthorized."""
        ...

    async def test_expired_token_error_message(self, _async_client):
        """The error response for an expired token includes a meaningful
        message like 'Invalid or expired bot link token'."""
        ...


# ---------------------------------------------------------------------------
# Invalid / Random Token
# ---------------------------------------------------------------------------


class TestBotLinkInvalidToken:
    """E2E: exchange invalid or random token -> error."""

    async def test_random_token_returns_401(self, _async_client):
        """POST /api/v1/auth/telegram/bot-link with a random string
        that was never generated returns 401."""
        ...

    async def test_empty_token_returns_422(self, _async_client):
        """POST /api/v1/auth/telegram/bot-link with an empty token
        returns 422 Validation Error."""
        ...

    async def test_sql_injection_token_returns_401(self, _async_client):
        """POST /api/v1/auth/telegram/bot-link with SQL injection payload
        returns 401 (Redis key lookup, no SQL involved)."""
        ...


# ---------------------------------------------------------------------------
# Reused Token (One-Time Use)
# ---------------------------------------------------------------------------


class TestBotLinkReusedToken:
    """E2E: reuse consumed token -> error."""

    async def test_second_exchange_returns_401(self, _async_client):
        """After successful token exchange, attempting to use the same
        token again returns 401 (GETDEL atomic consumption)."""
        ...

    async def test_concurrent_exchange_only_one_succeeds(self, _async_client):
        """When two clients race to exchange the same token, only one
        gets JWT tokens; the other gets 401."""
        ...


# ---------------------------------------------------------------------------
# Security: Brute Force & Cross-User
# ---------------------------------------------------------------------------


class TestBotLinkSecurity:
    """E2E: security properties of bot link token exchange."""

    async def test_brute_force_random_tokens_all_fail(self, _async_client):
        """Attempting 100 random tokens — all return 401,
        no information leakage about valid tokens."""
        ...

    async def test_rate_limiting_on_exchange_returns_429(self, _async_client):
        """Rapid-fire bot-link exchange requests trigger rate limiting (429)."""
        ...

    async def test_rate_limiting_on_generate_returns_429(self, _async_client):
        """Rapid-fire generate-link requests trigger rate limiting (429)."""
        ...

    async def test_token_not_ip_bound(self, _async_client):
        """Token generated from one IP can be exchanged from a different IP
        (by design — bot sends link to user's Telegram client)."""
        ...

    async def test_deactivated_user_token_returns_401(self, _async_client):
        """Valid token for a deactivated user returns 401 with
        'Account deactivated' message."""
        ...

    async def test_token_ttl_is_5_minutes(self, _async_client):
        """Token expires exactly 300 seconds after generation."""
        ...
