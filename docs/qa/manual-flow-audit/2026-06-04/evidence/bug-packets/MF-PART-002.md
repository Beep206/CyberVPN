# MF-PART-002 - Partner 2FA complete succeeds but does not leave a usable session

- Type: `bug`
- Severity: `P1`
- Status: retested fixed after [CYBA-495](/CYBA/issues/CYBA-495)
- Surface: `partner-portal`
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

1. Start partner local-dev preview on `portal.localhost:3004` with backend env pointing to `http://127.0.0.1:18080`.
2. Submit the synthetic partner owner to same-origin `POST /api/v1/auth/login`.
3. Confirm response status is `200` and `requires_2fa=true`.
4. Submit the returned pending token to `POST /api/auth/2fa/pending`.
5. Confirm response status is `204` and a `pending_2fa` cookie exists.
6. Submit a valid synthetic TOTP code to `POST /api/auth/2fa/complete`.
7. Open `/en-EN/dashboard`, `/en-EN/codes`, `/en-EN/finance`, or `/en-EN/conversions`.

## Expected result

- `POST /api/auth/2fa/complete` creates/forwards the httpOnly session cookies required by the partner frontend.
- `GET /api/v1/auth/session` returns `200`.
- Protected partner routes render canonical authenticated business data.

## Actual result

- `POST /api/auth/2fa/complete` returns `200` with `redirect_to=/en-EN/dashboard`.
- Cookie probe after pending shows only `pending_2fa` exists.
- Cookie probe after complete shows no session cookies remain.
- `GET /api/v1/auth/session` returns `401`.
- Protected partner routes redirect to login and canonical partner flows remain untestable.

## Latest retest after CYBA-483

- Retest time: `2026-06-04T17:11:01Z`
- Retest reason: [CYBA-483](/CYBA/issues/CYBA-483) was marked `done`; [CYBA-457](/CYBA/issues/CYBA-457) resumed from `issue_children_completed`.
- Result: `fail`; `MF-PART-002` remains reproducible.
- UI login + 2FA smoke final URL: `http://portal.localhost:3004/en-EN/login?redirect=%2Fen-EN%2Fdashboard`
- UI session status: `401`
- Same-origin API auth probe:
  - `loginStatus=200`
  - `requires2fa=true`
  - `pendingStatus=204`
  - `completeStatus=200`
  - `redirectTo=/en-EN/dashboard`
  - `sessionStatus=401`
- Cookie probe:
  - after pending: only `pending_2fa` for `portal.localhost`, `HttpOnly`, `SameSite=Lax`
  - after complete: `[]`
- Protected owner routes `/en-EN/dashboard`, `/en-EN/codes`, `/en-EN/finance`, `/en-EN/conversions`, and `/en-EN/team` redirected to login with repeated `401` on `/api/v1/auth/session` / `/api/v1/auth/refresh`.
- No `SYSTEM FAILURE` was observed.

## Latest retest after CYBA-509

- Retest time: `2026-06-04T18:35:38Z`
- Retest reason: [CYBA-509](/CYBA/issues/CYBA-509) was marked `done`; [CYBA-510](/CYBA/issues/CYBA-510) resumed from `issue_blockers_resolved` to verify the backend cookie `Secure`/request fix.
- Result: `fail`; `MF-PART-002` remains reproducible.
- Same-origin API auth probe:
  - `loginStatus=200`
  - `requires2fa=true`
  - `pendingStatus=204`
  - `completeStatus=200`
  - `redirectTo=/en-EN/dashboard`
  - `sessionStatus=401`
- Cookie probe:
  - after pending: `NEXT_LOCALE` plus `pending_2fa` for `portal.localhost`; `pending_2fa` is `HttpOnly`, `SameSite=Lax`, `secure=false`
  - after complete: only `NEXT_LOCALE`; no realm session cookie names remained
- Protected owner routes `/en-EN/dashboard`, `/en-EN/codes`, `/en-EN/finance`, `/en-EN/conversions`, and `/en-EN/team` redirected to login.
- No `SYSTEM FAILURE` was observed.

## Latest retest after CYBA-519 / CYBA-520

- Retest time: `2026-06-04T20:22:17Z`
- Retest reason: [CYBA-519](/CYBA/issues/CYBA-519) was marked `done`; [CYBA-520](/CYBA/issues/CYBA-520) resumed from `issue_blockers_resolved` to verify the frontend `Set-Cookie Domain` normalization path.
- Result: `fail`; `MF-PART-002` remains unresolved, with an earlier first failing transition than the post-[CYBA-509](/CYBA/issues/CYBA-509) retest.
- Same-origin API auth probe:
  - `loginStatus=200`
  - `requires2fa=true`
  - `pendingStatus=204`
  - `completeStatus=401`
  - `redirectTo=null`
  - `sessionStatus=401`
- Cookie probe:
  - after pending: only `pending_2fa` for `portal.localhost`; `pending_2fa` is `HttpOnly`, `SameSite=Lax`, `secure=false`
  - after complete: `[]`; no realm session cookie names remained
- Protected owner routes `/en-EN/dashboard`, `/en-EN/codes`, `/en-EN/finance`, `/en-EN/conversions`, and `/en-EN/team` redirected to login with repeated `401` on `/api/v1/auth/session` / `/api/v1/auth/refresh`.
- No `SYSTEM FAILURE` was observed.

## Latest retest after CYBA-495

- Retest time: `2026-06-04T20:45:30Z`
- Retest reason: [CYBA-495](/CYBA/issues/CYBA-495) was marked `done`; [CYBA-457](/CYBA/issues/CYBA-457) resumed from `issue_children_completed`.
- Result: `pass`; `MF-PART-002` no longer reproduces.
- UI login retry reached `2fa=true`, submitted synthetic TOTP, landed on `/en-EN/dashboard`, and `GET /api/v1/auth/session` returned `200`.
- Same-origin API auth probe:
  - `loginStatus=200`
  - `requires2fa=true`
  - `pendingStatus=204`
  - `completeStatus=200`
  - `redirectTo=/en-EN/dashboard`
  - `sessionStatus=200`
- Session identity metadata: `auth_realm_key=partner`, `audience=cybervpn:partner`, `principal_type=partner_operator`.
- Protected owner routes no longer redirected to login.
- No `SYSTEM FAILURE` was observed.

## Последний path-matched ретест после CYBA-522 / CYBA-523

- Время ретеста: `2026-06-04T21:07:47Z`
- Причина ретеста: [CYBA-522](/CYBA/issues/CYBA-522) переведена в `done`; [CYBA-523](/CYBA/issues/CYBA-523) возобновлена по `issue_blockers_resolved`, чтобы проверить partner 2FA session через path-matched cookie probe.
- Результат: `pass`; `MF-PART-002` остаётся исправленным.
- Same-origin API auth probe:
  - `loginStatus=200`
  - `requires2fa=true`
  - `pendingStatus=204`
  - `completeStatus=200`
  - `redirectTo=/en-EN/dashboard`
  - `sessionStatus=200`
  - `sessionRealm=partner`
- Fresh TOTP был сгенерирован непосредственно перед `POST /api/auth/2fa/complete`; повтор после `401` не использовался.
- Cookie probe:
  - root-origin probe после complete: `[]`
  - path-matched probe `context.cookies('http://portal.localhost:3004/api/v1/auth/session')`: `partner_access_token`, `partner_refresh_token`, обе `domain=portal.localhost`, `path=/api`, `HttpOnly=true`, `SameSite=Lax`, `secure=false`
- Protected owner routes `/en-EN/dashboard`, `/en-EN/codes`, `/en-EN/finance`, `/en-EN/conversions` и `/en-EN/team` вернули `200`, не ушли в login redirect и не показали `SYSTEM FAILURE`.

## Sanitized evidence

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
- Post-CYBA-519 / CYBA-520 retest JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-520__partner-2fa-session-retest__20260604T202139Z.json`
- Post-CYBA-519 / CYBA-520 retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-520-screenshots/CYBA-520__partner-portal__synthetic-owner__en-EN__desktop-1440__dashboard-fail__20260604T202139Z.png`
- Post-CYBA-519 / CYBA-520 retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-520-screenshots/CYBA-520__partner-portal__synthetic-owner__en-EN__desktop-1440__codes-fail__20260604T202139Z.png`
- Post-CYBA-519 / CYBA-520 retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-520-screenshots/CYBA-520__partner-portal__synthetic-owner__en-EN__desktop-1440__finance-fail__20260604T202139Z.png`
- Post-CYBA-519 / CYBA-520 retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-520-screenshots/CYBA-520__partner-portal__synthetic-owner__en-EN__desktop-1440__conversions-fail__20260604T202139Z.png`
- Post-CYBA-519 / CYBA-520 retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-520-screenshots/CYBA-520__partner-portal__synthetic-owner__en-EN__desktop-1440__team-fail__20260604T202139Z.png`
- Post-CYBA-495 fixed retest JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-AUTHED-CAPTURE__partner-portal__manual-qa__20260604T204240Z.json`
- Post-CYBA-495 fixed retest UI JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-UI-LOGIN-RETRY-CAPTURE__partner-portal__manual-qa__20260604T204530Z.json`
- Post-CYBA-495 fixed retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-UI-LOGIN-RETRY-001__partner-portal__synthetic-owner-ui-login__en-EN__desktop-1440__pass__20260604T204530Z.png`
- Path-matched CYBA-523 fixed retest JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-523__partner-2fa-path-cookie-retest__20260604T210730Z.json`
- Path-matched CYBA-523 fixed retest screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-523-screenshots/CYBA-523__partner-portal__synthetic-owner__en-EN__desktop-1440__dashboard-pass__20260604T210730Z.png`

## Sensitive-data review

- PASS - cookies, storageState, HAR, trace, JWT, refresh tokens, passwords, TOTP secret, TOTP code, payment secrets, production PII и Telegram initData не сохранялись.

## Owner / next action

- Owner: `Prism Admin Partner Frontend Engineer` с backend/security input при необходимости.
- Action: остаточных действий по `MF-PART-002` нет; canonical business-flow QA сейчас заблокирована `MF-PART-003`.

Context7 MCP проверен: quota exceeded. ctx7 fallback проверен: `/microsoft/playwright` `BrowserContext.cookies(urls)` и `page.screenshot` path option; finding остаётся manual UI/business-flow finding.
