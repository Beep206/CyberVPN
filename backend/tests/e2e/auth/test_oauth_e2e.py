"""Staging-oriented OAuth E2E specifications.

These tests remain skip-marked until the project wires real provider
credentials, browser automation, and staging infrastructure into CI.
The scenarios below document the current backend contract that the
Next.js BFF depends on for web OAuth login.
"""

import pytest
from httpx import AsyncClient

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skip(
        reason=(
            "Requires real provider registrations, staging callback URIs, "
            "Redis/PostgreSQL, and browser-assisted consent flows."
        )
    ),
]


class TestOAuthAuthorizeEndpoints:
    """Backend authorize endpoints used by the frontend BFF start routes."""

    async def test_google_login_authorize_uses_canonical_web_callback(self, async_client: AsyncClient):
        """`GET /api/v1/oauth/google/login` returns a Google authorize URL whose
        redirect URI matches `{OAUTH_WEB_BASE_URL}/api/oauth/callback/google`."""
        ...

    async def test_github_login_authorize_includes_pkce(self, async_client: AsyncClient):
        """GitHub authorize responses include `code_challenge` and
        `code_challenge_method=S256`."""
        ...

    async def test_discord_login_authorize_uses_state_only_contract(self, async_client: AsyncClient):
        """Discord authorize responses stay aligned with the current state-based
        rollout contract and exact web callback URI."""
        ...

    async def test_facebook_login_authorize_uses_exact_callback(self, async_client: AsyncClient):
        """Facebook authorize responses resolve the canonical non-localized web
        callback URI and never a locale-prefixed callback path."""
        ...

    async def test_microsoft_login_authorize_includes_pkce(self, async_client: AsyncClient):
        """Microsoft authorize responses include PKCE and the exact web callback URI."""
        ...

    async def test_twitter_login_authorize_uses_internal_twitter_slug(self, async_client: AsyncClient):
        """X uses the internal backend slug `twitter`, so the callback URI ends with
        `/api/oauth/callback/twitter`."""
        ...


class TestOAuthCallbackOutcomes:
    """Backend callback outcomes consumed by the frontend BFF callback routes."""

    async def test_google_callback_can_create_new_user(self, async_client: AsyncClient):
        """A first Google login creates a local user, links the OAuth account,
        and returns JWT tokens with `is_new_user=true`."""
        ...

    async def test_github_callback_can_login_existing_linked_account(self, async_client: AsyncClient):
        """A repeat GitHub login for an already linked account returns a normal
        authenticated session without creating a new user."""
        ...

    async def test_google_callback_auto_links_verified_existing_email(self, async_client: AsyncClient):
        """Google may auto-link an existing local account only when verified ID-token
        claims satisfy the trusted-email policy."""
        ...

    async def test_discord_callback_rejects_unverified_email(self, async_client: AsyncClient):
        """Discord login fails when the provider email is missing or unverified."""
        ...

    async def test_facebook_callback_returns_collision_for_existing_local_email(self, async_client: AsyncClient):
        """Facebook must not auto-link by email; existing local accounts surface a
        collision or linking-required response."""
        ...

    async def test_twitter_callback_returns_collision_for_existing_local_email(self, async_client: AsyncClient):
        """X must not auto-link by email in the current rollout."""
        ...

    async def test_callback_with_tampered_state_returns_401(self, async_client: AsyncClient):
        """A callback with tampered or expired OAuth state is rejected with 401."""
        ...

    async def test_callback_can_require_two_factor_without_full_session(self, async_client: AsyncClient):
        """When the user has TOTP enabled, the callback returns `requires_2fa=true`
        and `tfa_token` without establishing the full auth cookie session."""
        ...


class TestTokenRetentionAndSecurity:
    """Provider-token and storage expectations for staging verification."""

    async def test_login_only_flow_does_not_retain_provider_tokens_by_default(self, async_client: AsyncClient):
        """After login-only OAuth completion, persisted provider access/refresh tokens
        remain empty unless explicit retention allowlists are configured."""
        ...

    async def test_retained_provider_tokens_are_encrypted_when_key_is_configured(self, async_client: AsyncClient):
        """If retention is enabled for a provider, database rows use encrypted token
        storage rather than plaintext persistence."""
        ...
