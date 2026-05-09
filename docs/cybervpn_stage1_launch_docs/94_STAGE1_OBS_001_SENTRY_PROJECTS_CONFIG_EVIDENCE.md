# S1-OBS-001 — Sentry Critical Projects / Config Evidence

Date: 2026-05-06  
Revalidated: 2026-05-09  
Task ID: `S1-OBS-001`  
Scope: local/no-cost repository contract for S1 Sentry critical projects  
Result: completed locally and revalidated; live Sentry project/DSN/test-event/source-map/alert proof remains required before go-live

## Decision

For S1 Controlled Public Beta, the critical Sentry surfaces are:

| Runtime surface | Sentry project | Repo path | Environment model | Release model |
|---|---|---|---|---|
| Customer web / Mini App | `web-frontend` | `frontend/` | `NEXT_PUBLIC_APP_ENV` for browser, `APP_ENV` for server/edge | `frontend@<git-sha>` / public build release |
| Admin web | `web-admin` | `admin/` | `NEXT_PUBLIC_APP_ENV` for browser, `APP_ENV` for server/edge | `admin@<git-sha>` / public build release |
| Backend API | `backend-api` | `backend/` | `ENVIRONMENT` | `backend@<git-sha>` |
| Telegram Bot | `telegram-bot` | `services/telegram-bot/` | `ENVIRONMENT` | `telegram-bot@<git-sha>` |
| Task worker | `task-worker` | `services/task-worker/` | `ENVIRONMENT` | `task-worker@<git-sha>` |

`admin` is included even though the backlog acceptance mentions backend/frontend/bot/worker, because admin is launch-critical for support, payment attempts, manual subscription operations and incident handling.

## Implementation Completed

- Added `scripts/validate-s1-sentry-critical-projects.py` as the local S1 contract gate.
- Hardened `admin/src/instrumentation-client.ts` so browser Sentry config does not read private `APP_ENV` or `SENTRY_RELEASE`.
- Added admin Vitest coverage proving private env values do not leak into client instrumentation.
- Added explicit `SENTRY_AUTH_TOKEN`, `SENTRY_ORG` and `SENTRY_PROJECT` hooks to `frontend/next.config.ts` and `admin/next.config.ts` for source-map upload/release wiring.
- Updated `frontend/.env.example` and `admin/.env.example` with blank DSNs and explicit S1 project slugs: `web-frontend`, `web-admin`.
- Verified existing backend/bot/worker Sentry contracts use server-side DSNs, explicit environment/release, `send_default_pii=False`, disabled request bodies/local variables and before-send scrubbing hooks.

## Validation

| Command | Result |
|---|---|
| `python3 scripts/validate-s1-sentry-critical-projects.py` | PASS: `frontend`, `admin`, `backend`, `telegram-bot`, `task-worker` checked |
| `cd admin && npm run test:run -- src/__tests__/sentry-config.test.ts src/app/api/observability/sentry-contract/route.test.ts` | PASS: 2 files, 11 tests |
| `cd frontend && npm run test:run -- src/__tests__/sentry-config.test.ts src/app/api/observability/sentry-contract/route.test.ts` | PASS: 2 files, 11 tests |
| `cd backend && uv run pytest tests/unit/test_sentry_privacy.py -q --no-cov` | PASS: 2 tests |
| `cd services/telegram-bot && uv run pytest ...test_main.py::{sentry tests} -q --no-cov` | PASS: 4 tests |
| `cd services/task-worker && ENVIRONMENT=staging SENTRY_RELEASE=task-worker@testsha SENTRY_DSN=<redacted-valid-test-dsn> ... uv run pytest ... -q --no-cov` | PASS: 3 tests |
| `cd admin && npm run lint -- next.config.ts src/instrumentation-client.ts src/__tests__/sentry-config.test.ts` | PASS |
| `cd frontend && npm run lint -- next.config.ts` | PASS |

## 2026-05-09 Revalidation

This revalidation was run as the `S1-OBS-001` live-evidence follow-up. No live Sentry credentials or `sentry-cli` were available in the local/no-cost workspace, so the task can revalidate the repository contract but cannot prove live Sentry readiness.

Environment presence check was performed without printing secret values:

```text
SENTRY_URL=missing
SENTRY_AUTH_TOKEN=missing
SENTRY_ORG=missing
SENTRY_PROJECT=missing
NEXT_PUBLIC_SENTRY_DSN=missing
SENTRY_DSN=missing
SENTRY_RELEASE=missing
NEXT_PUBLIC_SENTRY_RELEASE=missing
sentry-cli=missing
```

Revalidation results:

| Check | Result |
|---|---|
| `python3 scripts/validate-s1-sentry-critical-projects.py` | PASS: five S1 critical surfaces checked |
| `cd frontend && npm run test:run -- src/__tests__/sentry-config.test.ts src/app/api/observability/sentry-contract/route.test.ts` | PASS: `2` files, `11` tests |
| `cd admin && npm run test:run -- src/__tests__/sentry-config.test.ts src/app/api/observability/sentry-contract/route.test.ts` | PASS: `2` files, `11` tests |
| `cd backend && uv run pytest tests/unit/test_sentry_privacy.py -q --no-cov` | PASS: `2` tests |
| `cd services/telegram-bot && uv run pytest tests/unit/test_main.py -k 'sentry or before_send or observability' -q --no-cov` | PASS: `5` tests, `6` deselected |
| `cd services/task-worker && uv run pytest tests/unit/test_observability.py -q --no-cov` | PASS: `1` test |

## Live Evidence Readiness Matrix

| Live evidence item | Current state | Required go-live evidence |
|---|---|---|
| Sentry organization / URL | Missing in local environment | `SENTRY_URL` or SaaS org URL recorded as redacted evidence |
| Sentry auth token | Missing in local environment | Token stored in approved secret store; never committed; redacted CI/provisioning proof attached |
| S1 critical projects | Local registry/contract only | Live projects exist: `web-frontend`, `web-admin`, `backend-api`, `telegram-bot`, `task-worker` |
| Runtime DSNs | Missing in local environment | Redacted DSN injection proof for staging/prod runtime envs |
| Frontend/admin source maps | Config contract exists | One release build uploads source maps successfully for `web-frontend` and `web-admin` |
| Test events | Not possible without live DSNs | One safe non-sensitive event per S1 critical surface, visible with correct project/environment/release |
| Alert routing | Local alert contract covered by `S1-OBS-004` | Live Sentry alert/test delivery to Telegram `-5173727789` and `backup@cyber-vpn.net` |

## Demo

| Component | Feature | Status |
|---|---|---|
| Repo validator | S1 critical Sentry project/config contract | PASS |
| Frontend/Admin | Browser/runtime Sentry config contract and protected route tests | PASS |
| Backend/Bot/Worker | Server-side privacy and Sentry initialization contract tests | PASS |
| Live Sentry | Project provisioning, DSN injection, test events, source maps and alerts | BLOCKED externally: credentials/CLI/organization are not present in this workspace |

Note: a first narrow backend pytest run without `--no-cov` functionally passed the two Sentry privacy tests but failed the repository-wide `fail-under=70` coverage gate because only a narrow test subset was selected. The focused command was repeated with `--no-cov` for this local contract evidence.

## Security Review

| Check | Result |
|---|---|
| Root `npm audit --omit=dev --audit-level=high` | PASS for high/critical. Existing moderate advisories remain in the repo audit output and were not introduced by this task. |
| Secret scan over touched Sentry config/docs/script files | PASS after replacing a test DSN transcript with `<redacted-valid-test-dsn>` in evidence. |
| Dangerous runtime pattern scan over touched code | PASS: no matches. |
| Client private-env scan | PASS: `admin/src/instrumentation-client.ts` and `frontend/src/instrumentation-client.ts` do not read `process.env.APP_ENV` or `process.env.SENTRY_RELEASE`. |

2026-05-09 revalidation security checks:

| Check | Result |
|---|---|
| Root `npm audit --omit=dev --audit-level=high` | PASS for high/critical; existing moderate Next/PostCSS advisory remains tracked because the force fix proposes a breaking downgrade path |
| `PYENV_VERSION=3.13.11 pip-audit --skip-editable .` in `backend/` | PASS: no known vulnerabilities found |
| `PYENV_VERSION=3.13.11 pip-audit --skip-editable .` in `services/telegram-bot/` | PASS: no known vulnerabilities found |
| `PYENV_VERSION=3.13.11 pip-audit --skip-editable .` in `services/task-worker/` | PASS: no known vulnerabilities found |
| Secret-pattern scan over updated `S1-OBS-001` source docs | PASS: no matches |
| Dangerous-pattern scan over updated `S1-OBS-001` source docs | PASS: no matches |

## Official Documentation Used

- Sentry Next.js manual setup and configuration: `https://docs.sentry.io/platforms/javascript/guides/nextjs/manual-setup/`
- Sentry JavaScript/Next.js options and source map/release guidance: `https://docs.sentry.io/platforms/javascript/guides/nextjs/configuration/options/`
- Sentry Python options: `https://docs.sentry.io/platforms/python/configuration/options/`
- Sentry Python FastAPI integration: `https://docs.sentry.io/platforms/python/integrations/fastapi/`

## Not Proven Yet

This evidence does not prove live Sentry readiness. Before go-live, attach:

- real Sentry org/project screenshots or exported settings for `web-frontend`, `web-admin`, `backend-api`, `telegram-bot`, `task-worker`;
- real staging/prod DSN injection evidence with redacted values;
- Sentry privacy/data-scrubbing rules applied in the live org;
- source-map upload proof for frontend/admin release builds;
- one forced non-sensitive test event per surface visible in the correct project/environment/release;
- alert routing proof to Telegram `-5173727789` and `backup@cyber-vpn.net`.

## Acceptance Result

`S1-OBS-001` is **completed locally and revalidated on 2026-05-09** as a repository Sentry critical-project/config contract.

Go-live remains blocked by live Sentry project/DSN/dashboard/alert evidence. `S1-OBS-004` local alert routing is completed, but live Telegram/email delivery proof remains required.

## 2026-05-09 Ordered Batch Revalidation

This pass revalidated `S1-OBS-001` as item `22` in the owner-requested ordered batch.

| Check | Result |
|---|---|
| Environment presence check for Sentry URL/token/org/project/DSNs/releases and `sentry-cli` | PASS as readiness inventory: all Sentry env values and `sentry-cli` are missing locally, so no secret values were exposed |
| `python3 scripts/validate-s1-sentry-critical-projects.py` | PASS: five S1 critical surfaces checked |
| `npm --prefix frontend run test:run -- src/__tests__/sentry-config.test.ts src/app/api/observability/sentry-contract/route.test.ts` | PASS: `2` files, `11` tests |
| `npm --prefix admin run test:run -- src/__tests__/sentry-config.test.ts src/app/api/observability/sentry-contract/route.test.ts` | PASS: `2` files, `11` tests |
| `cd backend && PYENV_VERSION=3.13.11 uv run pytest tests/unit/test_sentry_privacy.py -q --no-cov` | PASS: `2` tests |
| `cd services/telegram-bot && PYENV_VERSION=3.13.11 uv run pytest tests/unit/test_main.py -k 'sentry or before_send or observability' -q --no-cov` | PASS: `5` tests, `6` deselected |
| `cd services/task-worker && PYENV_VERSION=3.13.11 uv run pytest tests/unit/test_observability.py -q --no-cov` | PASS: `1` test |

`S1-OBS-002` was completed in `95_STAGE1_OBS_002_PII_SCRUBBING_EVIDENCE.md`, `S1-OBS-003` was completed locally in `96_STAGE1_OBS_003_METRICS_DASHBOARDS_EVIDENCE.md`, and `S1-OBS-004` was completed locally in `97_STAGE1_OBS_004_ALERTS_EVIDENCE.md`. Current next ordered step: `31. stage1-beta-rc.N` - create the controlled public beta release-candidate tag after owner confirms the ordered local evidence chain.
