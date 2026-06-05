# MF-PART-003 - Authenticated partner shell renders but canonical partner workspace/bootstrap APIs return 404

- Type: `bug`
- Severity: `P1`
- Status: retested fixed after [CYBA-525](/CYBA/issues/CYBA-525)
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
2. Sign in with the protected synthetic partner owner fixture.
3. Complete 2FA.
4. Confirm `GET /api/v1/auth/session` returns `200` with partner realm metadata.
5. Open `/en-EN/dashboard`, `/en-EN/codes`, `/en-EN/finance`, `/en-EN/conversions`, `/en-EN/team`, `/en-EN/settings`, `/en-EN/analytics`, or `/en-EN/programs`.
6. Inspect network calls for canonical partner data endpoints.

## Expected result

- Authenticated partner pages load the canonical workspace/bootstrap contract.
- `GET /api/v1/partner-workspaces/me`, `GET /api/v1/partner-session/bootstrap`, and `GET /api/v1/partner-notifications/preferences` return valid partner data or intentional empty/read-only states.
- Partner access states, codes/markup, finance, conversions/attribution, team/access, and client/cross-surface checks can be verified against backend data.

## Actual result

- UI login and same-origin API 2FA both establish an authenticated partner session.
- `GET /api/v1/auth/session` returns `200` with partner realm metadata.
- Protected owner routes render without login redirect and without `SYSTEM FAILURE`.
- The canonical partner endpoints repeatedly return `404`:
  - `/api/v1/partner-workspaces/me`
  - `/api/v1/partner-session/bootstrap`
  - `/api/v1/partner-notifications/preferences`
- Repo contract/source contains these endpoints in `partner/src/lib/api/partner-portal.ts`, `partner/src/lib/api/generated/types.ts`, and `backend/src/presentation/api/v1/partners/routes.py`.
- The visible route shell is therefore not enough to validate canonical business data end-to-end.

## Latest retest after CYBA-525

- Retest time: `2026-06-04T21:32:06Z`
- Result: `pass`; `MF-PART-003` no longer reproduces for the original base canonical endpoints.
- Auth flow: `loginStatus=200`, `pendingStatus=204`, `completeStatus=200`, `sessionStatus=200`.
- Direct API probe with `X-Auth-Realm: partner`:
  - `/api/v1/partner-workspaces/me` -> `200`
  - `/api/v1/partner-session/bootstrap` -> `200`
  - `/api/v1/partner-notifications/preferences` -> `200`
  - `/api/v1/partner-notifications/counters` -> `200`
- UI route network also shows `200` for workspace/bootstrap/notification endpoints.
- Remaining failures are tracked separately as `MF-PART-004`.

## Sanitized evidence

- JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-AUTHED-CAPTURE__partner-portal__manual-qa__20260604T204240Z.json`
- UI login retry JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-UI-LOGIN-RETRY-CAPTURE__partner-portal__manual-qa__20260604T204530Z.json`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-OWNER-DASH-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__pass__20260604T204240Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-OWNER-CODES-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__pass__20260604T204240Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-OWNER-FIN-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__pass__20260604T204240Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-OWNER-CONV-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__pass__20260604T204240Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-OWNER-TEAM-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__pass__20260604T204240Z.png`
- Fixed retest JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST525-API-PROBE__partner-portal__manual-qa__20260604T213206Z.json`
- Fixed retest route capture: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST525-AUTHED-CAPTURE__partner-portal__manual-qa__20260604T213002Z.json`

## Sensitive-data review

- PASS - no cookie values, storageState, HAR, trace, JWT, refresh tokens, passwords, TOTP secret, TOTP code, payment secrets, production PII, or Telegram initData saved.

## Owner / next action

- Owner: `Helio Backend API Engineer` or backend/local-stage readiness owner.
- Action: no remaining action for `MF-PART-003`; canonical business-flow QA is now blocked by `MF-PART-004`.

Context7 docs checked: N/A - manual API/business-flow contract finding. Repo contract/source checked: `partner/src/lib/api/partner-portal.ts`, `partner/src/lib/api/generated/types.ts`, `backend/src/presentation/api/v1/partners/routes.py`. Fallback official docs checked for evidence capture: Playwright navigation/screenshots/network events and MDN Set-Cookie cookie attributes.
