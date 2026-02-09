# PRD: Unified Authentication System

**Version:** 1.0
**Date:** 2026-02-09
**Status:** Draft
**Author:** CyberVPN Engineering
**Layers:** Backend (FastAPI) | Frontend (Next.js 16) | Mobile (Flutter)

---

## 1. Overview & Problem Statement

CyberVPN currently supports email/password login with OTP verification, Telegram OAuth (fully wired on all layers), and GitHub OAuth (backend + mobile linking only). The platform lacks:

1. **Multi-provider OAuth login** — Google, Discord, Apple, Microsoft, and X (Twitter) are not implemented. GitHub OAuth exists only for account linking, not as a primary login method.
2. **Magic link authentication** — passwordless email-based login is unavailable on any layer.
3. **Login/password mode** — users must provide an email to register; there is no username-only login flow without email verification.
4. **OAuth-as-login** — existing OAuth routes require an authenticated user (`get_current_active_user` dependency), making them usable only for account linking, not for unauthenticated login/registration.

### Business Impact

- Users in markets with high Telegram adoption can log in, but Google/Apple-dominant markets (US, EU, Japan) have no social login.
- Passwordless (magic link) authentication reduces friction for users who dislike managing passwords.
- Username/password login enables privacy-conscious users to avoid providing an email upfront.

---

## 2. Goals & Success Metrics

### Goals

| # | Goal | Priority |
|---|------|----------|
| G1 | Add Google, Discord, Apple, Microsoft, X OAuth login across all layers | P0 |
| G2 | Add magic link (passwordless email) authentication across all layers | P1 |
| G3 | Add login/password mode (no email required at registration) | P1 |
| G4 | Convert existing OAuth from linking-only to login-or-link | P0 |
| G5 | Zero breaking changes to existing email/password, Telegram, biometric flows | P0 |

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| OAuth login adoption | 30% of new registrations within 60 days | Backend analytics |
| Magic link usage | 10% of logins within 30 days | Backend analytics |
| Auth error rate | <1% of all auth attempts | Prometheus/Grafana |
| Time to first login (OAuth) | <5 seconds (after provider consent) | Frontend/Mobile instrumentation |
| Zero regressions | 0 broken existing flows | CI test suite |

---

## 3. Authentication Methods Matrix

| Method | Backend | Frontend | Mobile | Notes |
|--------|---------|----------|--------|-------|
| Email + Password | Exists | Exists | Exists | No changes needed |
| Login + Password (no email) | **New** | **New** | **New** | Username-only registration |
| OTP Email Verification | Exists | Exists | Exists | Used after email-based registration |
| Magic Link | **New** | **New** | **New** | Passwordless email login |
| Telegram OAuth | Exists | Exists | Exists | No changes needed |
| GitHub OAuth | Exists (link only) | **Modify** | Exists (link only) | Add login flow |
| Google OAuth | **New** | **New** | **New** | OIDC + PKCE |
| Discord OAuth | **New** | **New** | **New** | OAuth 2.0 |
| Apple Sign In | **New** | **New** | **New** | OIDC + nonce |
| Microsoft OAuth | **New** | **New** | **New** | OIDC v2.0 |
| X (Twitter) OAuth | **New** | **New** | **New** | OAuth 2.0 + PKCE |
| Biometric Login | N/A | N/A | Exists | Device-bound, no changes |
| TOTP 2FA | Exists | Exists | Exists | No changes needed |

---

## 4. User Stories

### 4.1 OAuth Login (All Providers)

**US-AUTH-01**: As a new user, I want to sign up using my Google/GitHub/Discord/Apple/Microsoft/X account so that I don't need to create a separate password.

**Acceptance Criteria:**
- Clicking a social button redirects to the provider's consent screen
- After consent, the user is automatically registered (if new) or logged in (if existing)
- Account is matched by email — if a user with that email exists, the OAuth account is linked automatically
- If the provider doesn't return an email (e.g., X/Twitter), the user is prompted to provide one
- JWT access + refresh tokens are returned on success

**US-AUTH-02**: As an existing user, I want to link additional OAuth providers to my account from my profile/settings page.

**Acceptance Criteria:**
- Uses the existing account linking flow (currently works for Telegram/GitHub)
- Extended to all 7 providers
- User can unlink any provider except their last auth method

### 4.2 Magic Link

**US-AUTH-03**: As a user, I want to log in by receiving a link in my email so that I don't need to remember a password.

**Acceptance Criteria:**
- User enters email on login page and clicks "Send magic link"
- Backend sends a single-use, time-limited link to the email
- Clicking the link logs the user in (or creates an account if new)
- Link expires after 15 minutes
- Link can only be used once
- Frontend: redirects to `/auth/magic-link/verify?token=...`
- Mobile: deep link opens the app and auto-authenticates

### 4.3 Login/Password (No Email)

**US-AUTH-04**: As a privacy-conscious user, I want to register with just a username and password (no email) so that I don't expose my email address.

**Acceptance Criteria:**
- Registration form allows username + password without email
- User can optionally add email later from profile settings
- Without email: no OTP verification required, account is immediately active
- Without email: magic link and "forgot password" are unavailable
- Login accepts either username or email in the same field (existing behavior via `login_or_email`)

---

## 5. Technical Architecture

### 5.1 Provider Abstraction Pattern

Reuse the existing `GitHubOAuthProvider` pattern from `backend/src/infrastructure/oauth/github.py`. Each provider implements:

```python
class OAuthProviderBase:
    """Abstract base for all OAuth providers."""

    AUTHORIZE_URL: str
    TOKEN_URL: str
    USER_API_URL: str

    def __init__(self) -> None: ...

    def authorize_url(self, redirect_uri: str, state: str, **kwargs) -> str:
        """Generate provider-specific authorization URL."""
        ...

    async def exchange_code(self, code: str, redirect_uri: str, **kwargs) -> dict | None:
        """Exchange authorization code for user info.

        Returns normalized dict:
        {
            "id": str,           # Provider's user ID
            "email": str | None, # Email (may be None for some providers)
            "username": str | None,
            "name": str | None,
            "avatar_url": str | None,
            "access_token": str,
            "refresh_token": str | None,
        }
        """
        ...
```

**Provider-specific notes:**

| Provider | Auth Type | PKCE | Email Guaranteed | Special Handling |
|----------|-----------|------|------------------|------------------|
| Google | OIDC | Yes | Yes (verified) | ID token validation via `google-auth` |
| GitHub | OAuth 2.0 | No | No (may be private) | Separate `/user/emails` API call needed |
| Discord | OAuth 2.0 | No | Yes | Scope: `identify email` |
| Apple | OIDC | Yes | Yes (first login only) | ID token only, no userinfo endpoint; name only on first auth |
| Microsoft | OIDC v2.0 | Yes | Yes | Multi-tenant: `common` endpoint |
| X (Twitter) | OAuth 2.0 | Yes | No | Scope: `users.read tweet.read`; email not in basic scope |
| Telegram | Custom HMAC | N/A | No | Existing implementation, no changes |

### 5.2 OAuth 2.0 / OIDC Unified Flow

```
┌─────────┐     ┌─────────┐     ┌──────────┐     ┌──────────┐
│  Client  │     │ Backend │     │  Redis   │     │ Provider │
│(FE/App)  │     │ (API)   │     │          │     │          │
└────┬─────┘     └────┬────┘     └────┬─────┘     └────┬─────┘
     │ 1. GET /oauth/{provider}/login  │                │
     │ ?redirect_uri=...               │                │
     │ ─────────────────────────────►  │                │
     │                                 │                │
     │      2. Generate state+PKCE     │                │
     │      ─────────────────────────► │                │
     │      Store state+verifier       │                │
     │      ◄───────────────────────── │                │
     │                                 │                │
     │ 3. Return authorize_url + state │                │
     │ ◄──────────────────────────────  │                │
     │                                 │                │
     │ 4. Redirect to provider         │                │
     │ ──────────────────────────────────────────────►  │
     │                                 │                │
     │ 5. User consents                │                │
     │ ◄──────────────────────────────────────────────  │
     │                                 │                │
     │ 6. POST /oauth/{provider}/login/callback         │
     │    {code, state, redirect_uri}  │                │
     │ ─────────────────────────────►  │                │
     │                                 │                │
     │      7. Validate state          │                │
     │      ─────────────────────────► │                │
     │      Consume state+verifier     │                │
     │      ◄───────────────────────── │                │
     │                                 │                │
     │      8. Exchange code+verifier  │                │
     │      ──────────────────────────────────────────► │
     │      ◄────────────────────────────────────────── │
     │                                 │                │
     │      9. Find/create user        │                │
     │      Issue JWT tokens           │                │
     │                                 │                │
     │ 10. Return tokens + user        │                │
     │ ◄──────────────────────────────  │                │
     └────────────────────────────────┘                │
```

### 5.3 Account Merging Strategy

When an OAuth provider returns user info, the backend must decide whether to **create** a new user or **link** to an existing one:

```
OAuth callback received with user_info
    │
    ├─ Check oauth_accounts for (provider, provider_user_id)
    │   └─ Found → Login as linked user → Return tokens
    │
    ├─ Check admin_users for matching email (if email provided)
    │   └─ Found → Auto-link OAuth account → Login → Return tokens
    │
    └─ No match → Create new user
        ├─ If email provided → Create with email, auto-verified
        ├─ If no email → Create with generated login, prompt for email
        └─ Link OAuth account → Return tokens
```

**Conflict resolution:**
- If the same email is linked to a different OAuth account of the same provider, reject with error
- Auto-linking by email only happens for **verified** emails from the provider
- Users can always manually link/unlink from profile settings

### 5.4 Magic Link Flow

```
┌─────────┐     ┌─────────┐     ┌──────────┐     ┌──────────┐
│  Client  │     │ Backend │     │  Redis   │     │  Email   │
└────┬─────┘     └────┬────┘     └────┬─────┘     └────┬─────┘
     │ 1. POST /auth/magic-link       │                │
     │    {email}                      │                │
     │ ─────────────────────────────►  │                │
     │                                 │                │
     │      2. Generate token          │                │
     │      ─────────────────────────► │                │
     │      Store token (15min TTL)    │                │
     │      ◄───────────────────────── │                │
     │                                 │                │
     │      3. Dispatch email task     │                │
     │      ──────────────────────────────────────────► │
     │                                 │                │
     │ 4. Return {message: "sent"}     │                │
     │ ◄──────────────────────────────  │                │
     │                                 │                │
     │ ... User clicks link in email ...│                │
     │                                 │                │
     │ 5. POST /auth/magic-link/verify │                │
     │    {token}                      │                │
     │ ─────────────────────────────►  │                │
     │                                 │                │
     │      6. Validate & consume      │                │
     │      ─────────────────────────► │                │
     │      ◄───────────────────────── │                │
     │                                 │                │
     │      7. Find/create user        │                │
     │      Issue JWT tokens           │                │
     │                                 │                │
     │ 8. Return tokens + user         │                │
     │ ◄──────────────────────────────  │                │
     └────────────────────────────────┘                │
```

**Token format:** `magic_link:{random_token}` → stored in Redis with JSON payload `{email, ip_address, created_at}`, TTL 900s (15 minutes).

### 5.5 PKCE (Proof Key for Code Exchange)

Required for Google, Apple, Microsoft, and X. Implemented in `OAuthStateService`:

```python
# Generate
code_verifier = secrets.token_urlsafe(64)  # 43-128 chars
code_challenge = base64url(sha256(code_verifier))

# Store alongside state in Redis
data = {
    "provider": "google",
    "code_verifier": code_verifier,
    "code_challenge": code_challenge,
    ...
}

# On callback: retrieve code_verifier and include in token exchange
```

---

## 6. Backend Implementation

### 6.1 New OAuth Providers

Create new provider files following the `GitHubOAuthProvider` pattern:

| File | Provider | OIDC |
|------|----------|------|
| `backend/src/infrastructure/oauth/google.py` | Google | Yes |
| `backend/src/infrastructure/oauth/discord.py` | Discord | No |
| `backend/src/infrastructure/oauth/apple.py` | Apple | Yes |
| `backend/src/infrastructure/oauth/microsoft.py` | Microsoft | Yes |
| `backend/src/infrastructure/oauth/twitter.py` | X (Twitter) | No |

#### 6.1.1 Google OAuth Provider

```python
class GoogleOAuthProvider:
    AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USER_API_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
    JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"

    def authorize_url(self, redirect_uri: str, state: str, code_challenge: str) -> str:
        params = urlencode({
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "consent",
        })
        return f"{self.AUTHORIZE_URL}?{params}"
```

#### 6.1.2 Discord OAuth Provider

```python
class DiscordOAuthProvider:
    AUTHORIZE_URL = "https://discord.com/oauth2/authorize"
    TOKEN_URL = "https://discord.com/api/oauth2/token"
    USER_API_URL = "https://discord.com/api/users/@me"

    def authorize_url(self, redirect_uri: str, state: str) -> str:
        params = urlencode({
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "identify email",
            "state": state,
        })
        return f"{self.AUTHORIZE_URL}?{params}"
```

#### 6.1.3 Apple Sign In Provider

```python
class AppleOAuthProvider:
    AUTHORIZE_URL = "https://appleid.apple.com/auth/authorize"
    TOKEN_URL = "https://appleid.apple.com/auth/token"
    JWKS_URL = "https://appleid.apple.com/auth/keys"

    # Apple uses a client_secret JWT signed with a private key
    def _generate_client_secret(self) -> str:
        """Generate JWT client secret signed with Apple private key."""
        ...

    def authorize_url(self, redirect_uri: str, state: str, nonce: str) -> str:
        params = urlencode({
            "client_id": self.client_id,  # Service ID
            "redirect_uri": redirect_uri,
            "response_type": "code id_token",
            "scope": "name email",
            "state": state,
            "nonce": nonce,
            "response_mode": "form_post",
        })
        return f"{self.AUTHORIZE_URL}?{params}"
```

**Apple-specific notes:**
- `client_secret` is a JWT signed with an ES256 private key from Apple Developer
- User's name is only returned on first authorization; store it immediately
- ID token contains email; no separate userinfo endpoint
- `response_mode=form_post` — Apple POSTs the callback, not GET redirect

#### 6.1.4 Microsoft OAuth Provider

```python
class MicrosoftOAuthProvider:
    AUTHORIZE_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    USER_API_URL = "https://graph.microsoft.com/v1.0/me"

    def authorize_url(self, redirect_uri: str, state: str, code_challenge: str) -> str:
        params = urlencode({
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile User.Read",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        })
        return f"{self.AUTHORIZE_URL}?{params}"
```

#### 6.1.5 X (Twitter) OAuth Provider

```python
class TwitterOAuthProvider:
    AUTHORIZE_URL = "https://twitter.com/i/oauth2/authorize"
    TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
    USER_API_URL = "https://api.twitter.com/2/users/me"

    def authorize_url(self, redirect_uri: str, state: str, code_challenge: str) -> str:
        params = urlencode({
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "users.read tweet.read",
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        })
        return f"{self.AUTHORIZE_URL}?{params}"
```

**X-specific notes:**
- Uses OAuth 2.0 with PKCE (not the legacy OAuth 1.0a)
- Email is NOT included in the basic scope; user must be prompted to provide one
- `client_id` is the OAuth 2.0 Client ID from the Twitter Developer Portal
- Token exchange uses HTTP Basic Auth (`client_id:client_secret`)

### 6.2 Magic Link Service

**File:** `backend/src/application/services/magic_link_service.py`

```python
class MagicLinkService:
    """Manages magic link tokens for passwordless authentication."""

    PREFIX = "magic_link:"
    TTL_SECONDS = 900  # 15 minutes
    RATE_LIMIT_PREFIX = "magic_link_rate:"
    MAX_REQUESTS_PER_HOUR = 5

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def generate(self, email: str, ip_address: str | None = None) -> str:
        """Generate a magic link token for the given email.

        Returns the token string. The full URL must be constructed by the caller.
        Rate limited to MAX_REQUESTS_PER_HOUR per email.
        """
        ...

    async def validate_and_consume(self, token: str) -> dict | None:
        """Validate and consume a magic link token.

        Returns {email, ip_address, created_at} if valid, None otherwise.
        Token is deleted after first use (single-use).
        """
        ...
```

### 6.3 New Routes

#### 6.3.1 OAuth Login Routes (Unauthenticated)

**File:** `backend/src/presentation/api/v1/oauth/routes.py` — add new endpoints alongside existing linking routes.

```python
# ── OAuth Login (unauthenticated) ──────────────────────────────────

@router.get("/{provider}/login", response_model=OAuthAuthorizeResponse)
async def oauth_login_authorize(
    provider: OAuthProviderEnum,
    redirect_uri: str = Query(...),
    request: Request = None,
    redis_client: redis.Redis = Depends(get_redis),
) -> OAuthAuthorizeResponse:
    """Get OAuth authorization URL for login/registration.

    No authentication required — this is for unauthenticated users.
    Generates PKCE code_verifier for providers that support it.
    """
    ...

@router.post("/{provider}/login/callback", response_model=OAuthLoginResponse)
async def oauth_login_callback(
    provider: OAuthProviderEnum,
    callback_data: OAuthLoginCallbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    auth_service: AuthService = Depends(get_auth_service),
) -> OAuthLoginResponse:
    """Process OAuth callback for login/registration.

    1. Validates state token
    2. Exchanges code for user info
    3. Finds existing user by provider_user_id or email
    4. Creates new user if not found
    5. Links OAuth account
    6. Returns JWT tokens
    """
    ...
```

#### 6.3.2 Magic Link Routes

**File:** `backend/src/presentation/api/v1/auth/routes.py` — add to existing auth router.

```python
@router.post("/magic-link", response_model=MagicLinkResponse)
async def request_magic_link(
    request: MagicLinkRequest,
    http_request: Request,
    redis_client: redis.Redis = Depends(get_redis),
    email_dispatcher: EmailTaskDispatcher = Depends(get_email_dispatcher),
) -> MagicLinkResponse:
    """Request a magic link for passwordless login.

    Rate limited to 5 requests per hour per email.
    """
    ...

@router.post("/magic-link/verify", response_model=TokenResponse)
async def verify_magic_link(
    request: MagicLinkVerifyRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Verify magic link token and return JWT tokens.

    If user doesn't exist, creates a new account (auto-verified).
    """
    ...
```

#### 6.3.3 Login/Password Registration Modification

**File:** `backend/src/presentation/api/v1/auth/routes.py`

The existing `RegisterRequest` requires `email: EmailStr`. Add a separate schema or make email optional:

```python
class RegisterRequest(BaseModel):
    login: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: EmailStr | None = None  # Optional for login/password mode
    password: str = Field(..., min_length=12, max_length=128)
    locale: str = Field(default="en-EN", max_length=10)

    @model_validator(mode="after")
    def check_registration_mode(self) -> "RegisterRequest":
        """If email is provided, it's email/password mode. If not, login/password mode."""
        return self
```

**Behavior change:**
- **With email:** Existing flow — create inactive user, send OTP, require verification
- **Without email:** Create active user immediately, skip OTP verification, `is_email_verified=False`

### 6.4 New Schemas

**File:** `backend/src/presentation/api/v1/oauth/schemas.py` — extend.

```python
class OAuthProviderEnum(StrEnum):
    """Valid OAuth providers."""
    TELEGRAM = "telegram"
    GITHUB = "github"
    GOOGLE = "google"
    DISCORD = "discord"
    APPLE = "apple"
    MICROSOFT = "microsoft"
    TWITTER = "twitter"  # X

class OAuthLoginCallbackRequest(BaseModel):
    """OAuth login callback — no auth required."""
    code: str = Field(..., description="Authorization code")
    state: str = Field(..., description="CSRF state token")
    redirect_uri: str = Field(..., description="Original redirect URI")

class OAuthLoginResponse(BaseModel):
    """Response for OAuth login with tokens and user info."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0
    user: AdminUserResponse
    is_new_user: bool = False  # True if account was just created

class MagicLinkRequest(BaseModel):
    email: EmailStr

class MagicLinkResponse(BaseModel):
    message: str = "If this email is registered, a login link has been sent."

class MagicLinkVerifyRequest(BaseModel):
    token: str = Field(..., min_length=32, max_length=128)
```

### 6.5 Settings Additions

**File:** `backend/src/config/settings.py` — add new provider credentials.

```python
# Google OAuth
google_client_id: str = ""
google_client_secret: SecretStr = SecretStr("")

# Discord OAuth
discord_client_id: str = ""
discord_client_secret: SecretStr = SecretStr("")

# Apple Sign In
apple_client_id: str = ""          # Service ID (e.g., com.cybervpn.auth)
apple_team_id: str = ""
apple_key_id: str = ""
apple_private_key: SecretStr = SecretStr("")  # ES256 private key PEM

# Microsoft OAuth
microsoft_client_id: str = ""
microsoft_client_secret: SecretStr = SecretStr("")
microsoft_tenant_id: str = "common"  # "common" for multi-tenant

# X (Twitter) OAuth
twitter_client_id: str = ""
twitter_client_secret: SecretStr = SecretStr("")

# Magic Link
magic_link_ttl_seconds: int = 900       # 15 minutes
magic_link_rate_limit: int = 5          # per hour per email
magic_link_base_url: str = ""           # e.g., https://app.cybervpn.com/auth/magic-link/verify
```

### 6.6 PKCE Enhancement to OAuthStateService

**File:** `backend/src/application/services/oauth_state_service.py` — extend to store PKCE verifier.

```python
async def generate(
    self,
    provider: str,
    user_id: str | None = None,
    ip_address: str | None = None,
    pkce: bool = False,          # New parameter
) -> tuple[str, str | None]:     # Returns (state, code_challenge | None)
    """Generate OAuth state with optional PKCE.

    If pkce=True, generates code_verifier and code_challenge.
    code_verifier is stored in Redis alongside state.
    code_challenge is returned for the authorization URL.
    """
    state = secrets.token_urlsafe(32)
    code_verifier = None
    code_challenge = None

    if pkce:
        code_verifier = secrets.token_urlsafe(64)
        digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

    data = {
        "provider": provider,
        "user_id": user_id,
        "ip_address": ip_address,
        "code_verifier": code_verifier,
        "created_at": datetime.now(UTC).isoformat(),
    }

    await self._redis.setex(f"{self.PREFIX}{state}", self.TTL_SECONDS, json.dumps(data))

    return state, code_challenge

async def validate_and_consume(self, state: str, provider: str, **kwargs) -> dict | None:
    """Validate, consume, and return state data including code_verifier."""
    # Returns full data dict instead of bool, so caller can access code_verifier
    ...
```

### 6.7 OAuth Login Use Case

**File:** `backend/src/application/use_cases/auth/oauth_login.py` (new)

```python
class OAuthLoginUseCase:
    """Handle OAuth login: find or create user, link provider, issue tokens."""

    def __init__(
        self,
        user_repo: AdminUserRepository,
        auth_service: AuthService,
        session: AsyncSession,
    ) -> None:
        ...

    async def execute(
        self,
        provider: str,
        user_info: dict,
        client_fingerprint: str | None = None,
    ) -> dict:
        """
        1. Check if oauth_account exists for (provider, provider_user_id) → login
        2. Check if admin_user exists for email → link + login
        3. Create new user + link → login
        """
        ...
```

### 6.8 Database

The existing `oauth_accounts` table (see `backend/src/infrastructure/database/models/oauth_account_model.py`) is sufficient:

```
oauth_accounts
├── id: UUID (PK)
├── user_id: UUID (FK → admin_users.id, CASCADE)
├── provider: VARCHAR(20)         ← Increase to VARCHAR(20) if needed
├── provider_user_id: VARCHAR(255)
├── provider_username: VARCHAR(255)
├── provider_email: VARCHAR(255)
├── provider_avatar_url: TEXT
├── access_token: TEXT
├── refresh_token: TEXT
├── token_expires_at: TIMESTAMP
├── created_at: TIMESTAMP
├── updated_at: TIMESTAMP
├── UNIQUE(provider, provider_user_id)  ← uq_provider_user
└── UNIQUE(user_id, provider)           ← uq_user_provider
```

**No new migration needed** — the `provider` VARCHAR(20) can hold all provider names ("telegram", "github", "google", "discord", "apple", "microsoft", "twitter") and all necessary columns exist.

**Registration mode change:** The `admin_users.email` column is already `nullable=True` (see model line 31), so login/password mode (no email) is already supported at the DB level. The `RegisterUseCase` needs a code change to skip OTP when email is absent.

---

## 7. Frontend Implementation

### 7.1 Wire SocialAuthButtons

**File:** `frontend/src/features/auth/components/SocialAuthButtons.tsx`

Currently has Google, GitHub, Discord buttons with **no handlers** — they render SVG icons but don't do anything on click. Additionally, Apple, Microsoft, and X buttons are missing.

**Changes:**

1. Add `onSocialAuth(provider: string)` handler that calls `authApi.oauthLoginAuthorize(provider, redirectUri)`
2. The handler receives the `authorize_url` from the backend, then redirects the browser: `window.location.href = authorize_url`
3. Add buttons for Apple, Microsoft, X with appropriate SVG icons
4. Pass `isLoading` state to disable buttons during OAuth flow

```tsx
// In SocialAuthButtons.tsx
const handleSocialLogin = async (provider: string) => {
  const redirectUri = `${window.location.origin}/${locale}/oauth/callback`;
  const { authorize_url } = await authApi.oauthLoginAuthorize(provider, redirectUri);
  window.location.href = authorize_url;
};
```

### 7.2 OAuth Callback Page

**New file:** `frontend/src/app/[locale]/(auth)/oauth/callback/page.tsx`

This page handles the redirect from all OAuth providers:

```tsx
"use client";

export default function OAuthCallbackPage() {
  // 1. Extract code, state from URL search params
  // 2. Determine provider from state (stored in sessionStorage before redirect)
  // 3. Call authApi.oauthLoginCallback(provider, { code, state, redirectUri })
  // 4. On success: store tokens, fetchUser, redirect to dashboard
  // 5. On error: show error message with retry button
  // 6. Show loading spinner with cyberpunk theme during exchange
}
```

**Provider detection:** Before redirecting to the OAuth provider, store `{provider, state}` in `sessionStorage`. On callback, retrieve the provider using the state parameter.

### 7.3 Magic Link Pages

**New file:** `frontend/src/app/[locale]/(auth)/magic-link/page.tsx`

Magic link request page:

```tsx
// Shows email input + "Send magic link" button
// Uses CyberInput for email field
// Shows success message after sending
// Rate limit countdown if 429
```

**New file:** `frontend/src/app/[locale]/(auth)/magic-link/verify/page.tsx`

Magic link verification page:

```tsx
// Extracts token from URL: ?token=...
// Automatically calls authApi.verifyMagicLink(token)
// Shows loading spinner during verification
// On success: store tokens, redirect to dashboard
// On error: show "Link expired or invalid" with retry option
```

### 7.4 Login/Password Toggle

**File:** `frontend/src/app/[locale]/(auth)/login/page.tsx`

Add a toggle between "Email" and "Username" modes in the login form. The existing `login_or_email` field already accepts both on the backend, so this is purely a UX label change.

**File:** `frontend/src/app/[locale]/(auth)/register/page.tsx`

Add a toggle between "Register with email" and "Register with username only":

- **Email mode** (default): Current flow — email + password + OTP verification
- **Username mode**: Username + password only — no OTP, account active immediately

### 7.5 Update Zustand Store

**File:** `frontend/src/stores/auth-store.ts`

Add new actions:

```typescript
interface AuthActions {
  // Existing
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  register: (login: string, email: string, password: string) => Promise<void>;
  // ...

  // New
  oauthLogin: (provider: string, code: string, state: string, redirectUri: string) => Promise<void>;
  requestMagicLink: (email: string) => Promise<void>;
  verifyMagicLink: (token: string) => Promise<void>;
  registerWithoutEmail: (login: string, password: string) => Promise<void>;
}
```

### 7.6 Update API Module

**File:** `frontend/src/lib/api/auth.ts`

Add new API functions:

```typescript
// OAuth login
oauthLoginAuthorize(provider: string, redirectUri: string): Promise<{ authorize_url: string; state: string }>;
oauthLoginCallback(provider: string, data: { code: string; state: string; redirect_uri: string }): Promise<AuthResponse>;

// Magic link
requestMagicLink(email: string): Promise<{ message: string }>;
verifyMagicLink(token: string): Promise<TokenResponse>;

// Register without email
registerWithoutEmail(login: string, password: string): Promise<RegisterResponse>;
```

### 7.7 i18n Updates

**File:** `frontend/messages/en-EN/auth.json` — add keys for all 38 locales.

New keys to add:

```json
{
  "Auth": {
    "login": {
      "magicLinkTab": "Magic Link",
      "sendMagicLink": "Send Login Link",
      "magicLinkSent": "Check your email for the login link",
      "magicLinkExpired": "This link has expired. Please request a new one.",
      "usernameOrEmail": "Username or email",
      "loginModeEmail": "Use email",
      "loginModeUsername": "Use username"
    },
    "register": {
      "registerModeEmail": "Register with email",
      "registerModeUsername": "Register with username only",
      "usernameOnlyWarning": "Without email, you won't be able to recover your password.",
      "usernameLabel": "Username"
    },
    "oauth": {
      "continueWithGoogle": "Continue with Google",
      "continueWithGithub": "Continue with GitHub",
      "continueWithDiscord": "Continue with Discord",
      "continueWithApple": "Continue with Apple",
      "continueWithMicrosoft": "Continue with Microsoft",
      "continueWithX": "Continue with X",
      "continueWithTelegram": "Continue with Telegram",
      "oauthProcessing": "Completing sign in...",
      "oauthError": "Authentication failed. Please try again.",
      "oauthAccountCreated": "Account created via {provider}",
      "noEmailFromProvider": "This provider didn't share your email. Please add one to your profile.",
      "providerAlreadyLinked": "This {provider} account is already linked to another user."
    },
    "magicLink": {
      "title": "Passwordless Login",
      "subtitle": "We'll send you a link to sign in instantly",
      "emailPlaceholder": "Enter your email",
      "sendButton": "Send Login Link",
      "checkInbox": "Check your inbox",
      "checkInboxDesc": "We sent a login link to {email}. Click the link to sign in.",
      "resend": "Didn't get it? Send again",
      "verifying": "Verifying your link...",
      "expired": "This link has expired",
      "expiredDesc": "Login links are valid for 15 minutes. Please request a new one.",
      "invalid": "Invalid link",
      "invalidDesc": "This link is invalid or has already been used.",
      "success": "You're in!",
      "requestNewLink": "Request new link"
    }
  }
}
```

---

## 8. Mobile Implementation

### 8.1 Native SDKs

Add to `cybervpn_mobile/pubspec.yaml`:

```yaml
dependencies:
  google_sign_in: ^6.2.2          # Google Sign In (latest)
  sign_in_with_apple: ^6.1.4      # Apple Sign In (latest)
  # Discord, Microsoft, X use web-based OAuth (url_launcher + deep links)
```

**Why native SDKs for Google and Apple only:**
- Google: `google_sign_in` provides native UI, one-tap sign-in, and better UX on Android/iOS
- Apple: Required by App Store Review Guidelines when offering social login — must use `sign_in_with_apple`
- Discord/Microsoft/X: No official Flutter SDK; use web-based OAuth via `url_launcher` (same pattern as existing GitHub/Telegram flows)

### 8.2 Extend OAuthProvider Enum

**File:** `cybervpn_mobile/lib/features/profile/domain/entities/oauth_provider.dart`

```dart
enum OAuthProvider {
  telegram,
  github,
  google,
  apple,
  discord,
  microsoft,
  twitter,  // X
}
```

### 8.3 OAuth Login Integration

**New file:** `cybervpn_mobile/lib/features/auth/domain/usecases/oauth_login.dart`

```dart
class OAuthLoginUseCase {
  final AuthRepository _authRepository;

  Future<Either<Failure, UserEntity>> execute({
    required OAuthProvider provider,
    required String code,
    required String state,
    required String redirectUri,
  }) async {
    // Calls POST /oauth/{provider}/login/callback
    // Returns tokens + user
  }
}
```

**New file:** `cybervpn_mobile/lib/features/auth/data/datasources/oauth_remote_ds.dart`

```dart
class OAuthRemoteDataSource {
  final ApiClient _client;

  /// Get OAuth authorization URL
  Future<OAuthAuthorizeResponse> getAuthorizeUrl(String provider, String redirectUri);

  /// Exchange code for tokens (login/register)
  Future<(UserModel, TokenModel)> loginCallback(String provider, OAuthLoginCallbackRequest request);
}
```

### 8.4 Google Sign In Flow (Native)

```dart
class GoogleSignInService {
  final GoogleSignIn _googleSignIn = GoogleSignIn(scopes: ['email', 'profile']);

  Future<GoogleSignInAuthentication?> signIn() async {
    final account = await _googleSignIn.signIn();
    if (account == null) return null;
    return await account.authentication;
    // Returns serverAuthCode → send to backend for token exchange
  }
}
```

**Android configuration:**
- Add Google Services JSON to `android/app/google-services.json`
- Configure OAuth client ID in Google Cloud Console
- SHA-1/SHA-256 fingerprints registered

**iOS configuration:**
- Add `GIDClientID` to `ios/Runner/Info.plist`
- Add URL scheme for Google Sign In redirect

### 8.5 Apple Sign In Flow (Native)

```dart
class AppleSignInService {
  Future<AuthorizationCredentialAppleID?> signIn() async {
    final credential = await SignInWithApple.getAppleIDCredential(
      scopes: [
        AppleIDAuthorizationScopes.email,
        AppleIDAuthorizationScopes.fullName,
      ],
    );
    // Returns authorizationCode → send to backend for token exchange
    // Also returns identityToken (JWT) with email
    return credential;
  }
}
```

**iOS configuration:**
- Enable "Sign In with Apple" capability in Xcode
- Configure in Apple Developer Portal

**Android configuration:**
- Uses web-based fallback via `url_launcher` (not native)

### 8.6 Web-based OAuth (Discord, Microsoft, X)

Same pattern as existing GitHub/Telegram flows in `social_accounts_screen.dart`:

```dart
Future<void> _handleOAuthLogin(OAuthProvider provider) async {
  // 1. Get authorize URL from backend
  final response = await authRemoteDs.getAuthorizeUrl(
    provider.name,
    'cybervpn://oauth/callback',
  );

  // 2. Store state in local storage for validation
  await _storeOAuthState(response.state, provider);

  // 3. Launch in external browser
  await launchUrl(
    Uri.parse(response.authorizeUrl),
    mode: LaunchMode.externalApplication,
  );

  // 4. Deep link handler (in _handleDeepLink) will receive callback
}
```

### 8.7 Deep Link Configuration

**Android** (`AndroidManifest.xml`):
```xml
<intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="cybervpn" android:host="oauth" android:pathPrefix="/callback" />
    <data android:scheme="cybervpn" android:host="magic-link" android:pathPrefix="/verify" />
</intent-filter>
```

**iOS** (`Info.plist`):
```xml
<key>CFBundleURLSchemes</key>
<array>
    <string>cybervpn</string>
</array>
```

### 8.8 Magic Link Flow (Mobile)

**New file:** `cybervpn_mobile/lib/features/auth/presentation/screens/magic_link_screen.dart`

```dart
class MagicLinkScreen extends ConsumerStatefulWidget {
  // 1. Email input with CyberTextField
  // 2. "Send Login Link" button
  // 3. Success state: "Check your email" message
  // 4. Rate limit handling
}
```

**Deep link handler** in `main.dart` or app router:

```dart
// Handle cybervpn://magic-link/verify?token=...
if (uri.host == 'magic-link' && uri.path == '/verify') {
  final token = uri.queryParameters['token'];
  if (token != null) {
    // Call POST /auth/magic-link/verify
    // Store tokens, navigate to connection screen
  }
}
```

### 8.9 Login/Password Toggle (Mobile)

**File:** `cybervpn_mobile/lib/features/auth/presentation/widgets/login_form.dart`

The login form currently has email + password fields. Add:

- The login field already accepts email or username (backend `login_or_email`)
- Update the hint text to say "Username or email"
- No structural change needed for login

**File:** `cybervpn_mobile/lib/features/auth/presentation/screens/register_screen.dart`

Add a toggle:
- **Email mode** (default): username + email + password → OTP verification
- **Username only mode**: username + password → immediately active

### 8.10 Update SocialAccountsScreen

**File:** `cybervpn_mobile/lib/features/profile/presentation/screens/social_accounts_screen.dart`

Add cards for all 7 providers (currently only Telegram and GitHub). Each card shows:
- Provider icon + name
- Linked username/email (if linked)
- Link/Unlink button

### 8.11 Social Login Buttons on Login Screen

**File:** `cybervpn_mobile/lib/features/auth/presentation/screens/login_screen.dart`

Currently shows only Telegram social login button. Add:
- Google (native `google_sign_in`)
- Apple (native `sign_in_with_apple`, iOS only — hide on Android)
- GitHub, Discord, Microsoft, X (web-based via `url_launcher`)

Layout: grid of circular icon buttons below the login form, matching cyberpunk theme.

### 8.12 i18n Updates

**File:** `cybervpn_mobile/lib/core/l10n/arb/app_en.arb` — add new keys.

```json
{
  "authContinueWithGoogle": "Continue with Google",
  "authContinueWithApple": "Continue with Apple",
  "authContinueWithDiscord": "Continue with Discord",
  "authContinueWithMicrosoft": "Continue with Microsoft",
  "authContinueWithX": "Continue with X",
  "authContinueWithGithub": "Continue with GitHub",
  "authContinueWithTelegram": "Continue with Telegram",
  "authMagicLinkTitle": "Passwordless Login",
  "authMagicLinkSubtitle": "We'll send you a link to sign in instantly",
  "authMagicLinkSend": "Send Login Link",
  "authMagicLinkCheckInbox": "Check your inbox",
  "authMagicLinkCheckInboxDesc": "We sent a login link to {email}",
  "authMagicLinkResend": "Send again",
  "authMagicLinkExpired": "This link has expired",
  "authMagicLinkInvalid": "Invalid or used link",
  "authMagicLinkVerifying": "Verifying...",
  "authRegisterUsernameOnly": "Register with username only",
  "authRegisterUsernameOnlyWarning": "Without email, you won't be able to recover your password",
  "authUsernameOrEmail": "Username or email",
  "authOAuthProcessing": "Completing sign in...",
  "authOAuthError": "Authentication failed",
  "authOAuthAccountCreated": "Account created via {provider}",
  "authNoEmailFromProvider": "Add an email to your profile for password recovery",
  "profileLinkedAccounts": "Linked Accounts",
  "profileLinkProvider": "Link {provider}",
  "profileUnlinkProvider": "Unlink {provider}",
  "profileProviderLinked": "{provider} linked successfully",
  "profileProviderUnlinked": "{provider} unlinked"
}
```

All 27 locales need these keys translated.

---

## 9. Security Requirements

### 9.1 OAuth Security

| Requirement | Implementation |
|-------------|---------------|
| **CSRF protection** | State parameter via `OAuthStateService` (existing) |
| **PKCE** | Code verifier/challenge for Google, Apple, Microsoft, X |
| **State single-use** | Redis atomic get+delete (existing in `validate_and_consume`) |
| **State TTL** | 10 minutes (existing) |
| **Nonce** (Apple) | Generated per-request, validated in ID token |
| **Redirect URI validation** | Whitelist of allowed redirect URIs per provider |
| **Token storage** | Provider access/refresh tokens encrypted at rest in `oauth_accounts` |

### 9.2 Magic Link Security

| Requirement | Implementation |
|-------------|---------------|
| **Single-use tokens** | Redis atomic get+delete |
| **TTL** | 15 minutes |
| **Rate limiting** | 5 requests per hour per email |
| **Email enumeration prevention** | Always return "If registered, link sent" (no user existence leak) |
| **Token entropy** | `secrets.token_urlsafe(48)` — 64 characters, 288 bits |
| **IP binding** | Optional — log warning if IP changes between request and verify |

### 9.3 Account Security

| Requirement | Implementation |
|-------------|---------------|
| **Last auth method protection** | Cannot unlink last auth method (must have at least password OR one OAuth) |
| **Email verification for auto-link** | Only auto-link OAuth by email if provider marks email as verified |
| **Brute force protection** | Existing `LoginProtectionService` — progressive lockout |
| **2FA enforcement** | If user has 2FA enabled, require TOTP after OAuth login |

### 9.4 Mobile-Specific Security

| Requirement | Implementation |
|-------------|---------------|
| **Deep link validation** | Verify state parameter matches stored state before processing callback |
| **Secure storage** | Store OAuth tokens in Flutter Secure Storage (existing pattern) |
| **Certificate pinning** | Existing — applies to all new OAuth endpoints |
| **Biometric gate** | If biometric lock is enabled, require biometric after OAuth login |

---

## 10. API Contracts

### 10.1 OAuth Login — Authorize

```
GET /api/v1/oauth/{provider}/login?redirect_uri={uri}
Authorization: None (public)
```

**Response 200:**
```json
{
  "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth?...",
  "state": "abc123..."
}
```

**Providers:** `google`, `github`, `discord`, `apple`, `microsoft`, `twitter`

### 10.2 OAuth Login — Callback

```
POST /api/v1/oauth/{provider}/login/callback
Authorization: None (public)
Content-Type: application/json
```

**Request:**
```json
{
  "code": "authorization_code_from_provider",
  "state": "abc123...",
  "redirect_uri": "https://app.cybervpn.com/en-EN/oauth/callback"
}
```

**Response 200:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "login": "username",
    "email": "user@example.com",
    "role": "user",
    "telegram_id": null,
    "is_active": true,
    "is_email_verified": true,
    "created_at": "2026-02-09T12:00:00Z"
  },
  "is_new_user": false
}
```

**Error 401:** Invalid state or code exchange failure
**Error 409:** Provider account already linked to different user

### 10.3 OAuth Account Linking — Authorize (Authenticated)

```
GET /api/v1/oauth/{provider}/authorize?redirect_uri={uri}
Authorization: Bearer {access_token}
```

*(Existing endpoint, extended to all providers)*

### 10.4 OAuth Account Linking — Callback (Authenticated)

```
POST /api/v1/oauth/{provider}/callback
Authorization: Bearer {access_token}
Content-Type: application/json
```

*(Existing endpoint for Telegram/GitHub, extended to all providers)*

### 10.5 Magic Link — Request

```
POST /api/v1/auth/magic-link
Authorization: None (public)
Content-Type: application/json
```

**Request:**
```json
{
  "email": "user@example.com"
}
```

**Response 200:**
```json
{
  "message": "If this email is registered, a login link has been sent."
}
```

**Response 429:** Rate limited

### 10.6 Magic Link — Verify

```
POST /api/v1/auth/magic-link/verify
Authorization: None (public)
Content-Type: application/json
```

**Request:**
```json
{
  "token": "abc123..."
}
```

**Response 200:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Response 400:** Invalid or expired token
**Response 429:** Rate limited

### 10.7 Register (Updated)

```
POST /api/v1/auth/register
Authorization: None (public)
Content-Type: application/json
```

**Request (with email — existing flow):**
```json
{
  "login": "username",
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "locale": "en-EN"
}
```

**Request (without email — new flow):**
```json
{
  "login": "username",
  "password": "SecurePassword123!"
}
```

**Response 201 (without email):**
```json
{
  "id": "uuid",
  "login": "username",
  "email": null,
  "is_active": true,
  "is_email_verified": false,
  "message": "Account created. Add an email for password recovery."
}
```

---

## 11. Testing Strategy

### 11.1 Backend Tests

| Test Category | File | Tests |
|---------------|------|-------|
| Unit: Provider classes | `tests/unit/infrastructure/oauth/test_*.py` | Each provider: `test_authorize_url`, `test_exchange_code_success`, `test_exchange_code_failure`, `test_pkce_generation` |
| Unit: Magic link service | `tests/unit/application/services/test_magic_link_service.py` | `test_generate`, `test_validate_and_consume`, `test_single_use`, `test_expired`, `test_rate_limit` |
| Unit: OAuth login use case | `tests/unit/application/use_cases/auth/test_oauth_login.py` | `test_existing_oauth_user`, `test_existing_email_user`, `test_new_user`, `test_email_conflict` |
| Integration: OAuth routes | `tests/integration/api/v1/oauth/test_oauth_login.py` | Full flow per provider with mocked provider APIs |
| Integration: Magic link routes | `tests/integration/api/v1/auth/test_magic_link.py` | Full flow with mocked email dispatch |
| Integration: Register without email | `tests/integration/api/v1/auth/test_register.py` | `test_register_without_email`, `test_register_with_email` |

### 11.2 Frontend Tests

| Test Category | File | Tests |
|---------------|------|-------|
| Component: SocialAuthButtons | `__tests__/SocialAuthButtons.test.tsx` | Renders all 7 providers, click handlers fire, loading state |
| Page: OAuth callback | `__tests__/oauth-callback.test.tsx` | Extracts params, calls API, redirects on success/error |
| Page: Magic link | `__tests__/magic-link.test.tsx` | Submit email, show success, rate limit countdown |
| Store: auth-store | `__tests__/auth-store.test.ts` | `oauthLogin`, `requestMagicLink`, `verifyMagicLink` actions |

### 11.3 Mobile Tests

| Test Category | File | Tests |
|---------------|------|-------|
| Unit: OAuthLoginUseCase | `test/features/auth/domain/usecases/oauth_login_test.dart` | Success, failure, new user |
| Widget: SocialLoginButtons | `test/features/auth/presentation/widgets/social_login_button_test.dart` | All providers render, tap handlers |
| Widget: MagicLinkScreen | `test/features/auth/presentation/screens/magic_link_screen_test.dart` | Email input, send, success state |
| Integration: Deep link | `test/core/deep_link_test.dart` | OAuth callback parsing, magic link parsing |

---

## 12. Rollout Plan

### Phase 1: Backend Foundation (Week 1-2)

1. Implement `OAuthStateService` PKCE enhancement
2. Implement all 5 new OAuth providers (Google, Discord, Apple, Microsoft, Twitter)
3. Implement `MagicLinkService`
4. Implement `OAuthLoginUseCase`
5. Add OAuth login routes (unauthenticated)
6. Add magic link routes
7. Update `RegisterRequest`/`RegisterUseCase` for optional email
8. Add settings for all new providers
9. Write backend tests

### Phase 2: Frontend Integration (Week 2-3)

1. Wire `SocialAuthButtons` handlers
2. Add Apple, Microsoft, X buttons
3. Create OAuth callback page
4. Create magic link request + verify pages
5. Add login/password toggle to registration
6. Update Zustand store with new actions
7. Update API module
8. Add i18n keys for all 38 locales
9. Write frontend tests

### Phase 3: Mobile Integration (Week 3-4)

1. Add `google_sign_in` and `sign_in_with_apple` packages
2. Extend `OAuthProvider` enum
3. Implement native Google/Apple sign-in services
4. Implement web-based OAuth for Discord/Microsoft/X
5. Configure deep links for OAuth callbacks and magic links
6. Create magic link screen
7. Update login/register screens with all social buttons
8. Update `SocialAccountsScreen` with all providers
9. Add i18n keys for all 27 locales
10. Write mobile tests

### Phase 4: QA & Hardening (Week 4-5)

1. End-to-end testing across all providers on all platforms
2. Security review (PKCE validation, state handling, rate limits)
3. Load testing on OAuth + magic link endpoints
4. App Store / Play Store review for new capabilities (Apple Sign In requirement)
5. Documentation: OAuth app setup guide for ops team

---

## 13. Third-Party OAuth App Setup Guide

Each provider requires creating an OAuth application in their developer console. Document for the ops team:

### Google

1. Go to Google Cloud Console → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID (Web application)
3. Add authorized redirect URIs:
   - `https://app.cybervpn.com/en-EN/oauth/callback` (frontend, per locale)
   - `cybervpn://oauth/callback` (mobile deep link — register as custom URI)
4. Copy Client ID → `GOOGLE_CLIENT_ID`
5. Copy Client Secret → `GOOGLE_CLIENT_SECRET`
6. Enable Google+ API (for userinfo endpoint)

### GitHub

Already configured. Add mobile redirect URI if not present.

### Discord

1. Go to Discord Developer Portal → Applications → New Application
2. OAuth2 → Add redirect URIs (same pattern as Google)
3. Copy Client ID → `DISCORD_CLIENT_ID`
4. Copy Client Secret → `DISCORD_CLIENT_SECRET`

### Apple

1. Apple Developer → Certificates, Identifiers & Profiles → Service IDs
2. Create a Service ID: `com.cybervpn.auth`
3. Enable "Sign In with Apple", configure return URLs
4. Create a Key for Sign In with Apple (download `.p8` private key)
5. Set env vars: `APPLE_CLIENT_ID`, `APPLE_TEAM_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY`

### Microsoft

1. Azure Portal → App registrations → New registration
2. Set redirect URIs (Web + Mobile)
3. Supported account types: "Accounts in any organizational directory and personal Microsoft accounts"
4. Copy Application (client) ID → `MICROSOFT_CLIENT_ID`
5. Create client secret → `MICROSOFT_CLIENT_SECRET`
6. Tenant ID: use "common" for multi-tenant

### X (Twitter)

1. Twitter Developer Portal → Projects & Apps → Create App
2. Enable OAuth 2.0 (not 1.0a)
3. Add callback URLs
4. Type: Web App, Confidential Client
5. Copy Client ID → `TWITTER_CLIENT_ID`
6. Copy Client Secret → `TWITTER_CLIENT_SECRET`

### Telegram

Already configured. No changes needed.

---

## 14. Dependency Summary

### Backend (new packages)

```
# None — all OAuth providers use httpx (already installed)
# Apple: may need PyJWT or joserfc for ES256 client_secret generation
# Google: may need google-auth for ID token validation (optional — can validate manually)
```

### Frontend (new packages)

```
# None — all OAuth is server-side redirect based
```

### Mobile (new packages)

```yaml
google_sign_in: ^6.2.2
sign_in_with_apple: ^6.1.4
```

---

## 15. Open Questions

| # | Question | Default Answer |
|---|----------|----------------|
| Q1 | Should OAuth login create users with `role=viewer` or `role=user`? | `role=viewer` (same as email registration) |
| Q2 | Should 2FA be required after OAuth login if enabled on the account? | Yes — redirect to 2FA screen after OAuth tokens received |
| Q3 | Should magic link work for unregistered emails (auto-register)? | Yes — creates new account with auto-verified email |
| Q4 | For username-only registration, should we enforce a minimum password length different from email registration? | No — same 12-char minimum |
| Q5 | Should we support account deletion cascade for OAuth accounts? | Yes — `ondelete=CASCADE` already set on `oauth_accounts.user_id` |
| Q6 | Apple Sign In: store name on first auth in `admin_users` or `oauth_accounts`? | `oauth_accounts.provider_username` (consistent with other providers) |
| Q7 | X/Twitter: when email is not available, should we require email before completing login? | Yes — redirect to "complete profile" screen with email input |
