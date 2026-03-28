# CyberVPN Phase 3 — Gap Closure + Full Observability — Agent Team Prompt

> Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.
> User presses **Shift+Tab** to enter delegate mode, then pastes this prompt.
> Teammates load `CLAUDE.md` automatically. Spawn prompts contain ONLY task-specific context.
> **Scope**: Close ALL remaining feature gaps + achieve 100% observability (Sentry, Prometheus, Grafana, Loki, OpenTelemetry).
> **Out of scope**: Telegram Bot (services/telegram-bot/).

---

## Goal

1. Close every remaining feature stub/placeholder across Frontend, Mobile, and Telegram Mini App
2. Achieve **100% observability coverage**: every service instrumented with Sentry, Prometheus metrics, structured logging, distributed tracing
3. Build production-ready Grafana dashboards and alert rules for the entire stack

**Done criteria:**
1. Zero `alert('...')` stubs in frontend `(dashboard)/` directory
2. Zero placeholder/mock data in API clients
3. All Mini App pages use real API data
4. Mobile referral/partner features show real data (not "Coming Soon")
5. Backend: `sentry-sdk` initialized, `prometheus-fastapi-instrumentator` active, structured JSON logs via structlog
6. Infrastructure: Loki running, 4 Prometheus exporters active, OTEL Collector deployed
7. Grafana: 8+ dashboards provisioned (API, DB, Redis, Infra, Worker, Application, Errors, Logs)
8. Alerts: API/DB/Redis/Infra alert rules firing to real webhook
9. `npm run build` (frontend), `flutter analyze` (mobile), `pytest` (backend) all pass

---

## Observability Audit Summary (Current State)

### What EXISTS

| Component | Version | Status | Notes |
|-----------|---------|--------|-------|
| **Prometheus** | v3.2.1 | Running | 4 scrape jobs (backend:9091, remnawave:3001, worker:9091, bot:9092) |
| **Grafana** | v11.5.2 | Running | Port 3002, 3 dashboards (worker, OTP, errors) |
| **AlertManager** | v0.28.1 | Running | 7 worker alert rules, webhook = placeholder URL |
| **Backend /metrics** | prometheus-client 0.20 | Running | Separate app on port 3001/9091, but only 1 custom metric |
| **Worker metrics** | prometheus-client 0.21 | Running | TaskIQ metrics exposed on 9091 |
| **Bot metrics** | prometheus-client 0.24 | Running | Exposed on 9092 |
| **Sentry Frontend** | @sentry/nextjs 10.38.0 | Configured | Error boundary + captureException + instrumentation.ts |
| **Sentry Mobile** | sentry_flutter 9.0.0 | Configured | PII sanitization, global error handler |
| **structlog** | >=24.0.0 | Imported | In pyproject.toml but NOT actively producing JSON output |
| **X-Request-ID** | Custom middleware | Working | Correlation header, not true tracing |
| **Health checks** | /health + /health/detailed | Working | DB, Redis, Remnawave checks |
| **Docker healthchecks** | All services | Working | pg_isready, valkey-cli ping, curl /health |

### What's MISSING

| Gap | Impact | Priority |
|-----|--------|----------|
| **Backend Sentry SDK** | Unhandled exceptions NOT captured from backend/worker/bot | P0 |
| **FastAPI instrumentation** | No request latency/throughput metrics (only 1 metric: `websocket_auth_method_total`) | P0 |
| **Custom app metrics** | No DB query time, cache hit/miss, task duration, external API latency | P1 |
| **Structured JSON logging** | structlog imported but logs remain unstructured Python logging | P1 |
| **OpenTelemetry tracing** | No distributed traces across backend→worker→Remnawave | P1 |
| **Loki log aggregation** | Logs only in Docker json-file driver, no centralized search | P1 |
| **postgres_exporter** | No PostgreSQL metrics (connections, query time, table bloat) | P1 |
| **redis_exporter** | No Redis metrics (memory, commands/sec, eviction) | P1 |
| **node_exporter** | No host system metrics (CPU, memory, disk, network) | P2 |
| **cAdvisor** | No container resource metrics (CPU/mem per container) | P2 |
| **API alert rules** | Only worker alerts exist — no API latency/error/5xx alerts | P1 |
| **DB/Redis alert rules** | No database or cache threshold alerts | P1 |
| **AlertManager webhook** | Placeholder URL — alerts go nowhere | P1 |
| **Grafana API dashboard** | Missing — no FastAPI request visualization | P0 |
| **Grafana DB dashboard** | Missing — no PostgreSQL monitoring | P1 |
| **Grafana Redis dashboard** | Missing — no cache monitoring | P1 |
| **Grafana Infra dashboard** | Missing — no host/container resources | P2 |
| **Frontend Web Vitals** | No LCP/FID/CLS/TTFB tracking | P2 |
| **Mobile perf tracing** | Sentry crash only, no transaction/span tracing | P2 |

---

## Remaining Feature Gaps

### Frontend Gaps

| ID | Gap | File | Line(s) | Current Code |
|----|-----|------|---------|--------------|
| FG-1 | Purchase flow | `frontend/src/app/[locale]/(dashboard)/subscriptions/components/SubscriptionsClient.tsx` | 24-28 | `alert(\`Purchase plan: ${planUuid}...\`)` |
| FG-2 | Wallet withdrawal | `frontend/src/app/[locale]/(dashboard)/wallet/components/WalletClient.tsx` | 46-52 | `alert('Withdrawal flow - to be implemented')` |
| FG-3 | VPN Usage mock | `frontend/src/lib/api/vpn.ts` + `usage.ts` | 19-20 | Returns placeholder mock data |
| FG-4 | Analytics page | `frontend/src/app/[locale]/(dashboard)/analytics/page.tsx` | 1-10 | `<PlaceholderPage />` |
| FG-5 | Monitoring page | `frontend/src/app/[locale]/(dashboard)/monitoring/page.tsx` | 1-10 | `<PlaceholderPage />` |

### Mini App Gaps

| ID | Gap | File | Line(s) | Current Code |
|----|-----|------|---------|--------------|
| MG-1 | Subscription check | `frontend/src/app/[locale]/(miniapp)/home/page.tsx` | 52 | `const hasActiveSubscription = false;` |
| MG-2 | Plans pricing | `frontend/src/app/[locale]/(miniapp)/plans/page.tsx` | 341-360 | `{t('contactForPrice')}` instead of real prices |
| MG-3 | Devices page | N/A | N/A | No miniapp devices management page exists |

### Mobile Gaps

| ID | Gap | File | Current State |
|----|-----|------|---------------|
| MB-1 | Referral "Coming Soon" | `referral/data/datasources/referral_remote_ds.dart:55` | `checkAvailability()` → GET `/referral/status` → fails → shows Coming Soon. Backend HAS this endpoint — investigate WHY it fails |
| MB-2 | Partner "Coming Soon" | `partner/data/datasources/partner_remote_ds.dart` | Same pattern as referral — availability check fails |
| MB-3 | Cancel not wired | `subscription/presentation/widgets/cancel_subscription_sheet.dart` | Widget fully built but NO screen displays it — no "Cancel" button anywhere in active subscription UI |
| MB-4 | Google/Apple OAuth | `auth/presentation/screens/login_screen.dart:332-346` | Buttons call `_showComingSoon()` instead of actual sign-in services |
| MB-5 | No perf tracing | `main.dart` | Sentry crash reporting works, but NO transaction/span tracing enabled |

---

## Team

| Role | Agent name | Model | Working directory | subagent_type | Tasks |
|------|-----------|-------|-------------------|---------------|-------|
| Lead (you) | — | opus | all (coordination only) | — | 0 |
| Backend Observability | `backend-obs` | sonnet | `backend/`, `services/` | backend-dev | 7 |
| Frontend + Mini App | `frontend-dev` | sonnet | `frontend/` | general-purpose | 11 |
| Mobile | `mobile-dev` | sonnet | `cybervpn_mobile/` | general-purpose | 6 |
| Infrastructure Obs | `infra-obs` | sonnet | `infra/` | devops-engineer | 8 |
| Test Engineer | `test-eng` | sonnet | `*/tests/`, `*/__tests__/` | test-runner | 6 |

---

## Spawn Prompts

### backend-obs

```
You are backend-obs on the CyberVPN team (Phase 3). You add full observability to the backend.
Stack: FastAPI, Python 3.13, SQLAlchemy 2, Redis, prometheus-client, structlog.
You work ONLY in backend/ and services/.

CONTEXT — What already exists:
- prometheus-client>=0.20.0 in pyproject.toml ✅
- structlog>=24.0.0 in pyproject.toml ✅ (imported but NOT producing JSON output)
- Separate metrics app on port 3001/9091 with /metrics endpoint ✅
- Only 1 custom metric: websocket_auth_method_total (Counter) in src/infrastructure/monitoring/metrics.py
- Health checks: GET /health (minimal) + GET /health/detailed (authenticated, checks DB+Redis+Remnawave) ✅
- X-Request-ID middleware for correlation ✅
- Logging middleware: logs method, URL, status, duration in src/presentation/middleware/logging.py ✅
- 85+ endpoints fully implemented across auth, OAuth, 2FA, wallet, payments, subscriptions, etc.
- No Sentry SDK anywhere in backend or services

KEY FILES:
- Main app: backend/src/main.py (lifespan, exception handlers, metrics app on :3001)
- Metrics: backend/src/infrastructure/monitoring/metrics.py (only 1 metric defined)
- Logging middleware: backend/src/presentation/middleware/logging.py
- Request ID: backend/src/presentation/middleware/request_id.py
- Exception handlers: backend/src/presentation/exception_handlers.py
- pyproject.toml: backend/pyproject.toml
- Worker broker: services/task-worker/src/broker.py
- Worker pyproject: services/task-worker/pyproject.toml
- Prometheus config (READ ONLY): infra/prometheus/prometheus.yml

RULES:
- Use Context7 MCP to look up library docs before using any library.
- Do NOT downgrade any existing package version.
- Do NOT break existing working endpoints or the /metrics endpoint.
- Do NOT modify infra/ files — infra-obs owns those.
- Every new package must be added to pyproject.toml dependencies.
- Backend is already scrapped by Prometheus at cybervpn-backend:9091/metrics.

YOUR TASKS:

BOB-1: Sentry SDK integration (P0)
  - Add sentry-sdk[fastapi]>=2.0.0 to backend/pyproject.toml
  - Initialize in main.py lifespan startup:
    import sentry_sdk
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,  # Add SENTRY_DSN to Settings
        traces_sample_rate=0.2,
        profiles_sample_rate=0.1,
        environment=settings.ENVIRONMENT,
        release=settings.VERSION,
        integrations=[FastApiIntegration()],
        send_default_pii=False,
    )
  - Add SENTRY_DSN: str = "" to src/config/settings.py (optional, empty = disabled)
  - Add sentry_sdk to exception_handlers.py: capture unhandled exceptions with sentry_sdk.capture_exception()
  - ALSO add sentry-sdk to services/task-worker/pyproject.toml and initialize in broker.py startup
  - File: main.py, config/settings.py, exception_handlers.py, pyproject.toml, services/task-worker/

BOB-2: FastAPI Prometheus instrumentation (P0)
  - Add prometheus-fastapi-instrumentator>=7.0.0 to pyproject.toml
  - Initialize in main.py after app creation:
    from prometheus_fastapi_instrumentator import Instrumentator
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        excluded_handlers=["/health", "/metrics", "/docs", "/openapi.json"],
        env_var_name="ENABLE_METRICS",
    )
    instrumentator.instrument(app)
    # Expose on the separate metrics app (port 3001), NOT main app
    instrumentator.expose(metrics_app, endpoint="/metrics", include_in_schema=False)
  - This auto-creates: http_requests_total, http_request_duration_seconds, http_requests_in_progress
  - Verify: GET :9091/metrics now shows FastAPI request metrics
  - File: main.py, pyproject.toml

BOB-3: Custom application metrics (P1)
  - Add to src/infrastructure/monitoring/metrics.py:
    # Database metrics
    db_query_duration_seconds = Histogram("db_query_duration_seconds", "Database query duration", ["operation"])
    db_connections_active = Gauge("db_connections_active", "Active DB connections")
    # Cache metrics
    cache_operations_total = Counter("cache_operations_total", "Cache operations", ["operation", "result"])  # result: hit/miss
    # External API metrics
    external_api_duration_seconds = Histogram("external_api_duration_seconds", "External API call duration", ["service", "endpoint"])
    external_api_errors_total = Counter("external_api_errors_total", "External API errors", ["service", "status_code"])
    # Auth metrics
    auth_attempts_total = Counter("auth_attempts_total", "Authentication attempts", ["method", "result"])  # method: password/oauth/magic_link, result: success/failure
    auth_2fa_operations_total = Counter("auth_2fa_operations_total", "2FA operations", ["operation", "result"])
    # Business metrics
    registrations_total = Counter("registrations_total", "User registrations", ["method"])
    subscriptions_activated_total = Counter("subscriptions_activated_total", "Subscriptions activated", ["plan_type"])
    payments_total = Counter("payments_total", "Payment transactions", ["status", "gateway"])
    trials_activated_total = Counter("trials_activated_total", "Trial activations")
  - Instrument key code paths:
    - SQLAlchemy: Use event listeners (after_cursor_execute) to record db_query_duration_seconds
    - Redis: Wrap cache calls in CacheService to record cache_operations_total
    - httpx: Add response hooks in Remnawave adapter for external_api_duration_seconds
    - Auth routes: Increment auth_attempts_total on login/register
    - Payment routes: Increment payments_total on checkout
  - File: src/infrastructure/monitoring/metrics.py, instrument in relevant use cases/services

BOB-4: Structured JSON logging with structlog (P1)
  - Configure structlog for JSON output in src/shared/logging/config.py (NEW FILE):
    import structlog
    import logging
    def configure_logging(json_output: bool = True, log_level: str = "INFO"):
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer() if json_output else structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, log_level)),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
  - Call configure_logging() in main.py lifespan startup
  - Add request context (request_id, user_id) via structlog.contextvars in request_id middleware
  - Replace all logging.getLogger("cybervpn") calls with structlog.get_logger()
  - Add JSON_LOGS: bool = True and LOG_LEVEL: str = "INFO" to Settings
  - File: src/shared/logging/config.py (NEW), main.py, config/settings.py

BOB-5: OpenTelemetry tracing instrumentation (P1)
  - Add to pyproject.toml:
    opentelemetry-api>=1.25.0
    opentelemetry-sdk>=1.25.0
    opentelemetry-exporter-otlp>=1.25.0
    opentelemetry-instrumentation-fastapi>=0.46b0
    opentelemetry-instrumentation-sqlalchemy>=0.46b0
    opentelemetry-instrumentation-httpx>=0.46b0
    opentelemetry-instrumentation-redis>=0.46b0
  - Initialize in main.py lifespan (AFTER Sentry, BEFORE instrumentator):
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    resource = Resource.create({"service.name": "cybervpn-backend", "service.version": settings.VERSION})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_ENDPOINT)))
    trace.set_tracer_provider(provider)
    # Auto-instrument
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    HTTPXClientInstrumentor().instrument()
    RedisInstrumentor().instrument()
  - Add OTEL_EXPORTER_ENDPOINT: str = "http://otel-collector:4317" to Settings (disabled if empty)
  - Propagate trace context via X-Request-ID → merge with OTEL trace_id
  - File: main.py, pyproject.toml, config/settings.py

BOB-6: Worker Sentry + metrics hardening (P2)
  - Add sentry-sdk>=2.0.0 to services/task-worker/pyproject.toml
  - Initialize in broker.py startup (same pattern as BOB-1)
  - Ensure TaskIQ metrics (taskiq_tasks_total, taskiq_task_duration_seconds) are properly exposed
  - Add custom worker metrics: email_send_duration_seconds, email_send_errors_total
  - File: services/task-worker/src/broker.py, services/task-worker/pyproject.toml

BOB-7: Backend /readiness endpoint (P2)
  - Add GET /readiness (no auth) alongside existing /health:
    - Checks: DB connection, Redis connection, queue depth < 1000
    - Returns 200 if all pass, 503 if any fail
    - For Kubernetes/orchestrator readiness probes
  - Separate from /health (which is always 200 for liveness)
  - File: main.py

DONE CRITERIA: pytest passes. GET :9091/metrics returns FastAPI request metrics + custom metrics. Sentry DSN configurable. JSON logs output. OTEL traces export to collector.
NOTIFY: Message infra-obs when BOB-2 is done (they need to verify Prometheus scraping new metrics). Message infra-obs when BOB-5 is done (they need OTEL Collector ready).
```

### frontend-dev

```
You are frontend-dev on the CyberVPN team (Phase 3). You close remaining feature gaps + add frontend observability.
Stack: Next.js 16, React 19, TypeScript 5.9, Tailwind CSS 4, Motion 12, TanStack Query 5, @sentry/nextjs 10.38.0.
You work ONLY in frontend/.

CONTEXT — What already exists (Phase 2 completed):
- 18 API client modules in frontend/src/lib/api/ — ALL working with real API calls ✅
- Security modals (2FA, Password, Antiphishing) — DONE, real API ✅
- Subscription page: cancel modal, trial section, codes section, plan cards — DONE ✅
- Wallet, Payment History, Referral, Partner pages — DONE ✅
- Settings: Profile, Security, Devices, LinkedAccounts sections — DONE ✅
- Sidebar: All menu items wired ✅
- Sentry: @sentry/nextjs configured, error boundary with captureException ✅
- Sentry files: instrumentation.ts, sentry.server.config.ts, sentry.edge.config.ts ✅
- Mini App: 10 routes exist (home, plans, wallet, profile, payments, referral, security, partner, vpn-config, payment-history) ✅
- Mini App security (2FA, password, antiphishing) in profile page — DONE ✅

REMAINING GAPS TO FIX:

KEY FILES TO READ FIRST:
- SubscriptionsClient: frontend/src/app/[locale]/(dashboard)/subscriptions/components/SubscriptionsClient.tsx (line 24-28: alert)
- WalletClient: frontend/src/app/[locale]/(dashboard)/wallet/components/WalletClient.tsx (line 46-52: alert)
- VPN API: frontend/src/lib/api/vpn.ts (mock data)
- Usage API: frontend/src/lib/api/usage.ts (mock data)
- Analytics page: frontend/src/app/[locale]/(dashboard)/analytics/page.tsx (placeholder)
- Monitoring page: frontend/src/app/[locale]/(dashboard)/monitoring/page.tsx (placeholder)
- Miniapp home: frontend/src/app/[locale]/(miniapp)/home/page.tsx (line 52: hardcoded false)
- Miniapp plans: frontend/src/app/[locale]/(miniapp)/plans/page.tsx (line 341-360: Contact for Price)
- Payments API: frontend/src/lib/api/payments.ts (createInvoice already exists!)
- Wallet API: frontend/src/lib/api/wallet.ts (requestWithdrawal already exists!)

RULES:
- Use Context7 MCP to look up library docs before using any library.
- All components must be cyberpunk-themed (Orbitron font, neon-cyan/pink/green, scanlines).
- Do NOT downgrade any library version.
- Do NOT modify generated/types.ts manually.
- Do NOT touch (miniapp) auth files (TelegramMiniAppAuthProvider, MiniAppNavGuard).
- i18n: useTranslations('Namespace') in client components.

YOUR TASKS:

FG-1: Purchase flow — replace alert with crypto invoice (P0)
  - File: frontend/src/app/[locale]/(dashboard)/subscriptions/components/SubscriptionsClient.tsx
  - Current (line 24-28): alert(`Purchase plan: ${planUuid}...`)
  - Target: Call paymentsApi.createInvoice({ plan_uuid: planUuid, currency: 'USDT' }) from frontend/src/lib/api/payments.ts
  - On success: redirect to invoice.payment_url (CryptoBot payment page) via window.open()
  - On error: show toast notification with error message
  - Add loading state during invoice creation
  - Add promo code support: if promo code is active, include in request
  - Create PurchaseConfirmModal.tsx: show plan details, price, promo discount → "Pay with Crypto" button

FG-2: Wallet withdrawal — replace alert with real modal (P0)
  - File: frontend/src/app/[locale]/(dashboard)/wallet/components/WalletClient.tsx
  - Current (line 46-52): alert('Withdrawal flow - to be implemented')
  - Target: Open WithdrawalModal with form:
    - Amount input (min validation from API)
    - Payment method selector (crypto address, etc.)
    - Wallet address input
    - Submit → walletApi.requestWithdrawal() from frontend/src/lib/api/wallet.ts (already exists!)
    - Success → show pending status, refresh transactions
  - Create frontend/src/app/[locale]/(dashboard)/wallet/components/WithdrawalModal.tsx
  - Cyberpunk-styled: neon border, terminal font, progress animation

FG-3: VPN Usage — replace mock data with real API (P1)
  - Files: frontend/src/lib/api/vpn.ts AND frontend/src/lib/api/usage.ts
  - Both currently return mock/placeholder data
  - Target: Wire to real GET /api/v1/users/me/usage endpoint (already exists in backend!)
  - Consolidate: usage.ts should be the single source, remove vpn.ts mock or have vpn.ts re-export
  - Response: { bandwidth_used, bandwidth_limit, connections_active, connections_limit, period_start, period_end, last_connection }
  - Update Dashboard stats component to show real bandwidth gauge + connection count
  - File: frontend/src/lib/api/usage.ts, frontend/src/app/[locale]/(dashboard)/dashboard/components/

FG-4: Analytics page — replace placeholder with real charts (P1)
  - File: frontend/src/app/[locale]/(dashboard)/analytics/page.tsx
  - Replace <PlaceholderPage /> with real analytics dashboard:
    - Revenue chart (from payments history data)
    - User growth chart (registration count over time)
    - Subscription distribution (pie chart by plan)
    - Active users stat card
    - Bandwidth consumption chart
  - Use TanStack Query to fetch: GET /payments/history, GET /users/me/usage
  - Charts: Use CSS-only or lightweight chart library (recharts if already available, or pure CSS bars/progress)
  - Cyberpunk-styled: neon gradients, terminal-style axes
  - Create frontend/src/app/[locale]/(dashboard)/analytics/components/AnalyticsClient.tsx

FG-5: Monitoring page — real system health dashboard (P1)
  - File: frontend/src/app/[locale]/(dashboard)/monitoring/page.tsx
  - Replace <PlaceholderPage /> with real monitoring dashboard:
    - System health overview cards (API status, DB status, Redis status, Worker status)
    - Use existing GET /health/detailed endpoint for service health
    - Use existing monitoring API: frontend/src/lib/api/monitoring.ts (has getStats, getBandwidth)
    - Show API response time (from monitoring stats)
    - Show bandwidth usage chart
    - Grafana embed: iframe to Grafana dashboard (http://localhost:3002) with dark theme
    - Or: custom metrics display using data from /health/detailed
  - Create frontend/src/app/[locale]/(dashboard)/monitoring/components/MonitoringClient.tsx
  - Cyberpunk-styled: neon status indicators, pulse animation for healthy services

FG-6: Frontend Web Vitals tracking (P2)
  - Add web-vitals integration with Sentry:
    - Sentry @sentry/nextjs already captures Web Vitals automatically
    - Verify in sentry.client.config.ts that performance tracking is enabled:
      tracesSampleRate: 0.2
      replaysSessionSampleRate: 0.1
    - If sentry.client.config.ts doesn't exist, create it
  - Add custom performance marks for key interactions:
    - Time to first server list render
    - Time to dashboard stats load
    - Subscription purchase flow duration
  - File: frontend/sentry.client.config.ts, frontend/src/app/layout.tsx

MG-1: Miniapp subscription check — wire real data (P1)
  - File: frontend/src/app/[locale]/(miniapp)/home/page.tsx
  - Current (line 52): const hasActiveSubscription = false;
  - Target: Fetch GET /subscriptions/active via subscriptionsApi
  - If subscription exists and status === 'active': hasActiveSubscription = true
  - Show real plan name, expiry date, traffic used/limit
  - Handle loading/error states gracefully
  - Use TanStack Query: useQuery({ queryKey: ['miniapp-subscription'], queryFn: ... })

MG-2: Miniapp plans pricing — show real prices (P1)
  - File: frontend/src/app/[locale]/(miniapp)/plans/page.tsx
  - Current (line 341-360): {t('contactForPrice')} placeholder
  - Target: Plans from GET /plans already include price data in template
  - Extract price from plan template data (check actual API response structure)
  - If price not in template: show duration + "from $X/mo" based on plan metadata
  - Format currency appropriately
  - Add "Purchase" button that creates crypto invoice (same flow as FG-1)

MG-3: Miniapp devices management page (P2)
  - Create frontend/src/app/[locale]/(miniapp)/devices/page.tsx
  - Fetch GET /auth/devices → list active sessions
  - Each device: type icon, name (parsed from user_agent), IP, last active, current device badge
  - "Logout" button per device → DELETE /auth/devices/{id}
  - "Logout All" button → POST /auth/logout-all
  - Mobile-first layout: full-width cards, touch-friendly buttons
  - Add link from Profile page → Devices page
  - Reuse auth API client: frontend/src/lib/api/auth.ts

MG-4: Miniapp purchase flow integration (P1)
  - In miniapp plans page: wire "Purchase" button to create crypto invoice
  - Use paymentsApi.createInvoice() (same API client as dashboard)
  - After invoice created: try WebApp.openInvoice() for Telegram native payment, fallback to window.open(payment_url)
  - Show loading state during invoice creation
  - File: frontend/src/app/[locale]/(miniapp)/plans/page.tsx

DONE CRITERIA: Zero alert() in (dashboard)/. All pages render real data. npm run lint && npm run build pass. Web Vitals reporting active.
```

### mobile-dev

```
You are mobile-dev on the CyberVPN team (Phase 3). You fix remaining mobile gaps + add Sentry performance tracing.
Stack: Flutter, Riverpod 3.x, GoRouter 17, Clean Architecture, sentry_flutter 9.0.0, 27 locales.
You work ONLY in cybervpn_mobile/.

CONTEXT — What already exists (Phase 2 completed):
- OTP verification: ENABLED (_kEnableOtpVerification = true) ✅
- Wallet: Full screen with real API (balance, transactions, withdraw) ✅
- Antiphishing: Full screen with get/set/delete ✅
- Change Password: Full screen ✅
- Payment History: Full screen ✅
- 2FA: Full screen (setup, verify, disable) ✅
- Invite codes: FULLY IMPLEMENTED — dialog on plans screen, calls /invites/redeem ✅
- Promo codes: FULLY IMPLEMENTED — expandable field in purchase flow, validates /promo/validate ✅
- Subscription cancel: Widget (cancel_subscription_sheet.dart) EXISTS but NOT wired into any screen ⚠️
- Referral: Full UI with graceful degradation — shows "Coming Soon" when availability check fails ⚠️
- Partner: Full UI with graceful degradation — shows "Coming Soon" when availability check fails ⚠️
- Google/Apple OAuth: Services defined (google_sign_in_service.dart, apple_sign_in_service.dart), but login screen buttons call _showComingSoon() ⚠️
- Sentry: sentry_flutter 9.0.0 configured with PII sanitization, crash reporting ✅
- Sentry performance tracing: NOT enabled ❌

KEY FILES TO READ FIRST:
- Referral DS: cybervpn_mobile/lib/features/referral/data/datasources/referral_remote_ds.dart (line 55: checkAvailability GET /referral/status)
- Partner DS: cybervpn_mobile/lib/features/partner/data/datasources/partner_remote_ds.dart
- Cancel widget: cybervpn_mobile/lib/features/subscription/presentation/widgets/cancel_subscription_sheet.dart
- Login screen: cybervpn_mobile/lib/features/auth/presentation/screens/login_screen.dart (lines 332-346: Coming Soon buttons)
- Google service: cybervpn_mobile/lib/features/auth/domain/usecases/google_sign_in_service.dart
- Apple service: cybervpn_mobile/lib/features/auth/domain/usecases/apple_sign_in_service.dart
- Main (Sentry): cybervpn_mobile/lib/main.dart
- API constants: cybervpn_mobile/lib/core/constants/api_constants.dart
- Profile dashboard: cybervpn_mobile/lib/features/profile/presentation/screens/profile_dashboard_screen.dart

RULES:
- Use Context7 MCP to look up library docs before using any library.
- Copy patterns from existing features.
- Provider scoping: autoDispose for screen-scoped, plain NotifierProvider for app-scoped.
- Do NOT downgrade any package version.
- Add i18n strings to app_en.arb.
- flutter analyze must pass with zero issues.

YOUR TASKS:

MB-1: Fix referral availability check (P0)
  - File: cybervpn_mobile/lib/features/referral/data/datasources/referral_remote_ds.dart
  - Current: checkAvailability() calls GET /api/v1/referral/status
  - Backend DOES have this endpoint (confirmed) — investigate WHY it returns error:
    1. Check api_constants.dart for exact URL path — does it match backend?
    2. Check if auth token is being sent in the request
    3. Check if the base URL is correct for dev/staging
    4. Try calling the endpoint manually from the datasource with debug logging
  - Fix the root cause. If path mismatch: update api_constants.dart
  - If backend returns different response shape: update the response parsing
  - After fix: referral dashboard should show real data (code, stats, recent commissions)
  - ALSO fix: Remove "Coming Soon" fallback so that real errors are visible during dev
  - Test: Verify GET /referral/code, GET /referral/stats, GET /referral/recent all work

MB-2: Fix partner availability check (P0)
  - File: cybervpn_mobile/lib/features/partner/data/datasources/partner_remote_ds.dart
  - Same investigation as MB-1 — partner endpoints ARE implemented on backend
  - Backend endpoints: GET /partner/dashboard, GET /partner/codes, GET /partner/earnings, POST /partner/bind
  - Fix availability check, update paths if needed
  - For non-partner users: should show "Bind Partner Code" input (already implemented in UI)
  - For partner users: should show dashboard with codes and earnings
  - Test: Verify partner dashboard loads correctly for both partner and non-partner users

MB-3: Wire cancel subscription into UI (P1)
  - The cancel_subscription_sheet.dart widget is FULLY BUILT but no screen shows it
  - Add "Cancel Subscription" button to profile_dashboard_screen.dart:
    - Find the subscription card/section in profile dashboard
    - Add a "Cancel Subscription" text button (red/danger colored) below subscription info
    - Only visible when user has active subscription
    - On tap: show CancelSubscriptionSheet() bottom sheet
    - After cancel: refresh subscription state, show success snackbar
  - Also consider adding to plans_screen.dart near the active plan indicator
  - Add localization strings: cancelSubscription, cancelConfirmTitle, cancelConfirmMessage
  - File: profile_dashboard_screen.dart, plans_screen.dart (optional)

MB-4: Wire Google/Apple OAuth buttons (P1)
  - File: cybervpn_mobile/lib/features/auth/presentation/screens/login_screen.dart
  - Current (lines 332-346): Both buttons call _showComingSoon()
  - Backend supports generic OAuth: GET /oauth/{provider}/login → authorize URL, POST /oauth/{provider}/login/callback
  - For mobile native: Use existing GoogleSignInService and AppleSignInService
  - Implementation plan:
    1. Google: Call GoogleSignInService.signIn() → get serverAuthCode → send to POST /oauth/google/login/callback
    2. Apple: Call AppleSignInService.signIn() → get identityToken → send to POST /oauth/apple/login/callback
    3. Both return JWT tokens → store in auth provider → navigate to home
  - Handle errors: show snackbar with user-friendly message
  - Apple button: only show on iOS (Platform.isIOS check)
  - Replace _showComingSoon() calls with actual sign-in logic
  - Add to register_screen.dart too (social sign-up buttons)
  - Test: Verify OAuth flow works end-to-end with backend

MB-5: Enable Sentry performance tracing (P2)
  - File: cybervpn_mobile/lib/main.dart
  - Current: Sentry is initialized for crash reporting only
  - Target: Enable transaction and span tracing:
    In SentryFlutter.init options:
      options.tracesSampleRate = 0.2;
      options.enableAutoPerformanceTracing = true;  // Auto-instrument navigation
      options.enableUserInteractionTracing = true;  // Track button taps
  - Add custom transactions for key flows:
    - API call spans: Wrap Dio/http interceptor with Sentry span
    - Screen load spans: Track time from navigation to first data render
    - VPN connection span: Time from "Connect" tap to connected state
  - Create SentryHttpInterceptor for Dio that creates child spans for each API call
  - File: main.dart, create core/network/sentry_interceptor.dart

MB-6: Active subscription display improvement (P2)
  - File: profile_dashboard_screen.dart
  - Ensure active subscription card shows:
    - Plan name and tier badge
    - Expiry date with days remaining
    - Traffic used / limit progress bar
    - Auto-renew status indicator
    - Cancel button (from MB-3)
  - Fetch from GET /subscriptions/active
  - If no subscription: show "Get Started" card with link to plans
  - If trial active: show trial badge with days remaining
  - Add api_constants: subscriptionActive if not already present

DONE CRITERIA: Referral and Partner show real data (not Coming Soon). Cancel subscription works. Google/Apple OAuth functional. Sentry tracing enabled. flutter analyze passes.
```

### infra-obs

```
You are infra-obs on the CyberVPN team (Phase 3). You build production-grade observability infrastructure.
You work ONLY in infra/ directory.

CONTEXT — What already exists:
- docker-compose.yml with monitoring profile: Prometheus v3.2.1, Grafana v11.5.2, AlertManager v0.28.1 ✅
- Prometheus scrapes: cybervpn-backend:9091, remnawave:3001, cybervpn-worker:9091, cybervpn-telegram-bot:9092 ✅
- Grafana: 3 dashboards (worker-dashboard.json, otp-dashboard.json, error-monitoring.json) ✅
- Grafana provisioning: datasources (Prometheus), dashboards auto-load ✅
- AlertManager: 7 worker alert rules in prometheus/rules/worker_alerts.yml ✅
- AlertManager webhook: placeholder URL (https://your-telegram-relay.example.com/alert) ❌
- Docker logging: json-file driver, max 100MB/5 files ✅

KEY FILES:
- Docker Compose: infra/docker-compose.yml (services start at line 336 for monitoring)
- Prometheus config: infra/prometheus/prometheus.yml (5 scrape jobs)
- Alert rules: infra/prometheus/rules/worker_alerts.yml (7 rules)
- AlertManager config: infra/alertmanager/alertmanager.yml
- Grafana datasources: infra/grafana/provisioning/datasources/datasources.yml
- Grafana dashboards dir: infra/grafana/dashboards/ (3 JSON files)
- Dashboard provisioning: infra/grafana/provisioning/dashboards/dashboards.yml

RULES:
- All new services MUST be under profiles: ["monitoring"] (same as existing Prometheus/Grafana)
- Follow existing docker-compose patterns (x-common, x-logging, networking)
- All ports MUST bind to 127.0.0.1 (not 0.0.0.0)
- Use specific image versions (no :latest tags)
- Add healthchecks to all new services
- Grafana dashboards must be JSON files in infra/grafana/dashboards/ (auto-provisioned)

YOUR TASKS:

IOB-1: Loki log aggregation (P1)
  - Add Loki service to docker-compose.yml:
    grafana/loki:3.4.2
    Port: 3100 (internal only, no external port needed)
    Profile: monitoring
    Config: infra/loki/loki-config.yml with:
      - Local filesystem storage
      - 7-day retention
      - BoltDB shipper for index
    Healthcheck: wget --spider http://localhost:3100/ready
  - Add Promtail sidecar to collect Docker container logs:
    grafana/promtail:3.4.2
    Mount /var/log and Docker socket
    Config: infra/loki/promtail-config.yml with:
      - Docker service discovery
      - Label extraction: container_name, compose_service
      - Pipeline stages for JSON parsing (backend logs)
  - Add Loki as Grafana datasource:
    Update infra/grafana/provisioning/datasources/datasources.yml:
      - name: Loki
        type: loki
        url: http://loki:3100
        access: proxy
  - Files: docker-compose.yml, loki/loki-config.yml (NEW), loki/promtail-config.yml (NEW), grafana datasources

IOB-2: Prometheus exporters — PostgreSQL + Redis + Node + cAdvisor (P1)
  - Add postgres_exporter to docker-compose.yml:
    prometheuscommunity/postgres-exporter:v0.17.0
    Env: DATA_SOURCE_NAME=postgresql://user:pass@remnawave-db:5432/remnawave?sslmode=disable
    Profile: monitoring
    Healthcheck: wget --spider http://localhost:9187/metrics
  - Add redis_exporter:
    oliver006/redis_exporter:v1.67.0
    Env: REDIS_ADDR=redis://remnawave-redis:6379
    Profile: monitoring
    Healthcheck: wget --spider http://localhost:9121/metrics
  - Add node_exporter:
    prom/node-exporter:v1.9.1
    Profile: monitoring
    Mount: /proc, /sys (read-only)
    Healthcheck: wget --spider http://localhost:9100/metrics
  - Add cAdvisor:
    gcr.io/cadvisor/cadvisor:v0.52.1
    Profile: monitoring
    Mount: /var/run/docker.sock (read-only), /sys, /var/lib/docker
    Port: 8080 (internal)
    Healthcheck: wget --spider http://localhost:8080/healthz
  - Update prometheus.yml with 4 new scrape jobs:
    - job_name: postgres, targets: [postgres-exporter:9187]
    - job_name: redis, targets: [redis-exporter:9121]
    - job_name: node, targets: [node-exporter:9100]
    - job_name: cadvisor, targets: [cadvisor:8080]
  - Files: docker-compose.yml, prometheus/prometheus.yml

IOB-3: OpenTelemetry Collector + Tempo (P1)
  - Add OTEL Collector:
    otel/opentelemetry-collector-contrib:0.121.0
    Profile: monitoring
    Config: infra/otel/otel-collector-config.yml:
      receivers: otlp (grpc:4317, http:4318)
      processors: batch, memory_limiter
      exporters: otlp/tempo (tempo:4317), prometheus (port 8889)
      service.pipelines:
        traces: receivers[otlp] → processors[batch] → exporters[otlp/tempo]
        metrics: receivers[otlp] → processors[batch] → exporters[prometheus]
    Healthcheck: wget --spider http://localhost:13133/
  - Add Tempo (trace storage):
    grafana/tempo:2.7.2
    Profile: monitoring
    Config: infra/tempo/tempo-config.yml:
      - Local filesystem storage
      - 7-day retention
      - OTLP receiver on 4317
    Port: 3200 (internal only for Grafana query)
  - Add Tempo as Grafana datasource:
    Update datasources.yml:
      - name: Tempo
        type: tempo
        url: http://tempo:3200
        access: proxy
  - Update prometheus.yml: add scrape job for otel-collector:8889
  - Files: docker-compose.yml, otel/otel-collector-config.yml (NEW), tempo/tempo-config.yml (NEW), grafana datasources, prometheus.yml

IOB-4: Grafana FastAPI API dashboard (P0)
  - Create infra/grafana/dashboards/api-dashboard.json
  - Panels (all using Prometheus datasource):
    - Request Rate (req/sec) by endpoint — timeseries
    - Request Latency P50/P95/P99 — timeseries with multiple queries
    - Error Rate (4xx vs 5xx) — stacked bars
    - In-Flight Requests — gauge
    - Top 10 Slowest Endpoints — table
    - Status Code Distribution — pie chart
    - Request Duration Heatmap — heatmap
  - Use metrics from prometheus-fastapi-instrumentator:
    - http_requests_total{handler, method, status}
    - http_request_duration_seconds{handler, method}
    - http_requests_in_progress
  - Dashboard variables: $handler (dropdown), $method (dropdown), $interval (auto)
  - Dark theme, cyberpunk accent colors where possible
  - File: infra/grafana/dashboards/api-dashboard.json

IOB-5: Grafana PostgreSQL + Redis dashboards (P1)
  - Create infra/grafana/dashboards/postgres-dashboard.json:
    - Active connections vs max_connections — gauge
    - Transactions per second (commits + rollbacks) — timeseries
    - Tuple operations (inserts, updates, deletes, selects) — stacked area
    - Cache hit ratio — gauge (target: >99%)
    - Table sizes (top 10) — table
    - Slow queries (if pg_stat_statements enabled) — table
    - Replication lag (if applicable) — stat
    - Dead tuples / bloat indicator — gauge
  - Create infra/grafana/dashboards/redis-dashboard.json:
    - Memory usage vs maxmemory — gauge
    - Commands per second — timeseries
    - Connected clients — stat
    - Keyspace hit/miss ratio — gauge
    - Evicted keys — timeseries
    - Memory fragmentation ratio — stat
    - Blocked clients — stat
  - Files: postgres-dashboard.json (NEW), redis-dashboard.json (NEW)

IOB-6: Grafana Infrastructure + Application dashboards (P2)
  - Create infra/grafana/dashboards/infrastructure-dashboard.json:
    - CPU usage by container — stacked area (cAdvisor metrics)
    - Memory usage by container — stacked area
    - Network I/O by container — timeseries
    - Disk I/O — timeseries
    - Host CPU/Memory/Disk (node_exporter) — gauges
    - Container restart count — stat
  - Create infra/grafana/dashboards/application-dashboard.json:
    - Combined overview: API health + DB health + Redis health + Worker health
    - Registration rate — timeseries (registrations_total)
    - Payment volume — timeseries (payments_total)
    - Active subscriptions — stat (subscriptions_activated_total)
    - Trial activations — stat (trials_activated_total)
    - Auth attempts by method — pie chart (auth_attempts_total)
    - 2FA operations — bar chart (auth_2fa_operations_total)
  - Files: infrastructure-dashboard.json (NEW), application-dashboard.json (NEW)

IOB-7: Alert rules expansion — API, DB, Redis, Infra (P1)
  - Create infra/prometheus/rules/api_alerts.yml:
    - APIHighLatency: http_request_duration_seconds P95 > 1s for 5min (warning)
    - APIHighErrorRate: 5xx rate > 1% for 5min (critical)
    - APIDown: up{job="cybervpn-backend"} == 0 for 3min (critical)
    - HighRequestRate: request rate > 1000/sec for 5min (warning — potential DDoS)
  - Create infra/prometheus/rules/db_alerts.yml:
    - DBConnectionPoolExhausted: active_connections > 80% of max for 5min (critical)
    - DBSlowQueries: avg query time > 500ms for 10min (warning)
    - DBHighDeadTuples: dead tuples > 10000 for 1hr (warning — needs VACUUM)
    - DBReplicationLag: lag > 30s (critical, if applicable)
  - Create infra/prometheus/rules/redis_alerts.yml:
    - RedisHighMemory: memory_used > 80% of maxmemory for 5min (warning)
    - RedisHighEviction: evicted_keys rate > 100/min for 5min (critical)
    - RedisDown: up{job="redis"} == 0 for 1min (critical)
  - Create infra/prometheus/rules/infra_alerts.yml:
    - HighCPU: CPU usage > 90% for 10min (warning)
    - HighMemory: memory usage > 85% for 10min (warning)
    - HighDisk: disk usage > 85% (warning), > 95% (critical)
    - ContainerRestarting: restart count > 3 in 15min (warning)
  - Update prometheus.yml rule_files to include all new rule files
  - Files: prometheus/rules/api_alerts.yml, db_alerts.yml, redis_alerts.yml, infra_alerts.yml (ALL NEW), prometheus.yml

IOB-8: AlertManager real configuration (P1)
  - Update infra/alertmanager/alertmanager.yml:
    - Keep existing structure but add real routing:
    route:
      group_by: ['alertname', 'service']
      group_wait: 30s
      group_interval: 5m
      repeat_interval: 4h
      receiver: 'default'
      routes:
        - match: { severity: critical }
          receiver: 'critical'
          repeat_interval: 1h
        - match: { severity: warning }
          receiver: 'warning'
          repeat_interval: 6h
    receivers:
      - name: 'default'
        webhook_configs:
          - url: '${ALERTMANAGER_WEBHOOK_URL}'  # Env var for flexibility
      - name: 'critical'
        webhook_configs:
          - url: '${ALERTMANAGER_WEBHOOK_URL}'
            send_resolved: true
      - name: 'warning'
        webhook_configs:
          - url: '${ALERTMANAGER_WEBHOOK_URL}'
            send_resolved: true
    # Template for Telegram-friendly alert format
    templates:
      - '/etc/alertmanager/templates/*.tmpl'
  - Create infra/alertmanager/templates/telegram.tmpl with formatted alert text
  - Add ALERTMANAGER_WEBHOOK_URL to .env.example with placeholder
  - File: alertmanager/alertmanager.yml, alertmanager/templates/telegram.tmpl (NEW)

DONE CRITERIA: docker compose --profile monitoring up -d starts all new services. All exporters healthy. Prometheus scrapes all targets. Grafana shows 8+ dashboards. Alerts fire correctly.
COORDINATE: Wait for backend-obs BOB-2 completion before verifying API dashboard metrics. OTEL Collector must be running before backend BOB-5 sends traces.
```

### test-eng

```
You are test-eng on the CyberVPN team (Phase 3). You write tests for all new features and observability.
You work across: backend/tests/, frontend/src/**/__tests__/, cybervpn_mobile/test/.

CONTEXT — What's already done:
- Backend: Integration tests for auth, wallet, codes, 2FA ✅
- Frontend: 11 API client test files + settings/subscriptions component tests ✅
- Mobile: Widget tests for OTP, wallet, antiphishing, change password, payment history ✅

KEY FILES:
- Backend fixtures: backend/tests/conftest.py
- Backend test pattern: backend/tests/integration/api/v1/auth/test_auth_flows.py
- Frontend test pattern: frontend/src/lib/api/__tests__/wallet.test.ts
- Mobile test pattern: cybervpn_mobile/test/features/wallet/presentation/screens/wallet_screen_test.dart

RULES:
- Backend: httpx.AsyncClient + pytest-asyncio + test DB
- Frontend: vitest + MSW for API mocking + React Testing Library
- Mobile: flutter_test + mocktail + ProviderScope overrides
- Use Context7 MCP to look up testing library docs.
- Wait for implementation tasks to finish before writing tests for new features.
- Follow existing test patterns exactly.

YOUR TASKS:

TOB-1: Backend observability smoke tests (P1, after BOB-1..3)
  - Test /metrics endpoint returns Prometheus format with expected metrics:
    - http_requests_total (from instrumentator)
    - db_query_duration_seconds (from custom metrics)
    - cache_operations_total (from custom metrics)
  - Test /readiness returns 200 when services healthy, 503 when not
  - Test Sentry initialization (mock DSN, verify sentry_sdk.init called)
  - Test structured logging output is valid JSON
  - File: backend/tests/integration/test_observability.py (NEW)

TOB-2: Frontend purchase + withdrawal tests (P1, after FG-1, FG-2)
  - Test PurchaseConfirmModal: renders plan details, calls createInvoice, handles success/error
  - Test WithdrawalModal: form validation, amount limits, submit flow, success state
  - Mock paymentsApi and walletApi with MSW
  - File: frontend/src/app/[locale]/(dashboard)/subscriptions/__tests__/PurchaseConfirmModal.test.tsx (NEW)
  - File: frontend/src/app/[locale]/(dashboard)/wallet/__tests__/WithdrawalModal.test.tsx (NEW)

TOB-3: Frontend analytics + monitoring page tests (P2, after FG-4, FG-5)
  - Test AnalyticsClient: renders charts with mocked data, handles loading/error
  - Test MonitoringClient: renders health cards, handles service status variations
  - Mock monitoring API and payments API with MSW
  - File: frontend/src/app/[locale]/(dashboard)/analytics/__tests__/ (NEW)
  - File: frontend/src/app/[locale]/(dashboard)/monitoring/__tests__/ (NEW)

TOB-4: Mobile cancel + OAuth tests (P2, after MB-3, MB-4)
  - Test cancel subscription flow: button visible when active, sheet opens, cancel API called
  - Test Google OAuth flow: sign-in → callback → tokens stored
  - Test Apple OAuth flow: sign-in → callback → tokens stored (iOS only)
  - File: cybervpn_mobile/test/features/subscription/presentation/widgets/cancel_subscription_sheet_test.dart
  - File: cybervpn_mobile/test/features/auth/ (new OAuth test files)

TOB-5: Mini App integration tests (P2, after MG-1..4)
  - Test miniapp home: subscription data loads, trial status correct
  - Test miniapp plans: prices displayed, purchase flow triggers invoice creation
  - Test miniapp devices: list renders, logout works
  - Mock Telegram WebApp SDK
  - File: frontend/src/app/[locale]/(miniapp)/__tests__/ (NEW)

TOB-6: E2E observability verification script (P3, after ALL)
  - Create backend/tests/e2e/test_observability_e2e.py:
    - Hit GET /metrics → verify all expected metric names present
    - Hit GET /readiness → verify 200
    - Hit GET /health/detailed → verify all services healthy
    - Make 10 API requests → verify http_requests_total incremented
    - Verify structured JSON log output format
  - Create infra/tests/test_monitoring_stack.sh:
    - curl prometheus:9094/api/v1/targets → all targets UP
    - curl grafana:3002/api/dashboards → 8+ dashboards listed
    - curl alertmanager:9093/api/v2/alerts → API reachable
    - curl loki:3100/ready → 200
    - curl otel-collector:13133/ → 200
  - Files: backend/tests/e2e/test_observability_e2e.py (NEW), infra/tests/test_monitoring_stack.sh (NEW)

DONE CRITERIA: All tests pass in their runners. pytest, vitest, flutter test all green.
```

---

## Task Registry & Dependencies

### Dependency Graph

```
                    ┌── BOB-1 (Sentry) ──────────────────────────┐
                    │                                             │
                    ├── BOB-2 (FastAPI metrics) ───→ IOB-4 ──────┤
                    │                                             │
PHASE 3 START ──────┤── BOB-3 (Custom metrics) ───→ IOB-6 ──────┤───→ TOB-1
                    │                                             │
                    ├── BOB-4 (Structured logs) ───→ IOB-1 ──────┤
                    │                                             │
                    ├── BOB-5 (OTEL) ───→ IOB-3 (Collector) ────┘
                    │
                    ├── FG-1..3 (feature gaps) ─────→ TOB-2
                    │
                    ├── FG-4,5 (analytics/monitoring) → TOB-3
                    │
                    ├── FG-6 (Web Vitals) ── independent
                    │
                    ├── MG-1..4 (miniapp) ──────────→ TOB-5
                    │
                    ├── MB-1,2 (referral/partner fix) ── independent
                    │
                    ├── MB-3 (cancel wire) ──────────→ TOB-4
                    │
                    ├── MB-4 (OAuth wire) ───────────→ TOB-4
                    │
                    ├── MB-5 (Sentry tracing) ── independent
                    │
                    ├── IOB-1 (Loki) ── after BOB-4
                    ├── IOB-2 (Exporters) ── independent
                    ├── IOB-3 (OTEL Collector) ── after BOB-5
                    ├── IOB-4 (API dashboard) ── after BOB-2
                    ├── IOB-5 (DB+Redis dashboards) ── after IOB-2
                    ├── IOB-6 (Infra+App dashboards) ── after IOB-2, BOB-3
                    ├── IOB-7 (Alert rules) ── after IOB-2
                    ├── IOB-8 (AlertManager) ── independent
                    │
                    └── TOB-6 (E2E obs) ── waits for ALL
```

### Full Task Table

| ID | Task | Agent | Depends on | Priority |
|----|------|-------|------------|----------|
| BOB-1 | Backend Sentry SDK | backend-obs | — | P0 |
| BOB-2 | FastAPI Prometheus instrumentation | backend-obs | — | P0 |
| BOB-3 | Custom application metrics | backend-obs | BOB-2 | P1 |
| BOB-4 | Structured JSON logging (structlog) | backend-obs | — | P1 |
| BOB-5 | OpenTelemetry tracing instrumentation | backend-obs | — | P1 |
| BOB-6 | Worker Sentry + metrics hardening | backend-obs | BOB-1 | P2 |
| BOB-7 | Backend /readiness endpoint | backend-obs | — | P2 |
| FG-1 | Purchase flow (crypto invoice) | frontend-dev | — | P0 |
| FG-2 | Wallet withdrawal modal | frontend-dev | — | P0 |
| FG-3 | VPN Usage real data | frontend-dev | — | P1 |
| FG-4 | Analytics page (real charts) | frontend-dev | — | P1 |
| FG-5 | Monitoring page (system health) | frontend-dev | — | P1 |
| FG-6 | Frontend Web Vitals | frontend-dev | — | P2 |
| MG-1 | Miniapp subscription check | frontend-dev | — | P1 |
| MG-2 | Miniapp plans pricing | frontend-dev | — | P1 |
| MG-3 | Miniapp devices page | frontend-dev | — | P2 |
| MG-4 | Miniapp purchase flow | frontend-dev | FG-1 | P1 |
| MB-1 | Fix referral availability | mobile-dev | — | P0 |
| MB-2 | Fix partner availability | mobile-dev | — | P0 |
| MB-3 | Wire cancel subscription | mobile-dev | — | P1 |
| MB-4 | Wire Google/Apple OAuth | mobile-dev | — | P1 |
| MB-5 | Sentry performance tracing | mobile-dev | — | P2 |
| MB-6 | Active subscription display | mobile-dev | MB-3 | P2 |
| IOB-1 | Loki log aggregation | infra-obs | BOB-4 | P1 |
| IOB-2 | Prometheus exporters (4) | infra-obs | — | P1 |
| IOB-3 | OTEL Collector + Tempo | infra-obs | BOB-5 | P1 |
| IOB-4 | Grafana API dashboard | infra-obs | BOB-2 | P0 |
| IOB-5 | Grafana DB + Redis dashboards | infra-obs | IOB-2 | P1 |
| IOB-6 | Grafana Infra + App dashboards | infra-obs | IOB-2, BOB-3 | P2 |
| IOB-7 | Alert rules (API, DB, Redis, Infra) | infra-obs | IOB-2 | P1 |
| IOB-8 | AlertManager real config | infra-obs | — | P1 |
| TOB-1 | Backend observability smoke tests | test-eng | BOB-1..3 | P1 |
| TOB-2 | Frontend purchase + withdrawal tests | test-eng | FG-1, FG-2 | P1 |
| TOB-3 | Frontend analytics + monitoring tests | test-eng | FG-4, FG-5 | P2 |
| TOB-4 | Mobile cancel + OAuth tests | test-eng | MB-3, MB-4 | P2 |
| TOB-5 | Mini App integration tests | test-eng | MG-1..4 | P2 |
| TOB-6 | E2E observability verification | test-eng | ALL | P3 |

### Task Counts

| Agent | Tasks | IDs |
|-------|-------|-----|
| backend-obs | 7 | BOB-1..7 |
| frontend-dev | 11 | FG-1..6, MG-1..4 |
| mobile-dev | 6 | MB-1..6 |
| infra-obs | 8 | IOB-1..8 |
| test-eng | 6 | TOB-1..6 |
| **TOTAL** | **38** | |

---

## Lead Coordination Rules

1. **Spawn all 5 agents immediately.** Initial assignments:
   - `backend-obs` → BOB-1 + BOB-2 in parallel (P0 — Sentry + Prometheus instrumentation)
   - `frontend-dev` → FG-1 + FG-2 in parallel (P0 — purchase flow + withdrawal)
   - `mobile-dev` → MB-1 + MB-2 in parallel (P0 — fix referral + partner availability)
   - `infra-obs` → IOB-2 + IOB-8 in parallel (P1 — exporters can start immediately + AlertManager config)
   - `test-eng` → Wait, then start TOB-1 after BOB-1..3, or TOB-2 after FG-1..2

2. **Communication protocol:**
   - backend-obs finishes BOB-2 → messages infra-obs ("FastAPI metrics active, verify API dashboard")
   - backend-obs finishes BOB-4 → messages infra-obs ("JSON logs active, Loki can ingest")
   - backend-obs finishes BOB-5 → messages infra-obs ("OTEL traces sending to :4317, need Collector")
   - infra-obs finishes IOB-2 → starts IOB-5 + IOB-7 (DB/Redis dashboards + alert rules)
   - infra-obs finishes IOB-3 → messages backend-obs ("OTEL Collector ready at otel-collector:4317")
   - frontend-dev finishes FG-1 → starts MG-4 (miniapp purchase uses same pattern)
   - frontend-dev finishes FG-1+FG-2 → messages test-eng ("purchase + withdrawal ready for testing")
   - mobile-dev finishes MB-1+MB-2 → starts MB-3+MB-4 (wave 2)

3. **Parallel execution strategy:**
   - Wave 1 (immediate): BOB-1+2, FG-1+2, MB-1+2, IOB-2+8
   - Wave 2 (after wave 1): BOB-3+4+5, FG-3+4+5, MG-1+2, MB-3+4, IOB-1+4+7
   - Wave 3 (after wave 2): BOB-6+7, FG-6, MG-3+4, MB-5+6, IOB-3+5+6, TOB-1+2
   - Wave 4 (final): TOB-3+4+5, then TOB-6 (E2E)

4. **File conflict prevention:**
   - backend-obs owns `backend/` and `services/` exclusively
   - frontend-dev owns `frontend/` exclusively (both dashboard and miniapp)
   - mobile-dev owns `cybervpn_mobile/` exclusively
   - infra-obs owns `infra/` exclusively
   - test-eng writes ONLY in `*/tests/`, `*/__tests__/`, `*/test/` directories
   - Nobody modifies another agent's files

5. **Do NOT start implementing if you are lead — delegate.** Use delegate mode exclusively.

6. **Progress tracking.** Use the shared TaskList (TaskCreate/TaskUpdate). Do NOT use beads (`bd`) — SQLite lock conflicts with parallel agents.

7. **If any agent is blocked >5 minutes:** reassign them to an independent task and come back to the blocked one later.

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

---

## Final Verification (Lead runs after ALL tasks complete)

```bash
# ===== Backend =====
cd backend && python -m pytest tests/ -v --tb=short
# Verify Sentry initialized
grep -r "sentry_sdk.init" backend/src/main.py
# Verify metrics endpoint returns FastAPI metrics
curl -s http://localhost:9091/metrics | grep "http_requests_total"
curl -s http://localhost:9091/metrics | grep "db_query_duration_seconds"
# Verify structured JSON logs
docker logs cybervpn-backend 2>&1 | head -5 | python -m json.tool
# Verify readiness
curl -s http://localhost:8000/readiness | python -m json.tool

# ===== Frontend =====
cd frontend && npm run lint
cd frontend && npm run test -- --run
cd frontend && npm run build
# Verify zero alert() stubs in dashboard
grep -r "alert(" frontend/src/app/\[locale\]/\(dashboard\)/ --include="*.tsx" | grep -v node_modules | grep -v test
# Must return ZERO results
# Verify zero mock data
grep -r "mock\|placeholder\|Not implemented" frontend/src/lib/api/ --include="*.ts" | grep -v test | grep -v __tests__
# Must return ZERO results

# ===== Mobile =====
cd cybervpn_mobile && flutter analyze
cd cybervpn_mobile && flutter test
# Verify no Coming Soon in release code
grep -r "ComingSoon\|_showComingSoon" cybervpn_mobile/lib/ --include="*.dart"
# Must return ZERO results (or only in graceful degradation fallback)

# ===== Infrastructure =====
cd infra && docker compose --profile monitoring config --quiet
# Verify all monitoring services start
docker compose --profile monitoring up -d
# Wait 30 seconds for services to initialize
sleep 30
# Verify Prometheus targets
curl -s http://localhost:9094/api/v1/targets | python -m json.tool | grep -c '"health":"up"'
# Must be >= 9 targets (backend, remnawave, worker, bot, postgres, redis, node, cadvisor, otel-collector)
# Verify Grafana dashboards
curl -s -u admin:grafana_local_password http://localhost:3002/api/search?type=dash-db | python -m json.tool | grep -c '"title"'
# Must be >= 8 dashboards
# Verify Loki
curl -s http://localhost:3100/ready
# Verify OTEL Collector
curl -s http://localhost:13133/
# Verify AlertManager
curl -s http://localhost:9093/api/v2/status | python -m json.tool

# ===== Alert Rules =====
ls infra/prometheus/rules/
# Must show: worker_alerts.yml, api_alerts.yml, db_alerts.yml, redis_alerts.yml, infra_alerts.yml
```

All commands must pass with zero errors. If any fail, assign fix to the responsible agent.

---

## Completion Checklist

### Feature Gaps
- [ ] Frontend: Purchase flow uses real crypto invoice API (no alert)
- [ ] Frontend: Wallet withdrawal uses real modal + API (no alert)
- [ ] Frontend: VPN Usage shows real data (no mock)
- [ ] Frontend: Analytics page shows real charts
- [ ] Frontend: Monitoring page shows system health
- [ ] Mini App: Subscription check uses real API
- [ ] Mini App: Plans show real prices
- [ ] Mini App: Devices management page exists
- [ ] Mini App: Purchase flow creates crypto invoice
- [ ] Mobile: Referral shows real data (no Coming Soon)
- [ ] Mobile: Partner shows real data (no Coming Soon)
- [ ] Mobile: Cancel subscription button wired in UI
- [ ] Mobile: Google/Apple OAuth buttons functional
- [ ] Mobile: Active subscription display complete

### Observability — Sentry
- [ ] Backend: sentry-sdk initialized in main.py
- [ ] Backend: Unhandled exceptions captured
- [ ] Worker: sentry-sdk initialized in broker.py
- [ ] Frontend: @sentry/nextjs configured (already done)
- [ ] Frontend: Web Vitals tracking enabled
- [ ] Mobile: sentry_flutter crash + performance tracing

### Observability — Prometheus
- [ ] Backend: prometheus-fastapi-instrumentator active (request count/latency/errors)
- [ ] Backend: Custom metrics (DB, cache, auth, business)
- [ ] Infrastructure: postgres_exporter running
- [ ] Infrastructure: redis_exporter running
- [ ] Infrastructure: node_exporter running
- [ ] Infrastructure: cAdvisor running
- [ ] Prometheus: 9+ scrape targets all UP

### Observability — Grafana
- [ ] Dashboard: API (request rate, latency, errors)
- [ ] Dashboard: PostgreSQL (connections, transactions, cache ratio)
- [ ] Dashboard: Redis (memory, commands, hit ratio)
- [ ] Dashboard: Infrastructure (CPU, memory, disk, network)
- [ ] Dashboard: Application (registrations, payments, subscriptions)
- [ ] Dashboard: Worker (existing, verified)
- [ ] Dashboard: OTP (existing, verified)
- [ ] Dashboard: Errors (existing, verified)

### Observability — Logging & Tracing
- [ ] Backend: structlog JSON output configured
- [ ] Loki: Running, ingesting container logs
- [ ] Grafana: Loki datasource configured
- [ ] OTEL Collector: Running, receiving traces
- [ ] Tempo: Running, storing traces
- [ ] Grafana: Tempo datasource configured
- [ ] Backend: OTEL instrumentation (FastAPI, SQLAlchemy, httpx, Redis)

### Observability — Alerts
- [ ] Alert rules: API (latency, errors, down)
- [ ] Alert rules: Database (connections, slow queries)
- [ ] Alert rules: Redis (memory, eviction)
- [ ] Alert rules: Infrastructure (CPU, memory, disk)
- [ ] AlertManager: Real webhook configured
- [ ] AlertManager: Severity-based routing (critical vs warning)

### Build Verification
- [ ] `npm run build` passes (frontend)
- [ ] `flutter analyze` passes (mobile)
- [ ] `pytest` passes (backend)
- [ ] `docker compose --profile monitoring up -d` starts all services
- [ ] All Prometheus targets UP
- [ ] All Grafana dashboards loading
