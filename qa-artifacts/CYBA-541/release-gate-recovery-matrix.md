# CYBA-541 Release Gate Recovery Ownership And Rerun Matrix

Date: 2026-06-05  
Issue: [CYBA-541](/CYBA/issues/CYBA-541) for [CYBA-540](/CYBA/issues/CYBA-540)  
Source gate: `qa-artifacts/CYBA-455/release-readiness-gate-summary.md`  
Historical result: `FAIL` on 2026-06-04T15:59:34+00:00  
Release decision: `NO-GO` until every required gate below has a green rerun or an explicit Board-approved scope-out.

## Acceptance Rule

`CYBA-550` may start final revalidation only after all upstream recovery issues are terminal green:

- [CYBA-541](/CYBA/issues/CYBA-541): this ownership/rerun matrix is complete.
- [CYBA-542](/CYBA/issues/CYBA-542): dirty worktree, branches, MRs and generated/runtime artifacts are separated.
- [CYBA-543](/CYBA/issues/CYBA-543): backend lint, pytest, env, Redis/Valkey and backend conformance blockers are green.
- [CYBA-544](/CYBA/issues/CYBA-544): canonical OpenAPI and generated API type drift are resolved.
- [CYBA-545](/CYBA/issues/CYBA-545): auth/session/security regression review is complete.
- [CYBA-546](/CYBA/issues/CYBA-546): safe customer fixture/business-flow evidence is complete.
- [CYBA-547](/CYBA/issues/CYBA-547): safe partner fixture/business-flow evidence is complete.
- [CYBA-548](/CYBA/issues/CYBA-548): payment/VPN sandbox policy is accepted.
- [CYBA-549](/CYBA/issues/CYBA-549): a11y/i18n/responsive polish is verified.
- [CYBA-551](/CYBA/issues/CYBA-551): customer frontend unit release gate is green.
- [CYBA-552](/CYBA/issues/CYBA-552): partner unit suite release gate is green.

Any failing gate remains release-blocking unless the Board explicitly approves a scope-out. Production deploy, production secrets, production customer/payment data, direct push to `main`, merge and production VPN/provisioning operations remain forbidden by [CYBA-540](/CYBA/issues/CYBA-540).

## Owner Matrix

| Gate family | Historical CYBA-455 failure evidence | Recovery owner | Required blocker issue | Exit evidence for CYBA-550 |
| --- | --- | --- | --- | --- |
| Release orchestration | `release-readiness-gate-summary.md` needed owner/rerun matrix | Orion CTO | [CYBA-541](/CYBA/issues/CYBA-541) | This file and issue comment; first-class blocker update for [CYBA-550](/CYBA/issues/CYBA-550) must be applied by its assignee because Paperclip least-privilege rules reject cross-assignee mutation |
| Worktree/MR hygiene | Dirty worktree existed before QA run; generated/runtime artifacts could create false failures | Atlas Platform & Remnawave NodeOps Engineer | [CYBA-542](/CYBA/issues/CYBA-542) | Branch/MR plan, excluded artifacts, `git status --short`, CI order |
| Customer frontend unit suite | `02-frontend-test-run.log`: legacy checkout `410`, `TerminalHeader` missing `QueryClientProvider`, nav inventory unexpected `/messages`; current rerun also shows MSW login token regression | Neon Customer Frontend Engineer | [CYBA-551](/CYBA/issues/CYBA-551) | Targeted test logs and full `npm run test:run -w frontend` PASS |
| Partner unit suite | `08-partner-test-run.log`: 22 failed files / 60 failed tests, dominated by React hook dispatcher/provider failures | Prism Admin Partner Frontend Engineer | [CYBA-552](/CYBA/issues/CYBA-552) | Representative harness test logs and full `npm run test:run -w partner` PASS |
| Backend lint and pytest collection | `10-backend-ruff.log`: 49 lint errors; `12-backend-pytest-dummy-env.log`: duplicate pytest module basenames/import mismatch | Helio Backend API Engineer | [CYBA-543](/CYBA/issues/CYBA-543) | `ruff check backend` PASS and `pytest backend` PASS with safe test env |
| Backend settings/env/Redis | `11-backend-pytest.log`: missing required settings; `17`/`18` conformance logs: Redis connection refused | Helio Backend API Engineer | [CYBA-543](/CYBA/issues/CYBA-543) | documented safe env, local Redis/Valkey or approved mock, green backend conformance logs |
| Partner/admin backend auth conformance | `14-conformance-partner-admin-dummy-env.log` and `15-conformance-partner-observability.log`: backend login assertions `401 != 200` | Helio Backend API Engineer, SecurityEngineer for auth-sensitive changes | [CYBA-543](/CYBA/issues/CYBA-543), [CYBA-545](/CYBA/issues/CYBA-545) | green backend conformance plus Security handoff if auth/session behavior changed |
| Mini App backend conformance | `16-conformance-miniapp-launch.log`: mock/session `object` lacks `execute`, `Depends` lacks `auth_realm` | Helio Backend API Engineer | [CYBA-543](/CYBA/issues/CYBA-543), [CYBA-546](/CYBA/issues/CYBA-546) | `npm run conformance:miniapp-launch` PASS or split sub-gates PASS |
| Canonical OpenAPI/generated API types | `19`, `20`, `27`, `28`, `31` logs: frontend/admin/partner generated type drift | Vega Backend Engineer | [CYBA-544](/CYBA/issues/CYBA-544) | canonical OpenAPI export, generated type sync, clean dirty diff after regeneration |
| Auth/session/passkey/CSRF regression risk | Dirty worktree includes auth/session/passkey/CSRF/API proxy changes; partner/admin login failures touch auth | SecurityEngineer | [CYBA-545](/CYBA/issues/CYBA-545) | sanitized security evidence, no-secret scan, explicit signoff or changes-requested |
| Customer fixtures/business flows | Customer growth notification/reporting gates require safe backend data and Redis/test state | Helio Backend API Engineer | [CYBA-546](/CYBA/issues/CYBA-546) | safe customer fixture pack, seed/reset notes, UI/API evidence |
| Partner fixtures/business flows | Partner/admin conformance requires partner states, roles, login and workspace fixtures | Prism Admin Partner Frontend Engineer | [CYBA-547](/CYBA/issues/CYBA-547) | safe partner fixture pack, role-boundary evidence, partner flow evidence |
| Payment/VPN policy | Legacy checkout, wallet/payment/VPN states are high-risk and cannot use real capture/provisioning | Ledger Billing & Subscription Risk Analyst | [CYBA-548](/CYBA/issues/CYBA-548) | accepted sandbox/no-real-capture/no-secret policy |
| A11y/i18n/responsive | P2 backlog: Arabic/Russian copy, mobile login clipping, focus indication, RTL risk | Luma Localization Translator | [CYBA-549](/CYBA/issues/CYBA-549) | screenshots and locale/RTL/focus evidence |
| Final release revalidation | CYBA-455 automated release-readiness was not green | qa-lead-flow-mapper | [CYBA-550](/CYBA/issues/CYBA-550) | new release-readiness summary, raw logs, Scribe evidence, Astra acceptance recommendation |

## Rerun Order

1. `CYBA-542` preflight: isolate dirty worktree, branch/MR strategy, generated/runtime artifacts and evidence outputs. Do not rerun final gates against an ambiguous tree.
2. `CYBA-544` contract sync: choose canonical backend OpenAPI, regenerate `frontend`, `admin` and `partner` API types, prove clean regeneration diff.
3. `CYBA-543` backend foundation: fix `ruff`, pytest collection, safe dummy settings, Redis/Valkey dependency and backend auth/conformance failures.
4. `CYBA-551` and `CYBA-552` frontend/partner unit suites: recover local test harnesses and real assertions after contract/backend fixes land.
5. `CYBA-545` security review: validate auth/session/passkey/CSRF/cross-realm changes after code fixes are stable.
6. `CYBA-546`, `CYBA-547` and `CYBA-548` fixture/policy work: validate customer, partner, payment and VPN evidence can run without production data/secrets.
7. `CYBA-549` a11y/i18n/responsive verification: run after UI copy/layout changes settle.
8. `CYBA-550` final rerun: execute the full automated matrix, collect raw logs and publish a new `release-readiness-gate-summary.md`.

## Command Matrix For CYBA-550

Use a fresh timestamped directory, for example `qa-artifacts/CYBA-550/rerun-YYYYMMDDTHHMMSSZ/logs/`. Every command log must include command, start time, end time, duration and `EXIT_STATUS`. Preserve raw stdout/stderr. Do not sanitize by deleting failure details; sanitize only secrets/tokens/customer data.

### Preflight

| Step | Command | Required result | Log path |
| --- | --- | --- | --- |
| Git state | `git status --short` | only intended release candidate changes and evidence artifacts are present | `00-git-status.log` |
| Node/npm/Python versions | `node --version`, `npm --version`, `python --version`, `backend/.venv/bin/python --version` | versions recorded | `00-runtime-versions.log` |
| Backend API artifact check | `backend/.venv/bin/python backend/scripts/export_openapi.py` with safe dummy env | `backend/docs/api/openapi.json` remains in sync | `00-openapi-export.log` |
| Generated API type check | `npm run generate:api-types -w frontend`, `npm run generate:api-types -w admin`, `npm run generate:api-types -w partner` | generated type files remain unchanged after regeneration | `00-generated-types.log` |

### Workspace Gates

| Historical CYBA-455 log | Command | Owner gate | Required result |
| --- | --- | --- | --- |
| `01-frontend-lint.log` | `npm run lint -w frontend` | [CYBA-551](/CYBA/issues/CYBA-551) | PASS |
| `02-frontend-test-run.log` | `NEXT_TELEMETRY_DISABLED=1 CI=1 npm run test:run -w frontend` | [CYBA-551](/CYBA/issues/CYBA-551), [CYBA-544](/CYBA/issues/CYBA-544) | PASS |
| `03-frontend-build.log` | `NEXT_TELEMETRY_DISABLED=1 npm run build -w frontend` | [CYBA-551](/CYBA/issues/CYBA-551) | PASS |
| `04-admin-lint.log` | `npm run lint -w admin` | [CYBA-544](/CYBA/issues/CYBA-544), [CYBA-545](/CYBA/issues/CYBA-545) | PASS |
| `05-admin-test-run.log` | `NEXT_TELEMETRY_DISABLED=1 CI=1 npm run test:run -w admin` | [CYBA-544](/CYBA/issues/CYBA-544), [CYBA-545](/CYBA/issues/CYBA-545) | PASS |
| `06-admin-build.log` | `NEXT_TELEMETRY_DISABLED=1 npm run build -w admin` | [CYBA-544](/CYBA/issues/CYBA-544) | PASS |
| `07-partner-lint.log` | `npm run lint -w partner` | [CYBA-552](/CYBA/issues/CYBA-552), [CYBA-547](/CYBA/issues/CYBA-547) | PASS |
| `08-partner-test-run.log` | `NEXT_TELEMETRY_DISABLED=1 CI=1 npm run test:run -w partner` | [CYBA-552](/CYBA/issues/CYBA-552), [CYBA-547](/CYBA/issues/CYBA-547) | PASS |
| `09-partner-build.log` | `NEXT_TELEMETRY_DISABLED=1 npm run build -w partner` | [CYBA-552](/CYBA/issues/CYBA-552) | PASS |
| `10-backend-ruff.log` | `backend/.venv/bin/python -m ruff check backend` | [CYBA-543](/CYBA/issues/CYBA-543) | PASS |
| `11`/`12-backend-pytest*.log` | `SKIP_TEST_DB_BOOTSTRAP=1 REMNAWAVE_TOKEN=<dummy> JWT_SECRET=<dummy>=32+ CRYPTOBOT_TOKEN=<dummy> DATABASE_URL=<local test> REDIS_URL=<local test> backend/.venv/bin/python -m pytest backend` | [CYBA-543](/CYBA/issues/CYBA-543), [CYBA-545](/CYBA/issues/CYBA-545) | PASS without collection errors |

### Conformance Gates

| Historical CYBA-455 log | Command | Owner gate | Required result |
| --- | --- | --- | --- |
| `13`/`14`/`19`/`20` | `npm run conformance:partner-admin` and split `:backend`, `:admin`, `:partner` when triaging | [CYBA-543](/CYBA/issues/CYBA-543), [CYBA-544](/CYBA/issues/CYBA-544), [CYBA-547](/CYBA/issues/CYBA-547) | PASS |
| `15`/`24`/`25`/`26` | `npm run conformance:partner-observability` and split `:backend`, `:partner`, `:admin`, `:assets` when triaging | [CYBA-543](/CYBA/issues/CYBA-543), [CYBA-544](/CYBA/issues/CYBA-544) | PASS |
| `16`/`21`/`22`/`23` | `npm run conformance:miniapp-launch` and split `:backend`, `:frontend`, `:admin`, `:assets` when triaging | [CYBA-543](/CYBA/issues/CYBA-543), [CYBA-546](/CYBA/issues/CYBA-546) | PASS |
| `17`/`27`/`28`/`29` | `npm run conformance:customer-growth-notifications` and split sub-gates when triaging | [CYBA-543](/CYBA/issues/CYBA-543), [CYBA-544](/CYBA/issues/CYBA-544), [CYBA-546](/CYBA/issues/CYBA-546) | PASS |
| `18`/`30`/`31` | `npm run conformance:customer-growth-reporting-governance` and split `:backend`, `:admin`, `:assets` when triaging | [CYBA-543](/CYBA/issues/CYBA-543), [CYBA-544](/CYBA/issues/CYBA-544), [CYBA-546](/CYBA/issues/CYBA-546) | PASS |

## Artifact Paths

Recommended final evidence layout:

- `qa-artifacts/CYBA-550/rerun-YYYYMMDDTHHMMSSZ/logs/`: raw command logs with exit statuses.
- `qa-artifacts/CYBA-550/rerun-YYYYMMDDTHHMMSSZ/subgate-status.tsv`: one row per gate with command, owner issue, status, log path.
- `qa-artifacts/CYBA-550/release-readiness-gate-summary.md`: final summary replacing historical `CYBA-455` evidence for the current release candidate.
- `qa-artifacts/CYBA-550/no-secret-scan.log`: evidence that stored logs/screenshots do not contain tokens, cookies, private keys, production secrets or customer data.
- `docs/evidence/...`: only sanitized browser/API evidence produced by the conformance scripts and manual QA.

## Go/No-Go Rules

- `GO` is allowed only when every required automated gate and required manual/security/a11y evidence gate is green.
- `NO-GO` remains mandatory if any P0/P1 issue is open, any required gate is failing, generated API artifacts drift after regeneration, backend pytest collection fails, auth/session/security review is missing, or staging credentials/URLs are absent for required staging smoke.
- A scoped-out gate requires explicit Board approval linked to the issue. Without that approval it is still failing for release readiness.
- Production readiness cannot be inferred from the historical [CYBA-455](/CYBA/issues/CYBA-455) run. `CYBA-550` must publish a fresh summary.

## Context7

Context7 docs checked: N/A - this heartbeat created a release/QA coordination artifact and Paperclip child issues only; no code, package, framework, SDK, build-tool configuration or library API behavior was written or changed. Attempted cross-assignee blocker/comment updates on [CYBA-550](/CYBA/issues/CYBA-550) were rejected by Paperclip least-privilege policy.
