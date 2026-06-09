# CYBA-610 partner security sessions browser QA

Date: `2026-06-09`

## Result

- Browser smoke: `FAIL`.
- Targeted Vitest: `PASS` (`1` file, `4` tests).
- Environment: local `partner` Next dev server `http://127.0.0.1:3002`, Chromium via Playwright, viewport `1440x1000`, locale `en-EN`.
- User role/state: `partner_operator`, development bypass, synthetic safe device fixture.
- Data safety: no credentials, cookies, JWTs, refresh tokens, storageState, HAR, payment data, production PII, or Telegram `initData` were stored.

## Finding

### CYBA-610-PART-SEC-001 - partner security sessions console is unreachable

- Severity: `P1`.
- Type: functional route/wiring bug.
- Route: `/en-EN/security/sessions`.
- Steps to reproduce:
  1. Start `partner` locally on `http://127.0.0.1:3002`.
  2. Use development bypass as `partner_operator`.
  3. Mock `GET /api/v1/auth/devices` with a current device and two remote devices.
  4. Open `/en-EN/security/sessions`.
- Expected result: the partner sessions console renders `Sessions Console`, the current device badge appears once, two remote device logout controls are available, and QA can verify selected-device revoke, `logout-others`, and realm-scoped `logout-all`.
- Actual result: document request returns `404`; the page renders the global not-found surface. No `GET /api/v1/auth/devices` request fires and no revoke/logout mutation can be exercised.
- Evidence:
  - Summary: `evidence/partner/CYBA-610/playwright-security-sessions-summary.json`
  - Log: `evidence/partner/CYBA-610/playwright-security-sessions.log`
  - Screenshot: `evidence/partner/CYBA-610/screenshots/CYBA-610__partner-security-sessions__safe-fixture__en-EN__desktop-1440__initial__fail__20260609.png`
  - Targeted unit log: `evidence/partner/CYBA-610/targeted-vitest.log`
- Route/source context:
  - `partner/src/app/[locale]/(dashboard)/_legacy-admin-routes/security/sessions/page.tsx:13` renders `SecuritySessionsConsole`, but the route file is under underscore-prefixed `_legacy-admin-routes`.
  - `partner/src/features/partner-shell/lib/legacy-route-retirement.ts:30` retires `/_legacy-admin-routes/security` to `/settings`.
  - `partner/src/features/partner-settings/components/settings-foundation-page.tsx:379` only exposes a `reviewedActiveSessions` settings toggle, not device revoke/logout controls.
- Context7 docs checked: MCP quota exceeded. ctx7 fallback checked `/microsoft/playwright` for `page.route`, `page.goto`, `page.screenshot`, and response capture; ctx7 fallback checked `/vercel/next.js/v16.2.2` for App Router private folders. Next docs state underscore-prefixed folders opt the folder and all subfolders out of routing.
- Follow-up: [CYBA-619](/CYBA/issues/CYBA-619) assigned to Prism Admin Partner Frontend Engineer.

## Not tested

- Selected-device revoke, `logout-others`, current badge count, and `logout-all` redirect behavior were not testable in browser because the sessions route is unreachable.
- No real backend/staging partner credentials or production/customer/payment data were used.

## Post-CYBA-619 Retest

Date: `2026-06-09`

- Child [CYBA-619](/CYBA/issues/CYBA-619) fixed the route-level 404: `GET /en-EN/security/sessions -> 200`.
- Targeted rerun passed: `2` files, `6` tests.
- Browser retest remains blocked by runtime hydration error:
  - `pageErrors=[{"message":"Invalid or unexpected token"}]`
  - final bounded smoke `pass=false`
  - failed run did not reliably reach `GET /api/v1/auth/devices` or device rows/actions.
- One action run reached the UI despite the same page error and verified:
  - current badge count `1`
  - remote logout buttons `2`
  - selected device revoke called once for `dev_remote_android`
  - `logout-others` called once
  - `logout-all` called once
  - login redirect `true`
- This is not sufficient for signoff because a subsequent bounded rerun reproduced the hydration-blocking `Invalid or unexpected token`.
- Follow-up: [CYBA-621](/CYBA/issues/CYBA-621) assigned to Prism Admin Partner Frontend Engineer.

### Post-fix evidence

- Canonical failed summary: `evidence/partner/CYBA-610/playwright-security-sessions-summary.json`
- Final failed log: `evidence/partner/CYBA-610/playwright-security-sessions-rerun-after-CYBA-619-final-second.log`
- Partial action log: `evidence/partner/CYBA-610/playwright-security-sessions-rerun-after-CYBA-619-final.log`
- Runtime probe log: `evidence/partner/CYBA-610/runtime-error-probe-after-CYBA-619-second.log`
- Targeted Vitest rerun: `evidence/partner/CYBA-610/targeted-vitest-rerun-after-CYBA-619.log`
- Screenshots: `evidence/partner/CYBA-610/screenshots/`

Context7 docs checked: MCP quota exceeded. ctx7 fallback checked `/microsoft/playwright` for route mocks/navigation/screenshot/response capture and `/vercel/next.js/v16.2.2` for App Router routing behavior.

## Post-CYBA-621 Final Retest

Date: `2026-06-09`

- Child [CYBA-621](/CYBA/issues/CYBA-621) fixed the runtime hydration blocker.
- Route checks:
  - `HEAD /en-EN/security/sessions -> 200`
  - `HEAD /en-EN/login -> 200`
- Targeted rerun passed: `2` files, `6` tests.
- Browser smoke final result: `PASS`.
  - `pass=true`
  - `pageErrors=[]`
  - `failedResponses=[]`
  - current badge count `1`
  - remote logout buttons `2`
  - selected-device revoke mutation count `1`
  - `logout-others` mutation count `1`
  - `logout-all` mutation count `1`
  - final redirect `/en-EN/login`

### Final evidence

- Summary: `evidence/partner/CYBA-610/playwright-security-sessions-summary.json`
- Final Playwright log: `evidence/partner/CYBA-610/playwright-security-sessions-rerun-after-CYBA-621-final.log`
- Targeted Vitest log: `evidence/partner/CYBA-610/targeted-vitest-rerun-after-CYBA-621.log`
- Screenshots:
  - `evidence/partner/CYBA-610/screenshots/CYBA-610__partner-security-sessions__safe-fixture__en-EN__desktop-1440__initial__pass__20260609.png`
  - `evidence/partner/CYBA-610/screenshots/CYBA-610__partner-security-sessions__safe-fixture__en-EN__desktop-1440__after-revoke-device__pass__20260609.png`
  - `evidence/partner/CYBA-610/screenshots/CYBA-610__partner-security-sessions__safe-fixture__en-EN__desktop-1440__after-logout-others__pass__20260609.png`
  - `evidence/partner/CYBA-610/screenshots/CYBA-610__partner-security-sessions__safe-fixture__en-EN__desktop-1440__after-logout-all__pass__20260609.png`

Context7 docs checked: MCP quota exceeded. ctx7 fallback evidence remains `/microsoft/playwright` and `/vercel/next.js/v16.2.2`; no new docs behavior conclusion was needed for this final retest.
