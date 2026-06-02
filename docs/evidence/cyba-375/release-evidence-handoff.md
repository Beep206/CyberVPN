# Release evidence handoff: [CYBA-360](/CYBA/issues/CYBA-360) important notifications

Date: 2026-06-01 UTC
Owner: Scribe Release Docs & Evidence Manager
Source issue: [CYBA-375](/CYBA/issues/CYBA-375)

## Executive summary

Status: ready for Board/CTO review for the approved in-site notification scope.

- All direct blockers of [CYBA-375](/CYBA/issues/CYBA-375) are `done`: [CYBA-367](/CYBA/issues/CYBA-367), [CYBA-368](/CYBA/issues/CYBA-368), [CYBA-369](/CYBA/issues/CYBA-369), [CYBA-370](/CYBA/issues/CYBA-370), [CYBA-371](/CYBA/issues/CYBA-371), [CYBA-372](/CYBA/issues/CYBA-372), [CYBA-373](/CYBA/issues/CYBA-373), [CYBA-374](/CYBA/issues/CYBA-374).
- The release evidence covers backend notification REST foundations, realtime sync/recovery, local worker fanout, customer notification UX, admin broadcast operations UI, localization, security/privacy review, and QA retest.
- [CYBA-374](/CYBA/issues/CYBA-374) initially found a mobile clipping blocker and delegated it to [CYBA-385](/CYBA/issues/CYBA-385). The retest after [CYBA-385](/CYBA/issues/CYBA-385) is `PASS`.
- No production deploy, production secrets, real customer/payment data, external Telegram/email/FCM/APNs delivery, VPN provisioning, or Remnawave production adapter work is evidenced or approved here.
- MR and pipeline links are not available. Multiple child handoffs explicitly record that no MR/pipeline was created or run from the heartbeat. The local evidence environment is branch `ai/cyba-244/w15-final-package`, commit `0b509f6`.

## Reviewer decision frame

Recommended decision for the current non-production in-site notification foundation: accept the evidence pack as complete for [CYBA-360](/CYBA/issues/CYBA-360) handoff.

Do not treat this as approval for:

- production external push or broad-audience automation;
- payment/auth/security/VPN provisioning/Remnawave trigger adapters;
- production deployment;
- production secrets or customer/payment data access.

Before production broad-audience or external-push rollout, [CYBA-373](/CYBA/issues/CYBA-373) requires server-side idempotency for broadcast create, backend-enforced broad-audience confirmation/approval, and explicit Board approval for sensitive trigger adapters.

## Traceability

| Area | Evidence source | Local artifact |
|---|---|---|
| Parent scope | [CYBA-360](/CYBA/issues/CYBA-360) | N/A |
| Release handoff | [CYBA-375](/CYBA/issues/CYBA-375) | `docs/evidence/cyba-375/release-evidence-handoff.md` |
| Backend REST foundation | [CYBA-367 completion](/CYBA/issues/CYBA-367#comment-024c51d3-8245-4ea2-971e-4a06c866a647) | `backend/tests/contract/test_site_notifications_openapi_contract.py`, `backend/tests/integration/test_site_notifications_api.py` |
| Realtime sync/recovery | [CYBA-368 completion](/CYBA/issues/CYBA-368#comment-a9735ce2-0247-4d59-be8d-f5f413b5849a) | `docs/evidence/cyba-368/realtime-delivery-sync-reliability.md` |
| Worker fanout | [CYBA-369 completion](/CYBA/issues/CYBA-369#comment-a5c6e4e3-b6bd-4f48-84b3-aabd739933be) | `services/task-worker/tests/unit/tasks/test_messaging_outbox.py` |
| Customer UX | [CYBA-370 final handoff](/CYBA/issues/CYBA-370#comment-d3624688-6906-4dfa-b237-13fd59fc2b6a) | `frontend/src/features/messaging/components/__tests__/CustomerMessagingClient.test.tsx` |
| Admin broadcast UI | [CYBA-371 completion](/CYBA/issues/CYBA-371#comment-c43aa308-b7e8-4f74-80c0-e05c05a9b483) | `admin/src/features/messaging/components/__tests__/messaging-console.test.tsx` |
| Localization | [CYBA-372 final handoff](/CYBA/issues/CYBA-372#comment-47459e78-2af9-4c92-9c66-6dc318b485b4), [localization-report](/CYBA/issues/CYBA-372#document-localization-report) | `frontend/messages/*/messaging.json`, `admin/messages/*/messaging.json` |
| Security/privacy | [CYBA-373 security approval](/CYBA/issues/CYBA-373#comment-dcc23c2e-beff-4c8c-9cf3-f2891f9d9392) | N/A, review evidence in issue thread |
| QA and screenshots | [CYBA-374 QA retest](/CYBA/issues/CYBA-374#comment-3be23382-ebcd-4f8c-be1f-55fa1da8fd74) | `docs/evidence/cyba-374/qa-report.md`, `docs/evidence/cyba-374/screenshots/` |

## Verification matrix

| Issue | Surface | Evidence result | Context7 line | Residual risk |
|---|---|---|---|---|
| [CYBA-367](/CYBA/issues/CYBA-367) | Backend notification foundation and REST hardening | `pytest --no-cov tests/contract/test_site_notifications_openapi_contract.py tests/integration/test_site_notifications_api.py -q` -> `5 passed`; ruff targeted files -> `All checks passed!`; migration `py_compile` -> passed; `git diff --check` -> passed. | Context7 MCP and `ctx7` quota exceeded; fallback official FastAPI route/header/status, Pydantic v2 validators, SQLAlchemy asyncio/AsyncSession docs checked. | Alembic head coordination may be needed before merge/release because parallel branches exist; no full workspace build/test. |
| [CYBA-368](/CYBA/issues/CYBA-368) | Realtime delivery and sync recovery | Backend realtime/integration slice -> `20 passed in 25.15s`; targeted ruff -> `All checks passed!`. | Context7 MCP and `ctx7` quota exceeded; fallback official FastAPI WebSocket/StreamingResponse docs and repo realtime specs/tests checked. | Browser delivery remains best-effort; authoritative recovery is REST sync after connect/reconnect/`sync_required`/cursor gap. |
| [CYBA-369](/CYBA/issues/CYBA-369) | Local task-worker notification fanout | Worker unit smoke -> `5 passed in 1.21s`; targeted ruff -> `All checks passed!`; duplicate/idempotency and retry/dead-letter behavior covered with fake data. | N/A: read-only verification heartbeat, no code/library behavior changed. | No TaskIQ scheduler/Redis/Postgres integration run; no external delivery enabled. |
| [CYBA-370](/CYBA/issues/CYBA-370) | Customer notification UX | Frontend focused suite -> `2 files / 12 tests passed`; frontend lint -> passed; i18n pretest/prelint generated 39 locale bundles. | Context7 MCP/`ctx7` quota unavailable; fallback official Testing Library, user-event, Vitest, next-intl, TanStack Query, React docs checked in implementation handoffs. | No full build; browser screenshot QA delegated to [CYBA-374](/CYBA/issues/CYBA-374). |
| [CYBA-371](/CYBA/issues/CYBA-371) | Admin broadcast operations UI | Admin focused suite -> `3 files / 15 tests passed`; targeted admin lint -> passed; admin conformance command -> passed, including API type sync, `growth-admin.test.ts` 24 tests, full admin ESLint and admin build/static pages. | Context7 quota exceeded; fallback official Next.js, React, next-intl, TanStack Query, Testing Library user-event, Vitest, MSW docs checked. | No MR/push; UI local session history only because backend list endpoint is absent; some recipient counts are operator-provided estimates. |
| [CYBA-372](/CYBA/issues/CYBA-372) | Localization | `frontend` i18n generation -> 39 bundles; `admin` i18n generation -> 2 bundles; source/generated parity: missing 0, extra 0, placeholder mismatch 0; hardcoded legacy mock labels not found. | `next-intl` Context7/`ctx7` quota exhausted; fallback official next-intl JSON messages/ICU/RTL docs checked. | Browser/RTL screenshot QA was outside localization gate and covered by [CYBA-374](/CYBA/issues/CYBA-374) only for selected surfaces. |
| [CYBA-373](/CYBA/issues/CYBA-373) | Security and privacy review | Backend security slice -> `42 passed in 30.53s`; admin tests -> `15 passed`; frontend tests -> `12 passed`; worker tests -> `5 passed in 1.06s`; review approved current non-production scope. | N/A: review-only heartbeat, no code/config/library behavior changed. | Server-side broadcast broad-audience guardrails/idempotency remain production hardening expectations before rollout. |
| [CYBA-374](/CYBA/issues/CYBA-374) | QA evidence and screenshots | Cross-surface QA: backend REST/realtime/security -> `52 passed in 30.34s`; frontend -> `2 files / 12 tests passed`; admin -> `3 files / 15 tests passed`; worker -> `5 passed in 1.08s`; retest after [CYBA-385](/CYBA/issues/CYBA-385): frontend component -> `1 file / 6 tests passed`; Playwright bounds passed on `390x844` and `1440x900`. | N/A: QA verification only, no code/config/library behavior changed. | Browser checks used `DEV_BYPASS_AUTH=true`, synthetic route mocks and disabled `EventSource`; not a substitute for full deployed-environment validation. |

## Screenshot artifacts

Saved under `docs/evidence/cyba-374/screenshots/`:

- `customer-notification-desktop.png`
- `customer-notification-mobile.png`
- `admin-broadcast-preview-desktop.png`
- `admin-broadcast-support-readonly-mobile.png`
- `customer-notification-mobile-retest.png`
- `customer-notification-desktop-retest.png`

Retest evidence from [CYBA-374](/CYBA/issues/CYBA-374):

- Mobile viewport `390x844`: dialog box `x=16`, `width=358`, right edge `374 <= 390`; title/body/read/dismiss controls visible and inside viewport.
- Desktop viewport `1440x900`: dialog box `x=544.140625`, `width=384`, right edge `928.140625 <= 1440`; title/body/read/dismiss controls visible and inside viewport.

## MR and pipeline status

No MR URL or pipeline URL is available in the collected evidence.

Evidence limitations from child handoffs:

- [CYBA-367](/CYBA/issues/CYBA-367): "MR/pipeline не создавал и не запускал из heartbeat."
- [CYBA-369](/CYBA/issues/CYBA-369): "Не делал commit, push, MR или pipeline запуск."
- [CYBA-370](/CYBA/issues/CYBA-370): "Не создавал MR/commit и не push."
- [CYBA-371](/CYBA/issues/CYBA-371): "Не создавал MR и не push-ил."

Current local branch evidence gathered by Scribe:

- Branch: `ai/cyba-244/w15-final-package`
- Commit: `0b509f6`
- Worktree: broad dirty/untracked Stage 2 changes pre-existed this heartbeat; unrelated changes were not reverted.

## Commands run by Scribe for this evidence pack

- `sed -n '1,220p' /home/beep/.local/lib/node_modules/paperclipai/node_modules/@paperclipai/server/skills/paperclip/SKILL.md`
- `sed -n '220,520p' /home/beep/.local/lib/node_modules/paperclipai/node_modules/@paperclipai/server/skills/paperclip/SKILL.md`
- `printf 'TASK=%s\nAGENT=%s\nCOMPANY=%s\nAPI=%s\nRUN=%s\nWAKE_REASON=%s\n' ...` without printing `PAPERCLIP_API_KEY`
- `git status --short`
- `find .. -maxdepth 2 -name AGENTS.md -o -name CLAUDE.md`
- `curl -fsS ... /api/issues/$PAPERCLIP_TASK_ID/heartbeat-context | jq '.'`
- `sed -n '1,220p' AGENTS.md`
- `find docs -maxdepth 3 -type f | sort | sed -n '1,240p'`
- `find docs/evidence -maxdepth 2 -type f | sort | sed -n '1,240p'`
- `rg -n "CYBA-36[0-9]|CYBA-37[0-5]|notifications|notification|уведом" docs admin frontend backend services/task-worker -g '*.md' -g '*.txt' -g '*.json'`
- `curl -fsS ... /api/issues/{blocker}/comments | jq ...` for direct blockers
- `curl -fsS ... /api/issues/e8471003-9e50-4e11-ba33-7f60d8c9ce35/comments | jq '.'`
- `curl -fsS ... /api/issues/{issue}/documents | jq ...` for [CYBA-375](/CYBA/issues/CYBA-375), [CYBA-372](/CYBA/issues/CYBA-372), [CYBA-374](/CYBA/issues/CYBA-374), [CYBA-368](/CYBA/issues/CYBA-368)
- `find docs/evidence/cyba-374 docs/evidence/cyba-368 docs/api docs/realtime -maxdepth 3 -type f ...`
- `sed -n '1,240p' docs/evidence/cyba-374/qa-report.md`
- `sed -n '1,240p' docs/evidence/cyba-368/realtime-delivery-sync-reliability.md`
- `ls -1 docs/api | rg 'notification|messaging'`
- `sed -n '1,220p' docs/api/2026-05-31-messaging-bounded-context-and-api-contracts-rfc.md`
- `git branch --show-current`
- `git rev-parse --short HEAD`
- `find docs/evidence/cyba-374 -maxdepth 3 -type f -printf '%p %s bytes\n' | sort`

## What Scribe did not do

- Did not access production secrets, production customer/payment data, or production systems.
- Did not deploy.
- Did not push, commit, create MR, or run a pipeline.
- Did not change production code.
- Did not rerun the full workspace build/typecheck/test suite; this handoff compiles existing issue evidence and runs only documentation-level verification.
- Did not enable scheduled autonomous work.

## Open risks and release gates

- Production external push, sensitive trigger adapters, and Remnawave/VPN/payment/auth/security-derived notification triggers remain deferred until separate Board-approved issues.
- Full deployed-environment validation remains a future release/rehearsal gate; current browser QA used synthetic local mocks and development auth bypass.
- Dirty worktree coordination remains necessary before MR creation because multiple Stage 2 tasks left broad modified/untracked files.
- Alembic migration head coordination may be required before merge because backend notification work landed alongside other active migration work.
- Broadcast v1 has high-privilege RBAC and rate limits, but server-side idempotency and backend-enforced broad-audience confirmation/approval are required before production broad-audience rollout.
