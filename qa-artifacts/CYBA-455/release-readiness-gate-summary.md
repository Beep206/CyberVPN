# CYBA-455 Automated Release-Readiness Gate Summary

Дата: 2026-06-04T15:59:34+00:00
Issue: [CYBA-455](/CYBA/issues/CYBA-455) для [CYBA-451](/CYBA/issues/CYBA-451)
Repo: `VPNBussiness-main`
Branch: `codex/cyba-386-worktree-snapshot`
Commit: `116407a`
Raw logs: `qa-artifacts/CYBA-455/logs/`

## Итог

FAIL для release-readiness. Колляция выполнена: запущен 31 automated gate/sub-gate, raw evidence сохранен. Зеленые build/lint gates есть, но релизный набор заблокирован failing unit suites, backend lint/pytest collection, conformance failures, generated API type drift и отсутствующим/неподготовленным local Redis/settings для части backend conformance.

## Environment

- Node: `v24.14.1`
- npm: `11.11.0`
- Python: `3.13.13`
- Backend venv: `backend/.venv`
- Dirty worktree существовал до QA run; это влияет на интерпретацию результатов.
- Staging smoke не запускался: нет approved non-production URL/credentials в issue context, production запрещен.

## Зеленые gates

- `npm run lint -w frontend` -> PASS, `01-frontend-lint.log`
- `npm run build -w frontend` -> PASS, `03-frontend-build.log`
- `npm run lint -w admin` -> PASS, `04-admin-lint.log`
- `npm run test:run -w admin` -> PASS, `05-admin-test-run.log`
- `npm run build -w admin` -> PASS, `06-admin-build.log`
- `npm run lint -w partner` -> PASS, `07-partner-lint.log`
- `npm run build -w partner` -> PASS, `09-partner-build.log`
- `npm run conformance:miniapp-launch:frontend` -> PASS, 5 files / 27 tests, `21-conformance-miniapp-launch-frontend.log`
- `npm run conformance:miniapp-launch:admin` -> PASS, 2 files / 13 tests, `22-conformance-miniapp-launch-admin.log`
- `npm run conformance:miniapp-launch:assets` -> PASS, `23-conformance-miniapp-launch-assets.log`
- `npm run conformance:partner-observability:partner` -> PASS, includes partner build + Sentry HTTP smoke `http://127.0.0.1:3201/api/observability/sentry-contract`, `24-conformance-partner-observability-partner.log`
- `npm run conformance:partner-observability:admin` -> PASS, includes admin build + Sentry HTTP smoke `http://127.0.0.1:3200/api/observability/sentry-contract`, `25-conformance-partner-observability-admin.log`
- `npm run conformance:customer-growth-reporting-governance:admin` -> PASS, targeted admin tests/lint/build, `30-conformance-customer-growth-reporting-governance-admin.log`

## Failing gates

- `npm run test:run -w frontend` -> FAIL, 3 failed files / 5 failed tests out of 1217. Failures: legacy checkout contract missing `410`, `TerminalHeader` missing `QueryClientProvider`, dashboard nav expected list excludes `/messages`. See `02-frontend-test-run.log`.
- `npm run test:run -w partner` -> FAIL, 22 failed files / 60 failed tests out of 686. Dominant failure class: React hook dispatcher null (`useState`, `useRef`, `useCallback`, `useSyncExternalStore`) in partner component/hook tests. See `08-partner-test-run.log`.
- `backend/.venv/bin/python -m ruff check backend` -> FAIL, 49 lint errors. Classes include import sorting, line length, `S608`, `UP007`, `UP035`. See `10-backend-ruff.log`.
- `backend/.venv/bin/python -m pytest backend` -> FAIL without env, required settings missing: `remnawave_token`, `jwt_secret`, `cryptobot_token`. See `11-backend-pytest.log`.
- `backend/.venv/bin/python -m pytest backend` with dummy env -> FAIL during collection: import file mismatch for duplicate `test_client.py` and `test_routes.py` module basenames. See `12-backend-pytest-dummy-env.log`.
- `npm run conformance:partner-admin` -> FAIL without env on required backend settings. See `13-conformance-partner-admin.log`.
- `npm run conformance:partner-admin` with dummy env -> FAIL, backend e2e pack 4 failed / 1 passed, all login assertions `401 != 200`. See `14-conformance-partner-admin-dummy-env.log`.
- `npm run conformance:partner-observability` with dummy env -> FAIL, backend observability 4 failed / 6 passed, all login assertions `401 != 200`. See `15-conformance-partner-observability.log`.
- `npm run conformance:miniapp-launch` -> FAIL, backend Mini App tests 4 failed / 24 passed. Failures: mock/session `object` lacks `execute`, `Depends` lacks `auth_realm`. See `16-conformance-miniapp-launch.log`.
- `npm run conformance:customer-growth-notifications` -> FAIL, backend 4 failed / 9 passed due `redis.exceptions.ConnectionError` to `localhost:6379`. See `17-conformance-customer-growth-notifications.log`.
- `npm run conformance:customer-growth-reporting-governance` -> FAIL, backend 1 failed / 3 passed due `redis.exceptions.ConnectionError` to `localhost:6379`. See `18-conformance-customer-growth-reporting-governance.log`.
- `npm run conformance:partner-admin:admin` -> FAIL, `admin/src/lib/api/generated/types.ts` drift after regeneration; removed `require_mfa_for_workspace` and `prefer_passkeys`. See `19-conformance-partner-admin-admin.log`.
- `npm run conformance:partner-admin:partner` -> FAIL, same generated type drift in `partner/src/lib/api/generated/types.ts`. See `20-conformance-partner-admin-partner.log`.
- `npm run conformance:partner-observability:assets` -> FAIL after `promtool/amtool` PASS; backend asset contract pytest blocked by missing required settings. See `26-conformance-partner-observability-assets.log`.
- `npm run conformance:customer-growth-notifications:frontend` -> FAIL, `frontend/src/lib/api/generated/types.ts` drift after regeneration, including added notification/messaging API types and removal of legacy checkout `410`. See `27-conformance-customer-growth-notifications-frontend.log`.
- `npm run conformance:customer-growth-notifications:admin` -> FAIL, generated type drift in `admin/src/lib/api/generated/types.ts`. See `28-conformance-customer-growth-notifications-admin.log`.
- `npm run conformance:customer-growth-notifications:assets` -> FAIL, backend asset contract pytest blocked by missing required settings. See `29-conformance-customer-growth-notifications-assets.log`.
- `npm run conformance:customer-growth-reporting-governance:assets` -> FAIL after `promtool/amtool` PASS and frontend type sync PASS; partner generated type drift remains. See `31-conformance-customer-growth-reporting-governance-assets.log`.

## Additional Evidence

- Automated observability/browser-style evidence produced under `evidence/` during conformance execution: 54 files including screenshots and JSON route/smoke artifacts.
- `qa-artifacts/CYBA-455/logs/` contains 31 raw command logs with command, start/end time, timing, and `EXIT_STATUS`.
- I restored unintended generated side effects to `frontend/src/lib/api/generated/types.ts`; `admin` and `partner` generated type files were already dirty before this heartbeat and remain dirty.

## Release Risk

- Automated release-readiness is not green.
- The most actionable blockers are frontend/partner test failures, backend lint/pytest collection, missing conformance env/service setup, auth/login failures in partner/admin e2e conformance, and generated OpenAPI/type drift.
- No production go/no-go can be inferred from this evidence.
