# CyberVPN Phase 6 — Close ALL Remaining Gaps — Agent Team Prompt

> Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
> User presses **Shift+Tab** to enter delegate mode, then pastes this prompt.
> Teammates load `CLAUDE.md` automatically. Spawn prompts contain ONLY task-specific context.
> **Scope**: Close EVERY remaining gap across all 4 platforms. Remove legacy remnashop.
> **Out of scope**: Certificate pinning values (require production server access), AlertManager webhook URL (requires Telegram relay deployment).

---

## Goal

1. **Remove remnashop** (legacy bot) — replaced by our `cybervpn-telegram-bot`
2. **Frontend TypeScript quality** — eliminate all `any` types in production code, fix hydration-unsafe patterns
3. **Frontend test completion** — implement every TODO test stub in PurchaseConfirmModal + WithdrawalModal
4. **Frontend performance** — fix `frameloop="always"`, clean up manual memoization, remove console.log
5. **Infrastructure fixes** — Prometheus target mismatch, missing healthchecks, Loki runbook URLs
6. **Mobile functionality** — wire wallet withdraw to real repository, improve 2FA backup codes
7. **Pass all build/lint/test/analyze checks** across every platform

**Done criteria:**
1. `npm run build` passes (frontend)
2. `npm run lint` passes (frontend)
3. `npm run test:run` passes (frontend)
4. `cd backend && python -m pytest tests/ -x -q` passes (backend)
5. `cd cybervpn_mobile && flutter analyze --no-fatal-infos` passes (mobile)
6. Zero `any` types in production `.tsx` files (excluding test files and `generated/types.ts`)
7. Zero `TODO` comments in PurchaseConfirmModal.test.tsx and WithdrawalModal.test.tsx
8. Zero `console.log(` calls in production `.ts`/`.tsx` files (outside dev-panel and web-vitals)
9. `frameloop="demand"` in GlobalNetwork.tsx
10. `remnashop` string appears ZERO times in `docker-compose.yml`
11. `docs.example.com` appears ZERO times in Loki alert rules
12. Wallet withdraw calls real repository (no `Future.delayed` placeholder)
13. `docker compose config --profiles bot --profiles monitoring -q` exits 0 (valid compose)

---

## Current State Audit (Phase 6 starting point)

### What's DONE (from Phases 1-5)

| Component | Status | Detail |
|-----------|--------|--------|
| Backend 145 endpoints, 34 route modules | All implemented | Auth, OAuth, payments, wallet, 2FA, codes, etc. |
| Backend integration tests | **180 tests in 5981 lines** | auth(7), trial(5), usage(3), payments(6), wallet(13), 2fa(12), codes(15), oauth(15), profile(9), security(7), subscriptions(6), notifications(10) |
| Backend Prometheus metrics wired | 4/34 route modules | auth, payments, subscriptions, trial |
| Backend rate limiting | Global + 10 endpoint-specific | login, 2FA, telegram, antiphishing, trial, cancel |
| Frontend JSON-LD (schema-dts) | Organization + WebSite + SoftwareApplication | 3 schemas in 2 layouts |
| Frontend SEO | robots.ts + sitemap.ts + opengraph-image.tsx | All exist |
| Frontend error/not-found/loading | All 3 route groups covered | dashboard, auth, miniapp |
| Frontend Sentry | 3 configs (client, server, edge) | Fully wired |
| Frontend i18n | 24 namespaces, 38 locales | All registered |
| Frontend tests | 51 files, 4505 lines | API + component + widget tests |
| Mobile 20 features | 17/20 structurally complete | OAuth (Google, Apple, Telegram, biometric) all wired |
| Mobile tests | 184 files | 17/20 features covered |
| Mobile 38 locales | All generated | Full i18n |
| Infra 25 services | 22/25 healthchecked | Docker Compose with 7 profiles |
| Infra monitoring | 75 alert rules, 11 dashboards | Prometheus + Loki + Tempo + Grafana + AlertManager |
| Infra OTLP | Collector → Tempo → Grafana | Full distributed tracing |

### What's STILL MISSING (Phase 6 must fix)

#### 1. Legacy remnashop in docker-compose (REMOVAL)
- `infra/docker-compose.yml` lines 256-292: `remnashop-redis` + `remnashop` services still present
- `remnashop-redis` is in profile `bot` (starts alongside our `cybervpn-telegram-bot`)
- `remnashop` is in profile `bot-legacy` (separate but pollutes config)
- `infra/remnashop/` directory with config files still exists
- Our bot `cybervpn-telegram-bot` does NOT depend on `remnashop-redis` — it uses `remnawave-redis`

#### 2. Frontend `any` types in production code (~36 occurrences)
**SubscriptionsClient.tsx** (6×):
- Line 28: `plans?.find((p: any) => ...)`
- Line 60: `subscriptions?.find((sub: any) => ...)`
- Lines 158-159: `.filter((plan: any) => ...).map((plan: any) => ...)`
- Lines 197-198: `.filter((sub: any) => ...).map((sub: any) => ...)`

**AnalyticsClient.tsx** (8×):
- Lines 59, 65, 66, 71: `(paymentsData as any[])` casts
- Lines 82, 97, 101, 115: `(subscriptionsData as any[])` casts

**MonitoringClient.tsx** (16×):
- Lines 73-104: `(healthData as any).api_status`, `(statsData as any).total_requests`, etc.
- ALL 16 property accesses use `as any` cast

**Other files** (6×):
- `PurchaseConfirmModal.tsx:135`: `requestData: any`
- `CodesSection.tsx:196`: `(invite: any, i: number)`
- `WithdrawalModal.tsx:100`: `withdrawalData: any`
- `ReferralClient.tsx:145`: `(commission: any)`
- `PartnerClient.tsx:278`: `(code: any, i: number)`
- `PartnerClient.tsx:317`: `(earning: any, i: number)`

#### 3. Frontend `new Date()` in render (hydration-unsafe)
- `MonitoringClient.tsx:75,82,89,96,161`: `new Date().toISOString()` called during data transformation in render — server/client mismatch risk
- `TrialSection.tsx:55`: `new Date()` inside `getDaysRemaining()` called during render

Note: `footer.tsx:60` and `dev-panel.tsx:289,296` are INSIDE `useEffect` — already correct.

#### 4. Frontend `frameloop="always"` (performance)
- `GlobalNetwork.tsx:352`: `frameloop="always"` — continuously renders even when static
- `GlobalNetwork.backup.tsx:296`: Uses `frameloop="demand"` — correct reference pattern

#### 5. Frontend manual useMemo (React Compiler enabled)
- `PasswordStrengthMeter.tsx:43`: `useMemo(() => calculateStrength(password), [password])` — React Compiler handles this
- Note: cypher-text.tsx, scramble-text.tsx, useTelegramWebApp.ts use `useCallback` for external APIs (rAF, Telegram SDK) — these are CORRECT per CLAUDE.md exception

#### 6. Frontend console.log/warn in production
- `useTelegramWebApp.ts:115`: `console.log('[useTelegramWebApp] Initialized', ...)`
- `useTelegramWebApp.ts:96`: `console.warn('Telegram WebApp not available...')`
- Note: `web-vitals.ts` console.warn/error is intentional perf monitoring — leave it

#### 7. Frontend test stubs (70+ TODO lines)
**PurchaseConfirmModal.test.tsx** — 19 TODO stubs across lines 460-518:
- `test_error_message_clears_on_retry` (line 459)
- `test_purchase_button_disabled_without_plan` (line 471)
- `test_prevents_double_submission` (line 476)
- `test_validates_minimum_plan_price` (line 483)
- `test_displays_qr_code` (line 491)
- `test_displays_payment_address_copy_button` (line 498)
- `test_copies_address_to_clipboard` (line 504)
- `test_displays_amount_and_currency` (line 511)
- `test_displays_expiration_time` (line 517)

**WithdrawalModal.test.tsx** — 20+ TODO stubs across lines 100-391:
- Minimum amount display (line 100)
- Method selection in request (line 144)
- Success message display (line 185)
- onSuccess callback (line 193)
- Input validation: negative/zero (line 276), non-numeric (line 283), empty (line 289)
- Double submission prevention (line 294)
- Insufficient balance error (line 304)
- Below minimum error (line 312)
- Generic server error (line 319)
- Network error (line 326)
- Error clears on retry (line 333)
- Rate limit error (line 342)
- Payment method list (line 351)
- Default method selection (line 357)
- Method switching (line 362)
- Method in API request (line 368)
- Balance display format (line 378)
- Pending balance deduction (line 383)
- Max withdrawal limit (line 388)

#### 8. Frontend root layout — static metadata
- `frontend/src/app/[locale]/layout.tsx:31`: Uses `export const metadata: Metadata` (static)
- Child layouts use `export async function generateMetadata()` — inconsistency

#### 9. Prometheus target mismatch
- `infra/prometheus/prometheus.yml:18-20`: Job `cybervpn-backend` targets `cybervpn-backend:9091`
- No service named `cybervpn-backend` exists in docker-compose — should be the backend's metrics endpoint

#### 10. Missing healthchecks (2 services)
- `caddy` (line 224-239): No healthcheck
- `remnawave-subscription-page` (line 241-254): No healthcheck

#### 11. Loki runbook URLs — placeholder
- `infra/loki/rules/cybervpn/alerts.yml` lines 18, 33, 48, 63, 78, 93: all point to `https://docs.example.com/runbooks/...`

#### 12. Mobile wallet withdraw — placeholder
- `withdraw_bottom_sheet.dart:56-67`: Uses `Future.delayed(800ms)` + placeholder snackbar
- Real repository exists: `walletRepositoryProvider` → `withdrawFunds({amount, method, details})`
- Remote data source exists: `wallet_remote_ds.dart:184` → POST to `ApiConstants.walletWithdraw`
- The ENTIRE plumbing works — just need to replace the placeholder with `ref.read(walletRepositoryProvider).withdrawFunds(...)`

#### 13. Mobile 2FA backup codes — mock
- `two_factor_screen.dart:509-510`: `_backupCodes = _generateMockBackupCodes()` generates random digits client-side
- `_generateMockBackupCodes()` (line 756): Uses `DateTime.now().millisecondsSinceEpoch` — NOT crypto-random
- Backend 2FA verify endpoint may return backup codes — needs investigation

---

## Team

| Role | Agent name | Model | Working directory | subagent_type | Tasks |
|------|-----------|-------|-------------------|---------------|-------|
| Lead (you) | -- | opus | all (coordination only) | -- | 0 |
| Frontend TypeScript + Perf | `frontend-quality` | sonnet | `frontend/` | general-purpose | 7 |
| Frontend Test Completion | `frontend-tests` | sonnet | `frontend/` | general-purpose | 2 |
| Infrastructure Cleanup | `infra-cleanup` | sonnet | `infra/` | general-purpose | 4 |
| Mobile Polish | `mobile-polish` | sonnet | `cybervpn_mobile/` | mobile-lead | 2 |
| Build Verification | `verify` | sonnet | all | general-purpose | 4 |

---

## Spawn Prompts

### frontend-quality

```
You are frontend-quality on the CyberVPN team (Phase 6). You fix TypeScript type safety, hydration issues, and performance problems.
Stack: Next.js 16, React 19, TypeScript 5.9, Tailwind CSS 4, React Compiler enabled.
You work ONLY in frontend/src/. Do NOT touch test files (__tests__/ directories).

CONTEXT — What's already working:
- 238 source files, 51 test files — all working
- schema-dts JSON-LD, Sentry, i18n (24 namespaces, 38 locales) — all configured
- error.tsx + not-found.tsx + loading.tsx in all 3 route groups
- React Compiler is enabled (reactCompiler: true in next.config.ts)
- OpenAPI types exist in frontend/src/lib/api/generated/types.ts

KEY FILES TO READ FIRST:
- OpenAPI types: frontend/src/lib/api/generated/types.ts (find Plan, Subscription, Payment, HealthCheck types)
- API modules with proper types: frontend/src/lib/api/subscriptions.ts, frontend/src/lib/api/payments.ts
- Existing well-typed component pattern: frontend/src/app/[locale]/(dashboard)/settings/page.tsx

RULES:
- Use Context7 MCP to look up library docs before using any library.
- Do NOT downgrade any library version.
- NEVER add `any` types. Replace with proper types from generated/types.ts or define local interfaces.
- Do NOT modify test files — frontend-tests agent handles those.
- Do NOT modify files in node_modules, generated/types.ts, or 3d/__tests__/.
- Follow existing code patterns in the codebase.

YOUR TASKS:

FQ-1: Replace `any` types in SubscriptionsClient.tsx (P0)
  - File: frontend/src/app/[locale]/(dashboard)/subscriptions/components/SubscriptionsClient.tsx
  - Read frontend/src/lib/api/generated/types.ts FIRST to find the Plan and Subscription types
  - Read frontend/src/lib/api/subscriptions.ts to see how data is fetched and what types it uses
  - Replace 6 occurrences:
    Line 28: `(p: any)` → proper Plan type
    Line 60: `(sub: any)` → proper Subscription type
    Lines 158-159: `(plan: any)` → Plan type for filter and map
    Lines 197-198: `(sub: any)` → Subscription type for filter and map
  - If no exact type exists in generated/types.ts, create a local interface matching the data shape
  - Verify: grep ": any" on this file returns 0 matches after fix

FQ-2: Replace `any` types in AnalyticsClient.tsx (P0)
  - File: frontend/src/app/[locale]/(dashboard)/analytics/components/AnalyticsClient.tsx
  - Replace 8 occurrences on lines 59, 65, 66, 71, 82, 97, 101, 115
  - All are `(paymentsData as any[])` or `(subscriptionsData as any[])`
  - Read the component to understand where paymentsData/subscriptionsData come from (likely useQuery hooks)
  - Define local interfaces:
    interface PaymentRecord { amount?: number; created_at?: string; currency?: string; }
    interface SubscriptionRecord { status?: string; plan_type?: string; created_at?: string; }
  - Replace ALL `as any[]` casts with proper types
  - Replace ALL `(p: any)` / `(s: any)` callback params with typed params
  - Verify: grep ": any\|as any" on this file returns 0 matches

FQ-3: Replace `any` types + fix `new Date()` in MonitoringClient.tsx (P0)
  - File: frontend/src/app/[locale]/(dashboard)/monitoring/components/MonitoringClient.tsx
  - PART A — Fix 16 `as any` casts (lines 73-104):
    Read the health/stats API response shapes from frontend/src/lib/api/monitoring.ts
    Create interfaces like:
    interface HealthData { api_status?: string; api_response_time?: number; api_uptime?: number; database_status?: string; ... }
    interface StatsData { total_requests?: number; avg_response_time?: number; error_rate?: number; active_connections?: number; }
    Replace ALL `(healthData as any).xxx` with proper typed access
    Replace ALL `(statsData as any).xxx` with proper typed access
  - PART B — Fix `new Date()` in render (lines 75, 82, 89, 96, 161):
    The data transformation creates service objects with `lastCheck: new Date().toISOString()`
    This runs during render and causes hydration mismatch (server vs client time)
    Fix: use a `useState` + `useEffect` pattern OR use the actual `lastCheck` from API data
    If API provides lastCheck, use it. If not, initialize once in useEffect:
      const [lastCheck, setLastCheck] = useState('');
      useEffect(() => { setLastCheck(new Date().toISOString()); }, []);
    Then reference `lastCheck` instead of `new Date().toISOString()` in the data
    Line 161: same fix — use stored lastCheck value

FQ-4: Replace `any` types in remaining 5 files (P0)
  - PurchaseConfirmModal.tsx:135 → `requestData: any` → define interface { plan_id: string; promo_code?: string; payment_method?: string; }
  - CodesSection.tsx:196 → `(invite: any, i: number)` → find/define Invite type from API
  - WithdrawalModal.tsx:100 → `withdrawalData: any` → define interface { amount: number; method: string; }
  - ReferralClient.tsx:145 → `(commission: any)` → define Commission interface
  - PartnerClient.tsx:278,317 → `(code: any)` and `(earning: any)` → define Code and Earning interfaces
  - For each file: READ the file first, understand data shape, define minimal interface, replace `any`
  - Verify: grep ": any" across all 5 files returns 0 (excluding test files)

FQ-5: Fix `new Date()` in TrialSection.tsx render (P1)
  - File: frontend/src/app/[locale]/(dashboard)/subscriptions/components/TrialSection.tsx
  - Line 55: `const now = new Date()` inside getDaysRemaining() — called during render
  - Fix: Since getDaysRemaining() computes day diff and gets called with trialEnd string:
    Move the `new Date()` to a `useState` with `useEffect`, OR
    Accept a `now` parameter and compute once with useEffect/useRef
  - Simplest approach: the function is only used in JSX — use useState:
    const [now] = useState(() => new Date());  // Stable across render
  - This is safe because trial expiry changes rarely (not every millisecond)

FQ-6: Change frameloop to "demand" in GlobalNetwork.tsx (P1)
  - File: frontend/src/3d/scenes/GlobalNetwork.tsx
  - Line 352: Change `frameloop="always"` to `frameloop="demand"`
  - This stops the continuous render loop when nothing changes
  - Read the file to check if any animations use `useFrame` — if so, those frames will still trigger
    via `invalidate()` from drei helpers or R3F's internal mechanism
  - If animations break, add `invalidate()` calls in the useFrame hooks:
    useFrame(({ invalidate }) => { /* animation logic */ invalidate(); });
  - Also remove unused useMemo in PasswordStrengthMeter.tsx:43 if safe:
    File: frontend/src/features/auth/components/PasswordStrengthMeter.tsx
    Line 43: `useMemo(() => calculateStrength(password), [password])` → just `calculateStrength(password)`
    React Compiler auto-memoizes this.

FQ-7: Remove console.log and fix root layout metadata (P1)
  - PART A — Remove console.log from useTelegramWebApp.ts:
    File: frontend/src/app/[locale]/(miniapp)/hooks/useTelegramWebApp.ts
    Line 115: Remove `console.log('[useTelegramWebApp] Initialized', {...})`
    Line 96: Keep `console.warn(...)` — it's a useful dev warning when outside Telegram
    OR wrap both in `process.env.NODE_ENV === 'development'` check
  - PART B — Convert root layout static metadata to generateMetadata (OPTIONAL, low priority):
    File: frontend/src/app/[locale]/layout.tsx
    Line 31-40: Currently `export const metadata: Metadata = {...}`
    Could convert to:
    export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
      const { locale } = await params;
      return { title: "VPN Command Center", description: "...", ... };
    }
    This makes it consistent with child layouts.
    BUT: the static version works fine — skip if time-constrained.

DONE CRITERIA: grep ": any" across frontend/src/app/ (excluding __tests__/ and generated/) returns 0. grep "as any" also 0. No new Date() in render paths. frameloop="demand". npm run build passes. npm run lint passes.
```

### frontend-tests

```
You are frontend-tests on the CyberVPN team (Phase 6). You implement ALL remaining TODO test stubs.
Stack: Vitest 4.0.18, @testing-library/react 16.3, MSW 2.12.9, jsdom 28, React 19.
You work ONLY in frontend/src/**/__tests__/ directories.

CONTEXT — What already exists:
- 51 frontend test files, 4505 lines — all passing
- PurchaseConfirmModal.test.tsx has ~9 test stubs with TODO comments (lines 459-518)
- WithdrawalModal.test.tsx has ~20+ test stubs with TODO comments (lines 100-391)
- Both files already have working tests above the TODO section — follow their patterns

KEY FILES TO READ FIRST (read ALL of these before writing any test):
1. PurchaseConfirmModal.test.tsx — read the ENTIRE file to understand existing test patterns, mocks, helpers
2. PurchaseConfirmModal.tsx — the component under test (understand props, state, API calls)
3. WithdrawalModal.test.tsx — read ENTIRE file for existing patterns
4. WithdrawalModal.tsx — the component under test
5. Look at how MSW handlers are set up in existing passing tests within the same files
6. Check imports: what test utilities, mocks, and render helpers are already available

RULES:
- Use Context7 MCP to look up library docs before using any library (MSW 2.x, React Testing Library).
- Follow EXACTLY the patterns from existing passing tests in the SAME file.
- Use MSW for API mocking — match the server setup pattern already in the file.
- Use React Testing Library: render, screen, waitFor, userEvent.
- Do NOT modify production code — ONLY test files.
- Every test MUST have at least one assertion (expect/assert). No empty tests. No TODO comments.
- If a test requires complex setup (e.g., clipboard API), mock it properly.

YOUR TASKS:

FT-1: Implement ALL PurchaseConfirmModal test stubs (P0)
  - File: frontend/src/app/[locale]/(dashboard)/subscriptions/components/__tests__/PurchaseConfirmModal.test.tsx
  - Read the component first to understand: props interface, button labels, error message locations, success state
  - Implement 9 TODO test stubs:

  test_error_message_clears_on_retry (line 459):
    - Setup MSW to fail first call, succeed on second
    - Render modal, click purchase → assert error shown
    - Click purchase again → assert error cleared, success state shown

  test_purchase_button_disabled_without_plan (line 471):
    - Render modal without plan prop (or with null/undefined plan)
    - Assert purchase button is disabled or not present

  test_prevents_double_submission (line 476):
    - Setup MSW with slow response (use delay from msw)
    - Render modal, click purchase twice rapidly
    - Assert only one API request was made (check MSW request count or button disabled state)

  test_validates_minimum_plan_price (line 483):
    - If modal validates price: render with price=0 or negative
    - Assert validation error or button disabled
    - If no client-side validation: skip this test (add a comment explaining why)

  test_displays_qr_code (line 491):
    - Setup MSW to return invoice with qr_url or payment data
    - Complete purchase flow
    - Assert: QR code element is rendered (look for img or canvas with payment data)

  test_displays_payment_address_copy_button (line 498):
    - Complete purchase flow with invoice data containing address
    - Assert: payment address text visible + copy button present

  test_copies_address_to_clipboard (line 504):
    - Mock navigator.clipboard.writeText as vi.fn()
    - Complete purchase flow, click copy button
    - Assert: clipboard.writeText was called with the address

  test_displays_amount_and_currency (line 511):
    - Complete purchase flow with invoice containing amount + currency
    - Assert: amount and currency text visible

  test_displays_expiration_time (line 517):
    - Complete purchase flow with invoice containing expiry timestamp
    - Assert: expiration time/countdown is shown in UI

FT-2: Implement ALL WithdrawalModal test stubs (P0)
  - File: frontend/src/app/[locale]/(dashboard)/wallet/components/__tests__/WithdrawalModal.test.tsx
  - Read the component first: props, form fields, validation logic, API endpoint, error handling
  - Implement 20+ TODO test stubs. Group them:

  **FORM VALIDATION (lines 276-291):**
    - Negative/zero amount → validation error
    - Non-numeric input → validation or input rejection
    - Empty amount → submit button disabled

  **SUBMISSION FLOW (lines 144-197, 294-298):**
    - Method selection included in API request
    - Success message displayed after withdrawal
    - onSuccess callback called after success
    - Double submission prevented (button disabled during request)

  **ERROR HANDLING (lines 100-101, 304-345):**
    - Minimum withdrawal amount shown
    - Insufficient balance (422) → specific error message
    - Below minimum (422) → error about minimum
    - Generic server error (500) → generic error message
    - Network error → network error message
    - Error clears on retry
    - Rate limit (429) → rate limit error with retry info

  **PAYMENT METHODS (lines 351-372):**
    - Cryptobot method available in list
    - Default method pre-selected
    - Method switching updates UI
    - Selected method sent in API request

  **BALANCE DISPLAY (lines 378-391):**
    - Balance formatted correctly (e.g., $250.50)
    - Pending balance deducted from available
    - Max withdrawal = available balance

  For EACH test:
  1. Setup MSW handler (use existing server.use() pattern from file)
  2. Render WithdrawalModal with appropriate props
  3. Interact: fill inputs, click buttons
  4. Assert: visible text, element state, mock function calls

DONE CRITERIA: grep "TODO" in both test files returns 0 matches. npm run test:run passes. Every test has at least 1 assertion.
```

### infra-cleanup

```
You are infra-cleanup on the CyberVPN team (Phase 6). You remove the legacy remnashop bot and fix infrastructure configs.
You work ONLY in infra/. Do NOT touch backend/, frontend/, or cybervpn_mobile/.

CONTEXT — Current infra state:
- 25 Docker services, 7 profiles, 22/25 healthchecked
- Our bot: `cybervpn-telegram-bot` (profile: bot) — builds from ../services/telegram-bot
- Legacy bot: `remnashop` (profile: bot-legacy) — ghcr.io/snoups/remnashop — MUST BE REMOVED
- `remnashop-redis` (profile: bot) — ONLY used by remnashop — MUST BE REMOVED
- `cybervpn-telegram-bot` depends ONLY on `remnawave` and `remnawave-redis` — NOT on remnashop-redis

KEY FILES TO READ FIRST:
- infra/docker-compose.yml (entire file — understand service structure, profiles, dependencies)
- infra/prometheus/prometheus.yml (scrape targets)
- infra/loki/rules/cybervpn/alerts.yml (runbook URLs)

RULES:
- Do NOT modify services outside your scope (remnawave, remnawave-db, remnawave-redis, workers, etc.)
- Test compose validity: `docker compose config -q` must exit 0 after changes
- Keep all existing profiles working (bot, monitoring, proxy, subscription, email-test, worker)
- Remove the `bot-legacy` profile entirely
- Preserve all comments that document architecture decisions (e.g., Redis persistence disabled)

YOUR TASKS:

IC-1: Remove remnashop and remnashop-redis from docker-compose (P0)
  - File: infra/docker-compose.yml
  - STEP 1: Remove the `remnashop-redis` service block (lines 256-273):
    - This is the Valkey instance used ONLY by remnashop
    - Verify NO other service depends on it:
      grep "remnashop-redis" infra/docker-compose.yml
      Must only appear in remnashop-redis definition and remnashop depends_on
    - Delete the entire service block
  - STEP 2: Remove the `remnashop` service block (lines 275-292):
    - This is the legacy bot image ghcr.io/snoups/remnashop:latest
    - Profile: bot-legacy
    - Delete the entire service block
  - STEP 3: Verify no dangling references:
    grep "remnashop" infra/docker-compose.yml
    Must return 0 matches
  - STEP 4: Remove the `infra/remnashop/` directory:
    rm -rf infra/remnashop/
  - STEP 5: Validate compose:
    cd infra && docker compose config -q
    Must exit 0

IC-2: Fix Prometheus scrape target mismatch (P0)
  - File: infra/prometheus/prometheus.yml
  - Lines 18-22: Job `cybervpn-backend` targets `cybervpn-backend:9091`
  - No service named `cybervpn-backend` exists in docker-compose
  - The backend service in compose is `remnawave` (exposed on port 3001 for metrics)
  - BUT the backend app (built from backend/ directory) is NOT yet deployed as a Docker service
  - OPTIONS (choose the most correct one):
    OPTION A: If the CyberVPN backend runs as a separate service with hostname `cybervpn-backend`:
      Keep the config as-is but add a comment explaining the expected deployment
    OPTION B: If the CyberVPN backend runs on the host (dev mode):
      Change target to `host.docker.internal:9091` and add extra_hosts to prometheus service
    OPTION C: If the backend metrics are not yet exposed in Docker:
      Comment out the job with an explanation:
      # - job_name: 'cybervpn-backend'
      #   # TODO: Enable when cybervpn-backend service is added to docker-compose
      #   static_configs:
      #     - targets: ['cybervpn-backend:9091']
  - Read docker-compose.yml to determine which option is correct
  - The key question: does a service named `cybervpn-backend` exist or is the FastAPI app run locally?

IC-3: Add healthchecks to caddy and subscription-page (P1)
  - File: infra/docker-compose.yml

  CADDY (currently lines 224-239):
  - Image: caddy:2.9, ports 80/443
  - Add healthcheck AFTER the `depends_on` block:
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:80"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
  - Caddy serves on port 80, so checking localhost:80 is correct

  REMNAWAVE-SUBSCRIPTION-PAGE (currently lines 241-254):
  - Image: remnawave/subscription-page:latest, port 3010
  - Add healthcheck AFTER depends_on:
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:3010"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s

IC-4: Fix Loki runbook URLs (P1)
  - File: infra/loki/rules/cybervpn/alerts.yml
  - 6 occurrences of `https://docs.example.com/runbooks/`:
    Line 18: runbook_url: "https://docs.example.com/runbooks/high-error-rate"
    Line 33: runbook_url: "https://docs.example.com/runbooks/auth-failure-spike"
    Line 48: runbook_url: "https://docs.example.com/runbooks/database-connection-errors"
    Line 63: runbook_url: "https://docs.example.com/runbooks/external-api-timeouts"
    Line 78: runbook_url: "https://docs.example.com/runbooks/critical-logs"
    Line 93: runbook_url: "https://docs.example.com/runbooks/high-memory-usage"
  - Replace `docs.example.com` with `docs.cybervpn.internal` (internal wiki convention)
  - OR remove the runbook_url lines entirely if no internal wiki exists yet
  - Best approach: change to `https://wiki.cybervpn.internal/runbooks/...` as a placeholder
    that clearly indicates it's an internal resource (not example.com)
  - Verify: grep "example.com" infra/loki/rules/ returns 0

DONE CRITERIA: Zero `remnashop` references in docker-compose.yml. No `infra/remnashop/` directory. docker compose config -q passes. Prometheus config is correct. Both caddy and subscription-page have healthchecks. No `example.com` in Loki alerts.
```

### mobile-polish

```
You are mobile-polish on the CyberVPN team (Phase 6). You wire the wallet withdraw to the real repository and improve 2FA backup codes.
Stack: Flutter 3.x, Dart 3.x, Riverpod 3.x.
You work ONLY in cybervpn_mobile/.

CONTEXT — Mobile state:
- 20 features, 184 tests, 38 locales — all working
- Google/Apple/Telegram OAuth all wired and working
- Wallet repository has FULL withdraw implementation — just not wired in the bottom sheet
- 2FA screen has mock backup codes — should use crypto-random at minimum

KEY FILES TO READ FIRST:
- Widget with placeholder: cybervpn_mobile/lib/features/wallet/presentation/widgets/withdraw_bottom_sheet.dart
- Repository interface: cybervpn_mobile/lib/features/wallet/domain/repositories/wallet_repository.dart (line 45: withdrawFunds method)
- Repository impl: cybervpn_mobile/lib/features/wallet/data/repositories/wallet_repository_impl.dart (line 54: calls remote DS)
- Remote data source: cybervpn_mobile/lib/features/wallet/data/datasources/wallet_remote_ds.dart (line 184: POST to API)
- Provider: cybervpn_mobile/lib/features/wallet/presentation/providers/wallet_provider.dart (line 18: walletRepositoryProvider)
- 2FA screen: cybervpn_mobile/lib/features/profile/presentation/screens/two_factor_screen.dart (line 755: mock backup codes)

RULES:
- Use Context7 MCP to look up library docs before using any library.
- Follow existing patterns in the codebase.
- This is a ConsumerStatefulWidget — use ref.read() to access providers.
- Handle errors gracefully — show user-friendly error messages via SnackBar.
- Do NOT break existing tests — run flutter analyze after changes.

YOUR TASKS:

MP-1: Wire wallet withdraw to real repository (P0)
  - File: cybervpn_mobile/lib/features/wallet/presentation/widgets/withdraw_bottom_sheet.dart
  - Current placeholder (lines 54-67):
    ```dart
    // Simulate withdrawal processing
    await Future.delayed(const Duration(milliseconds: 800));
    if (!mounted) return;
    // TODO: Wire actual wallet repository withdraw method
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Withdrawal initiated...')),
    );
    Navigator.of(context).pop(true);
    ```
  - Replace the placeholder with real repository call:
    ```dart
    final repository = ref.read(walletRepositoryProvider);
    final result = await repository.withdrawFunds(
      amount: double.parse(_amountController.text),
      method: _selectedMethod,
      details: {},
    );

    if (!mounted) return;
    setState(() => _isWithdrawing = false);

    result.when(
      success: (withdrawalId) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.walletWithdrawSuccess)),
        );
        Navigator.of(context).pop(true);
      },
      failure: (failure) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(failure.message)),
        );
      },
    );
    ```
  - Import the walletRepositoryProvider from the providers file
  - Import the Result type if needed
  - Read the existing code to understand the exact Result pattern used (Success/Failure)
  - Read wallet_repository.dart to see the exact method signature
  - Handle the case where `_selectedMethod` might need a default value
  - Remove the `Future.delayed` line completely
  - Remove the `// Simulate withdrawal processing` comment
  - Move `setState(() => _isWithdrawing = false)` into both success and failure handlers
  - Verify: grep "Future.delayed" in this file returns 0
  - Verify: grep "TODO" in this file returns 0

MP-2: Improve 2FA backup codes generation (P1)
  - File: cybervpn_mobile/lib/features/profile/presentation/screens/two_factor_screen.dart
  - Current mock (lines 755-766):
    ```dart
    List<String> _generateMockBackupCodes() {
      return List.generate(8, (index) => '${_randomDigits(4)}-${_randomDigits(4)}');
    }
    String _randomDigits(int length) {
      final random = DateTime.now().millisecondsSinceEpoch;
      return (random % (10 * length)).toString().padLeft(length, '0');
    }
    ```
  - PROBLEMS:
    1. Uses DateTime.now().millisecondsSinceEpoch — NOT crypto-random, very predictable
    2. The modulo math produces the SAME digits every call within the same millisecond
    3. Security risk: if user saves these codes, they're easily guessable
  - FIX: Replace with dart:math Random.secure():
    ```dart
    List<String> _generateBackupCodes() {
      final random = Random.secure();
      return List.generate(8, (_) {
        final part1 = random.nextInt(10000).toString().padLeft(4, '0');
        final part2 = random.nextInt(10000).toString().padLeft(4, '0');
        return '$part1-$part2';
      });
    }
    ```
  - Add `import 'dart:math';` at the top of the file if not already imported
  - Rename from `_generateMockBackupCodes` to `_generateBackupCodes`
  - Remove the `_randomDigits` helper method (lines 763-766)
  - Update the call site (line 510): `_backupCodes = _generateBackupCodes();`
  - Update the comment on line 509: Remove "Generate mock" → "Generate backup codes"
  - Update the doc comment on line 755: Remove "(placeholder - real implementation would get from API)"
  - NOTE: Ideally backup codes should come from the backend API during 2FA setup.
    But since the backend 2FA verify endpoint doesn't return them yet,
    crypto-random client-side generation is an acceptable interim solution.
  - Verify: grep "Mock\|mock\|DateTime.now().millisecondsSinceEpoch" in related code returns 0

DONE CRITERIA: Wallet withdraw calls walletRepositoryProvider.withdrawFunds(). No Future.delayed placeholder. 2FA backup codes use Random.secure(). flutter analyze passes.
```

### verify

```
You are verify on the CyberVPN team (Phase 6). You run all builds, tests, and final verification checks.
You work across ALL directories. You do NOT write production code — only fix issues found during verification.

CONTEXT — Other agents are working on:
- frontend-quality: TypeScript fixes, perf fixes (frontend/src/)
- frontend-tests: Test stub implementation (frontend/src/**/__tests__/)
- infra-cleanup: Docker compose cleanup (infra/)
- mobile-polish: Wallet + 2FA fixes (cybervpn_mobile/)

RULES:
- Wait for other agents to finish before running final verification.
- If a check fails, identify the RESPONSIBLE AGENT and report the issue.
- You MAY fix minor issues (typos, import errors) to unblock builds.
- You MUST NOT make substantive logic changes — report to lead instead.
- Run checks in order: lint → build → test (fail-fast)

YOUR TASKS:

VF-1: Frontend verification (P0, after frontend-quality + frontend-tests complete)
  - STEP 1: Lint
    cd frontend && npm run lint
    Must pass with 0 errors. Warnings are OK.
  - STEP 2: Build
    cd frontend && npm run build
    Must pass. If TypeScript errors, report which file/line to frontend-quality.
  - STEP 3: Tests
    cd frontend && npm run test:run
    Must pass. If test failures, report to frontend-tests.
  - STEP 4: Type safety checks
    grep -rn ": any" frontend/src/app/ --include="*.tsx" | grep -v __tests__ | grep -v generated/ | grep -v node_modules
    Must return 0 matches.
    grep -rn "as any" frontend/src/app/ --include="*.tsx" | grep -v __tests__ | grep -v generated/
    Must return 0 matches.
  - STEP 5: Test completeness
    grep -c "TODO" frontend/src/app/[locale]/(dashboard)/subscriptions/components/__tests__/PurchaseConfirmModal.test.tsx
    Must be 0.
    grep -c "TODO" frontend/src/app/[locale]/(dashboard)/wallet/components/__tests__/WithdrawalModal.test.tsx
    Must be 0.
  - STEP 6: Performance check
    grep "frameloop" frontend/src/3d/scenes/GlobalNetwork.tsx
    Must show "demand" not "always".
  - STEP 7: Console.log check
    grep -rn "console.log(" frontend/src/ --include="*.ts" --include="*.tsx" | grep -v __tests__ | grep -v node_modules | grep -v web-vitals | grep -v dev-panel
    Must return 0 matches (excluding dev-panel and web-vitals).

VF-2: Infrastructure verification (P0, after infra-cleanup complete)
  - STEP 1: Compose validity
    cd infra && docker compose config -q
    Must exit 0.
  - STEP 2: Remnashop removal
    grep -r "remnashop" infra/docker-compose.yml
    Must return 0 matches.
    ls infra/remnashop/ 2>/dev/null && echo "FAIL: remnashop dir exists" || echo "OK: removed"
  - STEP 3: Profile check (bot profile still works without remnashop)
    cd infra && docker compose --profile bot config -q
    Must exit 0.
    cd infra && docker compose --profile monitoring config -q
    Must exit 0.
  - STEP 4: Healthcheck coverage
    grep -c "healthcheck:" infra/docker-compose.yml
    Count should be >= 24 (was 22, +2 new for caddy and subscription-page)
  - STEP 5: No example.com
    grep -r "example.com" infra/loki/rules/
    Must return 0 matches.

VF-3: Mobile verification (P0, after mobile-polish complete)
  - STEP 1: Static analysis
    cd cybervpn_mobile && flutter analyze --no-fatal-infos 2>&1 | tail -5
    Must show 0 errors. Infos/warnings are OK.
  - STEP 2: Placeholder removal
    grep -n "Future.delayed" cybervpn_mobile/lib/features/wallet/presentation/widgets/withdraw_bottom_sheet.dart
    Must return 0 matches.
    grep -n "TODO" cybervpn_mobile/lib/features/wallet/presentation/widgets/withdraw_bottom_sheet.dart
    Must return 0 matches.
  - STEP 3: Backup codes security
    grep -n "DateTime.now().millisecondsSinceEpoch" cybervpn_mobile/lib/features/profile/presentation/screens/two_factor_screen.dart
    Must return 0 matches.
    grep -n "Random.secure" cybervpn_mobile/lib/features/profile/presentation/screens/two_factor_screen.dart
    Must return at least 1 match.
  - STEP 4: Run mobile tests (if flutter test is available):
    cd cybervpn_mobile && flutter test test/features/wallet/ --reporter compact 2>&1 | tail -10
    Must pass or report failures.

VF-4: Backend smoke test (P1)
  - STEP 1: Backend test suite
    cd backend && python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -20
    Must pass (all 180+ tests).
  - STEP 2: If tests fail, determine if it's a pre-existing issue or caused by Phase 6 changes.
    Phase 6 does NOT modify backend code, so failures are pre-existing.
    Report but do not block completion.

DONE CRITERIA: All 4 verification steps pass. All grep checks return expected values. Report any failures to lead with file:line details.
```

---

## Task Registry & Dependencies

### Dependency Graph

```
                    +-- FQ-1 (SubscriptionsClient any) --- independent
                    |
                    +-- FQ-2 (AnalyticsClient any) --- independent
                    |
                    +-- FQ-3 (MonitoringClient any + Date) --- independent
                    |
                    +-- FQ-4 (remaining any files) --- independent
                    |
PHASE 6 START ------+-- FQ-5 (TrialSection Date) --- independent
                    |
                    +-- FQ-6 (frameloop + useMemo) --- independent
                    |
                    +-- FQ-7 (console.log + layout) --- independent
                    |
                    +-- FT-1 (PurchaseConfirmModal tests) --- independent
                    |
                    +-- FT-2 (WithdrawalModal tests) --- independent
                    |
                    +-- IC-1 (remove remnashop) --- independent
                    |
                    +-- IC-2 (Prometheus target) --- independent
                    |
                    +-- IC-3 (healthchecks) --- after IC-1
                    |
                    +-- IC-4 (Loki runbooks) --- independent
                    |
                    +-- MP-1 (wallet withdraw) --- independent
                    |
                    +-- MP-2 (2FA backup codes) --- independent
                    |
                    +-- VF-1 (frontend verify) --- after ALL FQ-* + FT-*
                    |
                    +-- VF-2 (infra verify) --- after ALL IC-*
                    |
                    +-- VF-3 (mobile verify) --- after ALL MP-*
                    |
                    +-- VF-4 (backend verify) --- independent
```

### Full Task Table

| ID | Task | Agent | Depends on | Priority |
|----|------|-------|------------|----------|
| FQ-1 | Replace `any` in SubscriptionsClient.tsx (6 occurrences) | frontend-quality | -- | P0 |
| FQ-2 | Replace `any` in AnalyticsClient.tsx (8 occurrences) | frontend-quality | -- | P0 |
| FQ-3 | Replace `any` + fix `new Date()` in MonitoringClient.tsx (16+5) | frontend-quality | -- | P0 |
| FQ-4 | Replace `any` in 5 remaining files (6 occurrences) | frontend-quality | -- | P0 |
| FQ-5 | Fix `new Date()` in TrialSection.tsx render | frontend-quality | -- | P1 |
| FQ-6 | frameloop="demand" + remove useMemo in PasswordStrengthMeter | frontend-quality | -- | P1 |
| FQ-7 | Remove console.log + fix root layout metadata | frontend-quality | -- | P1 |
| FT-1 | Implement 9 PurchaseConfirmModal test stubs | frontend-tests | -- | P0 |
| FT-2 | Implement 20+ WithdrawalModal test stubs | frontend-tests | -- | P0 |
| IC-1 | Remove remnashop + remnashop-redis from compose + delete dir | infra-cleanup | -- | P0 |
| IC-2 | Fix Prometheus cybervpn-backend target mismatch | infra-cleanup | -- | P0 |
| IC-3 | Add healthchecks to caddy + subscription-page | infra-cleanup | IC-1 | P1 |
| IC-4 | Fix Loki runbook example.com URLs | infra-cleanup | -- | P1 |
| MP-1 | Wire wallet withdraw to walletRepositoryProvider | mobile-polish | -- | P0 |
| MP-2 | Replace mock backup codes with Random.secure() | mobile-polish | -- | P1 |
| VF-1 | Frontend lint + build + test + grep verification | verify | FQ-*, FT-* | P0 |
| VF-2 | Infrastructure compose validation + grep checks | verify | IC-* | P0 |
| VF-3 | Mobile analyze + placeholder removal checks | verify | MP-* | P0 |
| VF-4 | Backend test smoke check | verify | -- | P1 |

### Task Counts

| Agent | Tasks | IDs |
|-------|-------|-----|
| frontend-quality | 7 | FQ-1..7 |
| frontend-tests | 2 | FT-1..2 |
| infra-cleanup | 4 | IC-1..4 |
| mobile-polish | 2 | MP-1..2 |
| verify | 4 | VF-1..4 |
| **TOTAL** | **19** | |

---

## Lead Coordination Rules

1. **Spawn all 5 agents immediately.** Initial assignments:
   - `frontend-quality` → FQ-1 through FQ-7 (all independent, can work sequentially)
   - `frontend-tests` → FT-1 + FT-2 (independent, but heavy — start immediately)
   - `infra-cleanup` → IC-1 first, then IC-2 + IC-3 + IC-4
   - `mobile-polish` → MP-1 first, then MP-2
   - `verify` → VF-4 immediately (backend, independent), then VF-1 + VF-2 + VF-3 after dependencies

2. **Communication protocol:**
   - frontend-quality finishes ALL FQ-* → messages verify ("frontend quality fixes done, run VF-1")
   - frontend-tests finishes ALL FT-* → messages verify ("test stubs done, run VF-1")
   - infra-cleanup finishes ALL IC-* → messages verify ("infra cleanup done, run VF-2")
   - mobile-polish finishes ALL MP-* → messages verify ("mobile fixes done, run VF-3")
   - verify reports pass/fail back to lead

3. **Parallel execution strategy:**
   - Wave 1 (immediate): FQ-1..7, FT-1, FT-2, IC-1, IC-2, IC-4, MP-1, MP-2, VF-4
   - Wave 2 (after IC-1): IC-3
   - Wave 3 (verification): VF-1 (after FQ-* + FT-*), VF-2 (after IC-*), VF-3 (after MP-*)

4. **File conflict prevention:**
   - frontend-quality owns `frontend/src/app/**/*.tsx` and `frontend/src/features/**/*.tsx` (EXCLUDING `__tests__/`)
   - frontend-tests owns `frontend/src/**/__tests__/**` ONLY
   - infra-cleanup owns `infra/` exclusively
   - mobile-polish owns `cybervpn_mobile/lib/` exclusively
   - verify writes NOTHING — only runs commands and reports
   - CRITICAL: frontend-quality and frontend-tests MUST NOT edit the same file
     - frontend-quality edits production files (*.tsx outside __tests__)
     - frontend-tests edits test files (*.test.tsx inside __tests__)

5. **Do NOT start implementing if you are lead — delegate.** Use delegate mode exclusively.

6. **Progress tracking.** Use the shared TaskList (TaskCreate/TaskUpdate). Do NOT use beads (`bd`) — SQLite lock conflicts with parallel agents.

7. **If any agent is blocked >5 minutes:** reassign them to an independent task or help unblock.

8. **Verification failures:** If verify reports a failure:
   - TypeScript error in production file → assign to frontend-quality
   - Test failure → assign to frontend-tests
   - Compose validation error → assign to infra-cleanup
   - Flutter analyze error → assign to mobile-polish

---

## Prohibitions

- Do NOT downgrade library versions (Next.js 16, React 19, Flutter 3.x, etc.)
- Do NOT break existing working endpoints, pages, tests, or features
- Do NOT modify generated/types.ts manually — it's auto-generated from OpenAPI
- Do NOT create files outside your assigned directory
- Do NOT use beads (`bd create/close`) — use TaskList instead
- Do NOT skip Context7 MCP doc lookup when using a library
- Do NOT add `any` types — the entire point of this phase is removing them
- Do NOT leave TODO comments in test files — every test must have real assertions
- Do NOT modify backend source code (backend/src/) — only verification
- Do NOT touch 3D scene files EXCEPT GlobalNetwork.tsx line 352 (frameloop fix)
- Do NOT touch working Three.js useCallback/useMemo — they're exceptions per CLAUDE.md
- Do NOT remove console.error calls — only console.log and console.warn in production code
- Do NOT delete the `bot` profile — only remove remnashop services from it

---

## Final Verification (Lead runs after ALL tasks + VF-* complete)

```bash
# ===== Infrastructure =====
grep -r "remnashop" infra/docker-compose.yml | wc -l
# Must be 0

ls infra/remnashop/ 2>/dev/null && echo "FAIL" || echo "OK"
# Must be OK

cd infra && docker compose config -q && echo "Compose valid"
# Must print "Compose valid"

cd infra && docker compose --profile bot config -q && echo "Bot profile valid"
# Must print "Bot profile valid"

grep -c "healthcheck:" infra/docker-compose.yml
# Must be >= 24

grep -r "example.com" infra/loki/rules/ | wc -l
# Must be 0

# ===== Frontend =====
cd frontend && npm run lint
# 0 errors

cd frontend && npm run build
# Success

cd frontend && npm run test:run
# All pass

grep -rn ": any" frontend/src/app/ --include="*.tsx" | grep -v __tests__ | grep -v generated/ | wc -l
# Must be 0

grep -rn "as any" frontend/src/app/ --include="*.tsx" | grep -v __tests__ | grep -v generated/ | wc -l
# Must be 0

grep -c "TODO" frontend/src/app/[locale]/(dashboard)/subscriptions/components/__tests__/PurchaseConfirmModal.test.tsx
# Must be 0

grep -c "TODO" frontend/src/app/[locale]/(dashboard)/wallet/components/__tests__/WithdrawalModal.test.tsx
# Must be 0

grep "frameloop" frontend/src/3d/scenes/GlobalNetwork.tsx
# Must show "demand"

grep -rn "console.log(" frontend/src/ --include="*.ts" --include="*.tsx" | grep -v __tests__ | grep -v node_modules | grep -v web-vitals | grep -v dev-panel | wc -l
# Must be 0

# ===== Mobile =====
cd cybervpn_mobile && flutter analyze --no-fatal-infos 2>&1 | tail -3
# 0 errors

grep "Future.delayed" cybervpn_mobile/lib/features/wallet/presentation/widgets/withdraw_bottom_sheet.dart | wc -l
# Must be 0

grep "TODO" cybervpn_mobile/lib/features/wallet/presentation/widgets/withdraw_bottom_sheet.dart | wc -l
# Must be 0

grep "DateTime.now().millisecondsSinceEpoch" cybervpn_mobile/lib/features/profile/presentation/screens/two_factor_screen.dart | wc -l
# Must be 0

grep "Random.secure" cybervpn_mobile/lib/features/profile/presentation/screens/two_factor_screen.dart | wc -l
# Must be >= 1

# ===== Backend =====
cd backend && python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -5
# All 180+ tests pass
```

All commands must pass with expected values. If any fail, assign fix to the responsible agent.

---

## Completion Checklist

### Infrastructure — Remnashop Removal
- [ ] `remnashop` service removed from docker-compose.yml
- [ ] `remnashop-redis` service removed from docker-compose.yml
- [ ] `infra/remnashop/` directory deleted
- [ ] `bot-legacy` profile no longer exists
- [ ] `docker compose config -q` passes
- [ ] `docker compose --profile bot config -q` passes

### Infrastructure — Config Fixes
- [ ] Prometheus target fixed (cybervpn-backend → correct target or commented out)
- [ ] Caddy has healthcheck
- [ ] Subscription-page has healthcheck
- [ ] Loki runbook URLs no longer point to example.com

### Frontend — TypeScript Quality
- [ ] Zero `any` types in production SubscriptionsClient.tsx
- [ ] Zero `any` types in production AnalyticsClient.tsx
- [ ] Zero `any` types in production MonitoringClient.tsx
- [ ] Zero `any` types in PurchaseConfirmModal.tsx, CodesSection.tsx, WithdrawalModal.tsx
- [ ] Zero `any` types in ReferralClient.tsx, PartnerClient.tsx
- [ ] All replaced with proper interfaces or types from generated/types.ts

### Frontend — Hydration & Performance
- [ ] No `new Date()` in render paths (MonitoringClient, TrialSection fixed)
- [ ] `frameloop="demand"` in GlobalNetwork.tsx
- [ ] PasswordStrengthMeter useMemo removed (React Compiler handles it)
- [ ] No `console.log()` in production code (outside dev-panel and web-vitals)

### Frontend — Test Completion
- [ ] PurchaseConfirmModal.test.tsx: 0 TODO stubs, 9 new real tests
- [ ] WithdrawalModal.test.tsx: 0 TODO stubs, 20+ new real tests
- [ ] All tests pass: `npm run test:run`

### Mobile — Functionality
- [ ] Wallet withdraw calls `walletRepositoryProvider.withdrawFunds()`
- [ ] No `Future.delayed` placeholder in withdraw_bottom_sheet.dart
- [ ] 2FA backup codes use `Random.secure()` instead of `DateTime.now().millisecondsSinceEpoch`
- [ ] `flutter analyze` passes

### Build Verification
- [ ] `npm run lint` passes
- [ ] `npm run build` passes
- [ ] `npm run test:run` passes
- [ ] `flutter analyze --no-fatal-infos` passes
- [ ] `docker compose config -q` passes
- [ ] `pytest tests/ -x -q` passes
