# OAuth Setup And Rollout Guide

## Scope

This guide documents the production web OAuth stack for:

- Google
- GitHub
- Discord
- Facebook
- Microsoft
- X

Current implementation assumptions:

- FastAPI is the only auth authority and session issuer.
- Next.js handles browser-facing OAuth start/callback under same origin.
- Web provider callbacks are canonical and non-localized.
- Login-only flows do not retain provider tokens unless an explicit allowlist enables retention.
- `X` is the product label, but the internal provider slug remains `twitter`.

Apple code still exists in the repository, but it is not part of the active rollout plan.

## Topology

Web flow:

1. Browser hits `GET /api/oauth/start/{provider}` on the frontend origin.
2. Next.js BFF requests `GET /api/v1/oauth/{provider}/login` from FastAPI.
3. FastAPI creates OAuth state and PKCE material where required.
4. Browser is redirected to the provider.
5. Provider redirects back to `GET /api/oauth/callback/{provider}` on the frontend origin.
6. Next.js BFF validates the signed `oauth_tx` cookie and posts `code/state` to `POST /api/v1/oauth/{provider}/login/callback`.
7. FastAPI issues auth cookies or returns `requires_2fa=true`.
8. Next.js either forwards auth cookies to the browser or stages `pending_2fa` and redirects to localized login.

Cookie topology:

- `oauth_tx`: signed, `httpOnly`, 10 minutes, BFF transaction state.
- Backend auth cookies: forwarded from FastAPI to the browser after successful callback.
- `pending_2fa`: signed, `httpOnly`, 15 minutes, used when OAuth or Telegram login must continue through TOTP.
- `oauth_result`: short-lived non-`httpOnly` analytics marker consumed after session bootstrap.

## Canonical Callback URIs

Production examples below assume the current S1 canonical frontend origin is `https://cyber-vpn.net`.

Web callback template:

```text
{OAUTH_WEB_BASE_URL}/api/oauth/callback/{provider}
```

S1 provider slugs:

| Product label | Internal slug | Callback path |
|---|---|---|
| Google | `google` | `/api/oauth/callback/google` |
| GitHub | `github` | `/api/oauth/callback/github` |

Deferred provider slugs may remain in backend code for later stages, but S1 must not enable them publicly:
`discord`, `facebook`, `microsoft`, `twitter`, `apple`.

Environment matrix:

| Environment | `OAUTH_WEB_BASE_URL` | Example Google callback |
|---|---|---|
| Local | `http://localhost:3000` | `http://localhost:3000/api/oauth/callback/google` |
| Staging | `https://<staging-frontend-origin>` | `https://<staging-frontend-origin>/api/oauth/callback/google` |
| Production | `https://cyber-vpn.net` | `https://cyber-vpn.net/api/oauth/callback/google` |

Rules:

- Do not register locale-prefixed callbacks such as `/{locale}/oauth/callback`.
- Do not register backend `/api/v1/oauth/.../login/callback` as the browser callback for web login.
- Native or universal-link callbacks must be exact entries in `OAUTH_ALLOWED_REDIRECT_URIS` and stay isolated from the web flow.

## Environment Variables

### Backend

Core OAuth settings:

| Variable | Purpose |
|---|---|
| `OAUTH_WEB_BASE_URL` | Canonical frontend origin used to build browser callback URIs |
| `OAUTH_ALLOWED_REDIRECT_URIS` | Exact native/mobile callback allowlist |
| `OAUTH_ENABLED_LOGIN_PROVIDERS` | Rollout gate for active providers |
| `OAUTH_TRUSTED_EMAIL_LINK_PROVIDERS` | Allowlist for auto-link by verified email |
| `OAUTH_RETAINED_ACCESS_TOKEN_PROVIDERS` | Providers allowed to keep access tokens at rest |
| `OAUTH_RETAINED_REFRESH_TOKEN_PROVIDERS` | Providers allowed to keep refresh tokens at rest |
| `OAUTH_TOKEN_ENCRYPTION_KEY` | Dedicated AES-GCM key for provider tokens |
| `OAUTH_TOKEN_PLAINTEXT_FALLBACK_ENABLED` | Temporary rollout fallback for legacy plaintext rows |

Provider credentials:

- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`
- Deferred until later stages: `DISCORD_*`, `FACEBOOK_*`, `MICROSOFT_*`, `TWITTER_*`, `APPLE_*`

Recommended production baseline:

```env
OAUTH_WEB_BASE_URL=https://cyber-vpn.net
OAUTH_ALLOWED_REDIRECT_URIS=cybervpn://oauth/callback
OAUTH_ENABLED_LOGIN_PROVIDERS=google,github
OAUTH_TRUSTED_EMAIL_LINK_PROVIDERS=google,github
OAUTH_RETAINED_ACCESS_TOKEN_PROVIDERS=
OAUTH_RETAINED_REFRESH_TOKEN_PROVIDERS=
OAUTH_TOKEN_PLAINTEXT_FALLBACK_ENABLED=false
```

### Frontend

| Variable | Purpose |
|---|---|
| `API_URL` | Server-side BFF target for route handlers, usually backend origin |
| `NEXT_PUBLIC_API_URL` | Browser-side API base for normal frontend API client |
| `OAUTH_TRANSACTION_SECRET` | Required in production for signed `oauth_tx` |
| `PENDING_2FA_SECRET` | Optional dedicated secret for `pending_2fa`; falls back to `OAUTH_TRANSACTION_SECRET` |

Recommended local example:

```env
API_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
OAUTH_TRANSACTION_SECRET=replace-with-strong-secret
PENDING_2FA_SECRET=replace-with-strong-secret
```

## Provider Policy Matrix

| Provider | Protocol | PKCE | Auto-link policy | Notes |
|---|---|---|---|---|
| Google | OIDC auth code | Yes | Allowed only after validated ID token with `email_verified=true` | Uses discovery + JWKS |
| GitHub | OAuth 2.0 auth code | Yes | Allowed only with verified email from `/user/emails` | Callback must stay exact |
| Discord | OAuth 2.0 auth code | Deferred | Disabled in S1 | Keep implementation for later stage only |
| Facebook | OAuth 2.0 auth code | Deferred | Disabled in S1 | Legacy linking endpoints must return disabled-provider in S1 |
| Microsoft | OIDC auth code | Deferred | Disabled in S1 | Test both personal and work/school accounts before any later rollout |
| X | OAuth 2.0 auth code | Deferred | Disabled in S1 | Internal slug is `twitter` |
| Apple | OIDC auth code | Deferred | Disabled in S1 | Keep out of S1 provider consoles and runtime config |

Trust semantics in code:

- `google` and `github` can auto-link only when provider-specific verification rules pass.
- Deferred providers must not auto-link by email in S1 even if accidentally added to env config.
- Deferred providers must not complete public login or linking flows until a later stage explicitly approves them.

## Provider Console Notes

### Google

- Console: Google Cloud Console, OAuth consent screen + Credentials.
- Redirect URI: `https://cyber-vpn.net/api/oauth/callback/google`
- Scopes: `openid email profile`
- Keep the app in the correct publishing state before broad rollout.
- Offline access and consent prompts are already requested by backend code.

### GitHub

- Console: GitHub Developer settings, OAuth Apps.
- Redirect URI: `https://cyber-vpn.net/api/oauth/callback/github`
- Scope: `read:user user:email`
- PKCE is enabled in the app flow; do not document or configure it as a legacy non-PKCE app flow.
- Auto-link only works when `/user/emails` returns a verified address.

### Discord

- Console: Discord Developer Portal.
- Redirect URI: deferred until a later stage.
- Scope: `identify email`
- S1 must return a disabled-provider response before state validation or token exchange.
- Re-evaluate verified-email handling before any later-stage enablement.

### Facebook

- Console: Meta for Developers, Facebook Login for Web.
- Redirect URI: deferred until a later stage.
- Scopes: `public_profile,email`
- Pin the Graph API version in the app review and operational docs.
- Confirm app mode, domain verification, and allowed redirect URI settings before enabling production traffic.
- Existing-account auto-link stays disabled unless policy is explicitly revised.

### Microsoft

- Console: Microsoft Entra admin center / App registrations.
- Redirect URI: deferred until a later stage.
- Scopes: `openid email profile User.Read`
- `MICROSOFT_TENANT_ID=common` supports both personal Microsoft accounts and Entra work/school accounts.
- Later-stage staging smoke must cover both account classes before enablement.

### X

- Console: X Developer Portal.
- Redirect URI: deferred until a later stage.
- Scope in current code: `users.read`
- S1 must return a disabled-provider response before state validation or token exchange.
- Do not enable retention of X tokens unless a downstream feature requires them.

## Reverse Proxy And Cookie Requirements

Frontend assumptions:

- Browser-facing OAuth routes live on the same origin as the app.
- `/api/oauth/*` must terminate on Next.js.
- `/api/v1/*` must route to FastAPI.

Production checklist:

- `OAUTH_WEB_BASE_URL` must match the public frontend origin exactly.
- `cookie_secure=true` on backend in HTTPS environments.
- TLS termination must preserve `X-Forwarded-For` only from trusted proxies.
- Callback responses must not be cached by CDN or edge middleware.

## Local And Staging Verification

### Local

1. Set backend `OAUTH_WEB_BASE_URL=http://localhost:3000`.
2. Set frontend `API_URL` and `NEXT_PUBLIC_API_URL` to the local backend.
3. Register local provider callback URIs that point to `http://localhost:3000/api/oauth/callback/{provider}`.
4. Run backend and frontend.
5. Verify `/api/oauth/start/{provider}` sets `oauth_tx` and redirects correctly.

### Staging Smoke Matrix

Minimum staging checks before production:

- Google login from signed-out browser.
- GitHub login with PKCE.
- Deferred providers return disabled-provider responses before state validation or token exchange.
- Existing linked-account login repeat.
- Existing local-account collision for non-S1 providers is deferred until those providers are approved.
- `requires_2fa=true` continuation for OAuth and Telegram bot-link completion.
- Denied-consent redirect to localized login with stable `oauth_error`.
- Tampered or expired state rejection.
- Fresh protected-route access after social login.
- Logout, refresh, and login repetition.

## Token Retention And Encryption

Default policy:

- Do not retain provider access tokens.
- Do not retain provider refresh tokens.
- Encrypt retained tokens at rest with `OAUTH_TOKEN_ENCRYPTION_KEY`.

Rollout sequence for retention hardening:

1. Set `OAUTH_TOKEN_ENCRYPTION_KEY`.
2. Keep `OAUTH_TOKEN_PLAINTEXT_FALLBACK_ENABLED=true` briefly while legacy rows still exist.
3. Run the data cleanup / rewrite pass for old rows.
4. Switch `OAUTH_TOKEN_PLAINTEXT_FALLBACK_ENABLED=false`.

If a future feature needs retention, allow it explicitly:

```env
OAUTH_RETAINED_ACCESS_TOKEN_PROVIDERS=google
OAUTH_RETAINED_REFRESH_TOKEN_PROVIDERS=google
```

Do not enable retention pre-emptively.

## Rollout Plan

Recommended enablement order:

1. Google for S1.
2. GitHub for S1.
3. Additional providers only in a later approved stage/backlog item.

Per-provider release gate:

- Provider credentials configured in backend.
- Exact callback URI registered in provider console.
- Staging smoke for that provider passes.
- Error-rate telemetry remains clean for 24 hours before enabling the next provider.

Monitoring dimensions to watch:

- provider
- environment
- `oauth_error`
- `requires_2fa`
- callback status code
- collision / linking-required events

Rollback:

1. Remove the provider from `OAUTH_ENABLED_LOGIN_PROVIDERS`.
2. Keep the provider console callback intact until rollback is confirmed complete.
3. Inspect recent `oauth_error` and backend logs.
4. If retention was enabled for that provider, decide whether to preserve or purge retained tokens separately.

## Final Local Verification Commands

Run from repo root:

```bash
cd backend && pytest tests/security/test_oauth_security.py tests/unit/application/use_cases/auth/test_oauth_login.py tests/unit/infrastructure/oauth tests/integration/api/v1/oauth/test_oauth_login.py -q --no-cov
cd backend && ruff check src tests

cd frontend && npm run test:run -- src/stores/__tests__/auth-store.test.ts src/features/auth/components/__tests__/SocialAuthButtons.test.tsx 'src/app/[locale]/(auth)/oauth/callback/__tests__/page.test.tsx' src/app/api/oauth/start/[provider]/route.test.ts src/app/api/oauth/callback/[provider]/route.test.ts src/app/api/oauth/__tests__/oauth-web-flow.test.ts
cd frontend && NEXT_TELEMETRY_DISABLED=1 npm run build
cd frontend && npm run lint
```

Expected result:

- Targeted backend tests pass.
- Targeted frontend tests pass.
- Build and lint pass.
- No locale-prefixed web callback remains in the web OAuth path.
