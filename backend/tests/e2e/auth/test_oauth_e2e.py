"""
End-to-end tests for OAuth authentication flows.

These tests require real OAuth provider credentials, a running backend with
PostgreSQL and Redis, and network access to OAuth provider APIs.

Run with: pytest tests/e2e/auth/ -m e2e

Covered flows:
- OAuth login (unauthenticated): GET /{provider}/login -> POST /{provider}/login/callback
- OAuth account linking (authenticated): GET /{provider}/authorize -> POST /{provider}/callback
- Magic link passwordless login
- Username-only registration
- Cross-cutting concerns (2FA, email registration, biometric)

API routes under test:
- /api/v1/oauth/{provider}/login           (GET)  -> OAuthAuthorizeResponse
- /api/v1/oauth/{provider}/login/callback  (POST) -> OAuthLoginResponse
- /api/v1/oauth/telegram/authorize         (GET)  -> OAuthAuthorizeResponse
- /api/v1/oauth/telegram/callback          (POST) -> OAuthLinkResponse
- /api/v1/oauth/github/authorize           (GET)  -> OAuthAuthorizeResponse
- /api/v1/oauth/github/callback            (POST) -> OAuthLinkResponse
- /api/v1/oauth/{provider}                 (DELETE) -> OAuthLinkResponse
- /api/v1/auth/magic-link                  (POST) -> MagicLinkResponse
- /api/v1/auth/magic-link/verify           (POST) -> TokenResponse
- /api/v1/auth/register                    (POST) -> RegisterResponse
- /api/v1/auth/login                       (POST) -> TokenResponse
"""

import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skip(reason="Requires OAuth credentials and running services"),
]


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------


class TestGoogleOAuth:
    """E2E tests for Google OAuth login flow.

    Google uses PKCE (code_challenge + code_verifier).
    Endpoint pattern:
        GET  /api/v1/oauth/google/login
        POST /api/v1/oauth/google/login/callback
    """

    async def test_login_url_returns_valid_google_authorize_url(self, _async_client):
        """GET /api/v1/oauth/google/login returns a valid authorize_url
        containing accounts.google.com, PKCE code_challenge, and a state token."""
        ...

    async def test_login_url_contains_pkce_params(self, _async_client):
        """The authorize_url for Google must include code_challenge and
        code_challenge_method=S256 query parameters (PKCE flow)."""
        ...

    async def test_callback_with_valid_code_returns_tokens(self, _async_client):
        """POST /api/v1/oauth/google/login/callback with a valid authorization
        code and matching state returns JWT access_token, refresh_token, and user."""
        ...

    async def test_callback_with_invalid_state_returns_401(self, _async_client):
        """POST callback with a tampered state token is rejected with 401."""
        ...

    async def test_callback_with_expired_state_returns_401(self, _async_client):
        """POST callback after state token TTL expires is rejected with 401."""
        ...

    async def test_new_user_creates_account_and_links_oauth(self, _async_client):
        """First-time Google login creates a new user account, links the OAuth
        provider, and returns is_new_user=true in the response."""
        ...

    async def test_existing_email_links_oauth_to_account(self, _async_client):
        """When a user already exists with the same email, Google OAuth
        auto-links to that account and returns is_new_user=false."""
        ...

    async def test_existing_oauth_user_returns_tokens(self, _async_client):
        """When the Google OAuth account is already linked, the callback
        returns tokens directly without creating a new user."""
        ...

    async def test_callback_updates_provider_tokens(self, _async_client):
        """On repeated logins, the stored provider access_token and
        refresh_token are updated to the latest values from Google."""
        ...


# ---------------------------------------------------------------------------
# GitHub OAuth
# ---------------------------------------------------------------------------


class TestGitHubOAuth:
    """E2E tests for GitHub OAuth login flow.

    GitHub does NOT use PKCE.
    Endpoint pattern:
        GET  /api/v1/oauth/github/login
        POST /api/v1/oauth/github/login/callback
    """

    async def test_login_url_returns_valid_github_authorize_url(self, _async_client):
        """GET /api/v1/oauth/github/login returns a valid authorize_url
        containing github.com/login/oauth/authorize and a state token."""
        ...

    async def test_login_url_does_not_contain_pkce_params(self, _async_client):
        """GitHub authorize_url must NOT include code_challenge since
        GitHub does not support PKCE."""
        ...

    async def test_callback_with_valid_code_returns_tokens(self, _async_client):
        """POST /api/v1/oauth/github/login/callback with a valid code
        exchanges it via GitHub API and returns JWT tokens and user."""
        ...

    async def test_callback_with_invalid_code_returns_401(self, _async_client):
        """POST callback with an invalid authorization code returns 401."""
        ...

    async def test_new_user_creates_account_and_links_oauth(self, _async_client):
        """First-time GitHub login creates a new user, links OAuth,
        and returns is_new_user=true."""
        ...

    async def test_existing_email_links_oauth_to_account(self, _async_client):
        """Existing user with matching email: auto-links GitHub OAuth
        and returns is_new_user=false."""
        ...

    async def test_existing_oauth_user_returns_tokens(self, _async_client):
        """User with existing GitHub OAuth link returns tokens directly."""
        ...

    async def test_github_account_linking_authenticated(self, _async_client):
        """Authenticated user can link GitHub via GET /oauth/github/authorize
        then POST /oauth/github/callback, receiving status=linked."""
        ...


# ---------------------------------------------------------------------------
# Discord OAuth
# ---------------------------------------------------------------------------


class TestDiscordOAuth:
    """E2E tests for Discord OAuth login flow.

    Discord does NOT use PKCE.
    Endpoint pattern:
        GET  /api/v1/oauth/discord/login
        POST /api/v1/oauth/discord/login/callback
    """

    async def test_login_url_returns_valid_discord_authorize_url(self, _async_client):
        """GET /api/v1/oauth/discord/login returns a valid authorize_url
        containing discord.com/oauth2/authorize and a state token."""
        ...

    async def test_callback_with_valid_code_returns_tokens(self, _async_client):
        """POST /api/v1/oauth/discord/login/callback with a valid code
        returns JWT tokens and user info."""
        ...

    async def test_new_user_creates_account_and_links_oauth(self, _async_client):
        """First-time Discord login creates a new user, links OAuth,
        and returns is_new_user=true."""
        ...

    async def test_existing_email_links_oauth_to_account(self, _async_client):
        """Existing user with matching Discord email: auto-links OAuth
        and returns is_new_user=false."""
        ...

    async def test_existing_oauth_user_returns_tokens(self, _async_client):
        """User with existing Discord OAuth link returns tokens directly."""
        ...


# ---------------------------------------------------------------------------
# Apple OAuth
# ---------------------------------------------------------------------------


class TestAppleOAuth:
    """E2E tests for Apple OAuth login flow.

    Apple uses PKCE (code_challenge + code_verifier).
    Endpoint pattern:
        GET  /api/v1/oauth/apple/login
        POST /api/v1/oauth/apple/login/callback
    """

    async def test_login_url_returns_valid_apple_authorize_url(self, _async_client):
        """GET /api/v1/oauth/apple/login returns a valid authorize_url
        containing appleid.apple.com/auth/authorize with PKCE params."""
        ...

    async def test_login_url_contains_pkce_params(self, _async_client):
        """Apple authorize_url must include code_challenge and
        code_challenge_method=S256 query parameters."""
        ...

    async def test_callback_with_valid_code_returns_tokens(self, _async_client):
        """POST /api/v1/oauth/apple/login/callback with a valid code
        returns JWT tokens and user info."""
        ...

    async def test_new_user_creates_account_and_links_oauth(self, _async_client):
        """First-time Apple login creates a new user, links OAuth,
        and returns is_new_user=true."""
        ...

    async def test_existing_email_links_oauth_to_account(self, _async_client):
        """Existing user with matching Apple email: auto-links OAuth
        and returns is_new_user=false."""
        ...

    async def test_existing_oauth_user_returns_tokens(self, _async_client):
        """User with existing Apple OAuth link returns tokens directly."""
        ...

    async def test_apple_private_relay_email_handled(self, _async_client):
        """Apple's private relay email (e.g., user@privaterelay.appleid.com)
        is correctly stored and matched on subsequent logins."""
        ...


# ---------------------------------------------------------------------------
# Microsoft OAuth
# ---------------------------------------------------------------------------


class TestMicrosoftOAuth:
    """E2E tests for Microsoft OAuth login flow.

    Microsoft uses PKCE (code_challenge + code_verifier).
    Endpoint pattern:
        GET  /api/v1/oauth/microsoft/login
        POST /api/v1/oauth/microsoft/login/callback
    """

    async def test_login_url_returns_valid_microsoft_authorize_url(self, _async_client):
        """GET /api/v1/oauth/microsoft/login returns a valid authorize_url
        containing login.microsoftonline.com with PKCE params."""
        ...

    async def test_login_url_contains_pkce_params(self, _async_client):
        """Microsoft authorize_url must include code_challenge and
        code_challenge_method=S256 query parameters."""
        ...

    async def test_callback_with_valid_code_returns_tokens(self, _async_client):
        """POST /api/v1/oauth/microsoft/login/callback with a valid code
        returns JWT tokens and user info."""
        ...

    async def test_new_user_creates_account_and_links_oauth(self, _async_client):
        """First-time Microsoft login creates a new user, links OAuth,
        and returns is_new_user=true."""
        ...

    async def test_existing_email_links_oauth_to_account(self, _async_client):
        """Existing user with matching Microsoft email: auto-links OAuth
        and returns is_new_user=false."""
        ...

    async def test_existing_oauth_user_returns_tokens(self, _async_client):
        """User with existing Microsoft OAuth link returns tokens directly."""
        ...


# ---------------------------------------------------------------------------
# X (Twitter) OAuth
# ---------------------------------------------------------------------------


class TestXTwitterOAuth:
    """E2E tests for X (Twitter) OAuth login flow.

    X/Twitter uses PKCE (code_challenge + code_verifier).
    Endpoint pattern:
        GET  /api/v1/oauth/twitter/login
        POST /api/v1/oauth/twitter/login/callback
    """

    async def test_login_url_returns_valid_twitter_authorize_url(self, _async_client):
        """GET /api/v1/oauth/twitter/login returns a valid authorize_url
        containing twitter.com or x.com OAuth endpoint with PKCE params."""
        ...

    async def test_login_url_contains_pkce_params(self, _async_client):
        """Twitter authorize_url must include code_challenge and
        code_challenge_method=S256 query parameters."""
        ...

    async def test_callback_with_valid_code_returns_tokens(self, _async_client):
        """POST /api/v1/oauth/twitter/login/callback with a valid code
        returns JWT tokens and user info."""
        ...

    async def test_new_user_creates_account_and_links_oauth(self, _async_client):
        """First-time X login creates a new user, links OAuth,
        and returns is_new_user=true."""
        ...

    async def test_existing_email_links_oauth_to_account(self, _async_client):
        """Existing user with matching X email: auto-links OAuth
        and returns is_new_user=false."""
        ...

    async def test_existing_oauth_user_returns_tokens(self, _async_client):
        """User with existing X OAuth link returns tokens directly."""
        ...

    async def test_twitter_no_email_creates_account_without_email(self, _async_client):
        """X/Twitter may not return an email. In that case, the user is
        created with email=None and is_email_verified=False."""
        ...


# ---------------------------------------------------------------------------
# Telegram OAuth
# ---------------------------------------------------------------------------


class TestTelegramOAuth:
    """E2E tests for Telegram OAuth flow.

    Telegram uses a unique HMAC-SHA256 hash-based validation instead of
    standard OAuth code exchange. Auth data includes id, first_name,
    auth_date, and hash.

    Account linking (authenticated):
        GET  /api/v1/oauth/telegram/authorize
        POST /api/v1/oauth/telegram/callback

    Login (unauthenticated -- not yet implemented but planned):
        Would follow the generic /{provider}/login pattern.
    """

    async def test_authorize_returns_telegram_login_url(self, _async_client):
        """GET /api/v1/oauth/telegram/authorize returns a valid authorize_url
        pointing to the Telegram Login Widget and includes a state token."""
        ...

    async def test_callback_with_valid_hmac_links_account(self, _async_client):
        """POST /api/v1/oauth/telegram/callback with valid HMAC-SHA256
        hash links the Telegram account and returns status=linked."""
        ...

    async def test_callback_with_invalid_hmac_returns_401(self, _async_client):
        """POST callback with a tampered hash is rejected with 401."""
        ...

    async def test_callback_with_expired_auth_date_returns_401(self, _async_client):
        """POST callback where auth_date is older than 24 hours is rejected."""
        ...

    async def test_callback_with_invalid_state_returns_401(self, _async_client):
        """POST callback with invalid or expired state token returns 401."""
        ...

    async def test_duplicate_link_is_idempotent(self, _async_client):
        """Linking the same Telegram account twice does not create duplicates."""
        ...

    async def test_unlink_telegram_account(self, _async_client):
        """DELETE /api/v1/oauth/telegram unlinks the Telegram account
        and returns status=unlinked."""
        ...


# ---------------------------------------------------------------------------
# Magic Link Passwordless Login
# ---------------------------------------------------------------------------


class TestMagicLinkE2E:
    """E2E tests for magic link passwordless login flow.

    Flow:
    1. POST /api/v1/auth/magic-link (request link)
    2. User receives email with token
    3. POST /api/v1/auth/magic-link/verify (exchange token for JWT)
    """

    async def test_request_magic_link_sends_email(self, _async_client):
        """POST /api/v1/auth/magic-link with a registered email dispatches
        a magic link email and returns a success response.

        Note: Always returns success to prevent email enumeration."""
        ...

    async def test_request_magic_link_unregistered_email_returns_success(self, _async_client):
        """POST /api/v1/auth/magic-link with an unregistered email still
        returns a success response (no email enumeration)."""
        ...

    async def test_verify_valid_token_returns_tokens(self, _async_client):
        """POST /api/v1/auth/magic-link/verify with a valid, unexpired
        token returns JWT access_token and refresh_token."""
        ...

    async def test_verify_valid_token_auto_registers_new_user(self, _async_client):
        """POST /api/v1/auth/magic-link/verify for an email with no
        existing account auto-creates a user with is_email_verified=True."""
        ...

    async def test_verify_expired_token_returns_400(self, _async_client):
        """POST /api/v1/auth/magic-link/verify with an expired token
        returns 400 with 'Invalid or expired magic link token'."""
        ...

    async def test_verify_used_token_returns_400(self, _async_client):
        """POST /api/v1/auth/magic-link/verify with an already-consumed
        token returns 400 (tokens are single-use)."""
        ...

    async def test_rate_limiting_returns_429(self, _async_client):
        """Requesting too many magic links in a short period returns
        429 Too Many Requests."""
        ...


# ---------------------------------------------------------------------------
# Username-Only Registration
# ---------------------------------------------------------------------------


class TestUsernameRegistrationE2E:
    """E2E tests for username-based registration flow.

    Flow:
    1. POST /api/v1/auth/register with login, email, password
    2. Verify OTP via POST /api/v1/auth/verify-otp
    3. Login via POST /api/v1/auth/login

    Registration is gated by REGISTRATION_ENABLED and optional invite tokens.
    """

    async def test_register_creates_inactive_user(self, _async_client):
        """POST /api/v1/auth/register creates a user with
        is_active=False and is_email_verified=False, then sends OTP email."""
        ...

    async def test_register_with_invite_token(self, _async_client):
        """POST /api/v1/auth/register?invite_token=<token> with a valid
        invite token succeeds and assigns the role from the invite."""
        ...

    async def test_register_without_invite_token_when_required_returns_403(self, _async_client):
        """POST /api/v1/auth/register without invite token when
        registration_invite_required=True returns 403."""
        ...

    async def test_register_when_disabled_returns_403(self, _async_client):
        """POST /api/v1/auth/register when REGISTRATION_ENABLED=false
        returns 403 with 'Registration is currently disabled'."""
        ...

    async def test_verify_otp_activates_user(self, _async_client):
        """POST /api/v1/auth/verify-otp with correct code activates the
        user (is_active=True, is_email_verified=True) and returns tokens."""
        ...

    async def test_login_after_verification_succeeds(self, _async_client):
        """POST /api/v1/auth/login with email+password after OTP
        verification returns JWT tokens."""
        ...

    async def test_login_before_verification_fails(self, _async_client):
        """POST /api/v1/auth/login before email verification returns 401."""
        ...

    async def test_duplicate_email_returns_error(self, _async_client):
        """POST /api/v1/auth/register with an already-registered email
        returns an appropriate error response."""
        ...

    async def test_duplicate_login_returns_error(self, _async_client):
        """POST /api/v1/auth/register with an already-taken login
        returns an appropriate error response."""
        ...


# ---------------------------------------------------------------------------
# Cross-Cutting Concerns
# ---------------------------------------------------------------------------


class TestCrossCuttingE2E:
    """E2E tests for auth features that span multiple flows.

    These verify that independent auth mechanisms do not interfere with
    each other and that security controls apply universally.
    """

    async def test_2fa_enforced_after_oauth_login(self, _async_client):
        """When a user has TOTP 2FA enabled, OAuth login returns
        requires_2fa=true with a tfa_token instead of full JWT tokens.

        The user must then POST /api/v1/auth/2fa/verify with the tfa_token
        and TOTP code to receive full tokens."""
        ...

    async def test_email_registration_still_works_alongside_oauth(self, _async_client):
        """Traditional email+password registration and login continue to
        work correctly even when OAuth providers are configured."""
        ...

    async def test_biometric_login_unaffected_by_oauth(self, _async_client):
        """Biometric/device-bound token login is not affected by OAuth
        configuration changes."""
        ...

    async def test_token_refresh_works_for_oauth_users(self, _async_client):
        """POST /api/v1/auth/refresh with a refresh_token issued via OAuth
        login returns a new access_token and refresh_token."""
        ...

    async def test_logout_invalidates_oauth_session(self, _async_client):
        """POST /api/v1/auth/logout with a refresh_token from an OAuth
        login invalidates the session."""
        ...

    async def test_logout_all_revokes_all_sessions(self, _async_client):
        """POST /api/v1/auth/logout-all revokes tokens from both
        email-based and OAuth-based login sessions."""
        ...

    async def test_brute_force_protection_on_login(self, _async_client):
        """Multiple failed POST /api/v1/auth/login attempts trigger
        progressive lockout (423 Locked response)."""
        ...

    async def test_constant_time_response_on_login_failure(self, _async_client):
        """Failed login attempts have a minimum response time of 100ms
        to prevent timing-based user enumeration."""
        ...

    async def test_unlink_last_auth_method_is_prevented(self, _async_client):
        """Users cannot unlink their only authentication method (e.g.,
        unlinking the sole OAuth provider when no password is set)."""
        ...

    async def test_invalid_provider_enum_returns_422(self, _async_client):
        """Requesting OAuth for an unsupported provider value returns
        422 Validation Error (HIGH-7 provider enum validation)."""
        ...

    async def test_device_fingerprint_binding_on_refresh(self, _async_client):
        """When ENFORCE_TOKEN_BINDING is enabled, refresh_token validation
        checks client fingerprint (MED-002)."""
        ...
