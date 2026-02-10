"""Load tests for OAuth and magic link authentication endpoints.

Targets the new passwordless-login and social-login flows introduced in
the auth enhancement epic.  Exercises three areas:

1. OAuth authorize URL generation -- GET /api/v1/oauth/{provider}/login
2. Magic link request             -- POST /api/v1/auth/magic-link
3. Magic link token verification  -- POST /api/v1/auth/magic-link/verify
4. Rate limiting behaviour on the magic link endpoint

Run with:
    pip install locust
    cd backend
    locust -f tests/load/test_auth_load.py --host=http://localhost:8000

Scenarios:
    - Sustained: 100 users, ramp 10 users/s, run 5 minutes
        locust -f tests/load/test_auth_load.py --host=http://localhost:8000 \
               -u 100 -r 10 -t 5m --headless
    - Spike: 500 users, ramp 50 users/s, run 30 seconds
        locust -f tests/load/test_auth_load.py --host=http://localhost:8000 \
               -u 500 -r 50 -t 30s --headless
    - Rate-limit focus only:
        locust -f tests/load/test_auth_load.py --host=http://localhost:8000 \
               --tags rate-limit -u 50 -r 10 -t 2m --headless

Notes:
    - No production data is used; every email is randomly generated under
      the ``@loadtest.cybervpn.io`` domain which must never resolve to a
      real mailbox.
    - The OAuth authorize endpoint is public (no auth required) and is
      expected to return 200 with ``authorize_url`` and ``state`` fields,
      or 400 if a provider does not support the login flow.
    - Magic link verify intentionally sends an invalid token; 400 is the
      expected status code.
"""

import random
import string

from locust import HttpUser, between, tag, task

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _random_email() -> str:
    """Generate a unique random email for load testing.

    Uses the ``@loadtest.cybervpn.io`` domain to guarantee that no real
    mailbox is ever targeted.
    """
    name = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))  # noqa: S311
    return f"{name}@loadtest.cybervpn.io"


# Providers that support the unauthenticated login flow
# (matches ``_OAUTH_PROVIDERS`` in backend/src/presentation/api/v1/oauth/routes.py)
_LOGIN_PROVIDERS = ["google", "github", "discord", "apple", "microsoft", "twitter"]

# Provider that is a valid OAuthProvider enum member but does NOT appear in
# _OAUTH_PROVIDERS, so the login endpoint should return 400.
_UNSUPPORTED_LOGIN_PROVIDER = "telegram"


# ---------------------------------------------------------------------------
# Locust user
# ---------------------------------------------------------------------------


class AuthLoadUser(HttpUser):
    """Simulates users exercising OAuth and magic link authentication flows.

    Task weights approximate expected real-world traffic ratios:
        - OAuth authorize requests are the most frequent (weight 3).
        - Magic link requests are moderately frequent (weight 2).
        - Rate-limit probing and invalid-token verification are less
          frequent (weight 1 each).
        - Unsupported-provider requests are rare (weight 1).
    """

    wait_time = between(1, 3)

    # ------------------------------------------------------------------
    # OAuth authorize URL generation
    # ------------------------------------------------------------------

    @tag("oauth", "authorize")
    @task(3)
    def test_oauth_authorize_supported_provider(self):
        """GET /api/v1/oauth/{provider}/login -- supported provider.

        Arrange: pick a random supported provider and a redirect URI.
        Act:     send GET with redirect_uri query param.
        Assert:  200 with authorize_url and state, OR 422 if the provider
                 is not configured on the server (missing client_id, etc.).
        """
        provider = random.choice(_LOGIN_PROVIDERS)  # noqa: S311
        with self.client.get(
            f"/api/v1/oauth/{provider}/login",
            params={"redirect_uri": "http://localhost:3000/auth/callback"},
            name="/api/v1/oauth/[provider]/login",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                body = resp.json()
                if "authorize_url" not in body or "state" not in body:
                    resp.failure(f"Missing authorize_url or state in 200 response (provider={provider})")
            elif resp.status_code in (400, 422):
                # 400 = provider not in login flow map
                # 422 = validation error (e.g. missing redirect_uri)
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code} for provider={provider}")

    @tag("oauth", "authorize", "negative")
    @task(1)
    def test_oauth_authorize_unsupported_provider(self):
        """GET /api/v1/oauth/{provider}/login -- unsupported provider.

        Arrange: use a provider that exists in OAuthProvider enum but is
                 not in the _OAUTH_PROVIDERS login map (telegram).
        Act:     send GET.
        Assert:  400 with descriptive error message.
        """
        with self.client.get(
            f"/api/v1/oauth/{_UNSUPPORTED_LOGIN_PROVIDER}/login",
            params={"redirect_uri": "http://localhost:3000/auth/callback"},
            name="/api/v1/oauth/[provider]/login [unsupported]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 400:
                resp.success()
            else:
                resp.failure(f"Expected 400 for unsupported provider, got {resp.status_code}")

    # ------------------------------------------------------------------
    # Magic link request
    # ------------------------------------------------------------------

    @tag("magic-link", "request")
    @task(2)
    def test_magic_link_request_unique_email(self):
        """POST /api/v1/auth/magic-link -- fresh random email each time.

        Arrange: generate a unique random email.
        Act:     POST JSON with email field.
        Assert:  200 (always returns success to prevent email enumeration)
                 or 429 if server-wide rate limit triggers.
        """
        email = _random_email()
        with self.client.post(
            "/api/v1/auth/magic-link",
            json={"email": email},
            name="/api/v1/auth/magic-link",
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                body = resp.json()
                if "message" not in body:
                    resp.failure("Missing 'message' in 200 response")
            elif resp.status_code == 429:
                # Rate limited -- expected under heavy load
                resp.success()
            else:
                resp.failure(f"Unexpected status {resp.status_code}")

    # ------------------------------------------------------------------
    # Magic link rate-limit probing
    # ------------------------------------------------------------------

    @tag("magic-link", "rate-limit")
    @task(1)
    def test_magic_link_rate_limit_same_email(self):
        """POST /api/v1/auth/magic-link -- same email repeated.

        Arrange: use a fixed load-test email to trigger per-email rate
                 limiting (max 5 requests/hour in MagicLinkService).
        Act:     POST JSON with the fixed email.
        Assert:  200 for the first few requests, then 429 once the
                 per-email hourly limit is exceeded.  Both are valid.
        """
        email = "ratelimit-probe@loadtest.cybervpn.io"
        with self.client.post(
            "/api/v1/auth/magic-link",
            json={"email": email},
            name="/api/v1/auth/magic-link [rate-limit]",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 429):
                resp.success()
            else:
                resp.failure(f"Expected 200 or 429 for rate-limit probe, got {resp.status_code}")

    # ------------------------------------------------------------------
    # Magic link verify (invalid token)
    # ------------------------------------------------------------------

    @tag("magic-link", "verify")
    @task(1)
    def test_magic_link_verify_invalid_token(self):
        """POST /api/v1/auth/magic-link/verify -- invalid token.

        Arrange: use a deliberately invalid token string.
        Act:     POST JSON with the token.
        Assert:  400 (invalid or expired magic link token).
        """
        with self.client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": "invalid_token_for_load_test_00000000"},
            name="/api/v1/auth/magic-link/verify [invalid]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 400:
                resp.success()
            elif resp.status_code == 422:
                # Pydantic validation error (token too short, etc.)
                resp.success()
            else:
                resp.failure(f"Expected 400 or 422 for invalid token, got {resp.status_code}")

    # ------------------------------------------------------------------
    # Magic link request -- edge cases
    # ------------------------------------------------------------------

    @tag("magic-link", "negative")
    @task(1)
    def test_magic_link_request_invalid_email_format(self):
        """POST /api/v1/auth/magic-link -- malformed email.

        Arrange: use an email string that fails Pydantic EmailStr validation.
        Act:     POST JSON.
        Assert:  422 validation error.
        """
        with self.client.post(
            "/api/v1/auth/magic-link",
            json={"email": "not-an-email"},
            name="/api/v1/auth/magic-link [invalid-email]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 422:
                resp.success()
            else:
                resp.failure(f"Expected 422 for malformed email, got {resp.status_code}")

    @tag("magic-link", "negative")
    @task(1)
    def test_magic_link_request_empty_body(self):
        """POST /api/v1/auth/magic-link -- empty JSON body.

        Arrange: send ``{}`` with no email field.
        Act:     POST JSON.
        Assert:  422 validation error (email is required).
        """
        with self.client.post(
            "/api/v1/auth/magic-link",
            json={},
            name="/api/v1/auth/magic-link [empty-body]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 422:
                resp.success()
            else:
                resp.failure(f"Expected 422 for empty body, got {resp.status_code}")

    @tag("magic-link", "verify", "negative")
    @task(1)
    def test_magic_link_verify_empty_token(self):
        """POST /api/v1/auth/magic-link/verify -- empty token string.

        Arrange: send ``{"token": ""}`` (violates min_length=1).
        Act:     POST JSON.
        Assert:  422 validation error.
        """
        with self.client.post(
            "/api/v1/auth/magic-link/verify",
            json={"token": ""},
            name="/api/v1/auth/magic-link/verify [empty-token]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 422:
                resp.success()
            else:
                resp.failure(f"Expected 422 for empty token, got {resp.status_code}")

    @tag("oauth", "authorize", "negative")
    @task(1)
    def test_oauth_authorize_missing_redirect_uri(self):
        """GET /api/v1/oauth/{provider}/login -- no redirect_uri param.

        Arrange: omit the required ``redirect_uri`` query parameter.
        Act:     send GET.
        Assert:  422 validation error.
        """
        provider = random.choice(_LOGIN_PROVIDERS)  # noqa: S311
        with self.client.get(
            f"/api/v1/oauth/{provider}/login",
            name="/api/v1/oauth/[provider]/login [no-redirect]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 422:
                resp.success()
            else:
                resp.failure(f"Expected 422 for missing redirect_uri, got {resp.status_code}")
