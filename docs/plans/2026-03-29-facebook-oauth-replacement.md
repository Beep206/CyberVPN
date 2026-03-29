# Facebook OAuth Replacement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Facebook OAuth login, disable Apple login without deleting Apple code, and align backend/frontend callback handling with safe redirect validation.

**Architecture:** Keep the existing generic OAuth login pipeline on backend and frontend, but split "supported in code" from "enabled for login" so Apple remains in the codebase while Facebook becomes the active provider. Normalize the web callback URL to the real Next.js route, add redirect URI allowlist validation on backend, and plug Facebook into the same authorize/callback/token issuance flow used by Google, GitHub, Discord, Microsoft, and Twitter.

**Tech Stack:** FastAPI, Pydantic Settings, httpx, Next.js 16 App Router, React 19, Zustand, Vitest, pytest, Ruff, OpenAPI types

---

## Task 1: Normalize callback URLs and reject unsafe redirect URIs

**Files:**
- Modify: `backend/src/config/settings.py`
- Modify: `backend/src/presentation/api/v1/oauth/routes.py`
- Modify: `backend/.env.example`
- Modify: `frontend/src/stores/auth-store.ts`
- Test: `backend/tests/security/test_oauth_security.py`
- Test: `frontend/src/stores/__tests__/auth-store.test.ts`

**Step 1: Write failing backend security tests**

- Add a test that accepts trusted redirects such as `http://localhost:3001/en-EN/oauth/callback` and `cybervpn://oauth/callback`.
- Add a test that rejects an untrusted redirect such as `https://evil.example/callback` with `400`.

Run:

```bash
pytest backend/tests/security/test_oauth_security.py -q
```

Expected: new redirect validation tests fail before implementation.

**Step 2: Implement redirect allowlist parsing and validation**

- Add a new settings field in `backend/src/config/settings.py` for OAuth redirect allowlist entries.
- Parse comma-separated env values the same way `cors_origins` is parsed.
- In `backend/src/presentation/api/v1/oauth/routes.py`, validate `redirect_uri` before creating authorize URLs and before exchanging callback codes.
- Allow exact deep links like `cybervpn://oauth/callback` and web origins/prefixes needed by the Next.js frontend.

**Step 3: Fix the frontend callback URL to match the real route**

- Replace `${window.location.origin}/auth/callback/${provider}` in `frontend/src/stores/auth-store.ts` with a locale-aware helper that points to `${window.location.origin}${getLocalePrefix()}/oauth/callback`.
- Keep provider tracking in `sessionStorage`, because the callback page still resolves the provider from session state.

**Step 4: Verify targeted tests**

Run:

```bash
pytest backend/tests/security/test_oauth_security.py -q
npm run test:run -- src/stores/__tests__/auth-store.test.ts
```

Expected: redirect validation and callback URL tests pass.

---

## Task 2: Introduce enabled login provider gating and disable Apple login

**Files:**
- Modify: `backend/src/presentation/api/v1/oauth/routes.py`
- Modify: `backend/src/presentation/api/v1/oauth/schemas.py`
- Create: `frontend/src/features/auth/lib/oauth-provider-config.ts`
- Modify: `frontend/src/features/auth/components/SocialAuthButtons.tsx`
- Test: `backend/tests/e2e/auth/test_oauth_e2e.py`
- Test: `frontend/src/features/auth/components/__tests__/SocialAuthButtons.test.tsx`

**Step 1: Write failing tests for provider visibility/availability**

- Add a backend test that Apple login is rejected as disabled while other enabled providers still work.
- Add a frontend test that Apple is not rendered in the login button grid.

Run:

```bash
pytest backend/tests/e2e/auth/test_oauth_e2e.py -q
npm run test:run -- src/features/auth/components/__tests__/SocialAuthButtons.test.tsx
```

Expected: tests fail because Apple is still active and visible.

**Step 2: Implement provider gating without deleting Apple code**

- Keep `OAuthProvider.APPLE` in `backend/src/presentation/api/v1/oauth/schemas.py`.
- In `backend/src/presentation/api/v1/oauth/routes.py`, keep Apple in the provider registry but introduce a separate enabled-login allowlist that does not include Apple.
- In `frontend/src/features/auth/lib/oauth-provider-config.ts`, define all known providers, mark Apple disabled, and prepare Facebook as enabled.
- Render only enabled providers in `frontend/src/features/auth/components/SocialAuthButtons.tsx`.

**Step 3: Verify targeted tests**

Run:

```bash
pytest backend/tests/e2e/auth/test_oauth_e2e.py -q
npm run test:run -- src/features/auth/components/__tests__/SocialAuthButtons.test.tsx
```

Expected: Apple stays in code but is blocked from active login paths and hidden in web auth UI.

---

## Task 3: Add backend Facebook provider support

**Files:**
- Create: `backend/src/infrastructure/oauth/facebook.py`
- Modify: `backend/src/config/settings.py`
- Modify: `backend/src/presentation/api/v1/oauth/schemas.py`
- Modify: `backend/src/presentation/api/v1/oauth/routes.py`
- Test: `backend/tests/unit/infrastructure/oauth/test_facebook.py`
- Test: `backend/tests/e2e/auth/test_oauth_e2e.py`

**Step 1: Confirm Meta OAuth flow from current docs**

- Fetch current Facebook Login docs before coding.
- Confirm authorize endpoint, token endpoint, user info endpoint, required scopes, and whether PKCE is supported or required for this flow.

**Step 2: Write failing provider tests**

- Add unit tests for `authorize_url()` and `exchange_code()` in `backend/tests/unit/infrastructure/oauth/test_facebook.py`.
- Add e2e placeholder coverage in `backend/tests/e2e/auth/test_oauth_e2e.py` for `/api/v1/oauth/facebook/login` and `/api/v1/oauth/facebook/login/callback`.

Run:

```bash
pytest backend/tests/unit/infrastructure/oauth/test_facebook.py -q
pytest backend/tests/e2e/auth/test_oauth_e2e.py -q
```

Expected: tests fail because Facebook is not implemented yet.

**Step 3: Implement the provider**

- Add `facebook_client_id` and `facebook_client_secret` to `backend/src/config/settings.py`.
- Implement `FacebookOAuthProvider` in `backend/src/infrastructure/oauth/facebook.py` using the same normalized user-info contract as the other providers: `id`, `email`, `username`, `name`, `avatar_url`, `access_token`, optional `refresh_token`.
- Register Facebook in `backend/src/presentation/api/v1/oauth/schemas.py` and `backend/src/presentation/api/v1/oauth/routes.py`.
- Add Facebook to the enabled-login allowlist, keeping Apple disabled.

**Step 4: Verify backend checks**

Run:

```bash
pytest backend/tests/unit/infrastructure/oauth/test_facebook.py -q
pytest backend/tests/security/test_oauth_security.py -q
ruff check backend/src backend/tests
```

Expected: Facebook provider tests pass and backend remains lint-clean.

---

## Task 4: Wire Facebook into the web frontend and API types

**Files:**
- Modify: `frontend/src/lib/api/auth.ts`
- Modify: `frontend/src/lib/analytics/index.ts`
- Modify: `frontend/src/features/auth/lib/oauth-provider-config.ts`
- Modify: `frontend/src/features/auth/components/SocialAuthButtons.tsx`
- Modify: `frontend/src/test/mocks/handlers.ts`
- Modify: `frontend/src/stores/__tests__/auth-store.test.ts`
- Modify: `frontend/src/app/[locale]/(auth)/oauth/callback/__tests__/page.test.tsx`
- Modify: `frontend/src/features/auth/components/__tests__/SocialAuthButtons.test.tsx`
- Modify: `frontend/src/lib/api/__tests__/auth.test.ts`
- Regenerate: `frontend/src/lib/api/generated/types.ts`

**Step 1: Write failing frontend tests**

- Replace Apple expectations with Facebook where the active login surface is tested.
- Keep at least one assertion path proving the type layer can still represent Apple if needed, but do not render it in the active provider list.

Run:

```bash
npm run test:run -- src/features/auth/components/__tests__/SocialAuthButtons.test.tsx src/stores/__tests__/auth-store.test.ts src/app/[locale]/(auth)/oauth/callback/__tests__/page.test.tsx src/lib/api/__tests__/auth.test.ts
```

Expected: tests fail until Facebook is wired through.

**Step 2: Implement frontend provider updates**

- Add `facebook` to the `OAuthProvider` union in `frontend/src/lib/api/auth.ts` while keeping `apple` in the type.
- Update analytics login method typing in `frontend/src/lib/analytics/index.ts`.
- Add Facebook metadata/icon/button placement in `frontend/src/features/auth/lib/oauth-provider-config.ts` and `frontend/src/features/auth/components/SocialAuthButtons.tsx`.
- Update MSW handlers in `frontend/src/test/mocks/handlers.ts` to accept Facebook login and callback requests.

**Step 3: Regenerate OpenAPI types**

Run:

```bash
npm run generate:api-types
```

Expected: `frontend/src/lib/api/generated/types.ts` includes `facebook` and still keeps `apple` in the backend schema enum if Apple remains in the API contract.

**Step 4: Verify targeted frontend checks**

Run:

```bash
npm run test:run -- src/features/auth/components/__tests__/SocialAuthButtons.test.tsx src/stores/__tests__/auth-store.test.ts src/app/[locale]/(auth)/oauth/callback/__tests__/page.test.tsx src/lib/api/__tests__/auth.test.ts
npm run lint
```

Expected: web OAuth UI and callback flow pass with Facebook as the active replacement.

---

## Task 5: Update env/docs and run final verification

**Files:**
- Modify: `backend/.env.example`
- Modify: `docs/auth/oauth-setup-guide.md`
- Modify: `docs/plans/2026-03-29-facebook-oauth-replacement.md` (only if execution learns something new)

**Step 1: Update env and setup docs**

- Add `FACEBOOK_CLIENT_ID` and `FACEBOOK_CLIENT_SECRET` to `backend/.env.example`.
- Update `docs/auth/oauth-setup-guide.md` so the provider matrix reflects Facebook as active and Apple as disabled-but-retained in code.
- Document the redirect allowlist requirement and the real web callback route.

**Step 2: Run final verification**

Run:

```bash
pytest backend/tests/unit/infrastructure/oauth/test_facebook.py -q
pytest backend/tests/security/test_oauth_security.py -q
ruff check backend/src backend/tests
npm run test:run -- src/features/auth/components/__tests__/SocialAuthButtons.test.tsx src/stores/__tests__/auth-store.test.ts src/app/[locale]/(auth)/oauth/callback/__tests__/page.test.tsx src/lib/api/__tests__/auth.test.ts
npm run lint
```

Expected: all targeted backend/frontend checks pass.

**Step 3: Manual smoke checklist**

- Confirm `GET /api/v1/oauth/facebook/login` returns JSON with `authorize_url` and `state`.
- Confirm Apple login now returns a disabled-provider error instead of starting auth.
- Confirm the web app redirects to `/<locale>/oauth/callback` and finishes login via `POST /api/v1/oauth/facebook/login/callback`.
- Confirm no callback URL still points at `/auth/callback/{provider}`.
