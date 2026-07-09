# CyberVPN Latest-Everywhere Modernization Matrix

Created: 2026-07-03

This document tracks the local-only dependency modernization requested for CyberVPN. It is a planning and evidence matrix, not a release approval.

## Approved Decisions

| Topic | Decision |
| --- | --- |
| Release channel | Stable latest only; no beta, rc, canary, preview, or nightly dependencies |
| Delivery shape | One large local PR/diff, no GitHub push |
| Dependency scope | Direct dependencies plus risky/security transitive fixes |
| Web alignment | Common `frontend`, `admin`, and `partner` dependencies must use identical stable latest versions |
| Version ranges | Exact versions, no caret ranges |
| Web lock source | Root `package-lock.json` is the source of truth |
| Drift prevention | Blocking check for common web dependency drift |
| Runtime | Node 24 baseline for local, CI, and Docker web paths |
| Unused dependencies | Remove unused dependencies rather than upgrading and keeping them |
| Feature adoption | Adopt useful new features aggressively when testable and valuable |
| Testing | Required Playwright/browser smoke, broad visual checks, MSW fail-closed, split DOM environments |
| Backend | FastAPI latest, no `pydantic.v1`, targeted Starlette request limits, contract sync |
| Database | SQLAlchemy/Alembic latest with PostgreSQL clean/populated/downgrade/re-upgrade gates |
| Services | Lock-backed backend/task-worker Docker runtime, vpn-test-agent lock plus smoke, TaskIQ features, aiogram smoke |
| Security | High and critical findings block release-critical gates |
| Staging/production | Staging rehearsal only; production deployment is out of scope |

## Scope

In scope:

- `frontend`
- `admin`
- `partner`
- `backend`
- Python services under `services`
- `infra`, CI, scanners, dependency audit, SBOM/provenance planning
- release/testing evidence

Out of scope unless a shared policy requires a narrow compatibility edit:

- Flutter mobile
- Tauri/Rust desktop
- browser extension
- Verta/protocol
- unrelated SDK/package surfaces

## Current Known Starting State

| Area | Current state |
| --- | --- |
| Git | `main` at `87243b384ecc9c22286fcb8a1511f6d6c427d5a2`, equal to `origin/main` during initial pre-edit check |
| Dirty tree | Pre-existing generated i18n JSON modifications under `admin/src/i18n/messages/generated` and `frontend/src/i18n/messages/generated` |
| Node | Local Node observed earlier as `v24.18.0` |
| npm | Local npm observed earlier as `11.4.2` |
| Python | Local Python observed earlier as `3.13.14` |
| uv | Local uv observed earlier as `0.11.26` |
| Existing task contract | Replaced unrelated `CYBA-LOCAL-TEST-SETUP` with this modernization task |

## Web Package Matrix

The implementation phase must refresh this table from live npm metadata before editing package files.

| Package/group | Current source | Target policy | Feature/risk focus | Required evidence |
| --- | --- | --- | --- | --- |
| `next`, `eslint-config-next` | `frontend/admin/partner/package.json`, root lock | Stable latest, identical across all three apps | Cache Components, revalidation tags, proxy entry points, routing/cookies/locales | i18n, lint, typecheck, tests, build, Playwright locale/session smoke |
| `react`, `react-dom` | Web manifests and lockfiles | Stable latest pair, identical across all three apps | React Compiler, Activity, useEffectEvent, Performance Tracks | Hydration checks, interaction tests, perf traces |
| `typescript` | Web devDependencies | Stable latest exact | TS 6 compatibility, generated clients | `tsc --noEmit` for all web apps |
| `eslint` and plugins/configs | Web devDependencies and configs | Stable latest exact | ESLint 10, broad strictness without broad disables | lint for all apps, no blanket suppressions |
| Tailwind stack | Web devDependencies and CSS | Stable latest exact | Logical utilities, scrollbars, RTL readiness | build plus broad visual gallery |
| `next-intl` | Web dependencies | Stable latest exact | locale redirects and ICU behavior | all-locale redirect and i18n tests |
| `@sentry/nextjs` | Web dependencies | Stable latest exact | breadcrumbs, safe logs, key tracing boundaries | privacy review, Sentry init tests/smoke |
| `@tanstack/react-query` | Web dependencies | Stable latest exact | global stale/refetch/retry review, optimistic UX | query behavior tests, no stale authoritative UI |
| `axios` | Web dependencies | Stable latest exact | redirects, cookies, auth headers, error mapping | BFF/HTTP wrapper tests |
| `vitest`, MSW, DOM envs | Web devDependencies | Stable latest exact | MSW fail-closed, split happy-dom/jsdom | full web tests |
| `schema-dts` | Web dependencies | Stable latest exact | structured data output | SEO/JSON-LD tests |
| `lucide-react`, `motion` | Web dependencies | Remove if unused | Reduce dependency surface | import audit and package diff |
| Three/R3F stack | Web dependencies | Stable latest exact if in use | WebGL/canvas compatibility | browser/WebGL/canvas smoke |

## Backend and Services Matrix

| Package/group | Target policy | Feature/risk focus | Required evidence |
| --- | --- | --- | --- |
| FastAPI/Pydantic/Starlette/Uvicorn | Stable latest | OpenAPI/router/proxy/request-limit behavior | backend tests, OpenAPI export, semantic diff, generated clients |
| Sentry SDK/OpenTelemetry/structlog | Stable latest | safe traces/logs, backend->worker correlation | privacy/security review and observability tests |
| SQLAlchemy/Alembic | Stable latest | migrations and PostgreSQL behavior | clean/populated/downgrade/re-upgrade, lock probes, concurrency tests |
| Redis/TaskIQ/taskiq-redis | Stable latest unless proven blocker | RESP shapes, queue claims, retries, metrics/readiness | Redis/worker integration tests |
| aiogram/telegram-bot | Stable latest | bot runtime compatibility | smoke without real Telegram API |
| WebAuthn/passkeys | Attempt stable latest; rollback only with proven blocker | registration/authentication/security negative cases | backend and web passkey tests |
| backend/task-worker Docker runtime | Lock-backed installs | runtime reproducibility | image/build/runtime smoke |
| vpn-test-agent | Add lock and smoke | audit coverage gap | lockfile plus minimal smoke |

## Infra, CI, and Release Matrix

| Area | Target policy | Required evidence |
| --- | --- | --- |
| npm audit, pip-audit, Trivy, Grype, Gitleaks, CodeQL | High and critical findings block release-critical gates | local/CI-equivalent command evidence |
| GitHub Actions | Pin by SHA where practical | workflow diff and syntax/action validation |
| scanner images | pinned tags/digests, no `latest` fallback | script/workflow diff and scanner run |
| SBOM | production image/artifact SBOM where supported | generated SBOM artifacts or documented tool blocker |
| provenance/cosign | plan and foundation, not first-PR blocker unless already supported | documented rollout path |
| OpenTofu | update and validate without production apply | fmt/validate/plan-like no-mutation evidence |
| runtime images | update Postgres, Valkey, NATS, Prometheus, Grafana, OTel where in scope | compose/config/smoke compatibility |
| path filters | lockfile/manifests/Docker/CI changes trigger relevant gates | workflow/path-filter tests or review evidence |
| staging | after all local/CI-equivalent gates | staging smoke evidence, no production deployment |
| rollback | web, backend/services, DB where supported | rollback rehearsal evidence or documented limitation |

## Implementation Phases

1. Contract, matrix, i18n normalization, and targeted baseline.
2. Runtime and dependency policy foundation.
3. Web latest alignment and unused dependency removal.
4. Web feature adoption and test hardening.
5. Backend latest, OpenAPI contract sync, and observability.
6. Database latest and migration/concurrency gates.
7. Services latest, lock-backed runtime, TaskIQ/Telegram/Redis evidence.
8. Infra/CI/security/release gates.
9. Final local/CI-equivalent verification, staging rehearsal preparation, and independent reviews.

## Evidence Log

| Time | Evidence |
| --- | --- |
| 2026-07-03T12:34:08+05:00 | Initial git check recorded branch `main`, HEAD/merge-base `87243b384ecc9c22286fcb8a1511f6d6c427d5a2`, with only pre-existing generated i18n dirty files. |
