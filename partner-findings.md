# Partner portal findings

Дата: `2026-06-04`

Подробный partner findings log ведется здесь:

- `docs/qa/manual-flow-audit/2026-06-04/partner-findings.md`

## Current Result

- `MF-PART-001` protected-route `SYSTEM FAILURE` ранее подтверждён как исправленный в local-dev portal preview.
- `MF-PART-002` подтверждён исправленным в [CYBA-523](/CYBA/issues/CYBA-523) через обязательный path-matched cookie probe.
- Более ранний ретест [CYBA-520](/CYBA/issues/CYBA-520) после [CYBA-519](/CYBA/issues/CYBA-519) падал, потому что cookie probe не доказывал cookies с `Path=/api`:
  - `POST /api/v1/auth/login -> 200`, `requires_2fa=true`
  - `POST /api/auth/2fa/pending -> 204`
  - `POST /api/auth/2fa/complete -> 401`
  - `GET /api/v1/auth/session -> 401`
  - cookies after complete: `[]`
  - protected partner routes redirect to login
- Последний ретест [CYBA-523](/CYBA/issues/CYBA-523):
  - `POST /api/auth/2fa/complete -> 200`, `redirect_to=/en-EN/dashboard`
  - `GET /api/v1/auth/session -> 200`, `auth_realm_key=partner`
  - root-origin cookie probe после complete: `[]`
  - path-matched probe под `/api/v1/auth/session`: `partner_access_token`, `partner_refresh_token`, обе `Path=/api`
  - protected partner routes `/dashboard`, `/codes`, `/finance`, `/conversions`, `/team` render без login redirect
- Canonical partner dashboard data, codes, markup boundaries, client attribution, finance, earnings, balances, withdrawals и cross-surface attribution checks остаются заблокированы вне этого ретеста под `MF-PART-003`.

## Evidence

- JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-520__partner-2fa-session-retest__20260604T202139Z.json`
- JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-523__partner-2fa-path-cookie-retest__20260604T210730Z.json`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-520-screenshots/CYBA-520__partner-portal__synthetic-owner__en-EN__desktop-1440__dashboard-fail__20260604T202139Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-523-screenshots/CYBA-523__partner-portal__synthetic-owner__en-EN__desktop-1440__dashboard-pass__20260604T210730Z.png`
- Bug packet: `docs/qa/manual-flow-audit/2026-06-04/evidence/bug-packets/MF-PART-002.md`

Context7 MCP проверен: quota exceeded. ctx7 fallback проверен: `/microsoft/playwright` `BrowserContext.cookies(urls)` и `page.screenshot` path option.

## CYBA-573 Partner Business-Flow Recheck

Дата: `2026-06-06`

### Result

- Business-flow content: `PASS`.
- Routes checked: `/en-EN/dashboard`, `/en-EN/codes`, `/en-EN/finance`, `/en-EN/conversions`, `/en-EN/team`.
- Environment: local `partner` Next dev server `http://127.0.0.1:3002`, Chromium via Playwright, viewport `1440x1000`, locale `en-EN`.
- User role/state: `partner_operator`, workspace owner, active workspace, Creator / Affiliate lane, release ring `R4`, synthetic `Safe Partner Lab` fixture.
- Data safety: synthetic masked fixture only; no credentials, JWT/cookies/storageState, production PII, payment secrets, or live payout/customer data stored.
- Contract/unit checks: `8 passed`, `48 passed` in targeted partner Vitest.
- UI smoke content checks: all five route assertions passed with no `SYSTEM FAILURE` and no `pageErrors`.
- Overall smoke summary is `pass=false` only because console/network findings below remain in evidence.

### Bugs

#### CYBA-573-PART-I18N-001 - `/codes` logs missing `Partner.codes.modes.review`

- Severity: `P3`.
- Type: i18n/UX.
- Route: `/en-EN/codes`.
- Browser/viewport/locale: Chromium via Playwright, `1440x1000`, `en-EN`.
- Role/state: `partner_operator`, workspace owner, active safe fixture workspace.
- Steps to reproduce:
  1. Start `partner` locally on `http://127.0.0.1:3002`.
  2. Use dev bypass as partner operator with safe fixture mocks from `evidence/partner/CYBA-573/cyba-573-partner-smoke-rerun.mjs`.
  3. Open `/en-EN/codes`.
  4. Capture browser console.
- Expected result: page renders without missing-translation console errors; every commercial mode returned by `getPartnerCommercialSurfaceMode('codes', state)` has a `Partner.codes.modes.*` message.
- Actual result: page content renders, but console logs `IntlError: MISSING_MESSAGE: Could not resolve Partner.codes.modes.review in messages for locale en-EN`.
- Evidence:
  - Summary: `evidence/partner/CYBA-573/playwright-ui-smoke-summary.json`
  - Screenshot: `evidence/partner/CYBA-573/screenshots/CYBA-573__partner-codes__safe-fixture__en-EN__desktop-1440__pass__20260606-rerun.png`
  - Source context: `partner/src/features/partner-commercial/components/codes-tracking-page.tsx:135`, `partner/src/features/partner-commercial/lib/commercial-capabilities.ts:122`, `partner/messages/en-EN/partner.json:1166`.
- Context7 docs checked: MCP quota exceeded; ctx7 fallback `/amannn/next-intl` checked for missing messages, `IntlErrorCode.MISSING_MESSAGE`, `onError`, and `getMessageFallback`.

### Product Gaps

#### CYBA-573-PART-OBS-001 - local partner smoke logs 403 analytics beacon responses

- Severity: `P4`.
- Type: observability/dev-smoke hygiene.
- Routes affected during smoke: `/en-EN/dashboard`, `/en-EN/codes`, `/en-EN/finance`, `/en-EN/conversions`, `/en-EN/team`.
- Browser/viewport/locale: Chromium via Playwright, `1440x1000`, `en-EN`.
- Role/state: `partner_operator`, workspace owner, active safe fixture workspace.
- Steps to reproduce:
  1. Run the CYBA-573 Playwright harness against local `partner` dev server.
  2. Watch console/network responses while navigating the five partner routes.
- Expected result: local smoke either disables telemetry beacons or receives non-error responses so business-flow QA is not polluted by console/network 403 noise.
- Actual result: `navigator.sendBeacon` requests return 403 for `POST /api/analytics/web-vitals`, `POST /api/analytics/product-events`, and `POST /api/analytics/traffic`. Partner `/api/v1/partner-workspaces/**` mocks returned expected data and business content still rendered.
- Evidence:
  - Summary failedResponses: `evidence/partner/CYBA-573/playwright-ui-smoke-summary.json`
  - Log: `evidence/partner/CYBA-573/playwright-ui-smoke-rerun.log`
  - Source context: `partner/src/shared/lib/web-vitals.ts`, `partner/src/lib/product-intelligence/client.ts`, `partner/src/shared/ui/atoms/traffic-analytics-reporter.tsx`.
- Context7 docs checked: N/A - product observability/dev-environment finding; no framework behavior conclusion required.

### Not Tested / Limitations

- Real backend/staging partner credentials were not used.
- No production/customer/payment data was touched.
- Cross-surface client/admin attribution consistency was not verified against live backend data in this heartbeat; this recheck used safe local route mocks plus partner API contract tests.
- Withdrawal mutations, payout creation, and destructive partner data changes were not executed.

### Evidence

- Targeted Vitest log: `evidence/partner/CYBA-573/targeted-vitest.log`
- Playwright harness: `evidence/partner/CYBA-573/cyba-573-partner-smoke-rerun.mjs`
- Playwright summary: `evidence/partner/CYBA-573/playwright-ui-smoke-summary.json`
- Playwright log: `evidence/partner/CYBA-573/playwright-ui-smoke-rerun.log`
- Screenshots:
  - `evidence/partner/CYBA-573/screenshots/CYBA-573__partner-dashboard__safe-fixture__en-EN__desktop-1440__pass__20260606-rerun.png`
  - `evidence/partner/CYBA-573/screenshots/CYBA-573__partner-codes__safe-fixture__en-EN__desktop-1440__pass__20260606-rerun.png`
  - `evidence/partner/CYBA-573/screenshots/CYBA-573__partner-finance__safe-fixture__en-EN__desktop-1440__pass__20260606-rerun.png`
  - `evidence/partner/CYBA-573/screenshots/CYBA-573__partner-conversions__safe-fixture__en-EN__desktop-1440__pass__20260606-rerun.png`
  - `evidence/partner/CYBA-573/screenshots/CYBA-573__partner-team__safe-fixture__en-EN__desktop-1440__pass__20260606-rerun.png`

## CYBA-610 Partner Security Sessions Browser QA

Дата: `2026-06-09`

### Result

- Browser security-sessions smoke: `FAIL`.
- Targeted component/unit coverage: `PASS` (`1` file, `4` tests).
- Environment: local `partner` Next dev server `http://127.0.0.1:3002`, Chromium via Playwright, viewport `1440x1000`, locale `en-EN`.
- User role/state: `partner_operator`, development bypass, synthetic safe device fixture.
- Data safety: synthetic device fixture only; no credentials, JWT/cookies/refresh tokens, storageState, HAR, production PII, payment data, or Telegram `initData` stored.

### Bugs

#### CYBA-610-PART-SEC-001 - partner security sessions console route returns 404

- Severity: `P1`.
- Type: functional route/wiring bug.
- Route: `/en-EN/security/sessions`.
- Steps to reproduce:
  1. Start `partner` locally on `http://127.0.0.1:3002`.
  2. Use development bypass as `partner_operator`.
  3. Mock `GET /api/v1/auth/devices` with one current device and two remote devices.
  4. Open `/en-EN/security/sessions`.
- Expected result: partner sessions console renders `Sessions Console`; the current device badge appears once; two remote device controls are available; selected-device revoke, `logout-others`, and realm-scoped `logout-all` can be executed against the mocked API.
- Actual result: `GET /en-EN/security/sessions -> 404`; global not-found page renders. No `GET /api/v1/auth/devices` request fires and no revoke/logout mutation is possible.
- Evidence:
  - Summary: `evidence/partner/CYBA-610/playwright-security-sessions-summary.json`
  - Log: `evidence/partner/CYBA-610/playwright-security-sessions.log`
  - Screenshot: `evidence/partner/CYBA-610/screenshots/CYBA-610__partner-security-sessions__safe-fixture__en-EN__desktop-1440__initial__fail__20260609.png`
  - Targeted Vitest log: `evidence/partner/CYBA-610/targeted-vitest.log`
  - Notes: `evidence/partner/CYBA-610/notes/cyba-610-partner-security-sessions.md`
- Source context:
  - `partner/src/app/[locale]/(dashboard)/_legacy-admin-routes/security/sessions/page.tsx:13` renders `SecuritySessionsConsole`, but the route is under `_legacy-admin-routes`.
  - `partner/src/features/partner-shell/lib/legacy-route-retirement.ts:30` redirects `/_legacy-admin-routes/security` to `/settings`.
  - `partner/src/features/partner-settings/components/settings-foundation-page.tsx:379` only provides a `reviewedActiveSessions` settings toggle, not the device revoke/logout console.
- Follow-up: [CYBA-619](/CYBA/issues/CYBA-619) assigned to Prism Admin Partner Frontend Engineer.
- Context7 docs checked: MCP quota exceeded; ctx7 fallback `/microsoft/playwright` checked for route mocks/navigation/screenshot/response capture; ctx7 fallback `/vercel/next.js/v16.2.2` checked for App Router private folders. Next docs state underscore-prefixed folders opt the folder and all subfolders out of routing.

### Not Tested / Limitations

- Browser verification of unique-device rendering, one current badge, selected-device revoke, `logout-others`, and `logout-all` could not proceed because the route is unreachable.
- Real backend/staging partner credentials were not used.
- No production/customer/payment data was touched.

## CYBA-610 Post-CYBA-619 Retest

Дата: `2026-06-09`

### Result

- Route-level fix from [CYBA-619](/CYBA/issues/CYBA-619): `PARTIAL PASS`; `GET /en-EN/security/sessions -> 200`.
- Targeted tests: `PASS` (`2` files, `6` tests).
- Browser security-sessions smoke: `BLOCKED/FAIL` due runtime hydration error.
- Environment: local `partner` Next dev server `http://127.0.0.1:3002`, Chromium via Playwright, viewport `1440x1000`, locale `en-EN`.
- User role/state: `partner_operator`, development bypass, synthetic safe device fixture.
- Data safety: synthetic device fixture only; no credentials, JWT/cookies/refresh tokens, storageState, HAR, production PII, payment data, or Telegram `initData` stored.

### Bugs

#### CYBA-610-PART-SEC-002 - sessions route can fail hydration with `Invalid or unexpected token`

- Severity: `P1`.
- Type: browser runtime/hydration bug.
- Route: `/en-EN/security/sessions`.
- Steps to reproduce:
  1. Start `partner` locally on `http://127.0.0.1:3002`.
  2. Run `node evidence/partner/CYBA-610/cyba-610-partner-security-sessions-smoke.mjs`.
  3. Inspect `evidence/partner/CYBA-610/playwright-security-sessions-summary.json`.
- Expected result: route hydrates consistently, calls `GET /api/v1/auth/session`, `GET /api/v1/partner-workspaces/me`, `GET /api/v1/partner-session/bootstrap`, and `GET /api/v1/auth/devices`, then renders device rows/actions so selected-device revoke, `logout-others`, and `logout-all` can be verified.
- Actual result: route status is `200`, but Chromium can throw `pageError: Invalid or unexpected token`; the page remains around `AUTHENTICATING...`, device rows/actions are not reliably reachable, and final smoke `pass=false`.
- Evidence:
  - Canonical failed summary: `evidence/partner/CYBA-610/playwright-security-sessions-summary.json`
  - Final failed log: `evidence/partner/CYBA-610/playwright-security-sessions-rerun-after-CYBA-619-final-second.log`
  - Partial action log with same pageError: `evidence/partner/CYBA-610/playwright-security-sessions-rerun-after-CYBA-619-final.log`
  - Runtime probe log: `evidence/partner/CYBA-610/runtime-error-probe-after-CYBA-619-second.log`
  - Targeted Vitest rerun: `evidence/partner/CYBA-610/targeted-vitest-rerun-after-CYBA-619.log`
  - Screenshots: `evidence/partner/CYBA-610/screenshots/`
- Additional observation: one action run reached and exercised the mocked flow despite the page error: one current badge, two remote logout controls, selected-device revoke once, `logout-others` once, `logout-all` once, and login redirect true. This is not sufficient for signoff because a subsequent bounded run reproduced the hydration-blocking `Invalid or unexpected token`.
- Follow-up: [CYBA-621](/CYBA/issues/CYBA-621) assigned to Prism Admin Partner Frontend Engineer.
- Context7 docs checked: MCP quota exceeded; ctx7 fallback `/microsoft/playwright` checked for route mocks/navigation/screenshot/response capture; ctx7 fallback `/vercel/next.js/v16.2.2` checked for App Router routing behavior.

### Not Tested / Limitations

- Stable browser signoff of the full sessions flow remains blocked until [CYBA-621](/CYBA/issues/CYBA-621) is fixed.
- Real backend/staging partner credentials were not used.
- No production/customer/payment data was touched.

## CYBA-610 Post-CYBA-621 Final Retest

Дата: `2026-06-09`

### Result

- Final browser security-sessions smoke: `PASS`.
- Targeted tests: `PASS` (`2` files, `6` tests).
- Route checks: `HEAD /en-EN/security/sessions -> 200`, `HEAD /en-EN/login -> 200`.
- Environment: local `partner` Next dev server `http://127.0.0.1:3002`, Chromium via Playwright, viewport `1440x1000`, locale `en-EN`.
- User role/state: `partner_operator`, development bypass, synthetic safe device fixture.
- Data safety: synthetic device fixture only; no credentials, JWT/cookies/refresh tokens, storageState, HAR, production PII, payment data, or Telegram `initData` stored.

### Verification

- Initial render: `Sessions Console` rendered; current badge count `1`; remote logout controls `2`; expected device labels/IPs present; device limit `3/5`.
- Selected-device revoke: `DELETE /api/v1/auth/devices/dev_remote_android` called once; selected remote IP absent afterward; untouched remote IP remained present.
- `logout-others`: `POST /api/v1/auth/devices/logout-others` called once; remaining remote IP absent; current device still present.
- `logout-all`: `POST /api/v1/auth/logout-all` called once; browser redirected to `/en-EN/login`.
- Browser quality: `pageErrors=[]`, `failedResponses=[]`.

### Evidence

- Summary: `evidence/partner/CYBA-610/playwright-security-sessions-summary.json`
- Final Playwright log: `evidence/partner/CYBA-610/playwright-security-sessions-rerun-after-CYBA-621-final.log`
- Targeted Vitest log: `evidence/partner/CYBA-610/targeted-vitest-rerun-after-CYBA-621.log`
- Screenshots:
  - `evidence/partner/CYBA-610/screenshots/CYBA-610__partner-security-sessions__safe-fixture__en-EN__desktop-1440__initial__pass__20260609.png`
  - `evidence/partner/CYBA-610/screenshots/CYBA-610__partner-security-sessions__safe-fixture__en-EN__desktop-1440__after-revoke-device__pass__20260609.png`
  - `evidence/partner/CYBA-610/screenshots/CYBA-610__partner-security-sessions__safe-fixture__en-EN__desktop-1440__after-logout-others__pass__20260609.png`
  - `evidence/partner/CYBA-610/screenshots/CYBA-610__partner-security-sessions__safe-fixture__en-EN__desktop-1440__after-logout-all__pass__20260609.png`

Context7 docs checked: MCP quota exceeded; ctx7 fallback evidence remains `/microsoft/playwright` for route mocks/navigation/screenshot/response capture and `/vercel/next.js/v16.2.2` for App Router route behavior. No new external-doc behavior conclusion was needed for this final retest.

### Remaining limitations

- Real backend/staging partner credentials were not used.
- No production/customer/payment data was touched.
