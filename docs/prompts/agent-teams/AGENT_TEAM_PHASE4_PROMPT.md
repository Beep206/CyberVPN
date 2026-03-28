# CyberVPN Phase 4 — Final Gap Closure + 100% Observability — Agent Team Prompt

> Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
> User presses **Shift+Tab** to enter delegate mode, then pastes this prompt.
> Teammates load `CLAUDE.md` automatically. Spawn prompts contain ONLY task-specific context.
> **Scope**: Close ALL remaining gaps across Frontend, Mobile, Backend, Infrastructure.
> **Out of scope**: Telegram Bot (services/telegram-bot/).

---

## Goal

1. Close every remaining stub, placeholder, dead code, missing file, and compilation error
2. Achieve **100% observability**: metrics actually instrumented (not just defined), Loki/Tempo dashboards, log-based alerts, SLO tracking
3. Production-ready: error boundaries, SEO, i18n, Sentry on all platforms, healthchecks everywhere

**Done criteria:**
1. `npm run build` passes (frontend)
2. `flutter analyze` passes with zero errors (mobile)
3. `pytest backend/tests/ -v` passes (backend)
4. `docker compose --profile monitoring config --quiet` validates (infra)
5. Zero error.tsx/not-found.tsx missing from route groups
6. All 9 i18n namespaces registered in `request.ts`
7. Sentry config files exist for all 3 Next.js runtimes
8. Custom Prometheus metrics actually incremented in route handlers (not just defined)
9. Grafana has Loki + Tempo dashboards (not just Prometheus)
10. Prometheus & Grafana have healthchecks in docker-compose
11. Zero duplicate constant definitions in mobile
12. Zero `_showComingSoon` calls in mobile production code

---

## Current State Audit (Phase 4 starting point)

### What's DONE (from Phase 3)

| Component | Status |
|-----------|--------|
| Backend 120+ endpoints | All implemented |
| Sentry SDK (backend + worker) | Initialized in main.py and broker.py |
| FastAPI Instrumentator | Configured on port 9091 |
| structlog JSON logging | Configured with contextvars |
| OpenTelemetry 4 instrumentors | FastAPI, SQLAlchemy, httpx, Redis |
| /readiness endpoint | DB + Redis + queue depth checks |
| Frontend feature pages | All 31 pages working with real API |
| Frontend zero alert() stubs | Confirmed: zero matches |
| Mini App all pages | home, plans, devices, wallet, referral, security — all real API |
| Mobile OAuth | Google + Apple fully wired |
| Mobile cancel subscription | Wired in profile_dashboard_screen |
| Mobile referral/partner | Backend-ready, graceful degradation |
| Mobile Sentry tracing | enableAutoPerformanceTracing = true |
| Mobile OTP flag | _kEnableOtpVerification = true |
| Infrastructure 11 monitoring services | All deployed with specific versions |
| 10 Prometheus scrape jobs | All configured |
| 69 alert rules in 5 files | API, DB, Redis, Infra, Worker |
| 8 Grafana dashboards | API, App, Errors, Infra, OTP, Postgres, Redis, Worker |
| 3 datasources | Prometheus, Loki, Tempo with cross-linking |
| Loki + Promtail | 7-day retention, Docker SD, JSON pipeline |
| Tempo + OTEL Collector | Trace storage with metrics generator |
| AlertManager | Severity routing, inhibition rules, Telegram template |

### What's STILL BROKEN (Phase 4 must fix)

#### Backend — Metrics Dead Code (CRITICAL)
- 11 custom metrics defined in `metrics.py` but **ZERO are incremented** in route handlers
- Instrumentation helper functions exist in `instrumentation/routes.py` and `instrumentation/cache.py`
- **No route file imports them**: `grep -r "from src.infrastructure.monitoring.instrumentation" backend/src/presentation/api --include="*.py"` returns NOTHING
- Rate limiting only on `/auth/change-password` — missing from security, trial, subscriptions, usage endpoints

#### Frontend — Missing Error Boundaries (CRITICAL)
- **ZERO** `error.tsx` files exist in entire app
- **ZERO** `not-found.tsx` files exist in entire app
- Need: dashboard root + 11 sub-routes + miniapp root + auth root = ~15 error.tsx files
- Need: dashboard root + miniapp root + auth root + app root = 4 not-found.tsx files

#### Frontend — Missing Sentry Configs (CRITICAL)
- `sentry.client.config.ts` — DOES NOT EXIST
- `sentry.server.config.ts` — DOES NOT EXIST
- `sentry.edge.config.ts` — DOES NOT EXIST
- @sentry/nextjs 10.38.0 is installed but never configured

#### Frontend — i18n Namespaces Not Registered (CRITICAL)
- 9 namespaces used in pages but NOT imported in `i18n/request.ts`:
  Settings, Analytics, Monitoring, Subscriptions, Wallet, PaymentHistory, Referral, Partner, Devices
- Message JSON files may not exist for these namespaces

#### Frontend — SEO Files Missing
- `app/robots.ts` — missing
- `app/sitemap.ts` — missing
- `app/opengraph-image.tsx` — missing
- `generateMetadata` missing from dashboard layout and auth layout

#### Frontend — Test Stubs
- `PurchaseConfirmModal.test.tsx` — 70+ TODO comments, no real tests
- `WithdrawalModal.test.tsx` — 30+ TODO comments, no real tests

#### Mobile — Compilation Errors (CRITICAL)
- `api_constants.dart` line 577: duplicate `trialActivate` (already at line 334)
- `api_constants.dart` line 587: duplicate `trialStatus` (already at line 324)
- `e2e_auth_flow_test.dart`: 16 type errors (return types don't match `Future<Result<T>>`)
- `_showComingSoon()` in `login_screen.dart` line 81: dead code (never called)
- `_sensitiveEndpoints` in `api_client.dart` line 260: unused field
- `cert_pins.dart` lines 48, 54, 58: empty certificate fingerprints

#### Infrastructure — Missing Dashboards
- All 8 dashboards use ONLY Prometheus — no Loki or Tempo panels
- No "Logs Overview" dashboard with Loki datasource
- No "Traces Overview" dashboard with Tempo datasource
- No SLO/SLI dashboard with error budget tracking

#### Infrastructure — Missing Healthchecks
- Prometheus: no healthcheck in docker-compose
- Grafana: no healthcheck in docker-compose

#### Infrastructure — No Log-Based Alerts
- Loki ruler is configured pointing to AlertManager
- But `infra/loki/rules/` directory has NO rule files

---

## Team

| Role | Agent name | Model | Working directory | subagent_type | Tasks |
|------|-----------|-------|-------------------|---------------|-------|
| Lead (you) | — | opus | all (coordination only) | — | 0 |
| Backend Metrics Wiring | `backend-metrics` | sonnet | `backend/` | backend-dev | 5 |
| Frontend Hardening | `frontend-hard` | sonnet | `frontend/` | general-purpose | 8 |
| Mobile Fixes | `mobile-fix` | sonnet | `cybervpn_mobile/` | general-purpose | 5 |
| Infra Dashboards | `infra-dash` | sonnet | `infra/` | devops-engineer | 6 |
| Test Engineer | `test-eng` | sonnet | `*/tests/`, `*/__tests__/` | test-runner | 4 |

---

## Spawn Prompts

### backend-metrics

```
You are backend-metrics on the CyberVPN team (Phase 4). You wire defined-but-unused Prometheus metrics into actual route handlers.
Stack: FastAPI, Python 3.13, SQLAlchemy 2, Redis, prometheus-client, structlog.
You work ONLY in backend/.

CONTEXT — What exists but is NOT wired:
- Custom metrics defined in backend/src/infrastructure/monitoring/metrics.py (11 metrics)
- Instrumentation helpers defined in:
  - backend/src/infrastructure/monitoring/instrumentation/routes.py (track_auth_attempt, track_registration, track_payment, track_subscription_activation, track_trial_activation)
  - backend/src/infrastructure/monitoring/instrumentation/cache.py (@track_cache_operation decorator)
- ZERO route handlers import or call these functions
- Rate limiting only exists on POST /auth/change-password (3 req/hour via Redis)

KEY FILES TO READ FIRST:
- Metrics: backend/src/infrastructure/monitoring/metrics.py
- Route helpers: backend/src/infrastructure/monitoring/instrumentation/routes.py
- Cache helper: backend/src/infrastructure/monitoring/instrumentation/cache.py
- Auth routes: backend/src/presentation/api/v1/auth/routes.py
- Payment routes: backend/src/presentation/api/v1/payments/routes.py
- Subscription routes: backend/src/presentation/api/v1/subscriptions/routes.py
- Trial routes: backend/src/presentation/api/v1/trial/routes.py
- Security routes: backend/src/presentation/api/v1/security/routes.py
- Usage routes: backend/src/presentation/api/v1/usage/routes.py
- Cache service: backend/src/application/services/cache_service.py

RULES:
- Use Context7 MCP to look up library docs before using any library.
- Do NOT downgrade any existing package version.
- Do NOT break existing working endpoints.
- Do NOT modify infra/ files — infra-dash owns those.
- Follow existing code patterns (look at how change-password rate limiting is implemented).
- Every import must be minimal — only import the specific function needed.

YOUR TASKS:

BM-1: Wire auth metrics into auth routes (P0)
  - File: backend/src/presentation/api/v1/auth/routes.py
  - Import: from src.infrastructure.monitoring.instrumentation.routes import track_auth_attempt, track_registration
  - After successful login (POST /auth/login): call track_auth_attempt(method="password", result="success")
  - After failed login: call track_auth_attempt(method="password", result="failure")
  - After successful register (POST /auth/register): call track_registration(method="email")
  - After OAuth login: call track_auth_attempt(method="oauth", result="success")
  - After magic link verify: call track_auth_attempt(method="magic_link", result="success")
  - ALSO: Wire in 2FA routes — track_auth_attempt(method="2fa_verify", result=...)

BM-2: Wire payment + subscription + trial metrics (P0)
  - File: backend/src/presentation/api/v1/payments/routes.py
  - Import: from src.infrastructure.monitoring.instrumentation.routes import track_payment
  - After successful payment/invoice creation: call track_payment(status="created", gateway="cryptobot")
  - After webhook confirms payment: call track_payment(status="completed", gateway="cryptobot")

  - File: backend/src/presentation/api/v1/subscriptions/routes.py
  - Import: from src.infrastructure.monitoring.instrumentation.routes import track_subscription_activation
  - After GET /subscriptions/active returns active subscription: call track_subscription_activation(plan_type=subscription.plan_name)

  - File: backend/src/presentation/api/v1/trial/routes.py
  - Import: from src.infrastructure.monitoring.instrumentation.routes import track_trial_activation
  - After successful trial activation (POST /trial/activate): call track_trial_activation()

BM-3: Wire cache metrics via decorator (P1)
  - File: backend/src/application/services/cache_service.py (or wherever cache get/set/delete methods live)
  - Read backend/src/infrastructure/monitoring/instrumentation/cache.py to understand the decorator
  - Apply @track_cache_operation("get"), @track_cache_operation("set"), @track_cache_operation("delete") to CacheService methods
  - If decorator pattern doesn't fit, call metrics manually:
    from src.infrastructure.monitoring.metrics import cache_operations_total
    cache_operations_total.labels(operation="get", result="hit").inc()
  - Also wire db_query_duration_seconds if there's a central query executor

BM-4: Add rate limiting to new endpoints (P1)
  - Pattern: Copy from POST /auth/change-password (lines 801-865 in auth/routes.py)
  - Uses Redis key with TTL: f"rate_limit:{endpoint}:{user_id}"
  - Add rate limiting to:
    - POST /security/antiphishing: 10 req/hour
    - DELETE /security/antiphishing: 5 req/hour
    - POST /trial/activate: 3 req/hour (prevent abuse)
    - POST /subscriptions/cancel: 3 req/hour
  - GET endpoints generally don't need rate limiting (they're read-only)

BM-5: Add missing integration tests (P2)
  - Create: backend/tests/integration/api/v1/security/test_security_flows.py
    - Test: POST antiphishing → GET antiphishing → DELETE antiphishing
    - Test: POST antiphishing with too-long code (>50 chars) → 422
  - Create: backend/tests/integration/api/v1/subscriptions/test_subscription_flows.py
    - Test: GET /subscriptions/active (mock Remnawave response)
    - Test: POST /subscriptions/cancel
  - Follow existing test pattern from backend/tests/integration/api/v1/auth/test_auth_flows.py
  - Use httpx AsyncClient + pytest-asyncio + dependency overrides

DONE CRITERIA: grep -r "from src.infrastructure.monitoring.instrumentation" backend/src/presentation/api/ returns 5+ matches. curl :9091/metrics | grep "auth_attempts_total" shows non-zero counter after a login. pytest passes.
```

### frontend-hard

```
You are frontend-hard on the CyberVPN team (Phase 4). You add error boundaries, SEO files, Sentry configs, and fix i18n registration.
Stack: Next.js 16, React 19, TypeScript 5.9, Tailwind CSS 4, @sentry/nextjs 10.38.0, next-intl 4.7.
You work ONLY in frontend/.

CONTEXT — What's already working:
- All 31 pages render real data, zero alert() stubs
- @sentry/nextjs 10.38.0 is in package.json but NO config files exist
- 17 i18n namespaces registered, 9 more needed
- Loading.tsx exists for dashboard route group only
- Security modals, purchase flow, wallet — all DONE and real

CRITICAL GAPS TO FIX:

KEY FILES TO READ FIRST:
- i18n registration: frontend/src/i18n/request.ts (lines 75-112)
- Dashboard layout: frontend/src/app/[locale]/(dashboard)/layout.tsx
- Miniapp layout: frontend/src/app/[locale]/(miniapp)/layout.tsx
- Auth layout: frontend/src/app/[locale]/(auth)/layout.tsx
- Root layout: frontend/src/app/[locale]/layout.tsx
- Existing error pattern: Search for any error boundary in the codebase to follow style
- Message files: frontend/messages/en-EN/ (list existing files)

RULES:
- Use Context7 MCP to look up library docs before using any library.
- Do NOT downgrade any library version.
- All new components must be cyberpunk-themed (Orbitron font, neon-cyan, terminal style).
- i18n: No hardcoded strings. Use useTranslations().
- Error boundaries must catch + display error with Sentry capture.
- Do NOT modify existing working components — only ADD new files.
- Use the same pattern for all error.tsx files (create one template, replicate).

YOUR TASKS:

FH-1: Create Sentry configuration files (P0)
  - Create frontend/sentry.client.config.ts:
    import * as Sentry from "@sentry/nextjs";
    Sentry.init({
      dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
      tracesSampleRate: process.env.NODE_ENV === "production" ? 0.2 : 1.0,
      replaysSessionSampleRate: 0.1,
      replaysOnErrorSampleRate: 1.0,
      integrations: [
        Sentry.browserTracingIntegration(),
        Sentry.replayIntegration(),
      ],
      environment: process.env.NODE_ENV,
    });
  - Create frontend/sentry.server.config.ts:
    import * as Sentry from "@sentry/nextjs";
    Sentry.init({
      dsn: process.env.SENTRY_DSN,
      tracesSampleRate: process.env.NODE_ENV === "production" ? 0.2 : 1.0,
      environment: process.env.NODE_ENV,
    });
  - Create frontend/sentry.edge.config.ts:
    import * as Sentry from "@sentry/nextjs";
    Sentry.init({
      dsn: process.env.SENTRY_DSN,
      tracesSampleRate: process.env.NODE_ENV === "production" ? 0.2 : 1.0,
      environment: process.env.NODE_ENV,
    });
  - Add NEXT_PUBLIC_SENTRY_DSN="" and SENTRY_DSN="" to frontend/.env.example if it exists

FH-2: Create error.tsx for all route groups (P0)
  - Create a REUSABLE error boundary component first:
    frontend/src/shared/ui/route-error-boundary.tsx
    - 'use client'
    - Props: { error: Error & { digest?: string }; reset: () => void }
    - Calls Sentry.captureException(error) on mount
    - Cyberpunk-styled: neon-red border, terminal font, error code display
    - "Try Again" button calls reset()
    - "Go Home" link to /dashboard
  - Then create error.tsx files that import and use it:
    - frontend/src/app/error.tsx (root)
    - frontend/src/app/[locale]/(dashboard)/error.tsx
    - frontend/src/app/[locale]/(miniapp)/error.tsx
    - frontend/src/app/[locale]/(auth)/error.tsx
  - Each file is simply:
    'use client';
    import { RouteErrorBoundary } from '@/shared/ui/route-error-boundary';
    export default function Error(props) { return <RouteErrorBoundary {...props} />; }
  - Sub-route error.tsx files are OPTIONAL (route group error.tsx catches children)

FH-3: Create not-found.tsx files (P0)
  - Create a REUSABLE not-found component:
    frontend/src/shared/ui/route-not-found.tsx
    - Cyberpunk-styled 404 page
    - "SIGNAL LOST" / "404" heading with glitch effect
    - "Return to Base" button linking to /dashboard
    - Terminal-style: green text on dark background
  - Then create not-found.tsx files:
    - frontend/src/app/not-found.tsx (root)
    - frontend/src/app/[locale]/(dashboard)/not-found.tsx
    - frontend/src/app/[locale]/(miniapp)/not-found.tsx
    - frontend/src/app/[locale]/(auth)/not-found.tsx

FH-4: Register missing i18n namespaces (P0)
  - File: frontend/src/i18n/request.ts
  - Add 9 new imports to the Promise.all array (after line 91):
    import(`../../messages/${locale}/settings.json`).catch(() => ({ default: {} })),
    import(`../../messages/${locale}/analytics.json`).catch(() => ({ default: {} })),
    import(`../../messages/${locale}/monitoring.json`).catch(() => ({ default: {} })),
    import(`../../messages/${locale}/subscriptions.json`).catch(() => ({ default: {} })),
    import(`../../messages/${locale}/wallet.json`).catch(() => ({ default: {} })),
    import(`../../messages/${locale}/payment-history.json`).catch(() => ({ default: {} })),
    import(`../../messages/${locale}/referral.json`).catch(() => ({ default: {} })),
    import(`../../messages/${locale}/partner.json`).catch(() => ({ default: {} })),
    import(`../../messages/${locale}/devices.json`).catch(() => ({ default: {} })),
  - Add 9 new entries to the return object (after line 111):
    Settings: settings.default,
    Analytics: analytics.default,
    Monitoring: monitoring.default,
    Subscriptions: subscriptions.default,
    Wallet: wallet.default,
    PaymentHistory: paymentHistory.default,
    Referral: referral.default,
    Partner: partner.default,
    Devices: devices.default,
  - Update the destructured array variable names accordingly
  - Check if message JSON files exist in messages/en-EN/. If any are missing, create them with at minimum { "title": "..." } for each namespace
  - DO NOT create files for all 41 locales — just ensure en-EN has the files

FH-5: Create SEO files (P1)
  - Create frontend/src/app/robots.ts:
    import { MetadataRoute } from 'next';
    export default function robots(): MetadataRoute.Robots {
      return {
        rules: { userAgent: '*', disallow: ['/api/', '/_next/'] },
        sitemap: 'https://cybervpn.com/sitemap.xml',
      };
    }
  - Create frontend/src/app/sitemap.ts:
    import { MetadataRoute } from 'next';
    export default function sitemap(): MetadataRoute.Sitemap {
      return [
        { url: 'https://cybervpn.com', lastModified: new Date() },
        { url: 'https://cybervpn.com/dashboard', lastModified: new Date() },
      ];
    }
  - For opengraph-image.tsx: SKIP unless trivial (it requires image generation which is complex)

FH-6: Add generateMetadata to layouts (P1)
  - File: frontend/src/app/[locale]/(dashboard)/layout.tsx
  - Add:
    import { getTranslations } from 'next-intl/server';
    export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }) {
      const { locale } = await params;
      const t = await getTranslations({ locale, namespace: 'Dashboard' });
      return { title: t('title') + ' | CyberVPN' };
    }
  - File: frontend/src/app/[locale]/(auth)/layout.tsx
  - Same pattern with Auth namespace

FH-7: Implement test stubs (P2)
  - File: frontend/src/app/[locale]/(dashboard)/subscriptions/components/__tests__/PurchaseConfirmModal.test.tsx
  - Replace TODO comments with actual tests:
    - Test: renders plan name and price
    - Test: calls createInvoice on confirm click
    - Test: shows loading state during creation
    - Test: displays error on failure
  - File: frontend/src/app/[locale]/(dashboard)/wallet/components/__tests__/WithdrawalModal.test.tsx
  - Replace TODO comments with actual tests:
    - Test: renders form fields (amount, method, address)
    - Test: validates minimum amount
    - Test: calls requestWithdrawal on submit
    - Test: shows success message

FH-8: Fix Analytics page TODOs (P2)
  - File: frontend/src/app/[locale]/(dashboard)/analytics/components/AnalyticsClient.tsx
  - Line 61: Replace hardcoded growth: 12.5 with calculated value from payment history trend
  - Lines 70-73: Replace hardcoded user counts with real data (or show "N/A" instead of 0)
  - Line 72: Same for growth calculation
  - If backend doesn't provide user analytics endpoint, show "Data unavailable" gracefully

DONE CRITERIA: npm run lint && npm run build pass. error.tsx exists in all route groups. Sentry configs exist. i18n request.ts has 26 namespaces. robots.ts and sitemap.ts exist.
```

### mobile-fix

```
You are mobile-fix on the CyberVPN team (Phase 4). You fix compilation errors, remove dead code, and add missing security configs.
Stack: Flutter, Riverpod 3.x, GoRouter 17, Clean Architecture, 27 locales.
You work ONLY in cybervpn_mobile/.

CONTEXT — What's already working:
- All new features (wallet, security, payment history, OTP, OAuth) implemented
- Google/Apple OAuth fully wired — buttons call real sign-in services
- Cancel subscription wired in profile_dashboard_screen
- Sentry performance tracing enabled (tracesSampleRate, autoPerformance, userInteraction)
- Referral/Partner backend-ready with graceful degradation
- OTP feature flag = true

CRITICAL ISSUES TO FIX:

KEY FILES TO READ FIRST:
- API constants: cybervpn_mobile/lib/core/constants/api_constants.dart (look for duplicates around lines 324-334 and 577-587)
- Login screen: cybervpn_mobile/lib/features/auth/presentation/screens/login_screen.dart (line 81: _showComingSoon dead code)
- API client: cybervpn_mobile/lib/core/network/api_client.dart (line 260: _sensitiveEndpoints unused)
- Cert pins: cybervpn_mobile/lib/core/security/cert_pins.dart (lines 48-58: empty fingerprints)
- E2E test: cybervpn_mobile/test/integration/e2e_auth_flow_test.dart (16 type errors)
- Register screen: cybervpn_mobile/lib/features/auth/presentation/screens/register_screen.dart (lines 917, 929: T&C/Privacy TODOs)

RULES:
- Use Context7 MCP to look up library docs before using any library.
- Do NOT downgrade any package version.
- flutter analyze must pass with zero errors after your changes.
- Follow existing code patterns.
- Add i18n strings to app_en.arb only (generators will auto-create others).

YOUR TASKS:

MF-1: Fix duplicate API constant definitions (P0 — COMPILATION ERROR)
  - File: cybervpn_mobile/lib/core/constants/api_constants.dart
  - ISSUE: `trialActivate` defined at BOTH line ~334 AND line ~577
  - ISSUE: `trialStatus` defined at BOTH line ~324 AND line ~587
  - FIX: Remove the LATER duplicate definitions (keep the earlier ones)
  - VERIFY: Search the entire file for any other duplicate static const definitions
  - Run: flutter analyze to confirm compilation error is fixed

MF-2: Fix e2e integration test type errors (P0 — TEST FAILURE)
  - File: cybervpn_mobile/test/integration/e2e_auth_flow_test.dart
  - ISSUE: 16 type errors — methods return wrong types vs Future<Result<T>> signatures
  - Read the file carefully. The test mock methods likely return raw values instead of Result<T> wrappers
  - FIX: Update mock method return types to match the actual repository interfaces
  - If Result<T> is used: wrap returns in Result.success() or Result.failure()
  - If test is too broken to fix quickly: add @Skip('Type errors — needs Result<T> refactor') annotation to the test class
  - VERIFY: flutter test test/integration/e2e_auth_flow_test.dart

MF-3: Remove dead code (P1)
  - File: cybervpn_mobile/lib/features/auth/presentation/screens/login_screen.dart
  - Remove _showComingSoon() method (line 81-90) — it's defined but never called
  - Verify: grep -r "_showComingSoon" cybervpn_mobile/lib/ returns zero matches after removal

  - File: cybervpn_mobile/lib/core/network/api_client.dart
  - Remove _sensitiveEndpoints field (line ~260) — flagged as unused by flutter analyze
  - Check if anything references it first — if truly unused, delete it

  - VERIFY: flutter analyze shows fewer warnings after cleanup

MF-4: Add placeholder certificate fingerprints (P1 — SECURITY PREP)
  - File: cybervpn_mobile/lib/core/security/cert_pins.dart
  - Lines 48, 54, 58: Currently empty strings ''
  - Add TODO-documented placeholder values:
    // TODO(security): Replace with actual certificate fingerprints before production release
    // Generate with: openssl s_client -connect api.cybervpn.com:443 | openssl x509 -pubkey -noout | openssl pkey -pubin -outform DER | openssl dgst -sha256 -binary | openssl enc -base64
    static const String primaryFingerprint = ''; // Set before release
    static const String backupFingerprint = '';  // Set before release
    static const String stagingFingerprint = ''; // Set before release
  - Ensure certificate pinning remains DISABLED in debug/development mode (check existing flag)
  - Do NOT invent fake fingerprints — keep empty but document the generation command

MF-5: Wire Terms & Privacy links + wallet withdraw dialog (P2)
  - File: cybervpn_mobile/lib/features/auth/presentation/screens/register_screen.dart
  - Line ~917: TODO: open T&C page / URL
  - Line ~929: TODO: open Privacy Policy page / URL
  - FIX: Use url_launcher to open:
    - T&C: 'https://cybervpn.com/terms' (or use a constant from api_constants)
    - Privacy: 'https://cybervpn.com/privacy'
  - If url_launcher is not in pubspec.yaml, add it
  - Pattern: launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication)

  - File: cybervpn_mobile/lib/features/wallet/presentation/screens/wallet_screen.dart
  - Line ~283: TODO: Implement withdraw dialog with amount input and method selection
  - FIX: Create a basic withdraw bottom sheet:
    - Amount text field with validation (min amount from backend or 1.0)
    - Submit button calling walletRepository.withdraw(amount)
    - Loading/success/error states
    - Follow pattern from cancel_subscription_sheet.dart

DONE CRITERIA: flutter analyze shows zero errors. flutter test passes (or skipped tests documented). Zero _showComingSoon in lib/. Duplicate constants removed.
```

### infra-dash

```
You are infra-dash on the CyberVPN team (Phase 4). You add Loki/Tempo Grafana dashboards, healthchecks, log-based alerts, and SLO tracking.
You work ONLY in infra/ directory.

CONTEXT — What exists:
- 11 monitoring services running in docker-compose (monitoring profile)
- 8 Grafana dashboards — ALL use Prometheus datasource only
- 3 datasources configured: Prometheus (default), Loki, Tempo — with cross-linking
- 69 alert rules across 5 files (api, db, redis, infra, worker)
- Loki ruler configured pointing to AlertManager BUT no rule files exist
- Prometheus and Grafana have NO healthchecks in docker-compose
- Tempo metrics generator produces span-metrics and service-graphs

KEY FILES:
- Docker Compose: infra/docker-compose.yml
- Grafana dashboards: infra/grafana/dashboards/*.json (8 files)
- Prometheus config: infra/prometheus/prometheus.yml
- Alert rules: infra/prometheus/rules/ (5 yml files)
- Loki config: infra/loki/loki-config.yml (ruler section configured)
- Tempo config: infra/tempo/tempo-config.yml (metrics_generator section)
- Datasources: infra/grafana/provisioning/datasources/datasources.yml

RULES:
- All new services under profiles: ["monitoring"]
- Follow existing docker-compose patterns
- Grafana dashboards must be JSON files in infra/grafana/dashboards/
- Use specific image versions (no :latest)
- Healthchecks required on all services
- Port binding: 127.0.0.1 only

YOUR TASKS:

ID-1: Add Prometheus + Grafana healthchecks (P0)
  - File: infra/docker-compose.yml
  - Add healthcheck to prometheus service:
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:9090/-/healthy"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s
  - Add healthcheck to grafana service:
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

ID-2: Create Logs Overview dashboard with Loki (P0)
  - Create infra/grafana/dashboards/logs-dashboard.json
  - Datasource: Loki
  - Panels:
    1. Log Volume by Level — stacked bar chart: sum by(level) (rate({compose_project="remnawave-local"} |= `` [$__interval]))
    2. Error Logs Stream — logs panel: {compose_project="remnawave-local"} |= "ERROR" or level="error"
    3. Warning Logs Stream — logs panel: {compose_project="remnawave-local"} | level="warning"
    4. Request Logs Table — table panel: {compose_service="cybervpn-backend"} | json | line_format "{{.method}} {{.path}} {{.status_code}} {{.duration}}ms"
    5. Log Search — text input variable for ad-hoc log search
    6. Service Selector — dropdown variable: label_values(compose_service)
  - Use template variables: $service (compose_service), $level (level), $search (text)
  - Dashboard UID: "logs-overview"
  - Dark theme compatible

ID-3: Create Traces Overview dashboard with Tempo (P0)
  - Create infra/grafana/dashboards/traces-dashboard.json
  - Datasource: Tempo
  - Panels:
    1. Service Graph — node graph panel using Tempo service map (from metrics generator)
       Query: Use Prometheus datasource with traces_service_graph_request_total metric
    2. Trace Duration P50/P95/P99 — timeseries using span metrics:
       histogram_quantile(0.95, sum by(le) (rate(traces_spanmetrics_latency_bucket{service_name="cybervpn-backend"}[$__rate_interval])))
    3. Request Rate by Service — timeseries:
       sum by(service_name) (rate(traces_spanmetrics_calls_total[$__rate_interval]))
    4. Error Rate by Service — timeseries:
       sum by(service_name) (rate(traces_spanmetrics_calls_total{status_code="STATUS_CODE_ERROR"}[$__rate_interval]))
    5. Top 10 Slowest Endpoints — table:
       topk(10, sum by(span_name) (rate(traces_spanmetrics_latency_sum[$__rate_interval])) / sum by(span_name) (rate(traces_spanmetrics_latency_count[$__rate_interval])))
    6. Trace Search Panel — Tempo TraceQL search (datasource: Tempo)
  - Template variables: $service (service_name), $interval
  - Dashboard UID: "traces-overview"
  - NOTE: Check actual metric names by reading tempo-config.yml metrics_generator section

ID-4: Create SLO/SLI dashboard (P1)
  - Create infra/grafana/dashboards/slo-dashboard.json
  - Datasource: Prometheus
  - Panels:
    1. API Availability SLO (target: 99.9%) — gauge:
       (1 - (sum(rate(http_requests_total{status=~"5.."}[$__range])) / sum(rate(http_requests_total[$__range])))) * 100
    2. API Latency SLO (target: P95 < 500ms) — gauge:
       histogram_quantile(0.95, sum by(le) (rate(http_request_duration_seconds_bucket[$__range])))
    3. Error Budget Remaining — gauge:
       Calculate: (SLO target - actual error rate) / SLO target * 100
       Example: ((0.001 - error_rate) / 0.001) * 100 where error_rate = sum(rate(5xx)) / sum(rate(total))
    4. Error Budget Burn Rate — timeseries (1h, 6h, 24h windows):
       Shows how fast error budget is being consumed
    5. SLI Trends — timeseries showing availability and latency over time
    6. Apdex Score — stat panel:
       (sum(rate(http_request_duration_seconds_bucket{le="0.5"}[$__range])) + sum(rate(http_request_duration_seconds_bucket{le="2.0"}[$__range]))) / (2 * sum(rate(http_request_duration_seconds_count[$__range])))
  - Dashboard UID: "slo-tracking"

ID-5: Create Loki log-based alert rules (P1)
  - Create directory: infra/loki/rules/cybervpn/
  - Create infra/loki/rules/cybervpn/alerts.yml:
    groups:
      - name: log-alerts
        rules:
          - alert: HighErrorLogRate
            expr: sum(rate({compose_project="remnawave-local"} |= "ERROR" [5m])) > 10
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "High error log rate detected"
              description: "More than 10 error logs per second over 5 minutes"

          - alert: AuthFailureSpike
            expr: sum(rate({compose_service="cybervpn-backend"} |= "Authentication failed" [5m])) > 5
            for: 3m
            labels:
              severity: critical
            annotations:
              summary: "Authentication failure spike"
              description: "Possible brute force attack — >5 auth failures/sec"

          - alert: DatabaseConnectionErrors
            expr: sum(rate({compose_service="cybervpn-backend"} |= "database connection" |= "error" [5m])) > 0
            for: 2m
            labels:
              severity: critical
            annotations:
              summary: "Database connection errors in logs"

          - alert: ExternalAPITimeouts
            expr: sum(rate({compose_service="cybervpn-backend"} |= "timeout" |= "remnawave" [10m])) > 3
            for: 5m
            labels:
              severity: warning
            annotations:
              summary: "External API (Remnawave) timeouts detected"

  - Mount the rules directory in docker-compose loki service:
    volumes:
      - ./loki/rules:/loki/rules
  - Verify loki-config.yml ruler.rule_path matches: /loki/rules

ID-6: Verify monitoring stack integration (P2)
  - Create infra/tests/verify_monitoring.sh:
    #!/bin/bash
    set -e
    echo "=== Monitoring Stack Verification ==="

    # Prometheus targets
    echo "Checking Prometheus targets..."
    TARGETS=$(curl -sf http://localhost:9094/api/v1/targets | python3 -c "import sys,json; print(len([t for t in json.load(sys.stdin)['data']['activeTargets'] if t['health']=='up']))")
    echo "  Active targets: $TARGETS (expected: 10+)"

    # Grafana dashboards
    echo "Checking Grafana dashboards..."
    DASHBOARDS=$(curl -sf -u admin:grafana_local_password http://localhost:3002/api/search?type=dash-db | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
    echo "  Dashboards: $DASHBOARDS (expected: 11+)"

    # Loki
    echo "Checking Loki..."
    curl -sf http://localhost:3100/ready && echo "  Loki: ready" || echo "  Loki: NOT ready"

    # Tempo
    echo "Checking Tempo..."
    curl -sf http://localhost:3200/ready && echo "  Tempo: ready" || echo "  Tempo: NOT ready"

    # OTEL Collector
    echo "Checking OTEL Collector..."
    curl -sf http://localhost:13133/ && echo "  OTEL: ready" || echo "  OTEL: NOT ready"

    # AlertManager
    echo "Checking AlertManager..."
    curl -sf http://localhost:9093/api/v2/status > /dev/null && echo "  AlertManager: ready" || echo "  AlertManager: NOT ready"

    echo "=== Verification Complete ==="
  - chmod +x the script

DONE CRITERIA: 11+ Grafana dashboards (8 existing + logs + traces + SLO). Prometheus and Grafana have healthchecks. Loki rules directory mounted. verify_monitoring.sh runs successfully.
```

### test-eng

```
You are test-eng on the CyberVPN team (Phase 4). You verify that metrics are actually working and write smoke tests.
You work across: backend/tests/, frontend/src/**/__tests__/, infra/tests/.

CONTEXT — What already exists:
- Backend: 82 test files (integration + unit + e2e)
- Frontend: 11 API client test files + component tests
- Mobile: 32 screen tests
- Phase 4 changes: metrics wiring, error boundaries, Sentry configs, dashboards

YOUR TASKS:

TE-1: Backend metrics smoke test (P1, after BM-1 + BM-2)
  - Create backend/tests/integration/test_metrics_wired.py
  - Test that after calling key endpoints, Prometheus metrics are incremented:
    1. POST /auth/login → check auth_attempts_total counter increased
    2. POST /auth/register → check registrations_total counter increased
    3. POST /trial/activate → check trials_activated_total counter increased
  - Use httpx AsyncClient + ASGI transport (same pattern as existing tests)
  - Import prometheus_client and check REGISTRY for metric values
  - Pattern:
    from prometheus_client import REGISTRY
    before = REGISTRY.get_sample_value('auth_attempts_total', {'method': 'password', 'result': 'success'}) or 0
    # ... make API call ...
    after = REGISTRY.get_sample_value('auth_attempts_total', {'method': 'password', 'result': 'success'}) or 0
    assert after > before

TE-2: Frontend error boundary smoke test (P1, after FH-2)
  - Create frontend/src/shared/ui/__tests__/route-error-boundary.test.tsx
  - Test: renders error message when error prop provided
  - Test: "Try Again" button calls reset function
  - Test: Sentry.captureException is called with the error
  - Mock @sentry/nextjs with vi.mock()
  - Use React Testing Library

TE-3: Frontend Sentry config validation (P1, after FH-1)
  - Create frontend/__tests__/sentry-config.test.ts
  - Test: sentry.client.config.ts imports and calls Sentry.init
  - Test: verify DSN is read from environment variable
  - Test: tracesSampleRate is set based on NODE_ENV
  - Simple import-based tests (not integration)

TE-4: Infrastructure dashboard validation (P2, after ID-2 + ID-3 + ID-4)
  - Create infra/tests/validate_dashboards.sh:
    #!/bin/bash
    set -e
    echo "Validating Grafana dashboard JSON files..."
    EXPECTED_DASHBOARDS=11
    COUNT=$(ls -1 /home/beep/projects/VPNBussiness/infra/grafana/dashboards/*.json | wc -l)
    echo "  Dashboard files: $COUNT (expected: $EXPECTED_DASHBOARDS)"
    [ "$COUNT" -ge "$EXPECTED_DASHBOARDS" ] || { echo "FAIL: Not enough dashboards"; exit 1; }

    # Validate JSON syntax
    for f in /home/beep/projects/VPNBussiness/infra/grafana/dashboards/*.json; do
      python3 -m json.tool "$f" > /dev/null 2>&1 || { echo "FAIL: Invalid JSON in $f"; exit 1; }
      echo "  ✓ $(basename $f)"
    done

    # Check for Loki datasource usage
    grep -l "loki" /home/beep/projects/VPNBussiness/infra/grafana/dashboards/*.json > /dev/null 2>&1 || { echo "FAIL: No dashboard uses Loki datasource"; exit 1; }
    echo "  ✓ Loki datasource used in at least one dashboard"

    # Check for Tempo datasource usage
    grep -l "tempo" /home/beep/projects/VPNBussiness/infra/grafana/dashboards/*.json > /dev/null 2>&1 || { echo "FAIL: No dashboard uses Tempo datasource"; exit 1; }
    echo "  ✓ Tempo datasource used in at least one dashboard"

    echo "=== All dashboard validations passed ==="
  - chmod +x the script

DONE CRITERIA: All test files created and runnable. pytest and vitest pass. Validation scripts return 0.
```

---

## Task Registry & Dependencies

### Dependency Graph

```
                    ┌── BM-1 (auth metrics) ─────────────────────────┐
                    │                                                 │
                    ├── BM-2 (payment/sub/trial metrics) ────────────┤───→ TE-1
                    │                                                 │
PHASE 4 START ──────┤── BM-3 (cache metrics) ── independent          │
                    │                                                 │
                    ├── BM-4 (rate limiting) ── independent           │
                    │                                                 │
                    ├── BM-5 (integration tests) ── independent       │
                    │                                                 │
                    ├── FH-1 (Sentry configs) ─────→ TE-3            │
                    │                                                 │
                    ├── FH-2 (error.tsx) ──────────→ TE-2            │
                    │                                                 │
                    ├── FH-3 (not-found.tsx) ── independent           │
                    │                                                 │
                    ├── FH-4 (i18n namespaces) ── independent         │
                    │                                                 │
                    ├── FH-5 (SEO files) ── independent               │
                    │                                                 │
                    ├── FH-6 (generateMetadata) ── independent        │
                    │                                                 │
                    ├── FH-7 (test stubs) ── independent              │
                    │                                                 │
                    ├── FH-8 (analytics TODOs) ── independent         │
                    │                                                 │
                    ├── MF-1 (duplicate constants) ── independent     │
                    │                                                 │
                    ├── MF-2 (e2e test types) ── independent          │
                    │                                                 │
                    ├── MF-3 (dead code) ── independent               │
                    │                                                 │
                    ├── MF-4 (cert pins) ── independent               │
                    │                                                 │
                    ├── MF-5 (T&C + withdraw) ── independent          │
                    │                                                 │
                    ├── ID-1 (healthchecks) ── independent             │
                    │                                                 │
                    ├── ID-2 (Logs dashboard) ──────→ TE-4           │
                    │                                                 │
                    ├── ID-3 (Traces dashboard) ────→ TE-4           │
                    │                                                 │
                    ├── ID-4 (SLO dashboard) ───────→ TE-4           │
                    │                                                 │
                    ├── ID-5 (Loki alert rules) ── independent        │
                    │                                                 │
                    └── ID-6 (verify script) ── after ID-1..5         │
```

### Full Task Table

| ID | Task | Agent | Depends on | Priority |
|----|------|-------|------------|----------|
| BM-1 | Wire auth metrics into routes | backend-metrics | — | P0 |
| BM-2 | Wire payment/subscription/trial metrics | backend-metrics | — | P0 |
| BM-3 | Wire cache metrics via decorator | backend-metrics | — | P1 |
| BM-4 | Add rate limiting to new endpoints | backend-metrics | — | P1 |
| BM-5 | Add missing integration tests | backend-metrics | — | P2 |
| FH-1 | Create Sentry config files | frontend-hard | — | P0 |
| FH-2 | Create error.tsx for all route groups | frontend-hard | — | P0 |
| FH-3 | Create not-found.tsx files | frontend-hard | — | P0 |
| FH-4 | Register missing i18n namespaces | frontend-hard | — | P0 |
| FH-5 | Create SEO files (robots.ts, sitemap.ts) | frontend-hard | — | P1 |
| FH-6 | Add generateMetadata to layouts | frontend-hard | — | P1 |
| FH-7 | Implement test stubs | frontend-hard | — | P2 |
| FH-8 | Fix Analytics page TODOs | frontend-hard | — | P2 |
| MF-1 | Fix duplicate API constant definitions | mobile-fix | — | P0 |
| MF-2 | Fix e2e integration test type errors | mobile-fix | — | P0 |
| MF-3 | Remove dead code | mobile-fix | — | P1 |
| MF-4 | Add placeholder certificate fingerprints | mobile-fix | — | P1 |
| MF-5 | Wire T&C links + wallet withdraw dialog | mobile-fix | — | P2 |
| ID-1 | Add Prometheus + Grafana healthchecks | infra-dash | — | P0 |
| ID-2 | Create Logs Overview dashboard (Loki) | infra-dash | — | P0 |
| ID-3 | Create Traces Overview dashboard (Tempo) | infra-dash | — | P0 |
| ID-4 | Create SLO/SLI dashboard | infra-dash | — | P1 |
| ID-5 | Create Loki log-based alert rules | infra-dash | — | P1 |
| ID-6 | Create monitoring verification script | infra-dash | ID-1..5 | P2 |
| TE-1 | Backend metrics smoke test | test-eng | BM-1, BM-2 | P1 |
| TE-2 | Frontend error boundary test | test-eng | FH-2 | P1 |
| TE-3 | Frontend Sentry config test | test-eng | FH-1 | P1 |
| TE-4 | Infrastructure dashboard validation | test-eng | ID-2, ID-3, ID-4 | P2 |

### Task Counts

| Agent | Tasks | IDs |
|-------|-------|-----|
| backend-metrics | 5 | BM-1..5 |
| frontend-hard | 8 | FH-1..8 |
| mobile-fix | 5 | MF-1..5 |
| infra-dash | 6 | ID-1..6 |
| test-eng | 4 | TE-1..4 |
| **TOTAL** | **28** | |

---

## Lead Coordination Rules

1. **Spawn all 5 agents immediately.** Initial assignments:
   - `backend-metrics` → BM-1 + BM-2 in parallel (P0 — wire metrics into routes)
   - `frontend-hard` → FH-1 + FH-2 + FH-3 + FH-4 in parallel (P0 — all independent, bulk file creation)
   - `mobile-fix` → MF-1 + MF-2 in parallel (P0 — fix compilation errors first)
   - `infra-dash` → ID-1 + ID-2 + ID-3 in parallel (P0 — healthchecks + dashboards)
   - `test-eng` → Wait for BM-1+2 or FH-1+2, then start TE-1 or TE-2

2. **Communication protocol:**
   - backend-metrics finishes BM-1+2 → messages test-eng ("metrics wired, verify with TE-1")
   - frontend-hard finishes FH-1 → messages test-eng ("Sentry configs created, verify with TE-3")
   - frontend-hard finishes FH-2 → messages test-eng ("error boundaries done, verify with TE-2")
   - infra-dash finishes ID-2+3+4 → messages test-eng ("dashboards created, verify with TE-4")

3. **Parallel execution strategy:**
   - Wave 1 (immediate): BM-1+2, FH-1+2+3+4, MF-1+2, ID-1+2+3
   - Wave 2 (after wave 1): BM-3+4, FH-5+6, MF-3+4, ID-4+5, TE-1+2+3
   - Wave 3 (final): BM-5, FH-7+8, MF-5, ID-6, TE-4

4. **File conflict prevention:**
   - backend-metrics owns `backend/` exclusively
   - frontend-hard owns `frontend/` exclusively
   - mobile-fix owns `cybervpn_mobile/` exclusively
   - infra-dash owns `infra/` exclusively
   - test-eng writes ONLY in `*/tests/`, `*/__tests__/`, `*/test/` directories
   - Nobody modifies another agent's files

5. **Do NOT start implementing if you are lead — delegate.** Use delegate mode exclusively.

6. **Progress tracking.** Use the shared TaskList (TaskCreate/TaskUpdate). Do NOT use beads (`bd`) — SQLite lock conflicts with parallel agents.

7. **If any agent is blocked >5 minutes:** reassign them to an independent task.

---

## Prohibitions

- Do NOT downgrade library versions (Next.js 16, React 19, Flutter Riverpod 3.x, Prometheus 3.x, Grafana 11.x)
- Do NOT break existing working endpoints, pages, or dashboards
- Do NOT modify generated/types.ts manually
- Do NOT create files outside your assigned directory
- Do NOT use beads (`bd create/close`) — use TaskList instead
- Do NOT skip Context7 MCP doc lookup when using a library
- Do NOT touch Telegram bot code (services/telegram-bot/) — OUT OF SCOPE
- Do NOT use :latest Docker image tags — pin specific versions
- Do NOT expose ports on 0.0.0.0 — always bind to 127.0.0.1
- Do NOT hardcode secrets — use environment variables
- Do NOT invent fake certificate fingerprints — leave empty with documentation

---

## Final Verification (Lead runs after ALL tasks complete)

```bash
# ===== Backend =====
cd backend && python -m pytest tests/ -v --tb=short
# Verify metrics are ACTUALLY being used in routes
grep -r "from src.infrastructure.monitoring.instrumentation" backend/src/presentation/api/ --include="*.py" | wc -l
# Must be >= 5 (auth, payments, subscriptions, trial routes)
# Verify metrics increment after API call
curl -s http://localhost:9091/metrics | grep "auth_attempts_total"
# Must show non-zero values if any logins have occurred

# ===== Frontend =====
cd frontend && npm run lint
cd frontend && npm run build
# Verify error.tsx exists in route groups
find frontend/src/app -name "error.tsx" | wc -l
# Must be >= 4 (root, dashboard, miniapp, auth)
# Verify not-found.tsx exists
find frontend/src/app -name "not-found.tsx" | wc -l
# Must be >= 4
# Verify Sentry configs exist
ls frontend/sentry.*.config.ts | wc -l
# Must be 3
# Verify i18n namespaces
grep -c "default:" frontend/src/i18n/request.ts
# Must be >= 26 (17 existing + 9 new)
# Verify SEO files
ls frontend/src/app/robots.ts frontend/src/app/sitemap.ts
# Must exist

# ===== Mobile =====
cd cybervpn_mobile && flutter analyze
# Must show 0 errors (warnings OK)
# Verify no duplicate constants
grep -c "trialActivate" cybervpn_mobile/lib/core/constants/api_constants.dart
# Must be exactly 1
grep -c "trialStatus" cybervpn_mobile/lib/core/constants/api_constants.dart
# Must be exactly 1
# Verify no _showComingSoon calls
grep -r "_showComingSoon" cybervpn_mobile/lib/ --include="*.dart" | grep -v "//.*_showComingSoon" | wc -l
# Must be 0 (method definition removed)

# ===== Infrastructure =====
cd infra && docker compose --profile monitoring config --quiet
# Verify healthchecks on prometheus and grafana
grep -A4 "healthcheck:" infra/docker-compose.yml | grep -c "prometheus\|grafana"
# Verify dashboard count
ls infra/grafana/dashboards/*.json | wc -l
# Must be >= 11 (8 existing + logs + traces + SLO)
# Verify Loki rules exist
ls infra/loki/rules/cybervpn/alerts.yml
# Must exist
# Verify Loki datasource in at least one dashboard
grep -l "loki" infra/grafana/dashboards/*.json | wc -l
# Must be >= 1
# Verify Tempo datasource in at least one dashboard
grep -l "tempo" infra/grafana/dashboards/*.json | wc -l
# Must be >= 1
```

All commands must pass with zero errors. If any fail, assign fix to the responsible agent.

---

## Completion Checklist

### Backend — Metrics Wiring
- [ ] auth_attempts_total incremented in login/register routes
- [ ] registrations_total incremented in register route
- [ ] payments_total incremented in payment routes
- [ ] subscriptions_activated_total incremented in subscription routes
- [ ] trials_activated_total incremented in trial route
- [ ] cache_operations_total tracked on cache get/set/delete
- [ ] Rate limiting on /security/antiphishing, /trial/activate, /subscriptions/cancel
- [ ] Integration tests for security, subscriptions endpoints

### Frontend — Error Handling & Config
- [ ] sentry.client.config.ts created and configured
- [ ] sentry.server.config.ts created and configured
- [ ] sentry.edge.config.ts created and configured
- [ ] error.tsx in dashboard, miniapp, auth, root route groups
- [ ] not-found.tsx in dashboard, miniapp, auth, root
- [ ] RouteErrorBoundary component with Sentry capture
- [ ] RouteNotFound component with cyberpunk 404 page

### Frontend — i18n & SEO
- [ ] 9 namespaces added to i18n/request.ts imports
- [ ] 9 namespaces added to i18n/request.ts return object
- [ ] Message JSON files exist for all namespaces in en-EN
- [ ] robots.ts created
- [ ] sitemap.ts created
- [ ] generateMetadata in dashboard layout
- [ ] generateMetadata in auth layout

### Frontend — Tests
- [ ] PurchaseConfirmModal tests implemented (not just TODOs)
- [ ] WithdrawalModal tests implemented (not just TODOs)
- [ ] Analytics page TODOs resolved or gracefully handled

### Mobile — Bug Fixes
- [ ] Duplicate trialActivate removed (only 1 definition)
- [ ] Duplicate trialStatus removed (only 1 definition)
- [ ] e2e_auth_flow_test.dart compiles (types fixed or test skipped)
- [ ] _showComingSoon() method removed from login_screen.dart
- [ ] _sensitiveEndpoints removed from api_client.dart
- [ ] cert_pins.dart documented with generation command
- [ ] Terms & Privacy links open URLs
- [ ] Wallet withdraw dialog implemented

### Infrastructure — Observability
- [ ] Prometheus healthcheck in docker-compose
- [ ] Grafana healthcheck in docker-compose
- [ ] Logs Overview dashboard (Loki datasource)
- [ ] Traces Overview dashboard (Tempo datasource)
- [ ] SLO/SLI dashboard with error budget
- [ ] Loki log-based alert rules (4+ rules)
- [ ] Monitoring verification script

### Build Verification
- [ ] `npm run build` passes (frontend)
- [ ] `flutter analyze` — zero errors (mobile)
- [ ] `pytest` passes (backend)
- [ ] `docker compose --profile monitoring config` validates (infra)
