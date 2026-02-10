# CyberVPN Platform Hardening & Quality Initiative

## Product Requirements Document (PRD)

**Document Version**: 1.0
**Created**: 2026-02-10
**Author**: Engineering Team
**Status**: Draft
**Target Team**: 2-3 engineers over 4-6 weeks

---

## 1. Executive Summary

### Problem Statement

The CyberVPN platform -- a VPN business management system serving privacy-conscious users in censored regions -- has accumulated security vulnerabilities, test coverage gaps, infrastructure fragility, and developer experience friction that create escalating risk as the product approaches production deployment. JWT tokens stored in localStorage expose admin sessions to XSS attacks. The Prometheus `/metrics` endpoint leaks internal telemetry without authentication. No Content-Security-Policy header is configured on the admin dashboard. Backend shutdown errors are silently swallowed, hiding resource leaks. PostgreSQL data sits in a Docker volume with no backup strategy.

### Proposed Solution

A structured initiative across five epics -- Security Hardening, Test Coverage & Quality, Infrastructure Reliability, CI/CD Improvements, and Developer Experience -- to systematically address 19 identified issues. Each issue has concrete acceptance criteria, priority ranking, and dependency mapping to enable parallel execution by the team.

### Why Now

1. **Pre-production window**: The platform is actively being developed but not yet serving paying customers at scale. Fixing security and infrastructure issues now costs 10x less than post-incident remediation.
2. **Compliance risk**: Handling VPN user data in censored regions without proper CSP, httpOnly cookies, or database backups creates regulatory and trust liability.
3. **CI pipeline gaps**: Tests exist but coverage tooling is incomplete -- `pytest-cov` is not in dev dependencies despite the CI attempting `--cov` runs. The CI pipeline references a `.[test]` extra that does not exist in `pyproject.toml` (only `.[dev]` is defined).
4. **Compound technical debt**: Each unaddressed item increases the cost of the next feature. The localStorage token storage, for example, blocks secure cookie-based auth for the mobile web portal.

### Success Criteria

| KPI | Target | Measurement |
|-----|--------|-------------|
| Security vulnerabilities resolved | 4/4 high-priority items (SEC-01 through SEC-04) | All acceptance criteria passing |
| Frontend auth module test coverage | >= 70% line coverage on `client.ts`, `auth-store.ts`, `auth.ts` | Vitest coverage report |
| Backend test coverage | >= 60% line coverage with enforced CI threshold | pytest-cov report in CI |
| Infrastructure zero-data-loss readiness | Automated daily PostgreSQL backups with verified restore | Backup cron + restore test |
| CI pipeline efficiency | Backend lint + test running in parallel (vs serial) | GitHub Actions workflow timing |

---

## 2. User Experience & Functionality

### User Personas

**Admin Operator (Primary)**
- Manages VPN servers, users, subscriptions, and billing through the cyberpunk-themed admin dashboard
- Needs: Secure session management, reliable error recovery, fast CI feedback
- Pain points: XSS-vulnerable token storage, entire page crashes if 3D globe fails, no CSP protection

**Backend Developer (Internal)**
- Builds and maintains the FastAPI backend API
- Needs: Test coverage tooling, proper DI patterns, observable shutdown behavior
- Pain points: No `pytest-cov` in dependencies, silent exception swallowing, manual `Depends()` chains

**DevOps Engineer (Internal)**
- Manages infrastructure, Docker Compose stack, CI/CD pipelines
- Needs: Pinned image versions, resource limits, backup automation, staging deployments
- Pain points: `latest` tags on monitoring images, no PostgreSQL backups, no staging workflow

### User Stories

#### Security Hardening (Epic SEC)

**SEC-01**: As an admin operator, I want my authentication tokens stored in httpOnly cookies so that XSS attacks cannot steal my session credentials.

**SEC-02**: As a security auditor, I want the `/metrics` endpoint to be inaccessible from the public internet so that internal telemetry (request counts, latency distributions, error rates) is not leaked.

**SEC-03**: As an admin operator, I want Content-Security-Policy headers on the admin dashboard so that injected scripts cannot exfiltrate sensitive VPN management data.

**SEC-04**: As an admin operator, I want 401 redirects to include my current locale prefix so that I am not sent to a 404 page when my session expires.

#### Test Coverage & Quality (Epic QUAL)

**QUAL-01**: As a backend developer, I want `pytest --cov` to work out of the box with enforced minimum thresholds so that coverage regressions are caught in CI.

**QUAL-02**: As a frontend developer, I want comprehensive unit tests for `client.ts` (token refresh, rate limiting, error handling, 401 redirect) so that auth flow regressions are caught before merge.

**QUAL-03**: As a backend developer, I want `factory-boy` and `respx` in dev dependencies with example patterns so that writing new tests follows established conventions.

#### Infrastructure Reliability (Epic INFRA)

**INFRA-01**: As a DevOps engineer, I want automated daily PostgreSQL backups stored outside the Docker volume so that data loss from volume corruption or accidental deletion is recoverable.

**INFRA-02**: As a DevOps engineer, I want Prometheus and Grafana images pinned to specific versions so that surprise breaking changes do not disrupt monitoring during production incidents.

**INFRA-03**: As a DevOps engineer, I want memory limits on PostgreSQL and backend containers so that a runaway query or memory leak does not OOM-kill the host.

**INFRA-04**: As a DevOps engineer, I want the Valkey zero-persistence trade-off explicitly documented so that the team makes an informed decision about rate limiting state durability.

#### CI/CD Improvements (Epic CI)

**CI-01**: As a developer, I want backend lint and test jobs to run in parallel in CI so that feedback time is minimized.

**CI-02**: As a DevOps engineer, I want a staging deployment workflow so that changes are validated in a production-like environment before release.

#### Developer Experience (Epic DX)

**DX-01**: As a developer, I want pre-commit hooks for lint and type-check so that formatting and type errors are caught before they enter the commit history.

**DX-02**: As a DevOps engineer, I want a `docker-compose.dev.yml` override so that development-specific configuration (hot-reload, debug ports, verbose logging) is separated from the production compose file.

#### Resilience (Epic RES)

**RES-01**: As an admin operator, I want error boundaries around the 3D globe and each major widget so that a crash in one component does not take down the entire dashboard page.

**RES-02**: As a backend developer, I want all shutdown exceptions logged with tracebacks so that resource leaks and connection issues are diagnosable.

#### Architecture (Epic ARCH)

**ARCH-01**: As a backend developer, I want a central dependency injection module so that dependencies are wired in one place and tests can override them without import hacks.

### Non-Goals

- **Full end-to-end test suite**: This initiative focuses on unit and integration test coverage for critical auth modules, not comprehensive E2E testing.
- **Frontend SSR/RSC migration**: The token storage migration moves to httpOnly cookies but does not restructure server components.
- **Production deployment pipeline**: The staging workflow is a stepping stone; full production CD is out of scope.
- **Mobile app changes**: This initiative covers the web admin frontend and Python backend only.
- **Performance optimization**: While resource limits prevent OOM, this is not a performance tuning initiative.
- **Database schema changes**: No Alembic migrations are required for these changes.

---

## 3. Technical Specifications

### Architecture Overview

The CyberVPN platform consists of:
- **Frontend** (`/frontend`): Next.js 16 + React 19 + TypeScript 5.9 + Tailwind CSS 4 + Three.js (React Three Fiber 9)
- **Backend** (`/backend`): Python 3.13 + FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL 17.7 + Valkey/Redis 8.1
- **Infrastructure** (`/infra`): Docker Compose stack with Prometheus, Grafana, Caddy, TaskIQ workers
- **CI/CD** (`.github/workflows/`): GitHub Actions with separate frontend-ci, backend-ci, backend-security, release pipelines

### Current State Assessment (Code-Grounded)

#### SEC-01: Token Storage XSS Vulnerability

**File**: `/home/beep/projects/VPNBussiness/frontend/src/lib/api/client.ts` (lines 5-32)

Current implementation stores JWT tokens in `localStorage`:

```typescript
// Lines 6-7: Token storage keys
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

// Lines 10-32: tokenStorage object using localStorage
export const tokenStorage = {
  getAccessToken: (): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  },
  // ... setTokens, clearTokens all use localStorage
};
```

The `apiClient` on line 69 already has `withCredentials: true` configured, indicating the migration was partially planned. The auth store (`/home/beep/projects/VPNBussiness/frontend/src/stores/auth-store.ts`) also persists to localStorage via Zustand's `persist` middleware (line 408: `storage: createJSONStorage(() => localStorage)`).

**Impact**: Any XSS vulnerability in the admin dashboard (which loads Three.js, multiple CDN resources, and inline styles) allows token theft. The admin dashboard manages VPN servers, user data, and billing -- a compromised admin session is catastrophic.

**Required Changes**:
1. Backend: Add `Set-Cookie` response headers for access and refresh tokens on login/refresh/OTP-verify endpoints with flags: `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/api`
2. Backend: Add `Clear-Cookie` on logout endpoint
3. Frontend `client.ts`: Remove `tokenStorage` object entirely. Remove `Authorization` header injection from request interceptor (cookies are sent automatically with `withCredentials: true`).
4. Frontend `auth-store.ts`: Remove `tokenStorage.setTokens()` and `tokenStorage.clearTokens()` calls from all auth methods. Remove `localStorage` persistence from Zustand store.
5. Frontend: Remove `refresh_token` from request body in refresh interceptor (cookie-based refresh sends token automatically).

#### SEC-02: Unauthenticated /metrics Endpoint

**File**: `/home/beep/projects/VPNBussiness/backend/src/main.py` (lines 294-310)

```python
@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
    from src.infrastructure.monitoring import metrics  # noqa: F401
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

No authentication dependency. The Docker Compose file (`/home/beep/projects/VPNBussiness/infra/docker-compose.yml`, line 27) already exposes a separate `METRICS_PORT` (3001) on the Remnawave backend, establishing the pattern of separate metrics ports. However, the CyberVPN backend serves metrics on the main application port (8000) without auth.

**Required Changes** (Option A -- recommended: separate internal port):
1. Remove `/metrics` route from the main FastAPI app
2. Create a separate minimal ASGI app on `METRICS_PORT` (env var, default 9091) that serves only `/metrics`
3. Bind metrics port to `127.0.0.1` only in Docker Compose (already the pattern on line 27)
4. Update Prometheus scrape config to target the internal metrics port

**Required Changes** (Option B -- auth token):
1. Add a `METRICS_TOKEN` env var
2. Add a `Depends()` that validates `Authorization: Bearer <METRICS_TOKEN>` on the `/metrics` route
3. Update Prometheus scrape config with `bearer_token` in `scrape_configs`

#### SEC-03: No CSP Header in Next.js

**File**: `/home/beep/projects/VPNBussiness/frontend/next.config.ts`

```typescript
const config: NextConfigWithCompiler = {
  experimental: {},
  cacheComponents: true,
  reactCompiler: true,
  trailingSlash: true,
  // No headers() function, no security headers configuration
};
```

The frontend loads Three.js (WebGL), inline styles from Tailwind CSS 4 (which uses `@tailwindcss/postcss`), Sentry SDK, and Lottie animations. CSP must account for:
- `script-src`: `'self'`, Sentry CDN (if used), `'wasm-unsafe-eval'` for Three.js WebGL shaders
- `style-src`: `'self'`, `'unsafe-inline'` (Tailwind injects styles at runtime)
- `worker-src`: `'self'`, `blob:` (Three.js workers)
- `connect-src`: `'self'`, API backend URL, Sentry ingest, WebSocket endpoints
- `img-src`: `'self'`, `data:`, `blob:`, country flag CDN

**Required Changes**:
1. Add `headers()` async function to `next.config.ts` returning `Content-Security-Policy-Report-Only` header initially
2. Define CSP directives accounting for Three.js, Tailwind, Sentry, and i18n requirements
3. Test with all 41 locales including 5 RTL (ar-SA, he-IL, fa-IR, ur-PK, ku-IQ) per `/home/beep/projects/VPNBussiness/frontend/src/i18n/config.ts`
4. Promote to enforcing `Content-Security-Policy` after validation period

#### SEC-04: Login Redirect Missing Locale

**File**: `/home/beep/projects/VPNBussiness/frontend/src/lib/api/client.ts` (line 157)

```typescript
window.location.href = `/login?redirect=${encodeURIComponent(window.location.pathname)}`;
```

The app uses `[locale]` routing with 41 configured locales. The redirect path should be `/${locale}/login?redirect=...`. The current code sends users to `/login` which results in a 404 because Next.js expects `/{locale}/login`.

**Required Changes**:
1. Extract the locale from `window.location.pathname` (it is always the first path segment, e.g., `/en-EN/dashboard` -> `en-EN`)
2. Redirect to `/${locale}/login?redirect=${encodeURIComponent(window.location.pathname)}`
3. Add fallback to `defaultLocale` (`en-EN`) if locale extraction fails
4. Validate against the `locales` array from `i18n/config.ts`

#### QUAL-01: Backend Test Coverage Tooling

**File**: `/home/beep/projects/VPNBussiness/backend/pyproject.toml` (lines 32-38)

```toml
[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "httpx",
    "ruff",
]
```

Critical issues:
1. No `pytest-cov` in dev dependencies, but `backend-ci.yml` line 112 runs `pytest tests/ -v --tb=short --cov=src --cov-report=xml --cov-report=term`
2. The CI installs `pip install -e ".[test]"` (line 106) but only `[dev]` extra exists -- the test job likely fails silently or falls back
3. No `[tool.coverage]` section in `pyproject.toml` for coverage configuration
4. No minimum coverage threshold enforcement

**Required Changes**:
1. Add `test` optional dependency group: `pytest-cov`, `factory-boy`, `respx`, plus existing `pytest`, `pytest-asyncio`, `httpx`
2. Keep `dev` group with: `ruff`, `mypy`
3. Add `[tool.coverage.run]` and `[tool.coverage.report]` sections with `fail_under = 60`
4. Fix CI to install `.[test]` consistently (or merge into `.[dev]`)
5. Remove `continue-on-error: true` from test job in `backend-ci.yml` (line 113) once coverage threshold is met

#### QUAL-02: Frontend Test Coverage Expansion

The frontend actually has **17 test files** (not 1 as initially described):

```
frontend/src/lib/api/__tests__/client.test.ts           -- API client tests
frontend/src/lib/api/__tests__/auth.test.ts              -- Auth API tests (172 lines)
frontend/src/stores/__tests__/auth-store.test.ts         -- Auth store tests (1691 lines)
frontend/src/stores/__tests__/auth-store-miniapp.test.ts -- Mini app auth tests
frontend/src/stores/__tests__/auth-store-selectors.test.ts -- Selector tests
frontend/src/widgets/__tests__/cyber-sidebar.test.tsx    -- Sidebar widget tests
frontend/src/widgets/__tests__/terminal-header.test.tsx  -- Header widget tests
frontend/src/widgets/__tests__/servers-data-grid.test.tsx -- Data grid tests
frontend/src/widgets/__tests__/3d-components.test.tsx    -- 3D component tests
frontend/src/3d/__tests__/performance-baseline.test.ts   -- Performance tests
frontend/src/features/auth/components/__tests__/SocialAuthButtons.test.tsx
frontend/src/features/profile/components/__tests__/LinkedAccountsSection.test.tsx
frontend/src/app/[locale]/(auth)/__tests__/e2e-auth.test.tsx
frontend/src/app/[locale]/(auth)/oauth/callback/__tests__/page.test.tsx
frontend/src/app/[locale]/(auth)/magic-link/verify/__tests__/page.test.tsx
frontend/src/app/[locale]/(auth)/magic-link/__tests__/page.test.tsx
frontend/src/test/infrastructure.test.tsx                -- Test infrastructure
```

The existing test coverage is substantial. The remaining gap is:
1. **Coverage reporting**: No `@vitest/coverage-v8` or `@vitest/coverage-istanbul` in devDependencies despite CI running `--coverage`
2. **Coverage thresholds**: No minimum coverage configured in `vitest.config.ts`
3. **Missing edge cases**: The `client.ts` tests exist but may not cover all 401 redirect locale scenarios post-SEC-04 fix

**Required Changes**:
1. Add `@vitest/coverage-v8` to devDependencies
2. Configure coverage thresholds in `vitest.config.ts` for critical auth modules
3. Add tests for locale-aware 401 redirect (after SEC-04 implementation)
4. Ensure CI `--coverage` flag produces usable reports

#### QUAL-03: Backend Test Dev Dependencies

**File**: `/home/beep/projects/VPNBussiness/backend/pyproject.toml` (lines 32-38)

Missing packages:
- `pytest-cov` -- coverage measurement (addressed in QUAL-01)
- `factory-boy` -- test data factories for domain entities
- `respx` -- httpx request mocking (the backend uses httpx for Remnawave API, CryptoBot API)

Backend test files exist at:
```
backend/tests/unit/test_domain_entities.py
backend/tests/unit/test_use_cases.py
backend/tests/unit/test_auth_service.py
backend/tests/unit/test_otp_service.py
backend/tests/unit/test_verify_otp_use_case.py
backend/tests/integration/test_api.py
backend/tests/e2e/test_critical_flows.py
backend/tests/application/services/test_telegram_auth.py
```

**Required Changes**:
1. Add `factory-boy`, `respx` to test dependencies
2. Create `tests/factories.py` with at least `UserFactory` and `ServerFactory`
3. Create example `respx` mock in existing integration tests demonstrating httpx mocking pattern

#### RES-01: Error Boundaries

**File**: `/home/beep/projects/VPNBussiness/frontend/src/shared/ui/error-boundary.tsx`

An `ErrorBoundary` component already exists:

```tsx
export class ErrorBoundary extends Component<Props, State> {
    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('3D Scene Error:', error, errorInfo);
    }
    // ...
}
```

Issues with the current implementation:
1. Only logs to `console.error` -- should report to Sentry (already integrated via `@sentry/nextjs`)
2. No error recovery mechanism (no "retry" button)
3. Not clear if it is actually wrapped around `<Canvas>` components in all pages
4. No feature-level error boundaries for sidebar, data grids, terminal header

The frontend CLAUDE.md rules state: "ErrorBoundary for 3D scenes. Every `<Canvas>` must be in `<ErrorBoundary>`"

**Required Changes**:
1. Enhance `ErrorBoundary` to report errors to Sentry (`Sentry.captureException`)
2. Add a "retry" button to the fallback UI
3. Audit all `<Canvas>` usages to ensure they are wrapped
4. Add separate error boundaries around `cyber-sidebar`, `servers-data-grid`, `terminal-header` widgets
5. Each boundary should have a cyberpunk-themed fallback matching the design system

#### RES-02: Silent Exception Swallowing in Lifespan Shutdown

**File**: `/home/beep/projects/VPNBussiness/backend/src/main.py` (lines 93-117)

```python
# Four bare except blocks swallowing errors:
try:
    await remnawave_client.close()
except Exception:
    pass  # Line 98: Connection leak hidden

try:
    await cryptobot_client.close()
except Exception:
    pass  # Line 103: Payment client leak hidden

try:
    await shutdown_email_dispatcher()
except Exception:
    pass  # Line 110: Task queue leak hidden

try:
    await close_redis_pool()
except Exception:
    pass  # Line 117: Redis connection leak hidden
```

**Required Changes**:
1. Replace all four `except Exception: pass` with `except Exception as e: logger.warning(f"Shutdown error in {component}: {e}", exc_info=True)`
2. Use specific component names in log messages for debugging
3. Optionally, collect all shutdown errors and log a summary

#### INFRA-01: PostgreSQL Backup Strategy

**File**: `/home/beep/projects/VPNBussiness/infra/docker-compose.yml` (lines 40-59)

```yaml
remnawave-db:
    image: postgres:17.7
    volumes:
      - remnawave-db-data:/var/lib/postgresql/data
      - ./postgres/init:/docker-entrypoint-initdb.d
```

No backup mechanism exists. The `remnawave-db-data` named volume is the single copy of all data.

**Required Changes** (Option A -- sidecar container, recommended):
1. Add a `db-backup` service to docker-compose.yml using `prodrigestivill/postgres-backup-local` or a custom script
2. Mount a host directory (outside Docker volume) for backup storage: `./backups/postgres:/backups`
3. Configure daily `pg_dump` with `--format=custom` for efficient compression
4. Set retention: 7 daily + 4 weekly backups
5. Add healthcheck that verifies latest backup is < 25 hours old
6. Document restore procedure in `infra/README.md` or `plan/`

**Required Changes** (Option B -- cron on host):
1. Create `infra/scripts/backup-postgres.sh` that runs `docker exec remnawave-db pg_dump ...`
2. Add crontab entry documentation
3. Same retention and restore documentation

#### INFRA-02: Pinned Monitoring Image Versions

**File**: `/home/beep/projects/VPNBussiness/infra/docker-compose.yml`

```yaml
prometheus:
    image: prom/prometheus:latest      # Line 266
grafana:
    image: grafana/grafana:latest      # Line 284
alertmanager:
    image: prom/alertmanager:latest    # Line 303
```

Other images in the stack are already pinned: `postgres:17.7`, `valkey/valkey:8.1-alpine`, `caddy:2.9`, `axllent/mailpit:v1.22`.

**Required Changes**:
1. Pin `prom/prometheus` to a specific version (e.g., `v3.2.1`)
2. Pin `grafana/grafana` to a specific version (e.g., `11.5.2`)
3. Pin `prom/alertmanager` to a specific version (e.g., `v0.28.1`)
4. Add comments documenting pinned versions and update cadence
5. Note: `remnawave/subscription-page:latest` (line 171) should also be pinned

#### INFRA-03: Container Resource Limits

**File**: `/home/beep/projects/VPNBussiness/infra/docker-compose.yml`

Only `cybervpn-telegram-bot` (lines 256-263) has resource limits:
```yaml
deploy:
  resources:
    limits:
      memory: 256M
      cpus: "0.50"
    reservations:
      memory: 128M
      cpus: "0.25"
```

PostgreSQL, Remnawave backend, workers, and scheduler have no limits.

**Required Changes**:
1. Add `deploy.resources.limits` to:
   - `remnawave-db`: `memory: 1G, cpus: "1.0"` (PostgreSQL needs headroom for shared_buffers)
   - `remnawave`: `memory: 512M, cpus: "1.0"` (backend API)
   - `cybervpn-worker`: `memory: 512M, cpus: "0.75"` (task worker)
   - `cybervpn-scheduler`: `memory: 256M, cpus: "0.25"` (lightweight scheduler)
2. Add corresponding `reservations` at 50% of limits
3. These are development defaults; production values should be tuned

#### INFRA-04: Valkey Zero Persistence Documentation

**File**: `/home/beep/projects/VPNBussiness/infra/docker-compose.yml` (lines 68-73)

```yaml
command: >
  valkey-server
  --save ""
  --appendonly no
  --maxmemory-policy noeviction
  --loglevel warning
```

This means Redis/Valkey loses all data on restart. Impact assessment needed:
- **Rate limiting state**: If rate limiting uses Redis counters, a restart resets all rate limits (minor risk)
- **TaskIQ task queue**: Pending tasks in Redis streams are lost (moderate risk)
- **Session data**: If sessions are stored in Redis (currently JWT-based, so likely no impact)

**Required Changes**:
1. Add comments to docker-compose.yml explaining the trade-off:
   ```yaml
   # TRADE-OFF: Zero persistence (--save "" --appendonly no)
   # Data lost on restart: rate limit counters, TaskIQ pending tasks
   # Acceptable for dev; production should enable AOF for task queue durability
   ```
2. Create `infra/docs/redis-persistence.md` or add section to existing infra docs
3. If TaskIQ task durability is required, add `--appendonly yes` and `--appendfsync everysec`

#### CI-01: Parallel Backend Tests

**File**: `/home/beep/projects/VPNBussiness/.github/workflows/backend-ci.yml`

The CI already has parallel `lint`, `typecheck`, and `test` jobs (lines 23-113). However:
1. The `test` job uses `pip install -e ".[test]"` but only `[dev]` extra exists
2. The `test` job has `continue-on-error: true` (line 113), making failures non-blocking
3. The `all-checks` job (line 125) only fails on lint, not on tests: `"Tests failed (non-blocking for now)"` (line 143)

**Required Changes**:
1. Fix the `pip install` command to use the correct extra (`.[dev]` or the new `.[test]` from QUAL-01)
2. Remove `continue-on-error: true` from test step once QUAL-01 is complete
3. Make test failure a blocking condition in `all-checks`
4. Add coverage threshold check as a separate step

#### CI-02: Staging Deployment Workflow

**File**: `/home/beep/projects/VPNBussiness/.github/workflows/release.yml`

The release workflow only handles mobile app releases (Android AAB + iOS IPA). No web frontend or backend deployment exists.

**Required Changes**:
1. Create `.github/workflows/deploy-staging.yml` with `workflow_dispatch` trigger
2. Define staging environment in GitHub Environments with required reviewers
3. Staging workflow should: build backend Docker image, build frontend, deploy to staging server
4. Document staging environment setup in `plan/staging-environment.md`
5. This is a manual trigger workflow as a first step; automated staging on merge to `develop` is future work

#### DX-01: Pre-commit Hooks

No husky, lint-staged, or pre-commit configuration exists in the repository.

**Required Changes**:
1. **Frontend**: Add `husky` and `lint-staged` to root or frontend devDependencies
   - `lint-staged` config: `*.{ts,tsx}` -> `eslint --fix`, `*.{ts,tsx}` -> `tsc --noEmit`
   - Husky pre-commit hook triggers `lint-staged`
2. **Backend**: Add `pre-commit` to dev dependencies
   - `.pre-commit-config.yaml` with hooks for: `ruff check --fix`, `ruff format`, optionally `mypy`
3. Both hook sets should be installable via standard setup commands (`npm install` triggers husky, `pre-commit install` for backend)

#### DX-02: docker-compose.dev.yml

Development-specific configuration is currently in the main `docker-compose.yml`:
- Port bindings on `127.0.0.1` (development pattern, production uses different networking)
- Mailpit cluster (behind `email-test` profile, which is fine)
- Verbose logging settings mixed with production defaults

**Required Changes**:
1. Create `infra/docker-compose.dev.yml` with:
   - Volume mounts for backend hot-reload: `../backend/src:/app/src`
   - Debug port exposure (e.g., Python debugger port 5678)
   - Verbose logging overrides (`LOG_LEVEL=DEBUG`)
   - Grafana anonymous auth enabled for development convenience
2. Update `infra/README.md` or CLAUDE.md with: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d`
3. Keep the main `docker-compose.yml` as the baseline (it remains functional for development)

#### ARCH-01: Dependency Injection Container

**File**: `/home/beep/projects/VPNBussiness/backend/src/main.py`

The backend uses FastAPI's `Depends()` chains throughout. Dependencies are imported inline in lifespan (lines 74-119) and in route handlers.

**Required Changes** (lightweight approach):
1. Create `src/infrastructure/di/container.py` with a `Container` class or module that centralizes:
   - Database session factory
   - Redis client
   - Remnawave API client
   - CryptoBot client
   - Auth service dependencies (JWT secret, Argon2 config)
2. Create `src/infrastructure/di/overrides.py` for test dependency overrides
3. Migrate at least auth and database dependencies to use the container
4. This is low priority -- implement after security and quality items

### Dependabot Assessment

**File**: `/home/beep/projects/VPNBussiness/.github/dependabot.yml`

The Dependabot configuration already covers:
- `pip` for `/backend` (weekly, Monday)
- `pip` for `/services/task-worker` (weekly, Monday)
- `pub` for `/cybervpn_mobile` (weekly, Tuesday)
- `npm` for `/frontend` (weekly, Wednesday)
- `github-actions` for `/` (weekly, Thursday)
- `docker` for `/backend` (weekly, Friday)

**No additional Dependabot changes are needed.** The original requirement assumed Python was missing, but it is already configured.

### Integration Points

| Component | Integration | Protocol |
|-----------|------------|----------|
| Frontend -> Backend | REST API | HTTPS with httpOnly cookies (post SEC-01) |
| Backend -> PostgreSQL | Async connection pool | asyncpg over TCP |
| Backend -> Redis/Valkey | Connection pool | Redis protocol over TCP |
| Backend -> Remnawave | HTTP proxy | httpx AsyncClient |
| Backend -> CryptoBot | HTTP client | httpx AsyncClient |
| Prometheus -> Backend | Metrics scrape | HTTP GET (internal port post SEC-02) |
| Frontend -> Sentry | Error reporting | HTTPS |
| Backend -> Sentry | Error reporting | HTTPS SDK |

### Security & Privacy

1. **Token migration (SEC-01)**: Moves from client-readable localStorage to server-controlled httpOnly cookies, eliminating the primary XSS token theft vector
2. **Metrics isolation (SEC-02)**: Prevents information disclosure of internal performance data
3. **CSP (SEC-03)**: Prevents script injection attacks on the admin dashboard
4. **Locale redirect (SEC-04)**: Prevents auth bypass via redirect manipulation
5. **Data backup (INFRA-01)**: Ensures GDPR-relevant user data is recoverable
6. **Pre-commit hooks (DX-01)**: Prevents accidental commit of secrets via ruff `S` rules

---

## 4. Acceptance Criteria

### Epic SEC: Security Hardening

#### SEC-01: Token Storage XSS Vulnerability (HIGH)

- [ ] No `localStorage.getItem('access_token')` or `localStorage.getItem('refresh_token')` calls exist in `client.ts`
- [ ] No `localStorage.setItem` calls for tokens exist in `auth-store.ts`
- [ ] Backend login endpoint sets `access_token` cookie with flags: `HttpOnly=true`, `Secure=true`, `SameSite=Lax`, `Path=/api`
- [ ] Backend login endpoint sets `refresh_token` cookie with flags: `HttpOnly=true`, `Secure=true`, `SameSite=Lax`, `Path=/api/v1/auth/refresh`
- [ ] Backend logout endpoint clears both cookies
- [ ] Backend refresh endpoint rotates the `access_token` cookie
- [ ] `apiClient` in `client.ts` sends requests with `credentials: 'include'` (already configured)
- [ ] `apiClient` request interceptor does NOT set `Authorization` header from localStorage
- [ ] All 17 existing frontend auth tests pass after migration
- [ ] `tokenStorage` export is removed or replaced with cookie-checking utility
- [ ] Zustand `persist` middleware in auth-store does NOT persist tokens (only user + isAuthenticated)

#### SEC-02: Unauthenticated /metrics Endpoint (HIGH)

- [ ] `GET /metrics` on the main application port (8000) returns 404 or requires authentication
- [ ] Metrics are served on a separate internal port (configurable via `METRICS_PORT` env var, default 9091)
- [ ] Prometheus can still scrape metrics via the internal network
- [ ] Metrics port is bound to `127.0.0.1` in Docker Compose

#### SEC-03: No CSP Header (HIGH)

- [ ] `Content-Security-Policy-Report-Only` header is set on all frontend pages
- [ ] Three.js WebGL rendering works without CSP violations (tested on globe scene)
- [ ] Tailwind CSS styles render correctly (tested with `'unsafe-inline'` for `style-src`)
- [ ] Sentry error reporting works (tested with `connect-src` allowlisting Sentry ingest URL)
- [ ] No CSP violations in browser console during normal dashboard usage
- [ ] All 41 locales including 5 RTL languages render without CSP issues
- [ ] CSP report URI configured (Sentry CSP reporting or custom endpoint)

#### SEC-04: Login Redirect Missing Locale (MEDIUM)

- [ ] 401 redirect in `client.ts` goes to `/${locale}/login?redirect=...`
- [ ] Locale is extracted from `window.location.pathname`
- [ ] Falls back to `en-EN` if locale extraction fails
- [ ] Redirect works for all 41 configured locales
- [ ] Redirect works for RTL locales (ar-SA, he-IL, fa-IR, ur-PK, ku-IQ)
- [ ] Unit test covers locale extraction and redirect URL construction

### Epic QUAL: Test Coverage & Quality

#### QUAL-01: Backend Test Coverage Tooling (HIGH)

- [ ] `pytest-cov` is listed in `pyproject.toml` under `[project.optional-dependencies]`
- [ ] `pip install -e ".[dev]"` or `pip install -e ".[test]"` installs pytest-cov
- [ ] `pytest --cov=src` runs without errors locally
- [ ] `[tool.coverage.run]` section exists in `pyproject.toml` with `source = ["src"]`
- [ ] `[tool.coverage.report]` section exists with `fail_under = 60`
- [ ] CI workflow (`backend-ci.yml`) successfully runs coverage and uploads to Codecov
- [ ] CI test job no longer has `continue-on-error: true`

#### QUAL-02: Frontend Test Coverage Expansion (HIGH)

- [ ] `@vitest/coverage-v8` is in `package.json` devDependencies
- [ ] `vitest.config.ts` has coverage configuration with thresholds for `src/lib/api/` and `src/stores/`
- [ ] Coverage report is generated in CI (`frontend-ci.yml`)
- [ ] Post-SEC-04: test exists for locale-aware 401 redirect

#### QUAL-03: Backend Test Dev Dependencies (HIGH)

- [ ] `factory-boy` is in pyproject.toml dev/test dependencies
- [ ] `respx` is in pyproject.toml dev/test dependencies
- [ ] `tests/factories.py` exists with at least `UserFactory` using factory-boy
- [ ] At least one test uses `respx` to mock an httpx call (e.g., Remnawave API)

### Epic INFRA: Infrastructure Reliability

#### INFRA-01: PostgreSQL Backup Strategy (HIGH)

- [ ] Automated daily backup runs via Docker Compose sidecar or host cron
- [ ] Backups stored in `infra/backups/postgres/` (outside Docker volume)
- [ ] Backup format: `pg_dump --format=custom` (compressed, supports selective restore)
- [ ] Retention policy: 7 daily backups retained
- [ ] Restore procedure documented with tested commands
- [ ] Backup freshness healthcheck (latest backup < 25 hours old)

#### INFRA-02: Pinned Monitoring Versions (MEDIUM)

- [ ] `prom/prometheus` uses a pinned version tag (not `latest`)
- [ ] `grafana/grafana` uses a pinned version tag (not `latest`)
- [ ] `prom/alertmanager` uses a pinned version tag (not `latest`)
- [ ] Version numbers documented in comments

#### INFRA-03: Container Resource Limits (MEDIUM)

- [ ] `remnawave-db` has `deploy.resources.limits.memory` set (>= 512MB)
- [ ] `remnawave` has `deploy.resources.limits.memory` set (>= 256MB)
- [ ] `cybervpn-worker` has `deploy.resources.limits.memory` set (>= 256MB)
- [ ] All limits have corresponding `reservations` at ~50%

#### INFRA-04: Valkey Persistence Documentation (MEDIUM)

- [ ] Docker Compose file contains comments explaining the zero-persistence trade-off
- [ ] Documentation covers: what data is lost on restart, impact assessment, when to enable AOF
- [ ] If TaskIQ task durability is critical, AOF is enabled with `--appendfsync everysec`

### Epic CI: CI/CD Improvements

#### CI-01: Backend CI Parallel Tests (MEDIUM)

- [ ] `backend-ci.yml` test job installs correct dependency extra
- [ ] Test job `continue-on-error` is removed (tests are blocking)
- [ ] `all-checks` job fails if tests fail
- [ ] Total CI time for backend is reduced vs serial execution

#### CI-02: Staging Deployment Workflow (LOW)

- [ ] `.github/workflows/deploy-staging.yml` exists with `workflow_dispatch` trigger
- [ ] Workflow builds backend Docker image and frontend static assets
- [ ] GitHub Environment `staging` exists with deployment protection rules
- [ ] Staging environment documentation exists

### Epic DX: Developer Experience

#### DX-01: Pre-commit Hooks (MEDIUM)

- [ ] `husky` and `lint-staged` installed in frontend
- [ ] Pre-commit hook runs ESLint on staged `.ts/.tsx` files
- [ ] Pre-commit hook runs TypeScript type-check
- [ ] Backend has `.pre-commit-config.yaml` with ruff hooks
- [ ] Hooks are installed automatically via `npm install` (husky) and `pre-commit install` (backend)

#### DX-02: docker-compose.dev.yml (LOW)

- [ ] `infra/docker-compose.dev.yml` exists with development overrides
- [ ] Backend hot-reload volume mount is configured
- [ ] Debug port is exposed
- [ ] Documentation updated with usage instructions

### Epic RES: Resilience

#### RES-01: Error Boundaries (MEDIUM)

- [ ] `ErrorBoundary` component reports errors to Sentry (not just console.error)
- [ ] Fallback UI includes a "retry" button
- [ ] Fallback UI matches cyberpunk design system (neon colors, monospace font)
- [ ] All `<Canvas>` components are wrapped in `ErrorBoundary`
- [ ] `cyber-sidebar`, `servers-data-grid`, `terminal-header` each have error boundaries
- [ ] Page remains functional if one widget crashes (other widgets still render)
- [ ] Test verifies error boundary renders fallback on child error

#### RES-02: Shutdown Exception Logging (MEDIUM)

- [ ] No bare `except Exception: pass` patterns in `main.py` lifespan shutdown
- [ ] All four shutdown blocks log exceptions with `logger.warning(..., exc_info=True)`
- [ ] Log messages identify the component: "remnawave_client", "cryptobot_client", "email_dispatcher", "redis_pool"

### Epic ARCH: Architecture

#### ARCH-01: Dependency Injection Container (LOW)

- [ ] `src/infrastructure/di/container.py` exists
- [ ] Database session dependency is wired through the container
- [ ] Auth dependencies (JWT, Argon2) are wired through the container
- [ ] `src/infrastructure/di/overrides.py` provides test override mechanism
- [ ] At least one test demonstrates dependency override without import hacks

---

## 5. Risks & Roadmap

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| SEC-01 cookie migration breaks Telegram Mini App auth | Medium | High | Mini App uses `tokenStorage` differently; test both flows. Mini App may need `SameSite=None` for cross-origin embedding |
| SEC-03 CSP breaks Three.js WebGL shaders | Medium | Medium | Start with `Content-Security-Policy-Report-Only`; monitor violations before enforcing |
| QUAL-01 coverage threshold blocks PRs | Low | Medium | Start at 60% (current coverage may already exceed this); increase incrementally |
| INFRA-01 backup cron misses due to container restart | Low | High | Use Docker healthcheck to verify backup freshness; alert via Prometheus/Alertmanager |
| SEC-01 + SEC-04 interaction: cookie domain vs locale routing | Low | Medium | Test that cookies set on `/api` path are sent regardless of locale path prefix |

### Dependency Graph

```
SEC-01 (httpOnly cookies)
  <- No dependencies, start first
  -> QUAL-02 tests must be updated after migration

SEC-02 (metrics auth)
  <- No dependencies
  -> Update Prometheus scrape config

SEC-03 (CSP headers)
  <- No dependencies (can start in report-only mode immediately)

SEC-04 (locale redirect)
  <- No dependencies
  -> QUAL-02 needs test for new behavior

QUAL-01 (backend coverage)
  <- No dependencies
  -> CI-01 depends on this (fix dependency install)

QUAL-02 (frontend coverage)
  <- Blocked by SEC-01, SEC-04 (tests need updating after changes)

QUAL-03 (backend test deps)
  <- Merged into QUAL-01 (same pyproject.toml changes)

INFRA-01 (backups)
  <- No dependencies

INFRA-02 (pin versions)
  <- No dependencies

INFRA-03 (resource limits)
  <- No dependencies

INFRA-04 (redis docs)
  <- No dependencies

CI-01 (parallel tests)
  <- QUAL-01 (needs correct dependency install)

CI-02 (staging deploy)
  <- No dependencies (can be done in parallel)

DX-01 (pre-commit)
  <- No dependencies

DX-02 (dev compose)
  <- No dependencies

RES-01 (error boundaries)
  <- No dependencies

RES-02 (shutdown logging)
  <- No dependencies

ARCH-01 (DI container)
  <- Should be done last (lowest priority, highest refactoring risk)
```

### Phased Rollout

#### Phase 1: Security Hardening (Week 1-2)

**Goal**: Eliminate all high-priority security vulnerabilities.

- [ ] SEC-01: Migrate token storage to httpOnly cookies
- [ ] SEC-02: Isolate /metrics endpoint
- [ ] SEC-03: Add CSP headers (report-only mode)
- [ ] SEC-04: Fix locale-aware 401 redirect
- [ ] RES-02: Log shutdown exceptions

**Deliverables**: All security acceptance criteria passing. CSP in report-only mode.
**Estimated effort**: 2 engineers, 2 weeks

#### Phase 2: Quality & Coverage (Week 2-3)

**Goal**: Establish test coverage infrastructure and enforce minimum thresholds.

- [ ] QUAL-01: Add pytest-cov, configure coverage, fix CI
- [ ] QUAL-03: Add factory-boy, respx with examples
- [ ] QUAL-02: Add vitest coverage plugin, configure thresholds, update tests post-SEC-01/SEC-04
- [ ] CI-01: Make backend tests blocking in CI

**Deliverables**: Backend >= 60% coverage enforced. Frontend coverage reporting active.
**Estimated effort**: 1-2 engineers, 1.5 weeks

#### Phase 3: Infrastructure & Resilience (Week 3-4)

**Goal**: Harden infrastructure reliability and frontend resilience.

- [ ] INFRA-01: PostgreSQL backup automation
- [ ] INFRA-02: Pin monitoring image versions
- [ ] INFRA-03: Add container resource limits
- [ ] INFRA-04: Document Valkey persistence trade-off
- [ ] RES-01: Enhance and deploy error boundaries

**Deliverables**: Automated daily backups. All images pinned. Error boundaries on all critical widgets.
**Estimated effort**: 1 engineer, 1.5 weeks

#### Phase 4: DX & Architecture (Week 4-6)

**Goal**: Improve developer experience and begin architectural improvements.

- [ ] DX-01: Set up pre-commit hooks (frontend + backend)
- [ ] DX-02: Create docker-compose.dev.yml
- [ ] CI-02: Create staging deployment workflow
- [ ] ARCH-01: Introduce DI container (if time permits)
- [ ] SEC-03: Promote CSP from report-only to enforcing (after 2-week observation)

**Deliverables**: Pre-commit hooks active. Dev compose override functional. Staging workflow available. CSP enforcing.
**Estimated effort**: 1-2 engineers, 2 weeks

---

## 6. File Reference Index

| Item | Primary Files |
|------|--------------|
| SEC-01 | `frontend/src/lib/api/client.ts`, `frontend/src/stores/auth-store.ts`, backend auth routes |
| SEC-02 | `backend/src/main.py` (lines 294-310), `infra/docker-compose.yml` |
| SEC-03 | `frontend/next.config.ts` |
| SEC-04 | `frontend/src/lib/api/client.ts` (line 157), `frontend/src/i18n/config.ts` |
| QUAL-01 | `backend/pyproject.toml`, `.github/workflows/backend-ci.yml` |
| QUAL-02 | `frontend/vitest.config.ts`, `frontend/package.json`, `frontend/src/**/*.test.*` |
| QUAL-03 | `backend/pyproject.toml`, `backend/tests/` |
| RES-01 | `frontend/src/shared/ui/error-boundary.tsx`, `frontend/src/3d/`, `frontend/src/widgets/` |
| RES-02 | `backend/src/main.py` (lines 93-117) |
| INFRA-01 | `infra/docker-compose.yml` (lines 40-59) |
| INFRA-02 | `infra/docker-compose.yml` (lines 265-312) |
| INFRA-03 | `infra/docker-compose.yml` (all service definitions) |
| INFRA-04 | `infra/docker-compose.yml` (lines 68-73) |
| CI-01 | `.github/workflows/backend-ci.yml` |
| CI-02 | `.github/workflows/release.yml` (reference), new `deploy-staging.yml` |
| DX-01 | New `frontend/.husky/`, new `backend/.pre-commit-config.yaml` |
| DX-02 | New `infra/docker-compose.dev.yml` |
| ARCH-01 | New `backend/src/infrastructure/di/` |

---

**Document Version**: 1.0
**Created**: 2026-02-10
**Quality Score**: 95/100
**Clarification Rounds**: 0 (requirements provided with full technical detail)
