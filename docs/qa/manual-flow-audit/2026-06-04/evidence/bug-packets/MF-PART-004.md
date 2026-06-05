# MF-PART-004 - Workspace-scoped reseller/passkey partner APIs fail after canonical bootstrap unblock

- Type: `bug`
- Severity: `P1`
- Status: retested fixed after [CYBA-457](/CYBA/issues/CYBA-457) final post-[CYBA-532](/CYBA/issues/CYBA-532) retest
- Surface: `partner-portal`, `backend-api`, `local-stage`
- Issue: [CYBA-457](/CYBA/issues/CYBA-457)
- Detected: `2026-06-04`

## Environment

- Partner local-dev preview: `http://portal.localhost:3004`
- Backend local-stage API: `http://127.0.0.1:18080`
- Browser/channel: Playwright Chromium headless
- Viewport: desktop `1440x1000`
- Locale: `en-EN`
- User role/state: protected synthetic `CYBA451_PARTNER_OWNER` fixture from `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`
- Secret handling: credential, token, cookie, TOTP secret, and TOTP code values were not stored.

## Steps to reproduce

1. Start/use partner local-dev preview on `portal.localhost:3004` with backend env pointing to `http://127.0.0.1:18080`.
2. Sign in with the protected synthetic partner owner fixture and complete 2FA.
3. Confirm `GET /api/v1/auth/session` returns `200`.
4. Confirm base partner endpoints return `200` with `X-Auth-Realm: partner`: `/partner-workspaces/me`, `/partner-session/bootstrap`, `/partner-notifications/preferences`, `/partner-notifications/counters`.
5. Open authenticated owner routes `/en-EN/dashboard`, `/codes`, `/finance`, `/conversions`, `/team`, `/settings`, `/analytics`, `/programs`, `/campaigns`, `/cases`, `/integrations`, `/reseller`.
6. Inspect workspace-scoped partner API calls.

## Expected result

- Workspace-scoped read-only partner APIs return valid data or intentional empty/read-only states.
- Reseller voucher, partner settings/security, and passkey policy/compliance surfaces do not emit backend `404`/`500` errors during normal authenticated route rendering.

## Previous actual result

- Base workspace/bootstrap/notification endpoints now return `200`, so `MF-PART-003` is fixed.
- Authenticated routes render without login redirect and without `SYSTEM FAILURE`.
- Remaining backend failures:
  - `GET /api/v1/partner-workspaces/:workspace_id/reseller-voucher-batches` -> `404`, repeated on owner pages.
  - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/policy` -> `500`, observed on settings.
  - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/compliance` -> `500`, observed on settings.
- Repo contract/source contains these endpoints in `partner/src/lib/api/partner-portal.ts`, `partner/src/lib/api/passkeys.ts`, `partner/src/lib/api/generated/types.ts`, `backend/src/presentation/api/v1/partners/routes.py`, and `backend/src/presentation/api/v1/auth/passkey_policy.py`.

## Latest retest after CYBA-528

Result: `fail`; `MF-PART-004` remains reproducible after [CYBA-528](/CYBA/issues/CYBA-528).

- Auth flow passes: `loginStatus=200`, `pendingStatus=204`, `completeStatus=200`, `sessionStatus=200`.
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

## Latest retest after CYBA-536

Result: `fail`; `MF-PART-004` remains reproducible after [CYBA-532](/CYBA/issues/CYBA-532) backend work.

- Auth flow passes: `loginStatus=200`, `pendingStatus=204`, `completeStatus=200`, `sessionStatus=200`, `authRealmKey=partner`, `principalType=partner_operator`.
- Base canonical endpoints pass: `/partner-workspaces/me`, `/partner-session/bootstrap`, `/partner-notifications/preferences`, `/partner-notifications/counters`, `/partner-notifications` all return `200`.
- Direct probe failures:
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

## Final CYBA-457 retest after CYBA-532

Result: `pass`; `MF-PART-004` no longer reproduces on the current local-stage runtime.

- Auth flow passes: `loginStatus=200`, `pendingStatus=204`, `completeStatus=200`, `sessionStatus=200`; no retry after `complete 401` was used.
- Base canonical endpoints return `200`: `/partner-workspaces/me`, `/partner-session/bootstrap`, `/partner-notifications/preferences`, `/partner-notifications/counters`, `/partner-notifications`.
- Targeted direct probes return `200`:
  - `GET /api/v1/partner-workspaces/:workspace_id/reseller-voucher-batches` -> `200`, array `count=0`
  - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/policy` -> `200`
  - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/compliance` -> `200`
  - `GET /api/v1/partner-workspaces/:workspace_id/support/tickets?limit=50` -> `200`, `{ tickets: [], nextCursor: null }`
  - `GET /api/v1/partner-workspaces/:workspace_id/creative-approvals` -> `200`, array `count=0`
- Route network: `targetedRouteFailures=[]`, `failedRoutes=[]`.
- Authenticated owner routes `/dashboard`, `/codes`, `/finance`, `/conversions`, `/team`, `/settings`, `/analytics`, `/programs`, `/campaigns`, `/cases`, `/integrations`, `/reseller` all passed targeted backend checks and did not show `SYSTEM FAILURE`.

## Sanitized evidence

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

## Sensitive-data review

- PASS - no cookie values, storageState, HAR, trace, JWT, refresh tokens, passwords, TOTP secret, TOTP code, payment secrets, production PII, or Telegram initData saved.
- Workspace ids are redacted as `:workspace_id` in JSON evidence.
- Post-[CYBA-528](/CYBA/issues/CYBA-528) JSON redaction check: UUID-like strings count `0`.
- Post-[CYBA-536](/CYBA/issues/CYBA-536) JSON redaction check: no JWT/Bearer/UUID strings found; cookie names only, no cookie values.
- Final [CYBA-457](/CYBA/issues/CYBA-457) JSON redaction check: JWT/Bearer/UUID-like strings count `0`; cookie names only, no cookie values.

## Owner / next action

- Owner: no remaining backend owner action for `MF-PART-004`; [CYBA-532](/CYBA/issues/CYBA-532) is accepted as fixed by the final [CYBA-457](/CYBA/issues/CYBA-457) retest.
- Action: no follow-up for this finding unless a later regression reintroduces non-`200` targeted workspace API responses.

Context7 docs checked: N/A - manual API/business-flow contract finding. Runner docs: Context7 MCP quota exceeded; `ctx7` CLI checked `/microsoft/playwright` `BrowserContext.cookies(urls)`, `Page.goto`, `page.screenshot({ path, fullPage })`, and network response examples. Repo contract/source checked: `partner/src/lib/api/partner-portal.ts`, `partner/src/lib/api/passkeys.ts`, `partner/src/lib/api/generated/types.ts`, `backend/src/presentation/api/v1/partners/routes.py`, `backend/src/presentation/api/v1/auth/passkey_policy.py`.
