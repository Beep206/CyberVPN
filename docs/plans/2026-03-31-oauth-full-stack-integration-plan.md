# OAuth Full-Stack Integration Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Deliver a production-grade web OAuth login stack for Google, GitHub, Discord, Facebook, Microsoft, and X that works end-to-end on the existing Next.js 16 frontend and FastAPI backend with strict redirect control, provider-specific trust rules, SSR-safe session establishment, and production verification gates.

**Architecture:** Keep FastAPI as the single authority for users, linked identities, 2FA, token issuance, and audit logging. Add a Next.js BFF shell under `frontend/src/app/api/oauth/*` so the browser only talks to same-origin routes, provider callbacks are exact and non-localized, and locale/return-to state is restored via a signed transaction cookie rather than locale-specific redirect URIs or `sessionStorage`. Use OIDC verification where the provider supports it (Google, Microsoft), PKCE where current docs support it (GitHub, Google, Microsoft, X; Discord only if re-verified), and provider-specific verified-email policy before any auto-linking.

**Tech Stack:** Next.js 16 App Router, React 19, next-intl, Axios, Zustand, FastAPI, Pydantic 2, SQLAlchemy 2, Redis, httpx, PyJWT, optional `joserfc` or `Authlib` for OIDC/JWK validation, Vitest, pytest, Ruff.

---

## Why this plan

- Existing backend already owns user lifecycle, JWT/cookie sessions, 2FA, and OAuth account records. Introducing Auth.js/Better Auth would duplicate identity authority and create sync risk.
- Current web OAuth callback depends on locale-prefixed routes and `sessionStorage`, which is fragile under exact redirect matching, popup/tab changes, and JS hydration failures.
- `backend/src/presentation/api/v1/oauth/routes.py` currently accepts browser-supplied `redirect_uri`; final design must switch to server-controlled exact callback URIs.
- `backend/src/application/use_cases/auth/oauth_login.py` auto-links by email generically; production design must make auto-link provider-aware and verification-aware.
- `backend/src/infrastructure/database/models/oauth_account_model.py` currently stores provider access/refresh tokens in plaintext; login-only flows should not retain them by default.

## Non-Negotiables

1. FastAPI remains the only session issuer and source of truth for auth state.
2. No auth logic goes into `frontend/src/proxy.ts`.
3. Web provider callbacks must be canonical and non-localized.
4. Backend login endpoints must not trust arbitrary browser-supplied `redirect_uri` in the final design.
5. No auto-link by email unless the provider proves the email is verified and the policy explicitly allows it.
6. Provider access/refresh tokens must either be removed from persistence or stored encrypted with rotation support.
7. OAuth failure states must be observable by provider, error code, and environment.
8. The final web flow must complete without client-side token handling and without relying on `sessionStorage` for CSRF-critical state.

## Provider Policy Matrix

| Provider | Protocol | PKCE | Auto-link by email | Required notes |
|---------|----------|------|--------------------|----------------|
| Google | OIDC authorization code | Yes | Yes, only after validated ID token and `email_verified=true` | Use discovery + JWKS; `sub` is stable user key |
| GitHub | OAuth 2.0 web application flow | Yes | Yes, only with primary verified email from `/user/emails` | Current code must be upgraded to PKCE |
| Discord | OAuth 2.0 authorization code | Re-verify against current docs; default to state-only if PKCE is undocumented | Yes, only if `verified=true` and email present | Current code assumes PKCE; docs must be rechecked before keeping it |
| Facebook | OAuth 2.0 authorization code | Re-verify against current Meta manual-flow docs | Default off until verified-email semantics are documented for this app mode | Pin Graph API version and keep scope minimal (`public_profile,email`) |
| Microsoft | OIDC authorization code | Yes | Yes, only after validated ID token claims | Test both Microsoft personal accounts and Entra work/school accounts |
| X | OAuth 2.0 authorization code with PKCE | Yes | Default off unless `users.email` is approved and semantics are confirmed | Keep UI label `X`; internal slug may remain `twitter` until explicit migration |

## Current Gaps To Fix First

- `backend/src/presentation/api/v1/oauth/routes.py` uses origin/path pattern matching for redirect URIs instead of exact server-controlled callback URIs.
- `frontend/src/stores/auth-store.ts` stores OAuth provider and state in `sessionStorage` and completes the callback in client code.
- `frontend/src/app/[locale]/(auth)/oauth/callback/oauth-callback-client.tsx` makes login completion depend on client rendering.
- `backend/src/infrastructure/oauth/github.py` does not use PKCE even though current GitHub docs support and strongly recommend it.
- `backend/src/infrastructure/oauth/discord.py` includes PKCE-style params that are not obvious in the currently crawled Discord docs; this needs explicit confirmation.
- `backend/src/infrastructure/oauth/google.py` and `backend/src/infrastructure/oauth/microsoft.py` rely on access-token userinfo fetches rather than verified OIDC identity validation.
- `backend/src/application/use_cases/auth/oauth_login.py` auto-links any matching email without provider-specific trust checks.
- `backend/src/infrastructure/database/models/oauth_account_model.py` stores provider tokens directly even though login-only flows do not need them.
- Several backend OAuth integration/E2E tests are placeholders and still reference obsolete service names.

## Release Order

1. P0: Contract freeze and callback topology hardening.
2. P1: Backend provider/security normalization.
3. P2: Next.js BFF start/callback flow and UI/session refactor.
4. P3: Data minimization, telemetry, and verification matrix.
5. P4: Staging burn-in and controlled production rollout.

## Definition Of Done

- All six providers can start and finish login on the web through same-origin Next.js routes without manual token handling in the browser.
- Exact provider callback URIs are registered and environment-specific; localized callback URIs are no longer required.
- Google and Microsoft identities are validated through OIDC claims/JWKS, not only userinfo fetches.
- GitHub uses PKCE; Discord/Facebook implementation choices are aligned to current official docs at implementation time.
- Email auto-linking occurs only under explicit provider trust rules and is fully covered by tests.
- The login-only flow does not retain provider access tokens at rest unless an explicitly approved feature requires them.
- `2FA required`, `account collision`, `provider denied consent`, `callback mismatch`, `state mismatch`, and `refresh failure` paths have stable UX and observability.
- Targeted backend/frontend tests, build, lint, and a real staging smoke matrix all pass.

## Final Verification Gate

Run from repo root:

```bash
cd backend && pytest tests/security/test_oauth_security.py tests/unit/application/use_cases/auth/test_oauth_login.py tests/unit/infrastructure/oauth -q
cd backend && pytest tests/integration/api/v1/oauth/test_oauth_login.py -q
cd backend && ruff check src tests

cd frontend && npm run test:run -- src/stores/__tests__/auth-store.test.ts src/features/auth/components/__tests__/SocialAuthButtons.test.tsx 'src/app/[locale]/(auth)/oauth/callback/__tests__/page.test.tsx'
cd frontend && npm run test:run -- src/app/api/oauth/start/[provider]/route.test.ts src/app/api/oauth/callback/[provider]/route.test.ts
cd frontend && NEXT_TELEMETRY_DISABLED=1 npm run build
cd frontend && npm run lint
```

Expected:
- All provider/unit/security tests pass
- New Next.js BFF route tests pass
- Build and lint pass
- No locale-prefixed provider callback dependency remains in the web login path

### Task 1: Freeze the web OAuth contract around exact server-owned callback URIs

**Priority:** P0

**Files:**
- Modify: `backend/src/config/settings.py`
- Modify: `backend/src/presentation/api/v1/oauth/routes.py`
- Modify: `backend/src/presentation/api/v1/oauth/schemas.py`
- Modify: `backend/.env.example`
- Test: `backend/tests/security/test_oauth_security.py`

**Step 1: Write failing contract tests**

Cover:
- login authorize endpoints no longer accept arbitrary browser `redirect_uri` for web flow
- each provider resolves an exact configured callback URI
- unregistered environment/provider combinations fail closed
- legacy locale-prefixed callback URIs are rejected for the new web flow
- safe internal aliases for mobile deep links remain isolated from web flow

**Step 2: Run the focused security tests**

Run:

```bash
cd backend && pytest tests/security/test_oauth_security.py -q
```

Expected: FAIL because the current implementation still accepts caller-supplied redirect URIs.

**Step 3: Implement exact callback resolution**

Add settings shaped around exact URIs, not pattern matching. At minimum define:
- `oauth_web_base_url`
- `oauth_web_callback_prefix` or exact per-provider callback builder
- `oauth_mobile_allowed_redirect_uris` for non-web deep links
- `oauth_allowed_return_to_prefixes`

In routes:
- keep the public API provider enum
- remove browser control over login callback URIs for web login
- resolve the callback URI server-side from settings and provider
- keep a separate path for mobile/native redirect handling if that is still required later

**Step 4: Re-run the backend security tests**

Run:

```bash
cd backend && pytest tests/security/test_oauth_security.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/config/settings.py backend/src/presentation/api/v1/oauth/routes.py backend/src/presentation/api/v1/oauth/schemas.py backend/.env.example backend/tests/security/test_oauth_security.py
git commit -m "feat: freeze oauth callback contract"
```

### Task 2: Move web OAuth start/callback orchestration into Next.js BFF route handlers

**Priority:** P0

**Files:**
- Create: `frontend/src/app/api/oauth/start/[provider]/route.ts`
- Create: `frontend/src/app/api/oauth/callback/[provider]/route.ts`
- Create: `frontend/src/app/api/oauth/start/[provider]/route.test.ts`
- Create: `frontend/src/app/api/oauth/callback/[provider]/route.test.ts`
- Create: `frontend/src/features/auth/lib/oauth-transaction.ts`
- Modify: `frontend/src/stores/auth-store.ts`
- Modify: `frontend/src/lib/api/auth.ts`
- Modify: `frontend/src/app/[locale]/(auth)/oauth/callback/page.tsx`
- Modify: `frontend/src/app/[locale]/(auth)/oauth/callback/oauth-callback-client.tsx`

**Step 1: Write failing route-handler tests**

Cover:
- `GET /api/oauth/start/:provider` sets a short-lived signed transaction cookie and redirects to provider authorize URL
- `GET /api/oauth/callback/:provider` validates the transaction cookie, posts the code/state to backend, forwards `Set-Cookie`, clears transaction state, and redirects to locale-aware `return_to`
- provider mismatch, missing cookie, or denied consent redirects to a stable auth error route
- `2FA required` redirects to the existing challenge flow without establishing a full session

**Step 2: Run the focused frontend tests**

Run:

```bash
cd frontend && npm run test:run -- src/app/api/oauth/start/[provider]/route.test.ts src/app/api/oauth/callback/[provider]/route.test.ts src/stores/__tests__/auth-store.test.ts 'src/app/[locale]/(auth)/oauth/callback/__tests__/page.test.tsx'
```

Expected: FAIL because the current flow still depends on `sessionStorage` and client-side callback completion.

**Step 3: Implement the BFF flow**

- `start` route handler should:
  - read `locale` and validated `return_to`
  - create a signed, short-lived `oauth_tx` cookie
  - call the backend authorize endpoint
  - redirect the browser to the provider
- `callback` route handler should:
  - validate `code`/`state` and the signed `oauth_tx` cookie
  - call the backend callback endpoint server-to-server
  - forward auth cookies from backend to browser
  - redirect to `/{locale}/dashboard` or the validated `return_to`
- `auth-store.ts` should stop storing OAuth state/provider in `sessionStorage` and instead navigate to `/api/oauth/start/${provider}` for web login
- the locale-prefixed callback page should become a graceful legacy fallback page, not the primary completion path

**Step 4: Re-run the focused frontend tests**

Run:

```bash
cd frontend && npm run test:run -- src/app/api/oauth/start/[provider]/route.test.ts src/app/api/oauth/callback/[provider]/route.test.ts src/stores/__tests__/auth-store.test.ts 'src/app/[locale]/(auth)/oauth/callback/__tests__/page.test.tsx'
```

Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/app/api/oauth/start/[provider]/route.ts frontend/src/app/api/oauth/callback/[provider]/route.ts frontend/src/app/api/oauth/start/[provider]/route.test.ts frontend/src/app/api/oauth/callback/[provider]/route.test.ts frontend/src/features/auth/lib/oauth-transaction.ts frontend/src/stores/auth-store.ts frontend/src/lib/api/auth.ts 'frontend/src/app/[locale]/(auth)/oauth/callback/page.tsx' 'frontend/src/app/[locale]/(auth)/oauth/callback/oauth-callback-client.tsx'
git commit -m "feat: move web oauth flow into next route handlers"
```

### Task 3: Replace generic email auto-linking with provider trust policy

**Priority:** P1

**Files:**
- Create: `backend/src/application/services/oauth_trust_policy.py`
- Modify: `backend/src/application/use_cases/auth/oauth_login.py`
- Modify: `backend/src/application/use_cases/auth/account_linking.py`
- Modify: `backend/src/presentation/api/v1/oauth/schemas.py`
- Test: `backend/tests/unit/application/use_cases/auth/test_oauth_login.py`

**Step 1: Write failing policy tests**

Cover:
- Google/Microsoft auto-link only when verified identity claims are present
- GitHub auto-link only when a primary verified email is available
- Discord auto-link only when `verified=true`
- Facebook and X default to `linking_required` unless an approved verified-email rule exists
- collision with an existing account produces an explicit, user-safe response rather than silent linking

**Step 2: Run the use-case tests**

Run:

```bash
cd backend && pytest tests/unit/application/use_cases/auth/test_oauth_login.py -q
```

Expected: FAIL because the current use case links any matching email.

**Step 3: Implement provider trust policy**

- Introduce a normalized provider identity contract that includes:
  - `subject`
  - `email`
  - `email_verified`
  - `display_name`
  - `avatar_url`
  - `provider_claims`
- Move auto-link decisions out of the generic use case into a dedicated trust policy service
- Return explicit outcomes:
  - `authenticated`
  - `created`
  - `linked`
  - `linking_required`
  - `rejected`
- Preserve the existing 2FA gate after the identity is resolved

**Step 4: Re-run the use-case tests**

Run:

```bash
cd backend && pytest tests/unit/application/use_cases/auth/test_oauth_login.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/application/services/oauth_trust_policy.py backend/src/application/use_cases/auth/oauth_login.py backend/src/application/use_cases/auth/account_linking.py backend/src/presentation/api/v1/oauth/schemas.py backend/tests/unit/application/use_cases/auth/test_oauth_login.py
git commit -m "feat: add provider trust policy for oauth linking"
```

### Task 4: Hard-code provider rules where current code diverges from official guidance

**Priority:** P1

**Files:**
- Modify: `backend/src/infrastructure/oauth/google.py`
- Create: `backend/src/infrastructure/oauth/oidc.py`
- Modify: `backend/src/infrastructure/oauth/github.py`
- Modify: `backend/src/infrastructure/oauth/discord.py`
- Modify: `backend/src/infrastructure/oauth/facebook.py`
- Modify: `backend/src/infrastructure/oauth/microsoft.py`
- Modify: `backend/src/infrastructure/oauth/twitter.py`
- Modify: `backend/src/presentation/api/v1/oauth/routes.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/unit/infrastructure/oauth/test_google.py`
- Create: `backend/tests/unit/infrastructure/oauth/test_github.py`
- Test: `backend/tests/unit/infrastructure/oauth/test_discord.py`
- Test: `backend/tests/unit/infrastructure/oauth/test_facebook.py`
- Test: `backend/tests/unit/infrastructure/oauth/test_microsoft.py`
- Test: `backend/tests/unit/infrastructure/oauth/test_twitter.py`

**Step 1: Write or extend failing provider tests**

Minimum coverage:
- Google: OIDC discovery/JWKS usage, ID token validation, `email_verified` extraction
- GitHub: PKCE challenge/verifier support and verified primary email fallback
- Discord: explicit docs-aligned handling for `identify email`; PKCE only if current docs confirm it
- Facebook: pinned Graph API version, normalized `email/public_profile` user fields
- Microsoft: `openid profile email offline_access` flow, OIDC claim extraction
- X: `api.x.com` token/user endpoints, PKCE, `offline.access` when refresh tokens are required

**Step 2: Run provider unit tests**

Run:

```bash
cd backend && pytest tests/unit/infrastructure/oauth -q
```

Expected: FAIL because multiple providers still use outdated or under-specified behavior.

**Step 3: Implement provider normalization**

- Google and Microsoft:
  - use OIDC discovery + JWKS validation for ID tokens
  - keep userinfo only for supplemental profile data
- GitHub:
  - add `code_challenge` / `code_verifier`
  - keep `user:email` resolution for primary verified email
- Discord:
  - remove undocumented PKCE if current docs do not support it
  - keep `verified=true` guard for email trust
- Facebook:
  - pin Graph API version explicitly
  - keep scopes to `public_profile,email`
  - treat email trust conservatively unless current docs prove verified semantics
- X:
  - use `https://x.com/i/oauth2/authorize` and `https://api.x.com/2/...`
  - request `offline.access` only if refresh tokens are actually needed
  - keep internal slug `twitter` unless the entire API contract is intentionally migrated

**Step 4: Re-run provider unit tests and lint**

Run:

```bash
cd backend && pytest tests/unit/infrastructure/oauth -q
cd backend && ruff check src tests
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/infrastructure/oauth/google.py backend/src/infrastructure/oauth/oidc.py backend/src/infrastructure/oauth/github.py backend/src/infrastructure/oauth/discord.py backend/src/infrastructure/oauth/facebook.py backend/src/infrastructure/oauth/microsoft.py backend/src/infrastructure/oauth/twitter.py backend/src/presentation/api/v1/oauth/routes.py backend/pyproject.toml backend/tests/unit/infrastructure/oauth
git commit -m "feat: harden oauth provider implementations"
```

### Task 5: Stop persisting unneeded provider tokens, or encrypt them if retention is explicitly required

**Priority:** P1

**Files:**
- Modify: `backend/src/infrastructure/database/models/oauth_account_model.py`
- Modify: `backend/src/application/use_cases/auth/oauth_login.py`
- Modify: `backend/src/application/use_cases/auth/account_linking.py`
- Create: `backend/src/shared/security/oauth_token_store.py`
- Create: `backend/src/infrastructure/database/migrations/<timestamp>_oauth_token_minimization.py`
- Test: `backend/tests/security/test_oauth_security.py`

**Step 1: Write failing retention tests**

Cover:
- login-only providers do not persist provider access tokens by default
- if a provider is configured to retain refresh tokens for a later product reason, the value is encrypted before persistence
- old plaintext rows are migrated or purged safely
- unlink/delete flows remove retained provider secrets

**Step 2: Run the security tests**

Run:

```bash
cd backend && pytest tests/security/test_oauth_security.py -q
```

Expected: FAIL because plaintext token storage still exists.

**Step 3: Implement the minimal-retention policy**

Recommended default:
- store only `provider`, `provider_user_id`, `provider_email`, `provider_avatar_url`, and timestamps
- keep provider access/refresh tokens out of persistence for login-only flows
- if business requirements later need provider API access, store only the minimum required token set in an encrypted path with key rotation support

**Step 4: Re-run security tests**

Run:

```bash
cd backend && pytest tests/security/test_oauth_security.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/src/infrastructure/database/models/oauth_account_model.py backend/src/application/use_cases/auth/oauth_login.py backend/src/application/use_cases/auth/account_linking.py backend/src/shared/security/oauth_token_store.py backend/src/infrastructure/database/migrations backend/tests/security/test_oauth_security.py
git commit -m "refactor: minimize oauth token retention"
```

### Task 6: Normalize frontend UX around start routes, post-login redirects, and stable provider errors

**Priority:** P2

**Files:**
- Modify: `frontend/src/features/auth/components/SocialAuthButtons.tsx`
- Modify: `frontend/src/stores/auth-store.ts`
- Modify: `frontend/src/lib/analytics/index.ts`
- Create: `frontend/src/features/auth/lib/oauth-error-codes.ts`
- Modify: `frontend/src/features/auth/components/__tests__/SocialAuthButtons.test.tsx`
- Modify: `frontend/src/stores/__tests__/auth-store.test.ts`

**Step 1: Write failing UI/store tests**

Cover:
- each provider button navigates to the new same-origin start route
- X remains labeled `X` while using the internal provider slug consistently
- provider-denied, collision, and 2FA-required errors map to stable UX codes
- locale and `return_to` survive the external redirect round-trip
- no `sessionStorage` dependency remains for OAuth login

**Step 2: Run the focused frontend tests**

Run:

```bash
cd frontend && npm run test:run -- src/features/auth/components/__tests__/SocialAuthButtons.test.tsx src/stores/__tests__/auth-store.test.ts
```

Expected: FAIL because the current UI/store still use the old client callback contract.

**Step 3: Implement the UI/store changes**

- provider buttons should trigger full-page navigation to the new BFF start route
- auth store should treat OAuth as a navigation flow, not an in-browser token exchange
- analytics should record `started`, `callback_success`, `callback_failed`, `2fa_required`, `collision`, and `provider_denied`
- keep Telegram separate if its UX remains bot-link/magic-link based

**Step 4: Re-run frontend tests**

Run:

```bash
cd frontend && npm run test:run -- src/features/auth/components/__tests__/SocialAuthButtons.test.tsx src/stores/__tests__/auth-store.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/features/auth/components/SocialAuthButtons.tsx frontend/src/stores/auth-store.ts frontend/src/lib/analytics/index.ts frontend/src/features/auth/lib/oauth-error-codes.ts frontend/src/features/auth/components/__tests__/SocialAuthButtons.test.tsx frontend/src/stores/__tests__/auth-store.test.ts
git commit -m "feat: normalize oauth frontend ux"
```

### Task 7: Make session restoration and authenticated surfaces compatible with Next.js 16 cache components

**Priority:** P2

**Files:**
- Modify: `frontend/src/app/providers/auth-provider.tsx`
- Modify: `frontend/src/features/auth/components/AuthGuard.tsx`
- Modify: `frontend/src/lib/api/client.ts`
- Create: `frontend/src/features/auth/lib/session.ts`
- Test: `frontend/src/features/auth/components/__tests__/AuthGuard.test.tsx`

**Step 1: Write failing session tests**

Cover:
- public auth routes remain cache-safe and do not attempt to cache user-specific session data
- protected routes still validate the session through same-origin `/api/v1/auth/*`
- expired session refresh does not redirect-loop from public auth routes
- successful OAuth callback hydration leads to immediate authenticated state after redirect

**Step 2: Run the focused tests**

Run:

```bash
cd frontend && npm run test:run -- src/features/auth/components/__tests__/AuthGuard.test.tsx src/stores/__tests__/auth-store.test.ts
```

Expected: FAIL if the new redirect/callback lifecycle is not yet wired through session restoration.

**Step 3: Implement cache-safe session boundaries**

- keep public auth shells static/cached where possible
- keep user session lookups dynamic and behind explicit runtime boundaries
- do not put session logic in `proxy.ts`
- ensure the post-callback redirect lands on a route that can immediately fetch the authenticated session without cache pollution

**Step 4: Re-run the focused tests**

Run:

```bash
cd frontend && npm run test:run -- src/features/auth/components/__tests__/AuthGuard.test.tsx src/stores/__tests__/auth-store.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/app/providers/auth-provider.tsx frontend/src/features/auth/components/AuthGuard.tsx frontend/src/lib/api/client.ts frontend/src/features/auth/lib/session.ts frontend/src/features/auth/components/__tests__/AuthGuard.test.tsx frontend/src/stores/__tests__/auth-store.test.ts
git commit -m "fix: align session restoration with oauth bff flow"
```

### Task 8: Replace placeholder OAuth integration tests with real route-level coverage

**Priority:** P3

**Files:**
- Modify: `backend/tests/integration/api/v1/oauth/test_oauth_login.py`
- Modify: `backend/tests/e2e/auth/test_oauth_e2e.py`
- Create: `frontend/src/app/api/oauth/__tests__/oauth-web-flow.test.ts`
- Modify: `frontend/src/app/[locale]/(auth)/__tests__/e2e-auth.test.tsx`

**Step 1: Write failing integration tests with the real contract**

Cover:
- start route returns redirect and sets signed transaction cookie
- callback route consumes the backend response and forwards auth cookies
- provider callback failure surfaces a stable error code
- new user creation, existing linked account, verified-email auto-link, and 2FA required are all exercised

**Step 2: Run the integration suites**

Run:

```bash
cd backend && pytest tests/integration/api/v1/oauth/test_oauth_login.py -q
cd frontend && npm run test:run -- src/app/api/oauth/__tests__/oauth-web-flow.test.ts
```

Expected: FAIL because the current tests still target obsolete behavior.

**Step 3: Replace placeholder mocks with current route-level tests**

- stop referencing non-existent `oauth_service` abstractions
- assert on real request/response shapes
- add fixture helpers for provider callback payloads and backend callback stubs
- leave full real-provider E2E tests skip-marked but accurate and runnable in staging

**Step 4: Re-run integration suites**

Run:

```bash
cd backend && pytest tests/integration/api/v1/oauth/test_oauth_login.py -q
cd frontend && npm run test:run -- src/app/api/oauth/__tests__/oauth-web-flow.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git add backend/tests/integration/api/v1/oauth/test_oauth_login.py backend/tests/e2e/auth/test_oauth_e2e.py frontend/src/app/api/oauth/__tests__/oauth-web-flow.test.ts 'frontend/src/app/[locale]/(auth)/__tests__/e2e-auth.test.tsx'
git commit -m "test: replace placeholder oauth integration coverage"
```

### Task 9: Add provider console setup docs, env matrix, and rollout runbooks

**Priority:** P3

**Files:**
- Create: `docs/auth/oauth-setup-guide.md`
- Modify: `backend/.env.example`
- Create: `frontend/.env.example`
- Modify: `docs/plans/2026-03-31-oauth-full-stack-integration-plan.md` only if implementation discovers contract changes

**Step 1: Write the setup/runbook docs**

Document:
- exact callback URIs per provider and environment
- required console switches and scopes
- how to test local/staging/prod
- provider-specific gotchas:
  - Google consent screen + app verification
  - GitHub exact callback and PKCE fields
  - Discord redirect whitelist
  - Meta app mode / Graph API version
  - Microsoft `common` vs tenant-specific behavior
  - X app type, `offline.access`, and email scope availability
- cookie topology requirements (`https://vpn.ozoxy.ru` reverse proxy to `/api/v1/*`)

**Step 2: Add rollout checklist**

Include:
- feature flags per provider
- shadow/staging verification
- canary enablement order
- monitoring dashboard queries
- rollback steps per provider

**Step 3: Commit**

```bash
git add docs/auth/oauth-setup-guide.md backend/.env.example frontend/.env.example docs/plans/2026-03-31-oauth-full-stack-integration-plan.md
git commit -m "docs: add oauth setup and rollout guides"
```

### Task 10: Run end-to-end staging smoke and production readiness review

**Priority:** P4

**Files:**
- No new source files required
- Update any failing doc/checklist artifacts only if staging results demand it

**Step 1: Prepare staging credentials**

For each provider, configure the exact staging callback URI and confirm the app is in the correct live/test mode for that environment.

**Step 2: Execute the smoke matrix**

Web smoke checklist:
- Google login from signed-out browser
- GitHub login with PKCE
- Discord login with verified email
- Facebook login in live mode
- Microsoft login with personal account
- Microsoft login with work/school account
- X login with standard user account
- repeat login for an already linked account
- 2FA required path after social sign-in
- denied consent path
- provider callback with tampered state
- provider callback with expired state
- protected route access after fresh social login
- logout and re-login
- refresh token rotation after social login

**Step 3: Final verification commands**

Run:

```bash
cd backend && pytest tests/security/test_oauth_security.py tests/unit/application/use_cases/auth/test_oauth_login.py tests/unit/infrastructure/oauth tests/integration/api/v1/oauth/test_oauth_login.py -q
cd backend && ruff check src tests
cd frontend && npm run test:run -- src/stores/__tests__/auth-store.test.ts src/features/auth/components/__tests__/SocialAuthButtons.test.tsx src/app/api/oauth/start/[provider]/route.test.ts src/app/api/oauth/callback/[provider]/route.test.ts src/app/api/oauth/__tests__/oauth-web-flow.test.ts
cd frontend && NEXT_TELEMETRY_DISABLED=1 npm run build
cd frontend && npm run lint
```

Expected:
- all targeted tests PASS
- staging smoke matrix PASS
- no provider-specific redirect mismatch or cookie propagation failures
- no plaintext provider tokens remain after login-only flows

**Step 4: Production release gate**

Do not enable all providers at once. Recommended order:

1. Google
2. GitHub
3. Microsoft
4. Discord
5. X
6. Facebook

Only promote the next provider after 24 hours of clean error-rate and callback telemetry on the previous one.
