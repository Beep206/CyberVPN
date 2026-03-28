# CyberVPN Phase 5 — Final Polish + JSON-LD SEO — Agent Team Prompt

> Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
> User presses **Shift+Tab** to enter delegate mode, then pastes this prompt.
> Teammates load `CLAUDE.md` automatically. Spawn prompts contain ONLY task-specific context.
> **Scope**: Close every remaining gap across Frontend and Backend. Add JSON-LD structured data.
> **Out of scope**: Telegram Bot (services/telegram-bot/), Mobile (cybervpn_mobile/ — all gaps closed), Infrastructure (infra/ — 100% complete).

---

## Goal

1. Add **JSON-LD structured data** across the frontend using `schema-dts` for type-safe schemas
2. Close every remaining frontend gap: loading states, OG image, alert() stubs, test stubs
3. Close every remaining backend gap: missing integration tests for trial, usage, payments
4. Pass all build/lint/test checks across both platforms

**Done criteria:**
1. `npm run build` passes (frontend)
2. `npm run lint` passes (frontend)
3. `npm run test:run` passes (frontend)
4. `pytest backend/tests/ -v` passes (backend)
5. `schema-dts` is in `frontend/package.json` dependencies
6. JSON-LD `<script type="application/ld+json">` rendered in root layout HTML output
7. `opengraph-image.tsx` exists at `frontend/src/app/`
8. `loading.tsx` exists for miniapp and auth route groups
9. Zero `alert()` calls in production frontend code (outside test files)
10. PurchaseConfirmModal test file has zero TODO-only test cases
11. Integration test directories exist for trial/, usage/, payments/ in backend

---

## Current State Audit (Phase 5 starting point)

### What's DONE (from Phases 3-4)

| Component | Status |
|-----------|--------|
| Backend 120+ endpoints, 44 routers | All implemented |
| Backend Prometheus metrics wired | auth, payments, subscriptions, trial -- ALL instrumented |
| Backend cache metrics | @track_cache_operation on get/set/delete |
| Backend rate limiting | 5 endpoints + global middleware + mobile + 2FA |
| Backend Sentry + OTEL + structlog | All configured |
| Backend integration tests | auth, oauth, 2fa, wallet, codes, profile, notifications, security, subscriptions |
| Frontend 31 pages + 8 miniapp pages | All real API, zero stubs |
| Frontend error.tsx (4) + not-found.tsx (4) | All route groups covered |
| Frontend Sentry 3 configs | client, server, edge -- all exist |
| Frontend i18n 26 namespaces | All registered in request.ts |
| Frontend SEO robots.ts + sitemap.ts | Both exist |
| Frontend generateMetadata | 3/3 layouts (dashboard, auth, miniapp) |
| Frontend 51 test files | API tests fully implemented |
| Mobile all features | Wallet, security, referral, partner, OAuth, OTP -- all done |
| Mobile compilation | Zero duplicate constants, clean analyze |
| Infra 11 dashboards | Prometheus + Loki + Tempo + SLO |
| Infra 75 alert rules | 69 Prometheus + 6 Loki |
| Infra all healthchecks | 11/11 services |

### What's STILL MISSING (Phase 5 must fix)

#### Frontend -- JSON-LD Structured Data (NEW REQUIREMENT)
- **No JSON-LD** exists anywhere in the frontend
- Need `schema-dts` package for TypeScript-typed Schema.org definitions
- Need structured data on: root layout (Organization + WebSite), dashboard layout (WebApplication), auth pages (WebPage)
- Google Rich Results require JSON-LD in `<script type="application/ld+json">`

#### Frontend -- Missing loading.tsx Files
- `frontend/src/app/[locale]/(miniapp)/loading.tsx` -- DOES NOT EXIST
- `frontend/src/app/[locale]/(auth)/loading.tsx` -- DOES NOT EXIST
- Only dashboard has loading.tsx (CSS-only pulse animation, no JS)

#### Frontend -- Missing opengraph-image.tsx
- `frontend/src/app/opengraph-image.tsx` -- DOES NOT EXIST
- robots.ts and sitemap.ts exist, but no OG image for social previews

#### Frontend -- alert() in Production Code
- `frontend/src/app/[locale]/(miniapp)/wallet/page.tsx` line 313: `alert(axiosError.response?.data?.detail || t('withdrawError'))`
- `frontend/src/app/[locale]/(miniapp)/wallet/page.tsx` line 321: `alert(t('invalidAmount'))`
- `frontend/src/app/[locale]/(miniapp)/wallet/page.tsx` line 325: `alert(t('insufficientBalance'))`
- `frontend/src/app/[locale]/(miniapp)/wallet/page.tsx` line 329: `alert(t('paymentMethodRequired'))`
- This is a Telegram Mini App page -- should use `webApp?.showAlert()` from `useTelegramWebApp` hook (already imported on line 18)

#### Frontend -- PurchaseConfirmModal Test Stubs
- File: `frontend/src/app/[locale]/(dashboard)/subscriptions/components/__tests__/PurchaseConfirmModal.test.tsx`
- 6 test cases are TODO-only stubs (lines 206-305):
  - `test_displays_crypto_invoice_after_purchase_success` (line 206)
  - `test_calls_onSuccess_callback_after_purchase` (line 214)
  - `test_closes_modal_on_cancel_button_click` (line 223)
  - `test_displays_insufficient_balance_error` (line 287)
  - `test_displays_plan_not_found_error` (line 294)
  - `test_displays_network_error_message` (line 301)

#### Backend -- Missing Integration Tests
- `backend/tests/integration/api/v1/trial/` -- DOES NOT EXIST
- `backend/tests/integration/api/v1/usage/` -- DOES NOT EXIST
- `backend/tests/integration/api/v1/payments/` -- DOES NOT EXIST (webhook handlers untested)
- Unit tests exist for trial and usage but no integration-level API tests

---

## Team

| Role | Agent name | Model | Working directory | subagent_type | Tasks |
|------|-----------|-------|-------------------|---------------|-------|
| Lead (you) | -- | opus | all (coordination only) | -- | 0 |
| Frontend SEO + Polish | `frontend-seo` | sonnet | `frontend/` | general-purpose | 7 |
| Backend Test Coverage | `backend-tests` | sonnet | `backend/` | backend-dev | 3 |
| Test and Verify | `test-verify` | sonnet | `frontend/` + `backend/` | test-runner | 3 |

---

## Spawn Prompts

### frontend-seo

```
You are frontend-seo on the CyberVPN team (Phase 5). You add JSON-LD structured data, fix missing loading states, create OG image, and replace alert() stubs.
Stack: Next.js 16, React 19, TypeScript 5.9, Tailwind CSS 4, next-intl 4.7, @sentry/nextjs 10.38.0.
You work ONLY in frontend/.

CONTEXT -- What's already working:
- All 31 dashboard pages + 8 miniapp pages use real APIs
- error.tsx (4 files) + not-found.tsx (4 files) exist
- Sentry fully configured (3 config files)
- 26 i18n namespaces registered
- robots.ts + sitemap.ts exist
- generateMetadata in all 3 layouts
- Dashboard loading.tsx exists (CSS-only pulse skeleton)

RULES:
- Use Context7 MCP to look up library docs before using any library.
- Do NOT downgrade any library version.
- All new components must be cyberpunk-themed (Orbitron font, neon-cyan, terminal style).
- Follow existing code patterns.
- Do NOT modify existing working components -- only ADD new files or make minimal edits.

YOUR TASKS:

FS-1: Install schema-dts and create JSON-LD utility (P0)
  - Run: cd frontend && npm install schema-dts
  - Create frontend/src/shared/lib/json-ld.tsx:
    import type { Thing, WithContext } from 'schema-dts';

    export function JsonLd<T extends Thing>({ data }: { data: WithContext<T> }) {
      return (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
        />
      );
    }
  - NOTE: dangerouslySetInnerHTML is the STANDARD Next.js pattern for JSON-LD.
    The content is JSON.stringify of our own typed schema data, NOT user input. This is safe.
  - This is a Server Component (no 'use client') -- can be used in layouts
  - Export it from the file

FS-2: Add Organization + WebSite JSON-LD to root layout (P0)
  - File: frontend/src/app/[locale]/layout.tsx
  - Import: import { JsonLd } from '@/shared/lib/json-ld';
  - Import types: import type { Organization, WebSite } from 'schema-dts';
  - Add inside the <body> tag (before closing </body>):
    <JsonLd<Organization>
      data={{
        '@context': 'https://schema.org',
        '@type': 'Organization',
        name: 'CyberVPN',
        url: 'https://cybervpn.com',
        logo: 'https://cybervpn.com/logo.png',
        sameAs: [
          'https://t.me/cybervpn',
        ],
      }}
    />
    <JsonLd<WebSite>
      data={{
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        name: 'CyberVPN',
        url: 'https://cybervpn.com',
        potentialAction: {
          '@type': 'SearchAction',
          target: 'https://cybervpn.com/search?q={search_term_string}',
          // @ts-expect-error - schema.org query-input format
          'query-input': 'required name=search_term_string',
        },
      }}
    />
  - Read the existing layout.tsx FIRST to understand where to insert
  - The layout currently has static `metadata` export (line 31) -- keep it as-is
  - JSON-LD goes inside the JSX return, NOT in the metadata export

FS-3: Add SoftwareApplication JSON-LD to dashboard layout (P0)
  - File: frontend/src/app/[locale]/(dashboard)/layout.tsx
  - Import: import { JsonLd } from '@/shared/lib/json-ld';
  - Import type: import type { SoftwareApplication } from 'schema-dts';
  - Add inside the layout JSX (after <AuthGuard>, before the children div):
    <JsonLd<SoftwareApplication>
      data={{
        '@context': 'https://schema.org',
        '@type': 'SoftwareApplication',
        name: 'CyberVPN',
        applicationCategory: 'SecurityApplication',
        operatingSystem: 'Web, Android, iOS',
        offers: {
          '@type': 'Offer',
          price: '0',
          priceCurrency: 'USD',
        },
      }}
    />
  - Be careful with the JSX structure -- AuthGuard wraps everything

FS-4: Create opengraph-image.tsx (P1)
  - Create frontend/src/app/opengraph-image.tsx
  - Use Next.js ImageResponse API:
    import { ImageResponse } from 'next/og';

    export const runtime = 'edge';
    export const alt = 'CyberVPN - Advanced VPN Service';
    export const size = { width: 1200, height: 630 };
    export const contentType = 'image/png';

    export default function OGImage() {
      return new ImageResponse(
        (
          <div
            style={{
              fontSize: 64,
              background: 'linear-gradient(135deg, #0a0e1a 0%, #1a1e2e 50%, #0a0e1a 100%)',
              width: '100%',
              height: '100%',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#00ffff',
              fontFamily: 'monospace',
            }}
          >
            <div style={{ fontSize: 80, fontWeight: 'bold', marginBottom: 20 }}>
              CYBER<span style={{ color: '#00ff88' }}>VPN</span>
            </div>
            <div style={{ fontSize: 32, color: '#888', marginTop: 10 }}>
              Advanced VPN Service
            </div>
          </div>
        ),
        { ...size }
      );
    }
  - This generates a dynamic OG image at build time
  - Keep it simple -- no external fonts (edge runtime limitations)

FS-5: Create loading.tsx for miniapp route group (P1)
  - Create frontend/src/app/[locale]/(miniapp)/loading.tsx
  - Follow the pattern from existing dashboard loading.tsx:
    frontend/src/app/[locale]/(dashboard)/loading.tsx
  - But simpler (miniapp is mobile-focused):
    export default function MiniAppLoading() {
      return (
        <div className="animate-pulse space-y-4 p-4" aria-label="Loading">
          {/* Balance card skeleton */}
          <div className="h-32 rounded-sm bg-terminal-surface/50 border border-grid-line" />

          {/* Action buttons skeleton */}
          <div className="flex gap-3">
            <div className="h-10 flex-1 rounded-xs bg-neon-cyan/10" />
            <div className="h-10 flex-1 rounded-xs bg-neon-cyan/10" />
          </div>

          {/* List items skeleton */}
          {Array.from({ length: 5 }, (_, i) => (
            <div
              key={i}
              className="flex items-center gap-3 rounded-sm border border-grid-line/50 p-3"
            >
              <div className="h-8 w-8 rounded-full bg-foreground/5" />
              <div className="flex-1 space-y-1">
                <div className="h-3 w-24 rounded-xs bg-foreground/5" />
                <div className="h-2 w-16 rounded-xs bg-foreground/5" />
              </div>
              <div className="h-4 w-12 rounded-xs bg-foreground/5" />
            </div>
          ))}
        </div>
      );
    }
  - Server Component -- CSS-only animation, no JS hydration
  - No 'use client' directive

FS-6: Create loading.tsx for auth route group (P1)
  - Create frontend/src/app/[locale]/(auth)/loading.tsx
  - Auth pages are centered forms:
    export default function AuthLoading() {
      return (
        <div className="flex items-center justify-center min-h-[60vh]" aria-label="Loading">
          <div className="w-full max-w-md animate-pulse space-y-6 p-6">
            {/* Logo skeleton */}
            <div className="flex justify-center">
              <div className="h-12 w-12 rounded-lg bg-neon-cyan/10" />
            </div>

            {/* Title skeleton */}
            <div className="space-y-2 text-center">
              <div className="mx-auto h-6 w-48 rounded-xs bg-neon-cyan/10" />
              <div className="mx-auto h-3 w-64 rounded-xs bg-foreground/5" />
            </div>

            {/* Form fields skeleton */}
            {Array.from({ length: 3 }, (_, i) => (
              <div key={i} className="space-y-1">
                <div className="h-3 w-16 rounded-xs bg-foreground/5" />
                <div className="h-10 rounded-sm border border-grid-line bg-terminal-surface/50" />
              </div>
            ))}

            {/* Submit button skeleton */}
            <div className="h-10 rounded-sm bg-neon-cyan/10" />
          </div>
        </div>
      );
    }
  - Server Component -- CSS-only animation, no JS hydration

FS-7: Replace alert() with webApp?.showAlert() in miniapp wallet (P0)
  - File: frontend/src/app/[locale]/(miniapp)/wallet/page.tsx
  - The file already imports `useTelegramWebApp` (line 18) and destructures
    `{ webApp, haptic, hapticNotification }` (used elsewhere in the file)
  - Verify that `webApp` and `hapticNotification` are available in the component scope
  - Add a showError helper near the top of the component function:
    const showError = (msg: string) => {
      hapticNotification('error');
      if (webApp) {
        webApp.showAlert(msg);
      } else {
        console.error('[Wallet]', msg);
      }
    };
  - Replace 4 instances:
    Line 313: alert(...) -> showError(...)
    Line 321: alert(...) -> showError(...)
    Line 325: alert(...) -> showError(...)
    Line 329: alert(...) -> showError(...)
  - Verify: grep -r "alert(" frontend/src/app --include="*.tsx" | grep -v __tests__ | grep -v test/
    Must return ZERO matches after fix

DONE CRITERIA: npm run build passes. npm run lint passes. schema-dts in package.json. JSON-LD script tags in root and dashboard layouts. opengraph-image.tsx exists. loading.tsx in miniapp + auth. Zero alert() in production code.
```

### backend-tests

```
You are backend-tests on the CyberVPN team (Phase 5). You create missing integration tests for trial, usage, and payments endpoints.
Stack: FastAPI, Python 3.13, SQLAlchemy 2, Redis, pytest-asyncio, httpx.
You work ONLY in backend/.

CONTEXT -- What already exists:
- 18 integration test files in backend/tests/integration/api/v1/
- Existing directories: auth/ (8 files), oauth/, two_factor/, codes/, wallet/, profile/, notifications/, security/, subscriptions/
- MISSING directories: trial/, usage/, payments/
- Unit tests exist for trial (6 tests) and usage (2 tests) in backend/tests/unit/api/v1/
- E2E tests in backend/tests/e2e/test_all_endpoints.py cover some flows

KEY FILES TO READ FIRST:
- Test conftest: backend/tests/conftest.py (fixtures: auth_client, admin_user, db_session, redis_client)
- Integration conftest: backend/tests/integration/conftest.py (if exists -- extra fixtures)
- Existing test pattern: backend/tests/integration/api/v1/auth/test_auth_flows.py (copy this pattern)
- Existing test pattern: backend/tests/integration/api/v1/security/test_security_flows.py (simpler pattern)
- Trial routes: backend/src/presentation/api/v1/trial/routes.py
- Usage routes: backend/src/presentation/api/v1/usage/routes.py
- Payments routes: backend/src/presentation/api/v1/payments/routes.py
- Factories: backend/tests/factories.py (user/token factories)

RULES:
- Use Context7 MCP to look up library docs before using any library.
- Do NOT downgrade any package version.
- Follow EXACTLY the pattern from existing integration tests (same fixtures, same imports).
- Use httpx AsyncClient + pytest-asyncio.
- Mock external services (Remnawave, CryptoBot) -- do NOT make real HTTP calls.
- Each test file must have __init__.py in its directory.
- Use dependency_overrides for injecting test doubles.

YOUR TASKS:

BT-1: Create trial integration tests (P0)
  - Create directory: backend/tests/integration/api/v1/trial/
  - Create backend/tests/integration/api/v1/trial/__init__.py (empty)
  - Create backend/tests/integration/api/v1/trial/test_trial_flows.py
  - Tests to write:
    1. test_activate_trial_success -- POST /api/v1/trial/activate with valid auth -> 200 + trial activated
    2. test_activate_trial_already_used -- POST /api/v1/trial/activate when trial already claimed -> 409 or 400
    3. test_activate_trial_rate_limited -- POST /api/v1/trial/activate 4 times in a row -> 429 on 4th (rate limit: 3/hour)
    4. test_get_trial_status -- GET /api/v1/trial/status with valid auth -> 200 + status payload
    5. test_trial_endpoints_require_auth -- Both endpoints without auth -> 401
  - Pattern: Use auth_client fixture, mock the trial use case's external Remnawave call
  - Read trial/routes.py to understand exact response schemas and dependencies

BT-2: Create usage integration tests (P0)
  - Create directory: backend/tests/integration/api/v1/usage/
  - Create backend/tests/integration/api/v1/usage/__init__.py (empty)
  - Create backend/tests/integration/api/v1/usage/test_usage_flows.py
  - Tests to write:
    1. test_get_usage_success -- GET /api/v1/users/me/usage with valid auth -> 200 + usage data
    2. test_get_usage_no_subscription -- GET /api/v1/users/me/usage when user has no subscription -> graceful response (200 with zeros or 404)
    3. test_usage_requires_auth -- GET without auth -> 401
  - Read usage/routes.py to understand exact response format and external API dependency
  - Mock Remnawave API responses

BT-3: Create payments integration tests (P0)
  - Create directory: backend/tests/integration/api/v1/payments/
  - Create backend/tests/integration/api/v1/payments/__init__.py (empty)
  - Create backend/tests/integration/api/v1/payments/test_payment_flows.py
  - Tests to write:
    1. test_create_invoice_success -- POST /api/v1/payments/invoice with valid plan_id -> 200 + invoice URL
    2. test_create_invoice_invalid_plan -- POST with non-existent plan_id -> 404 or 400
    3. test_get_payment_history -- GET /api/v1/payments/history with auth -> 200 + list
    4. test_webhook_valid_signature -- POST /api/v1/webhooks/cryptobot with valid signature -> 200
    5. test_webhook_invalid_signature -- POST /api/v1/webhooks/cryptobot with bad signature -> 403 or 400
    6. test_payments_require_auth -- Create invoice without auth -> 401
  - Mock CryptoBot API responses
  - Use existing webhook handler patterns from the codebase

DONE CRITERIA: pytest backend/tests/integration/api/v1/trial/ passes. pytest backend/tests/integration/api/v1/usage/ passes. pytest backend/tests/integration/api/v1/payments/ passes. Total 14+ new integration tests added.
```

### test-verify

```
You are test-verify on the CyberVPN team (Phase 5). You implement frontend test stubs and run final build verification.
You work across: frontend/src/**/__tests__/ and run build commands.

CONTEXT -- What already exists:
- 51 frontend test files, 5433 lines of API tests (all complete)
- 1 test file with TODO stubs: PurchaseConfirmModal.test.tsx (6 TODO-only tests, lines 206-305)
- Testing stack: Vitest 4.0.18, @testing-library/react 16.3, MSW 2.12.9, jsdom 28

KEY FILES TO READ FIRST:
- Test with stubs: frontend/src/app/[locale]/(dashboard)/subscriptions/components/__tests__/PurchaseConfirmModal.test.tsx
- The component under test: frontend/src/app/[locale]/(dashboard)/subscriptions/components/PurchaseConfirmModal.tsx
- Existing working test pattern: frontend/src/lib/api/__tests__/subscriptions.test.ts
- Existing component test: frontend/src/app/[locale]/(dashboard)/subscriptions/components/__tests__/ (look for other tests)
- MSW setup: look for mocks/ or handlers/ directories

RULES:
- Use Context7 MCP to look up library docs before using any library.
- Follow existing test patterns exactly.
- Use MSW for API mocking.
- Use React Testing Library (screen, render, waitFor, userEvent).
- Do NOT modify production code -- only test files.

YOUR TASKS:

TV-1: Implement PurchaseConfirmModal test stubs (P0)
  - File: frontend/src/app/[locale]/(dashboard)/subscriptions/components/__tests__/PurchaseConfirmModal.test.tsx
  - Read the component FIRST to understand its props and behavior
  - Implement 6 TODO tests:

    test_displays_crypto_invoice_after_purchase_success (line 206):
    - Setup MSW handler: POST /api/v1/payments/invoice -> 200 with invoice data
    - Render modal with a plan prop
    - Click the purchase/confirm button
    - Wait for success state
    - Assert: invoice details visible (amount, address text or QR code if rendered)

    test_calls_onSuccess_callback_after_purchase (line 214):
    - Setup MSW handler for successful purchase
    - Create vi.fn() for onSuccess callback
    - Render modal with onSuccess prop
    - Click purchase button, wait for completion
    - Assert: onSuccess was called

    test_closes_modal_on_cancel_button_click (line 223):
    - Render modal with onClose callback
    - Click cancel/close button (find by role or text)
    - Assert: onClose was called

    test_displays_insufficient_balance_error (line 287):
    - Setup MSW handler: POST /api/v1/payments/invoice -> 422 { detail: 'Insufficient balance' }
    - Render modal, click purchase
    - Assert: error message about balance visible

    test_displays_plan_not_found_error (line 294):
    - Setup MSW handler: POST /api/v1/payments/invoice -> 404 { detail: 'Plan not found' }
    - Render modal, click purchase
    - Assert: plan not found error visible

    test_displays_network_error_message (line 301):
    - Setup MSW handler: throw network error (msw passthrough or network error simulation)
    - Render modal, click purchase
    - Assert: network error message visible

  - Each test must actually assert something -- no TODO comments left

TV-2: Run frontend build verification (P1, after FS-* tasks complete)
  - Run: cd frontend && npm run lint
  - Run: cd frontend && npm run build
  - Run: cd frontend && npm run test:run
  - If any test fails, read the failure output and fix it
  - Verify: grep -r "alert(" frontend/src/app --include="*.tsx" | grep -v __tests__ | grep -v test/ returns ZERO
  - Verify: ls frontend/src/app/opengraph-image.tsx exists
  - Verify: ls frontend/src/app/[locale]/(miniapp)/loading.tsx exists
  - Verify: ls frontend/src/app/[locale]/(auth)/loading.tsx exists
  - Verify: grep "schema-dts" frontend/package.json returns a match
  - Verify: grep "application/ld+json" frontend/src/app/[locale]/layout.tsx returns a match

TV-3: Run backend test verification (P1, after BT-* tasks complete)
  - Run: cd backend && python -m pytest tests/integration/api/v1/trial/ -v
  - Run: cd backend && python -m pytest tests/integration/api/v1/usage/ -v
  - Run: cd backend && python -m pytest tests/integration/api/v1/payments/ -v
  - If any test fails, read the error and determine if it's a test issue or a production code issue
  - If test issue: fix the test
  - If production issue: report to lead (do NOT fix production code)
  - Count total integration tests: find backend/tests/integration -name "test_*.py" -exec grep -c "async def test_" {} + | paste -sd+ | bc
  - Must be >= 30 total integration tests

DONE CRITERIA: All builds pass. All tests pass. Zero TODO-only test stubs. Zero alert() in production code. JSON-LD present in layouts.
```

---

## Task Registry & Dependencies

### Dependency Graph

```
                    +-- FS-1 (install schema-dts) --> FS-2, FS-3
                    |
                    +-- FS-2 (root JSON-LD) --- after FS-1
                    |
                    +-- FS-3 (dashboard JSON-LD) --- after FS-1
                    |
PHASE 5 START ------+-- FS-4 (opengraph-image) -- independent
                    |
                    +-- FS-5 (miniapp loading.tsx) -- independent
                    |
                    +-- FS-6 (auth loading.tsx) -- independent
                    |
                    +-- FS-7 (alert -> showAlert) -- independent
                    |
                    +-- BT-1 (trial tests) -- independent
                    |
                    +-- BT-2 (usage tests) -- independent
                    |
                    +-- BT-3 (payments tests) -- independent
                    |
                    +-- TV-1 (PurchaseConfirmModal tests) -- independent
                    |
                    +-- TV-2 (frontend verification) -- after ALL FS-* + TV-1
                    |
                    +-- TV-3 (backend verification) -- after ALL BT-*
```

### Full Task Table

| ID | Task | Agent | Depends on | Priority |
|----|------|-------|------------|----------|
| FS-1 | Install schema-dts + create JsonLd utility | frontend-seo | -- | P0 |
| FS-2 | Add Organization + WebSite JSON-LD to root layout | frontend-seo | FS-1 | P0 |
| FS-3 | Add SoftwareApplication JSON-LD to dashboard layout | frontend-seo | FS-1 | P0 |
| FS-4 | Create opengraph-image.tsx | frontend-seo | -- | P1 |
| FS-5 | Create loading.tsx for miniapp | frontend-seo | -- | P1 |
| FS-6 | Create loading.tsx for auth | frontend-seo | -- | P1 |
| FS-7 | Replace alert() with webApp?.showAlert() | frontend-seo | -- | P0 |
| BT-1 | Create trial integration tests | backend-tests | -- | P0 |
| BT-2 | Create usage integration tests | backend-tests | -- | P0 |
| BT-3 | Create payments integration tests | backend-tests | -- | P0 |
| TV-1 | Implement PurchaseConfirmModal test stubs | test-verify | -- | P0 |
| TV-2 | Frontend build verification | test-verify | FS-*, TV-1 | P1 |
| TV-3 | Backend test verification | test-verify | BT-* | P1 |

### Task Counts

| Agent | Tasks | IDs |
|-------|-------|-----|
| frontend-seo | 7 | FS-1..7 |
| backend-tests | 3 | BT-1..3 |
| test-verify | 3 | TV-1..3 |
| **TOTAL** | **13** | |

---

## Lead Coordination Rules

1. **Spawn all 3 agents immediately.** Initial assignments:
   - `frontend-seo` -> FS-1 first (install schema-dts), then FS-2+3+4+5+6+7 in parallel
   - `backend-tests` -> BT-1 + BT-2 + BT-3 in parallel (all independent)
   - `test-verify` -> TV-1 immediately (PurchaseConfirmModal tests), then TV-2 + TV-3 after dependencies

2. **Communication protocol:**
   - frontend-seo finishes ALL FS-* -> messages test-verify ("all frontend changes done, run TV-2")
   - backend-tests finishes ALL BT-* -> messages test-verify ("all backend tests written, run TV-3")
   - test-verify reports pass/fail back to lead

3. **Parallel execution strategy:**
   - Wave 1 (immediate): FS-1, FS-4, FS-5, FS-6, FS-7, BT-1, BT-2, BT-3, TV-1
   - Wave 2 (after FS-1): FS-2, FS-3
   - Wave 3 (verification): TV-2 (after ALL FS-* + TV-1), TV-3 (after ALL BT-*)

4. **File conflict prevention:**
   - frontend-seo owns `frontend/` exclusively (except test files)
   - backend-tests owns `backend/tests/integration/` exclusively
   - test-verify writes ONLY in `*/__tests__/` directories AND runs verification commands
   - Nobody modifies another agent's files

5. **Do NOT start implementing if you are lead -- delegate.** Use delegate mode exclusively.

6. **Progress tracking.** Use the shared TaskList (TaskCreate/TaskUpdate). Do NOT use beads (`bd`) -- SQLite lock conflicts with parallel agents.

7. **If any agent is blocked >5 minutes:** reassign them to an independent task.

---

## Prohibitions

- Do NOT downgrade library versions (Next.js 16, React 19, schema-dts latest)
- Do NOT break existing working endpoints, pages, or tests
- Do NOT modify generated/types.ts manually
- Do NOT create files outside your assigned directory
- Do NOT use beads (`bd create/close`) -- use TaskList instead
- Do NOT skip Context7 MCP doc lookup when using a library
- Do NOT touch Telegram bot code (services/telegram-bot/) -- OUT OF SCOPE
- Do NOT touch mobile code (cybervpn_mobile/) -- all gaps closed
- Do NOT touch infrastructure code (infra/) -- 100% complete
- Do NOT add `'use client'` to loading.tsx or opengraph-image.tsx (they must be Server Components)
- Do NOT hardcode domain URLs in JSON-LD -- use constants or environment variables where possible
- Do NOT leave any TODO-only test stubs -- every test must assert something

---

## Final Verification (Lead runs after ALL tasks complete)

```bash
# ===== Frontend Build =====
cd frontend && npm run lint
# Must pass with zero errors

cd frontend && npm run build
# Must pass with zero errors

cd frontend && npm run test:run
# Must pass with zero failures

# ===== Frontend File Checks =====
# JSON-LD utility exists
ls frontend/src/shared/lib/json-ld.tsx
# Must exist

# schema-dts installed
grep "schema-dts" frontend/package.json
# Must match

# JSON-LD in root layout
grep "application/ld+json" frontend/src/app/[locale]/layout.tsx
# Must match

# JSON-LD in dashboard layout
grep "application/ld+json" frontend/src/app/[locale]/(dashboard)/layout.tsx
# Must match

# OG image exists
ls frontend/src/app/opengraph-image.tsx
# Must exist

# Loading states exist
ls frontend/src/app/[locale]/(miniapp)/loading.tsx
ls frontend/src/app/[locale]/(auth)/loading.tsx
# Both must exist

# Zero alert() in production
grep -r "alert(" frontend/src/app --include="*.tsx" | grep -v __tests__ | grep -v test/ | wc -l
# Must be 0

# Zero TODO-only tests in PurchaseConfirmModal
grep -c "TODO:" frontend/src/app/[locale]/(dashboard)/subscriptions/components/__tests__/PurchaseConfirmModal.test.tsx
# Must be 0

# ===== Backend Tests =====
cd backend && python -m pytest tests/integration/api/v1/trial/ -v
# Must pass

cd backend && python -m pytest tests/integration/api/v1/usage/ -v
# Must pass

cd backend && python -m pytest tests/integration/api/v1/payments/ -v
# Must pass

# Count total integration test files
ls backend/tests/integration/api/v1/*/test_*.py | wc -l
# Must be >= 20 files
```

All commands must pass with zero errors. If any fail, assign fix to the responsible agent.

---

## Completion Checklist

### Frontend -- JSON-LD Structured Data
- [ ] `schema-dts` installed in package.json
- [ ] JsonLd<T> utility component at shared/lib/json-ld.tsx
- [ ] Organization + WebSite JSON-LD in root layout
- [ ] SoftwareApplication JSON-LD in dashboard layout
- [ ] JSON-LD renders as `<script type="application/ld+json">` in HTML output

### Frontend -- Missing Files
- [ ] opengraph-image.tsx created (edge runtime, cyberpunk design)
- [ ] loading.tsx for miniapp (CSS-only pulse skeleton)
- [ ] loading.tsx for auth (centered form skeleton)

### Frontend -- Code Quality
- [ ] Zero alert() calls in production code (replaced with webApp?.showAlert())
- [ ] showError helper handles non-Telegram fallback
- [ ] PurchaseConfirmModal tests: 6 TODO stubs -> 6 real assertions

### Backend -- Integration Test Coverage
- [ ] trial/ directory: 5+ tests (activate, already_used, rate_limit, status, auth)
- [ ] usage/ directory: 3+ tests (success, no_subscription, auth)
- [ ] payments/ directory: 6+ tests (invoice, invalid_plan, history, webhook_valid, webhook_invalid, auth)

### Build Verification
- [ ] `npm run lint` passes
- [ ] `npm run build` passes
- [ ] `npm run test:run` passes
- [ ] `pytest` passes for all new test directories
