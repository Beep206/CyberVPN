# CYBA-457 partner portal findings

Дата: `2026-06-04`

## Summary

Partner portal manual QA resumed after [CYBA-452](/CYBA/issues/CYBA-452) moved to `GO - local-stage synthetic QA` and [CYBA-464](/CYBA/issues/CYBA-464) was completed.

Current result:

- `MF-PART-001` protected-route `SYSTEM FAILURE` is retested as fixed in local-dev portal preview.
- Public partner login pages render in desktop EN and mobile RU.
- Anonymous protected routes redirect to login without global crash.
- `DEV_BYPASS_AUTH=true` simulated partner owner/analyst/restricted routes render without `SYSTEM FAILURE`.
- Real synthetic partner owner login reaches `2FA complete` success through same-origin API, but no usable session cookies remain after completion; protected routes redirect back to login with `401 /api/v1/auth/session`. This blocks canonical authenticated partner business-flow QA.
- Latest retest after [CYBA-509](/CYBA/issues/CYBA-509) was marked `done` still fails with the same `MF-PART-002` symptom: `POST /api/auth/2fa/complete` returns `200`, `GET /api/v1/auth/session` remains `401`, and no realm session cookie names remain after completion.
- Latest retest after [CYBA-519](/CYBA/issues/CYBA-519) was marked `done` still fails, with an earlier first failing transition: `POST /api/auth/2fa/complete` now returns `401`, browser cookies after completion are `[]`, `GET /api/v1/auth/session` remains `401`, and protected partner routes still redirect to login.
- Latest retest after [CYBA-495](/CYBA/issues/CYBA-495) passes for `MF-PART-002`: UI login reaches `2fa=true`, `POST /api/auth/2fa/complete` returns `200`, `/api/v1/auth/session` returns `200`, and protected owner routes no longer redirect to login.
- Последний path-matched ретест после [CYBA-522](/CYBA/issues/CYBA-522) подтверждает, что `MF-PART-002` исправлен: `POST /api/auth/2fa/complete` возвращает `200`, `/api/v1/auth/session` возвращает `200`, root-origin cookie probe пустой как ожидается для `Path=/api`, а path-matched probe под `/api/v1/auth/session` видит `partner_access_token` и `partner_refresh_token`.
- Historical blocker: authenticated partner route shells rendered while canonical workspace/bootstrap APIs returned `404`; this was tracked as `MF-PART-003`.
- Latest retest after [CYBA-525](/CYBA/issues/CYBA-525) passes for `MF-PART-003`: base partner workspace/bootstrap/notification endpoints return `200` with `X-Auth-Realm: partner`; UI route network also shows these endpoints at `200`.
- Historical blocker: workspace-scoped reseller voucher batches, passkey policy/compliance, support tickets, and creative approvals previously failed under `MF-PART-004`.
- Fresh [CYBA-457](/CYBA/issues/CYBA-457) retest after [CYBA-532](/CYBA/issues/CYBA-532) passes for `MF-PART-004`: targeted direct probes for `reseller-voucher-batches`, passkey policy/compliance, `support/tickets?limit=50`, and `creative-approvals` all return `200`; all 12 authenticated owner route checks have no targeted backend failures.
- Current full read-only partner portal QA status: `pass` for auth/session, base canonical partner endpoints, workspace-scoped read APIs, and authenticated owner route coverage. Remaining not-tested areas are safety/fixture limitations, not active app blockers.

## Bugs

### MF-PART-004 - Workspace-scoped reseller/passkey partner APIs fail after canonical bootstrap unblock

- Type: `bug`
- Severity: `P1`
- Status: retested fixed after [CYBA-457](/CYBA/issues/CYBA-457) final post-[CYBA-532](/CYBA/issues/CYBA-532) retest
- Surface: `partner-portal`, `backend-api`, `local-stage`
- Environment:
  - partner local-dev preview: `http://portal.localhost:3004`
  - backend local-stage API: `http://127.0.0.1:18080`
  - preview env included `API_URL=http://127.0.0.1:18080`, `NEXT_PUBLIC_API_URL=http://127.0.0.1:18080`
- Browser/channel: Playwright Chromium headless
- Viewport: desktop `1440x1000`
- Locale: `en-EN`
- User role/state: protected synthetic `CYBA451_PARTNER_OWNER` fixture from `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`; credential values were not stored.

Steps to reproduce:

1. Start/use partner local-dev preview on `portal.localhost:3004` with backend env pointing to `http://127.0.0.1:18080`.
2. Sign in with the protected synthetic partner owner fixture and complete 2FA.
3. Confirm `GET /api/v1/auth/session` returns `200`.
4. Confirm base partner endpoints return `200` with `X-Auth-Realm: partner`: `/partner-workspaces/me`, `/partner-session/bootstrap`, `/partner-notifications/preferences`, `/partner-notifications/counters`.
5. Open authenticated owner routes `/en-EN/dashboard`, `/codes`, `/finance`, `/conversions`, `/team`, `/settings`, `/analytics`, `/programs`, `/campaigns`, `/cases`, `/integrations`, `/reseller`.
6. Inspect workspace-scoped partner API calls.

Expected result:

- Workspace-scoped read-only partner APIs return valid data or intentional empty/read-only states.
- Reseller voucher, partner settings/security, and passkey policy/compliance surfaces do not emit backend `404`/`500` errors during normal authenticated route rendering.

Previous actual result:

- Base workspace/bootstrap/notification endpoints now return `200`, so `MF-PART-003` is fixed.
- Authenticated routes render without login redirect and without `SYSTEM FAILURE`.
- Remaining backend failures:
  - `GET /api/v1/partner-workspaces/:workspace_id/reseller-voucher-batches` -> `404`, repeated on owner pages.
  - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/policy` -> `500`, observed on settings.
  - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/compliance` -> `500`, observed on settings.
- Repo contract/source contains these endpoints in `partner/src/lib/api/partner-portal.ts`, `partner/src/lib/api/passkeys.ts`, `partner/src/lib/api/generated/types.ts`, `backend/src/presentation/api/v1/partners/routes.py`, and `backend/src/presentation/api/v1/auth/passkey_policy.py`.

Latest retest after [CYBA-528](/CYBA/issues/CYBA-528):

- Result: `fail`; `MF-PART-004` remains reproducible.
- Auth flow still passes: `loginStatus=200`, `pendingStatus=204`, `completeStatus=200`, `sessionStatus=200`.
- Base canonical endpoints pass: `/partner-workspaces/me`, `/partner-session/bootstrap`, `/partner-notifications/preferences`, `/partner-notifications/counters`, `/partner-notifications` all return `200`.
- Many workspace APIs pass, including `settings`, `members`, `roles`, `programs`, `lane-applications`, `codes`, `campaign-assets`, `statements`, `payout-accounts`, `payout-history`, `conversion-records`, `analytics-metrics`, `report-exports`, `review-requests`, `traffic-declarations`, `cases`, `integration-credentials`, `integration-delivery-logs`, and `postback-readiness`.
- Direct probe failures:
  - `GET /api/v1/partner-workspaces/:workspace_id/reseller-voucher-batches` -> `404`
  - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/policy` -> `500`
  - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/compliance` -> `500`
- Route network failures:
  - `GET /api/v1/partner-workspaces/:workspace_id/reseller-voucher-batches` -> `404`, repeated on all 12 owner route checks.
  - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/policy` -> `500`, observed twice on `/en-EN/settings`.
  - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/compliance` -> `500`, observed twice on `/en-EN/settings`.
  - `GET /api/v1/partner-workspaces/:workspace_id/support/tickets?limit=50` -> `500`, observed on `/en-EN/cases`.
- Observed contract/method gap: direct probe `GET /api/v1/partner-workspaces/:workspace_id/creative-approvals` -> `405`; route network did not show this as the primary blocker, but backend/frontend should confirm whether `GET` is expected or update the QA probe/API contract.
- All 12 route checks stayed authenticated and avoided `SYSTEM FAILURE`, but were marked `fail` because blocking API failures remained.

Latest retest after [CYBA-536](/CYBA/issues/CYBA-536):

- Result: `fail`; `MF-PART-004` remains reproducible after [CYBA-532](/CYBA/issues/CYBA-532) backend work.
- Auth flow passes: `loginStatus=200`, `pendingStatus=204`, `completeStatus=200`, `sessionStatus=200`, `authRealmKey=partner`, `principalType=partner_operator`.
- Base canonical endpoints pass:
  - `GET /api/v1/partner-workspaces/me` -> `200`
  - `GET /api/v1/partner-session/bootstrap` -> `200`
  - `GET /api/v1/partner-notifications/preferences` -> `200`
  - `GET /api/v1/partner-notifications/counters` -> `200`
  - `GET /api/v1/partner-notifications` -> `200`
- Targeted direct probe failures:
  - `GET /api/v1/partner-workspaces/:workspace_id/reseller-voucher-batches` -> `404`, sanitized detail `Reseller voucher batches are not enabled for this workspace`; expected `200` list response, including allowed `[]`.
  - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/policy` -> `500`, sanitized detail `Internal server error`.
  - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/compliance` -> `500`, sanitized detail `Internal server error`.
  - `GET /api/v1/partner-workspaces/:workspace_id/support/tickets?limit=50` -> `500`, sanitized detail `Internal server error`; expected `200` with `{ tickets: [], nextCursor: null }` or synthetic tickets.
  - `GET /api/v1/partner-workspaces/:workspace_id/creative-approvals` -> `405`, sanitized detail `Method Not Allowed`; expected `200` list response per retest request.
- Route network failures:
  - `GET /api/v1/partner-workspaces/:workspace_id/reseller-voucher-batches` -> `404` on `/dashboard`, `/codes`, `/finance`, `/conversions`, `/team`, `/settings`, `/analytics`, `/programs`, `/campaigns`, `/cases`, `/integrations`, `/reseller`.
  - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/policy` -> `500`, observed on `/en-EN/settings`.
  - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/compliance` -> `500`, observed on `/en-EN/settings`.
  - `GET /api/v1/partner-workspaces/:workspace_id/support/tickets?limit=50` -> `500`, observed on `/en-EN/cases`.
- All 12 route checks returned document `200`, stayed authenticated, and avoided `SYSTEM FAILURE`, but were marked `fail` because targeted partner workspace API failures remained.

Final [CYBA-457](/CYBA/issues/CYBA-457) retest after [CYBA-532](/CYBA/issues/CYBA-532):

- Result: `pass`; `MF-PART-004` no longer reproduces on the current local-stage runtime.
- Auth flow passes: `loginStatus=200`, `pendingStatus=204`, `completeStatus=200`, `sessionStatus=200`; no retry after `complete 401` was used.
- Base canonical endpoints return `200`:
  - `GET /api/v1/partner-workspaces/me`
  - `GET /api/v1/partner-session/bootstrap`
  - `GET /api/v1/partner-notifications/preferences`
  - `GET /api/v1/partner-notifications/counters`
  - `GET /api/v1/partner-notifications`
- Targeted direct probes return `200`:
  - `GET /api/v1/partner-workspaces/:workspace_id/reseller-voucher-batches` -> `200`, array `count=0`
  - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/policy` -> `200`
  - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/compliance` -> `200`
  - `GET /api/v1/partner-workspaces/:workspace_id/support/tickets?limit=50` -> `200`, `{ tickets: [], nextCursor: null }`
  - `GET /api/v1/partner-workspaces/:workspace_id/creative-approvals` -> `200`, array `count=0`
- Route network: `targetedRouteFailures=[]`, `failedRoutes=[]`.
- Authenticated owner routes `/dashboard`, `/codes`, `/finance`, `/conversions`, `/team`, `/settings`, `/analytics`, `/programs`, `/campaigns`, `/cases`, `/integrations`, `/reseller` all passed targeted backend checks and did not show `SYSTEM FAILURE`.

Sanitized evidence:

- JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST525-AUTHED-CAPTURE__partner-portal__manual-qa__20260604T213002Z.json`
- Supplemental API probe: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST525-API-PROBE__partner-portal__manual-qa__20260604T213206Z.json`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST525-OWNER-DASH-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T213002Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST525-OWNER-FIN-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T213002Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST525-OWNER-SETTINGS-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T213002Z.png`
- Post-[CYBA-528](/CYBA/issues/CYBA-528) JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST528-FINAL-CAPTURE__partner-portal__manual-qa__20260604T215018Z.json`
- Post-[CYBA-528](/CYBA/issues/CYBA-528) screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST528-OWNER-DASH-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T215018Z.png`
- Post-[CYBA-528](/CYBA/issues/CYBA-528) screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST528-OWNER-SETTINGS-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T215018Z.png`
- Post-[CYBA-528](/CYBA/issues/CYBA-528) screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST528-OWNER-CASES-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T215018Z.png`
- Post-[CYBA-528](/CYBA/issues/CYBA-528) screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST528-OWNER-RESELLER-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T215018Z.png`
- Post-[CYBA-536](/CYBA/issues/CYBA-536) JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-536__partner-workspace-api-retest__20260604T222151Z.json`
- Post-[CYBA-536](/CYBA/issues/CYBA-536) runner: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba536-partner-workspace-api-retest.mjs`
- Post-[CYBA-536](/CYBA/issues/CYBA-536) screenshots directory: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/` (`13` PNGs: login plus 12 owner routes).
- Post-[CYBA-536](/CYBA/issues/CYBA-536) key screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/CYBA-536__partner-portal__synthetic-owner__en-EN__desktop-1440__dashboard-fail__20260604T222151Z.png`
- Post-[CYBA-536](/CYBA/issues/CYBA-536) key screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/CYBA-536__partner-portal__synthetic-owner__en-EN__desktop-1440__settings-fail__20260604T222151Z.png`
- Post-[CYBA-536](/CYBA/issues/CYBA-536) key screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/CYBA-536__partner-portal__synthetic-owner__en-EN__desktop-1440__cases-fail__20260604T222151Z.png`
- Post-[CYBA-536](/CYBA/issues/CYBA-536) key screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/CYBA-536__partner-portal__synthetic-owner__en-EN__desktop-1440__reseller-fail__20260604T222151Z.png`
- Final [CYBA-457](/CYBA/issues/CYBA-457) retest JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-536__partner-workspace-api-retest__20260604T224847ZCYBA457.json`
- Final [CYBA-457](/CYBA/issues/CYBA-457) screenshots directory: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/` (`13` PNGs ending `20260604T224847ZCYBA457.png`: login plus 12 owner routes).
- Final [CYBA-457](/CYBA/issues/CYBA-457) key screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/CYBA-536__partner-portal__synthetic-owner__en-EN__desktop-1440__dashboard-pass__20260604T224847ZCYBA457.png`
- Final [CYBA-457](/CYBA/issues/CYBA-457) key screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/CYBA-536__partner-portal__synthetic-owner__en-EN__desktop-1440__settings-pass__20260604T224847ZCYBA457.png`
- Final [CYBA-457](/CYBA/issues/CYBA-457) key screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/CYBA-536__partner-portal__synthetic-owner__en-EN__desktop-1440__cases-pass__20260604T224847ZCYBA457.png`
- Final [CYBA-457](/CYBA/issues/CYBA-457) key screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/CYBA-536__partner-portal__synthetic-owner__en-EN__desktop-1440__reseller-pass__20260604T224847ZCYBA457.png`

Sensitive-data review:

- PASS - no cookie values, storageState, HAR, trace, JWT, refresh tokens, passwords, TOTP secret, TOTP code, payment secrets, production PII, or Telegram initData saved. Workspace ids are redacted as `:workspace_id` in JSON evidence.
- Post-[CYBA-528](/CYBA/issues/CYBA-528) JSON redaction check: UUID-like strings count `0`.
- Post-[CYBA-536](/CYBA/issues/CYBA-536) JSON redaction check: no JWT/Bearer/UUID strings found; cookie names only, no cookie values.
- Final [CYBA-457](/CYBA/issues/CYBA-457) JSON redaction check: JWT/Bearer/UUID-like strings count `0`; cookie names only, no cookie values.

Owner and next action:

- Owner: no remaining backend owner action for `MF-PART-004`; [CYBA-532](/CYBA/issues/CYBA-532) is accepted as fixed by the final [CYBA-457](/CYBA/issues/CYBA-457) retest.
- Action: no follow-up for this finding unless a later regression reintroduces non-`200` targeted workspace API responses.

Context7 docs checked: N/A - manual API/business-flow contract finding. Runner docs: Context7 MCP quota exceeded; `ctx7` CLI checked `/microsoft/playwright` `BrowserContext.cookies(urls)`, `Page.goto`, `page.screenshot({ path, fullPage })`, and network response examples. Repo contract/source checked: `partner/src/lib/api/partner-portal.ts`, `partner/src/lib/api/passkeys.ts`, `partner/src/lib/api/generated/types.ts`, `backend/src/presentation/api/v1/partners/routes.py`, `backend/src/presentation/api/v1/auth/passkey_policy.py`.

### MF-PART-003 - Authenticated partner shell renders but canonical partner workspace/bootstrap APIs return 404

- Type: `bug`
- Severity: `P1`
- Status: retested fixed after [CYBA-525](/CYBA/issues/CYBA-525)
- Surface: `partner-portal`, `backend-api`, `local-stage`
- Environment:
  - partner local-dev preview: `http://portal.localhost:3004`
  - backend local-stage API: `http://127.0.0.1:18080`
  - preview env included `API_URL=http://127.0.0.1:18080`, `NEXT_PUBLIC_API_URL=http://127.0.0.1:18080`
- Browser/channel: Playwright Chromium headless
- Viewport: desktop `1440x1000`
- Locale: `en-EN`
- User role/state: protected synthetic `CYBA451_PARTNER_OWNER` fixture from `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`; credential values were not stored.

Steps to reproduce:

1. Start/use partner local-dev preview on `portal.localhost:3004` with backend env pointing to `http://127.0.0.1:18080`.
2. Sign in with the protected synthetic partner owner fixture.
3. Complete 2FA.
4. Confirm `GET /api/v1/auth/session` returns `200` with partner realm metadata.
5. Open `/en-EN/dashboard`, `/en-EN/codes`, `/en-EN/finance`, `/en-EN/conversions`, `/en-EN/team`, `/en-EN/settings`, `/en-EN/analytics`, or `/en-EN/programs`.
6. Inspect network calls for canonical partner data endpoints.

Expected result:

- Authenticated partner pages load the canonical workspace/bootstrap contract.
- `GET /api/v1/partner-workspaces/me`, `GET /api/v1/partner-session/bootstrap`, and `GET /api/v1/partner-notifications/preferences` return valid partner data or intentional empty/read-only states.
- Partner access states, codes/markup, finance, conversions/attribution, team/access, and client/cross-surface checks can be verified against backend data.

Actual result:

- UI login and same-origin API 2FA both establish an authenticated partner session.
- Protected owner routes render without login redirect and without `SYSTEM FAILURE`.
- The canonical partner endpoints repeatedly return `404`:
  - `/api/v1/partner-workspaces/me`
  - `/api/v1/partner-session/bootstrap`
  - `/api/v1/partner-notifications/preferences`
- Repo contract/source contains these endpoints in `partner/src/lib/api/partner-portal.ts`, `partner/src/lib/api/generated/types.ts`, and `backend/src/presentation/api/v1/partners/routes.py`.
- The visible route shell is therefore not enough to validate canonical business data end-to-end.

Latest retest after [CYBA-525](/CYBA/issues/CYBA-525):

- Result: `pass`; `MF-PART-003` no longer reproduces for the original base canonical endpoints.
- Auth flow: `loginStatus=200`, `pendingStatus=204`, `completeStatus=200`, `sessionStatus=200`.
- Direct API probe with `X-Auth-Realm: partner`:
  - `/api/v1/partner-workspaces/me` -> `200`
  - `/api/v1/partner-session/bootstrap` -> `200`
  - `/api/v1/partner-notifications/preferences` -> `200`
  - `/api/v1/partner-notifications/counters` -> `200`
- UI route network also shows `200` for workspace/bootstrap/notification endpoints.
- Remaining failures are tracked separately as `MF-PART-004`.

Sanitized evidence:

- JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-AUTHED-CAPTURE__partner-portal__manual-qa__20260604T204240Z.json`
- UI login retry JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-UI-LOGIN-RETRY-CAPTURE__partner-portal__manual-qa__20260604T204530Z.json`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-OWNER-DASH-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__pass__20260604T204240Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-OWNER-CODES-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__pass__20260604T204240Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-OWNER-FIN-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__pass__20260604T204240Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-OWNER-CONV-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__pass__20260604T204240Z.png`
- Fixed retest JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST525-API-PROBE__partner-portal__manual-qa__20260604T213206Z.json`
- Fixed retest route capture: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST525-AUTHED-CAPTURE__partner-portal__manual-qa__20260604T213002Z.json`

Sensitive-data review:

- PASS - no cookie values, storageState, HAR, trace, JWT, refresh tokens, passwords, TOTP secret, TOTP code, payment secrets, production PII, or Telegram initData saved.

Owner and next action:

- Owner: `Helio Backend API Engineer` or backend/local-stage readiness owner.
- Action: no remaining action for `MF-PART-003`; downstream `MF-PART-004` was also fixed by the final post-[CYBA-532](/CYBA/issues/CYBA-532) retest.

Context7 docs checked: N/A - manual API/business-flow contract finding. Repo contract/source checked: `partner/src/lib/api/partner-portal.ts`, `partner/src/lib/api/generated/types.ts`, `backend/src/presentation/api/v1/partners/routes.py`. Fallback official docs checked for evidence capture: Playwright navigation/screenshots/network events and MDN Set-Cookie cookie attributes.

### MF-PART-002 - Partner 2FA complete succeeds but does not leave a usable session

- Type: `bug`
- Severity: `P1`
- Status: retested fixed after [CYBA-495](/CYBA/issues/CYBA-495)
- Surface: `partner-portal`
- Environment:
  - partner local-dev preview: `http://portal.localhost:3004`
  - backend local-stage API: `http://127.0.0.1:18080`
  - preview env included `API_URL=http://127.0.0.1:18080`, `NEXT_PUBLIC_API_URL=http://127.0.0.1:18080`, `PARTNER_API_URL=http://127.0.0.1:18080`
- Browser/channel: Playwright Chromium headless
- Viewport: desktop `1440x1000`
- Locale: `en-EN`
- User role/state: protected synthetic `CYBA451_PARTNER_OWNER` fixture from `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`; credential values were not stored.

Steps to reproduce:

1. Start partner local-dev preview on a portal host, e.g. `portal.localhost:3004`, with backend env pointing to `http://127.0.0.1:18080`.
2. Submit synthetic partner owner credentials to same-origin `POST /api/v1/auth/login` with partner realm header.
3. Observe login returns `200` with `requires_2fa=true`.
4. Submit returned pending token to `POST /api/auth/2fa/pending`; observe `204` and `pending_2fa` cookie.
5. Submit current synthetic TOTP code to `POST /api/auth/2fa/complete`.
6. Open `http://portal.localhost:3004/en-EN/dashboard`, `/codes`, `/finance`, or `/conversions`.

Expected result:

- `POST /api/auth/2fa/complete` creates a usable authenticated partner session.
- `GET /api/v1/auth/session` returns `200` for the synthetic partner owner.
- Protected partner routes render canonical backend-backed workspace/dashboard/codes/finance/conversion data.

Actual result:

- `POST /api/auth/2fa/complete` returns `200` and `redirect_to=/en-EN/dashboard`.
- Cookie probe after pending: `pending_2fa` exists for `portal.localhost`, `HttpOnly`, `SameSite=Lax`.
- Cookie probe after complete: no cookies remain in browser context.
- Subsequent `GET /api/v1/auth/session` returns `401`.
- Protected routes redirect to `/en-EN/login?redirect=...`; no canonical partner business data can be tested.

Latest retest after [CYBA-483](/CYBA/issues/CYBA-483):

- Result: `fail`; `MF-PART-002` remains reproducible in the QA workspace.
- UI login + 2FA smoke ended at `/en-EN/login?redirect=%2Fen-EN%2Fdashboard`.
- Same-origin API auth probe: `loginStatus=200`, `requires2fa=true`, `pendingStatus=204`, `completeStatus=200`, `sessionStatus=401`.
- Cookie probe after pending: only `pending_2fa`; cookie probe after complete: `[]`.
- Protected owner routes `/dashboard`, `/codes`, `/finance`, `/conversions`, and `/team` all redirected to login and recorded repeated `401` for `/api/v1/auth/session` / `/api/v1/auth/refresh`.
- No `SYSTEM FAILURE` was observed in this retest.

Latest retest after [CYBA-509](/CYBA/issues/CYBA-509):

- Result: `fail`; `MF-PART-002` remains reproducible in the QA workspace after the backend cookie `Secure`/request fix review passed.
- Same-origin API auth probe: `loginStatus=200`, `requires2fa=true`, `pendingStatus=204`, `completeStatus=200`, `redirectTo=/en-EN/dashboard`, `sessionStatus=401`.
- Cookie probe after pending: `NEXT_LOCALE` plus `pending_2fa` for `portal.localhost`; `pending_2fa` is `HttpOnly`, `SameSite=Lax`, `secure=false`.
- Cookie probe after complete: only `NEXT_LOCALE`; no realm session cookie names remained.
- Protected owner routes `/dashboard`, `/codes`, `/finance`, `/conversions`, and `/team` all redirected to login.
- No `SYSTEM FAILURE` was observed in this retest.

Latest retest after [CYBA-519](/CYBA/issues/CYBA-519):

- Result: `fail`; `MF-PART-002` remains unresolved after frontend `Set-Cookie Domain` normalization review.
- First failing transition changed to `POST /api/auth/2fa/complete -> 401`; no `redirect_to` was returned.
- Same-origin API auth probe: `loginStatus=200`, `requires2fa=true`, `pendingStatus=204`, `completeStatus=401`, `sessionStatus=401`.
- Cookie probe after pending: only `pending_2fa` for `portal.localhost`; `pending_2fa` is `HttpOnly`, `SameSite=Lax`, `secure=false`.
- Cookie probe after complete: `[]`; no realm session cookie names remained.
- Protected owner routes `/dashboard`, `/codes`, `/finance`, `/conversions`, and `/team` all redirected to login.
- No `SYSTEM FAILURE` was observed in this retest.

Latest retest after [CYBA-495](/CYBA/issues/CYBA-495):

- Result: `pass`; `MF-PART-002` no longer reproduces.
- UI login retry: form filled after hydration wait, reached `2fa=true`, submitted TOTP, landed on `/en-EN/dashboard`.
- Same-origin API auth probe: `loginStatus=200`, `requires2fa=true`, `pendingStatus=204`, `completeStatus=200`, `sessionStatus=200`.
- Session identity metadata: `auth_realm_key=partner`, `audience=cybervpn:partner`, `principal_type=partner_operator`.
- Protected owner routes no longer redirect to login and no `SYSTEM FAILURE` was observed.

Последний path-matched ретест после [CYBA-522](/CYBA/issues/CYBA-522) / [CYBA-523](/CYBA/issues/CYBA-523):

- Результат: `pass`; `MF-PART-002` остаётся исправленным при обязательной проверке path-matched cookie probe.
- Same-origin API auth probe: `loginStatus=200`, `requires2fa=true`, `pendingStatus=204`, `completeStatus=200`, `redirectTo=/en-EN/dashboard`, `sessionStatus=200`, `sessionRealm=partner`.
- Fresh TOTP был сгенерирован непосредственно перед `POST /api/auth/2fa/complete`; повтор после `401` не использовался.
- Root-origin cookie probe после 2FA complete: `[]`.
- Path-matched cookie probe `context.cookies('http://portal.localhost:3004/api/v1/auth/session')` после 2FA complete: `partner_access_token`, `partner_refresh_token`, обе `domain=portal.localhost`, `path=/api`, `HttpOnly=true`, `SameSite=Lax`, `secure=false`.
- Protected owner routes `/dashboard`, `/codes`, `/finance`, `/conversions` и `/team` вернули `200`, не ушли в login redirect и не показали `SYSTEM FAILURE`.

Sanitized evidence:

- JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-AUTHED-API-CAPTURE__partner-portal__manual-qa__20260604T164832Z.json`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-AUTHED-API-OWNER-DASH-001__partner-portal__synthetic-owner-api-authenticated__en-EN__desktop-1440__fail__20260604T164832Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-AUTHED-API-OWNER-CODES-001__partner-portal__synthetic-owner-api-authenticated__en-EN__desktop-1440__fail__20260604T164832Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-AUTHED-API-OWNER-FIN-001__partner-portal__synthetic-owner-api-authenticated__en-EN__desktop-1440__fail__20260604T164832Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-AUTHED-API-OWNER-CONV-001__partner-portal__synthetic-owner-api-authenticated__en-EN__desktop-1440__fail__20260604T164832Z.png`
- Latest retest JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RETEST-AUTHED-CAPTURE__partner-portal__manual-qa__20260604T171101Z.json`
- Latest retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RETEST-UI-LOGIN-001__partner-portal__synthetic-owner-ui-login__en-EN__desktop-1440__fail__20260604T171101Z.png`
- Latest retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RETEST-OWNER-DASH-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T171101Z.png`
- Latest retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RETEST-OWNER-CODES-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T171101Z.png`
- Latest retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RETEST-OWNER-FIN-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T171101Z.png`
- Latest retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RETEST-OWNER-CONV-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T171101Z.png`
- Latest retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RETEST-OWNER-TEAM-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T171101Z.png`
- Post-CYBA-509 retest JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST509-AUTHED-CAPTURE__partner-portal__manual-qa__20260604T183538Z.json`
- Post-CYBA-509 retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST509-OWNER-DASH-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T183538Z.png`
- Post-CYBA-509 retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST509-OWNER-CODES-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T183538Z.png`
- Post-CYBA-509 retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST509-OWNER-FIN-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T183538Z.png`
- Post-CYBA-509 retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST509-OWNER-CONV-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T183538Z.png`
- Post-CYBA-509 retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST509-OWNER-TEAM-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T183538Z.png`
- Post-CYBA-519 / [CYBA-520](/CYBA/issues/CYBA-520) retest JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-520__partner-2fa-session-retest__20260604T202139Z.json`
- Post-CYBA-519 / [CYBA-520](/CYBA/issues/CYBA-520) retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-520-screenshots/CYBA-520__partner-portal__synthetic-owner__en-EN__desktop-1440__dashboard-fail__20260604T202139Z.png`
- Post-CYBA-519 / [CYBA-520](/CYBA/issues/CYBA-520) retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-520-screenshots/CYBA-520__partner-portal__synthetic-owner__en-EN__desktop-1440__codes-fail__20260604T202139Z.png`
- Post-CYBA-519 / [CYBA-520](/CYBA/issues/CYBA-520) retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-520-screenshots/CYBA-520__partner-portal__synthetic-owner__en-EN__desktop-1440__finance-fail__20260604T202139Z.png`
- Post-CYBA-519 / [CYBA-520](/CYBA/issues/CYBA-520) retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-520-screenshots/CYBA-520__partner-portal__synthetic-owner__en-EN__desktop-1440__conversions-fail__20260604T202139Z.png`
- Post-CYBA-519 / [CYBA-520](/CYBA/issues/CYBA-520) retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-520-screenshots/CYBA-520__partner-portal__synthetic-owner__en-EN__desktop-1440__team-fail__20260604T202139Z.png`
- Post-CYBA-495 fixed retest JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-AUTHED-CAPTURE__partner-portal__manual-qa__20260604T204240Z.json`
- Post-CYBA-495 fixed retest UI JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-UI-LOGIN-RETRY-CAPTURE__partner-portal__manual-qa__20260604T204530Z.json`
- Post-CYBA-495 fixed retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-UI-LOGIN-RETRY-001__partner-portal__synthetic-owner-ui-login__en-EN__desktop-1440__pass__20260604T204530Z.png`
- Path-matched [CYBA-523](/CYBA/issues/CYBA-523) retest JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-523__partner-2fa-path-cookie-retest__20260604T210730Z.json`
- Path-matched [CYBA-523](/CYBA/issues/CYBA-523) retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-523-screenshots/CYBA-523__partner-portal__synthetic-owner__en-EN__desktop-1440__dashboard-pass__20260604T210730Z.png`
- Path-matched [CYBA-523](/CYBA/issues/CYBA-523) retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-523-screenshots/CYBA-523__partner-portal__synthetic-owner__en-EN__desktop-1440__codes-pass__20260604T210730Z.png`
- Path-matched [CYBA-523](/CYBA/issues/CYBA-523) retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-523-screenshots/CYBA-523__partner-portal__synthetic-owner__en-EN__desktop-1440__finance-pass__20260604T210730Z.png`
- Path-matched [CYBA-523](/CYBA/issues/CYBA-523) retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-523-screenshots/CYBA-523__partner-portal__synthetic-owner__en-EN__desktop-1440__conversions-pass__20260604T210730Z.png`
- Path-matched [CYBA-523](/CYBA/issues/CYBA-523) retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-523-screenshots/CYBA-523__partner-portal__synthetic-owner__en-EN__desktop-1440__team-pass__20260604T210730Z.png`
- Cookie/status probe: recorded in raw notes; only cookie names/domain/path/httpOnly/secure/sameSite were printed, no values.

Sensitive-data review:

- PASS - no cookies, storage state, JWT, refresh tokens, passwords, TOTP secret, TOTP code, payment secrets, production PII, or Telegram initData saved.

Owner and next action:

- Owner: `Prism Admin Partner Frontend Engineer` with backend/security input as needed.
- Action: no remaining action for `MF-PART-002`; downstream `MF-PART-003` and `MF-PART-004` were also retested fixed.

Context7 MCP проверен: quota exceeded. ctx7 fallback проверен: `/microsoft/playwright` `BrowserContext.cookies(urls)` и `page.screenshot` path option; finding остаётся manual UI/business-flow finding.

### MF-PART-001 - Protected partner routes crash before route guard/business UI renders

- Type: `bug`
- Severity: `P1`
- Status: retested fixed after [CYBA-464](/CYBA/issues/CYBA-464)
- Original evidence:
  - `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-CAPTURE-RERUN-DEVENV__partner-portal__manual-qa__20260604T160419Z.json`
  - `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RERUN-AUTH-002__partner-portal__anonymous__en-EN__desktop-1440__fail__20260604T160406Z.png`
  - `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RERUN-CODES-001__partner-portal__dev-bypass-owner-active__en-EN__desktop-1440__fail__20260604T160410Z.png`
- Retest evidence:
  - `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-PORTAL-CAPTURE__partner-portal__manual-qa__20260604T164039Z.json`
  - `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-PORTAL-AUTH-002__partner-portal__anonymous__en-EN__desktop-1440__pass__20260604T164039Z.png`
  - `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-PORTAL-CODES-001__partner-portal__dev-bypass-owner-active__en-EN__desktop-1440__pass__20260604T164039Z.png`
  - `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-PORTAL-FIN-001__partner-portal__dev-bypass-owner-active__en-EN__desktop-1440__pass__20260604T164039Z.png`
  - `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-PORTAL-ROLE-001__partner-portal__dev-bypass-analyst-active__en-EN__desktop-1440__pass__20260604T164039Z.png`

Retest result:

- Anonymous `/en-EN/dashboard` redirects to `/en-EN/login?redirect=%2Fen-EN%2Fdashboard`.
- Simulated owner active `/dashboard`, `/codes`, `/finance`, `/conversions` render without `SYSTEM FAILURE`.
- Simulated analyst `/team` and restricted owner `/finance` render without `SYSTEM FAILURE`.
- Network still shows expected unauthenticated `401` API calls in simulated/dev-bypass mode; this is not canonical authenticated coverage.

## Passed

- `MF-PART-FINAL-UI-LOGIN-RETRY-001`: UI login + 2FA reaches `/en-EN/dashboard` and `/api/v1/auth/session=200`.
- `MF-PART-FINAL-OWNER-DASH-001`: authenticated owner dashboard route renders without redirect or `SYSTEM FAILURE`.
- `MF-PART-FINAL-OWNER-CODES-001`: authenticated owner codes route renders without redirect or `SYSTEM FAILURE`.
- `MF-PART-FINAL-OWNER-FIN-001`: authenticated owner finance route renders without redirect or `SYSTEM FAILURE`.
- `MF-PART-FINAL-OWNER-CONV-001`: authenticated owner conversions route renders without redirect or `SYSTEM FAILURE`.
- `MF-PART-FINAL-OWNER-TEAM-001`: authenticated owner team route renders without redirect or `SYSTEM FAILURE`.
- `CYBA-523-PARTNER-2FA-PATH-MATCHED-COOKIE-RETEST`: authenticated partner 2FA session валидна, path-matched `/api` cookie probe видит `partner_access_token` и `partner_refresh_token`, пять protected owner routes рендерятся без login redirect.
- `MF-PART-POST525-API-PROBE`: base canonical endpoints `/partner-workspaces/me`, `/partner-session/bootstrap`, `/partner-notifications/preferences`, `/partner-notifications/counters` return `200` with `X-Auth-Realm: partner`.
- `MF-PART-POST525-AUTHED-CAPTURE`: authenticated route network confirms `200` for core workspace APIs including codes, statements, payout accounts/history, conversion records, analytics metrics, members, roles, settings, programs/lane-applications, report exports, review requests, traffic declarations, integration credentials/logs, cases, and notifications.
- `CYBA-457-FINAL-POST532-RETEST`: authenticated partner owner retest passes for auth/session, base partner endpoints, targeted workspace APIs (`reseller-voucher-batches`, passkey policy/compliance, support tickets, creative approvals), and 12 owner routes with no targeted backend failures.
- `MF-PART-PORTAL-AUTH-001`: portal public login renders on `http://portal.localhost:3004/en-EN/login`.
- `MF-PART-PORTAL-AUTH-002`: anonymous protected dashboard redirects to login without crash.
- `MF-PART-PORTAL-SHELL-001`: simulated owner active dashboard renders without crash.
- `MF-PART-PORTAL-CODES-001`: simulated owner active codes/tracking surface renders without crash.
- `MF-PART-PORTAL-FIN-001`: simulated owner active finance surface renders without crash.
- `MF-PART-PORTAL-CONV-001`: simulated owner active conversions/attribution surface renders without crash.
- `MF-PART-PORTAL-ROLE-001`: simulated analyst team/access route renders without crash.
- `MF-PART-PORTAL-STATE-001`: simulated restricted finance state renders without crash.
- `MF-PART-PORTAL-MOBILE-001`: mobile RU portal login renders.

## Blocked / not tested

- No active P1 partner portal blocker remains after the final post-[CYBA-532](/CYBA/issues/CYBA-532) retest.
- Withdrawals, payout approval/rejection, payment capture/refund, provisioning and production-data mutations were not attempted.
- Suspended/disabled workspace state: no listed fixture.
- OAuth, email, Telegram, real payment capture/refund/payout, production Remnawave/provisioning: explicitly blocked/not-tested by [CYBA-452](/CYBA/issues/CYBA-452) safety decisions.
