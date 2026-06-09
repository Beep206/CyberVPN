# Partner portal raw notes

Дата: `2026-06-04`

Основной журнал partner manual QA ведется здесь:

- `docs/qa/manual-flow-audit/2026-06-04/raw-notes/agent-partner.md`

## CYBA-520 heartbeat snapshot

- Issue: [CYBA-520](/CYBA/issues/CYBA-520)
- Wake reason: `issue_blockers_resolved`; [CYBA-519](/CYBA/issues/CYBA-519) was `done`.
- Retest target: `http://portal.localhost:3004` against backend `http://127.0.0.1:18080`.
- Account: protected synthetic `CYBA451_PARTNER_OWNER` fixture; credentials, TOTP, tokens, cookie values, storageState, HAR, trace, payment secrets, production PII, and Telegram initData were not stored.
- Result: `FAIL`.
- First failing transition: `POST /api/auth/2fa/complete -> 401`.
- Cookie state: after `POST /api/auth/2fa/pending`, only `pending_2fa` existed for `portal.localhost`; after complete, cookies were `[]`.
- Session check: `GET /api/v1/auth/session -> 401`.
- Protected routes `/en-EN/dashboard`, `/en-EN/codes`, `/en-EN/finance`, `/en-EN/conversions`, and `/en-EN/team` redirected to login.
- Evidence JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-520__partner-2fa-session-retest__20260604T202139Z.json`

Context7 docs checked: unavailable - quota exceeded. Fallback official docs checked: Playwright `browser.newContext`, `context.cookies`, `page.goto`, `page.screenshot`, and `chromium.launch`.

## CYBA-523 heartbeat snapshot

- Issue: [CYBA-523](/CYBA/issues/CYBA-523)
- Причина wake: `issue_blockers_resolved`; [CYBA-522](/CYBA/issues/CYBA-522) перешла в `done`.
- Цель ретеста: `http://portal.localhost:3004` с backend `http://127.0.0.1:18080`.
- Account: protected synthetic `CYBA451_PARTNER_OWNER` fixture; credentials, TOTP, tokens, cookie values, storageState, HAR, trace, payment secrets, production PII и Telegram initData не сохранялись.
- Результат: `PASS`.
- Auth flow: `POST /api/v1/auth/login -> 200`, `requires_2fa=true`; `POST /api/auth/2fa/pending -> 204`; `POST /api/auth/2fa/complete -> 200`, `redirect_to=/en-EN/dashboard`; `GET /api/v1/auth/session -> 200`, `auth_realm_key=partner`.
- Cookie state после complete:
  - root-origin probe `context.cookies('http://portal.localhost:3004')` -> `[]`
  - path-matched probe `context.cookies('http://portal.localhost:3004/api/v1/auth/session')` -> `partner_access_token`, `partner_refresh_token`, both `Path=/api`
- Protected routes `/en-EN/dashboard`, `/en-EN/codes`, `/en-EN/finance`, `/en-EN/conversions` и `/en-EN/team` отрендерились без login redirect и без `SYSTEM FAILURE`.
- Evidence JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-523__partner-2fa-path-cookie-retest__20260604T210730Z.json`

Context7 MCP проверен: quota exceeded. ctx7 fallback проверен: `/microsoft/playwright` `BrowserContext.cookies(urls)` и `page.screenshot` path option.

## CYBA-573 heartbeat snapshot

- Issue: [CYBA-573](/CYBA/issues/CYBA-573)
- Причина wake: `issue_blockers_resolved`; blocker [CYBA-569](/CYBA/issues/CYBA-569) был закрыт, поэтому recheck выполнялся на текущем clean `main`-baseline без повторного checkout.
- Scope: partner portal business-flow recheck для access/visibility, partner codes/markup, team access, finance balances/payout posture, conversion attribution/explainability.
- Environment: local `partner` Next dev server `http://127.0.0.1:3002`, Chromium via Playwright, viewport `1440x1000`, locale `en-EN`.
- Data safety: использован synthetic safe fixture `Safe Partner Lab`, partner code `CYBA-SAFE-42`, masked customers (`masked-customer-*`), masked payout account `Bank **** 4242`; credentials, JWT/cookies/storageState, payment secrets, production PII и Telegram initData не сохранялись.
- Targeted partner Vitest:
  - `npm run test:run -- src/lib/api/__tests__/partner-portal.test.ts src/features/partner-portal-state/lib/safe-partner-fixtures.test.ts src/features/partner-portal-state/lib/portal-access.test.ts src/features/partner-portal-state/lib/portal-visibility.test.ts src/features/partner-portal-state/components/partner-route-guard.test.tsx src/features/partner-finance/lib/finance-contract.test.ts src/features/partner-commercial/lib/commercial-capabilities.test.ts src/features/partner-operations/lib/reporting-finance-capabilities.test.ts`
  - Result: `8 passed`, `48 passed`.
- Playwright rerun:
  - Harness: `evidence/partner/CYBA-573/cyba-573-partner-smoke-rerun.mjs`
  - Summary: `evidence/partner/CYBA-573/playwright-ui-smoke-summary.json`
  - Log: `evidence/partner/CYBA-573/playwright-ui-smoke-rerun.log`
  - Assertions used full normalized body text; `bodyTextSample` is truncated evidence only.
- Business-flow content result: `PASS` for `/en-EN/dashboard`, `/en-EN/codes`, `/en-EN/finance`, `/en-EN/conversions`, `/en-EN/team`; no `SYSTEM FAILURE`, no `pageErrors`.
- Corrected earlier false negatives:
  - Finance contains `SAFE FIXTURE SETTLEMENT ACCOUNT` and `$280.00`; earlier mixed-case expected text caused a false miss.
  - Conversions contains `masked-customer-001`, `CYBA-SAFE-42`, and contract-backed explainability `eligible`; rerun used required `commissionability_evaluation` response and called `/conversion-records/safe-conversion-first-paid/explainability`.
- Findings left after rerun:
  - `P3` i18n/UX bug: `/en-EN/codes` logs `IntlError: MISSING_MESSAGE` for `Partner.codes.modes.review`.
  - `P4` product/observability gap: local smoke logs 403 responses for `POST /api/analytics/web-vitals`, `POST /api/analytics/product-events`, and `POST /api/analytics/traffic`; these are `navigator.sendBeacon` telemetry calls and did not block partner business content.
- Local dev server started only for this smoke and stopped after evidence collection; `127.0.0.1:3002` no longer listening.

Context7 MCP проверен: quota exceeded. ctx7 fallback проверен: `/microsoft/playwright` `page.goto`, route mocks, console capture, screenshot; `/amannn/next-intl` missing-message `IntlErrorCode.MISSING_MESSAGE`, `onError`, `getMessageFallback`.

## CYBA-610 heartbeat snapshot

- Issue: [CYBA-610](/CYBA/issues/CYBA-610)
- Причина wake: `issue_blockers_resolved`; blocker [CYBA-604](/CYBA/issues/CYBA-604) был `done`.
- Scope: partner security sessions browser QA для unique devices, current badge, selected-device revoke, `logout-others`, and realm-scoped `logout-all`.
- Environment: local `partner` Next dev server `http://127.0.0.1:3002`, Chromium via Playwright, viewport `1440x1000`, locale `en-EN`.
- User role/state: `partner_operator`, development bypass, synthetic safe device fixture.
- Data safety: credentials, cookies, JWTs, refresh tokens, storageState, HAR, payment data, production PII и Telegram `initData` не сохранялись.
- Targeted partner Vitest:
  - `npm run test:run -- src/features/security/components/__tests__/security-sessions-console.test.tsx`
  - Result: `1 passed`, `4 passed`.
- Browser smoke result: `FAIL`.
  - `GET /en-EN/security/sessions -> 404`.
  - Route body rendered global not-found: `SIGNAL LOST / REQUESTED COORDINATES NOT FOUND IN NETWORK`.
  - No `GET /api/v1/auth/devices` fired, `mutations=[]`, so selected-device revoke, `logout-others`, current badge, and `logout-all` browser behavior could not be exercised.
- Route/source context:
  - `SecuritySessionsConsole` is only wired through `partner/src/app/[locale]/(dashboard)/_legacy-admin-routes/security/sessions/page.tsx`.
  - `/_legacy-admin-routes/security` is retired to `/settings`, and `/settings` only exposes a `reviewedActiveSessions` settings toggle rather than revoke/logout device controls.
- Evidence:
  - Summary: `evidence/partner/CYBA-610/playwright-security-sessions-summary.json`
  - Log: `evidence/partner/CYBA-610/playwright-security-sessions.log`
  - Screenshot: `evidence/partner/CYBA-610/screenshots/CYBA-610__partner-security-sessions__safe-fixture__en-EN__desktop-1440__initial__fail__20260609.png`
  - Targeted Vitest log: `evidence/partner/CYBA-610/targeted-vitest.log`
  - Notes: `evidence/partner/CYBA-610/notes/cyba-610-partner-security-sessions.md`
- Follow-up: [CYBA-619](/CYBA/issues/CYBA-619) assigned to Prism Admin Partner Frontend Engineer; [CYBA-610](/CYBA/issues/CYBA-610) remains blocked pending fix and retest.

Context7 docs checked: MCP quota exceeded. ctx7 fallback checked `/microsoft/playwright` for route mocks/navigation/screenshot/response capture and `/vercel/next.js/v16.2.2` for App Router private folders; Next docs state underscore-prefixed folders opt the folder and all subfolders out of routing.

## CYBA-610 post-CYBA-619 retest snapshot

- Issue: [CYBA-610](/CYBA/issues/CYBA-610)
- Wake reason: `issue_children_completed`; child [CYBA-619](/CYBA/issues/CYBA-619) was `done`.
- Scope: retest partner security sessions after route fix.
- Environment: local `partner` Next dev server `http://127.0.0.1:3002`, Chromium via Playwright, viewport `1440x1000`, locale `en-EN`.
- User role/state: `partner_operator`, development bypass, synthetic safe device fixture.
- Data safety: credentials, cookies, JWTs, refresh tokens, storageState, HAR, payment data, production PII и Telegram `initData` не сохранялись.
- Route state after [CYBA-619](/CYBA/issues/CYBA-619):
  - `GET /en-EN/security/sessions -> 200`.
  - New focused route/unit tests passed.
- Targeted partner Vitest rerun:
  - `npm run test:run -- 'src/app/[locale]/(dashboard)/security/sessions/__tests__/page.test.tsx' src/features/security/components/__tests__/security-sessions-console.test.tsx`
  - Result: `2 passed`, `6 passed`.
- Browser smoke result: `BLOCKED/FAIL` due runtime hydration error.
  - Final bounded run: `pageErrors=[Invalid or unexpected token]`, `pass=false`.
  - Body remained around `AUTHENTICATING...`; device rows/actions were not reliably reachable.
  - One earlier action run did execute the core mocked actions despite the same page error: current badge count `1`, remote logout buttons `2`, `DELETE /api/v1/auth/devices/dev_remote_android` once, `POST /api/v1/auth/devices/logout-others` once, `POST /api/v1/auth/logout-all` once, login redirect `true`.
  - Because the same browser runtime error can block initial hydration, stable QA signoff is not possible yet.
- Evidence:
  - Canonical failed summary: `evidence/partner/CYBA-610/playwright-security-sessions-summary.json`
  - Final failed log: `evidence/partner/CYBA-610/playwright-security-sessions-rerun-after-CYBA-619-final-second.log`
  - Partial action log: `evidence/partner/CYBA-610/playwright-security-sessions-rerun-after-CYBA-619-final.log`
  - Runtime probe log: `evidence/partner/CYBA-610/runtime-error-probe-after-CYBA-619-second.log`
  - Targeted Vitest log: `evidence/partner/CYBA-610/targeted-vitest-rerun-after-CYBA-619.log`
  - Screenshots: `evidence/partner/CYBA-610/screenshots/`
- Follow-up: [CYBA-621](/CYBA/issues/CYBA-621) assigned to Prism Admin Partner Frontend Engineer; [CYBA-610](/CYBA/issues/CYBA-610) remains blocked pending stable hydration fix and retest.

Context7 docs checked: MCP quota exceeded. ctx7 fallback from this QA packet remains `/microsoft/playwright` for route mocks/navigation/screenshot/response capture and `/vercel/next.js/v16.2.2` for App Router route behavior.

## CYBA-610 post-CYBA-621 final retest snapshot

- Issue: [CYBA-610](/CYBA/issues/CYBA-610)
- Wake reason: `issue_children_completed`; child [CYBA-621](/CYBA/issues/CYBA-621) was `done`.
- Scope: final partner security sessions browser retest after route and hydration fixes.
- Environment: local `partner` Next dev server `http://127.0.0.1:3002`, Chromium via Playwright, viewport `1440x1000`, locale `en-EN`.
- User role/state: `partner_operator`, development bypass, synthetic safe device fixture.
- Data safety: credentials, cookies, JWTs, refresh tokens, storageState, HAR, payment data, production PII и Telegram `initData` не сохранялись.
- Route status:
  - `HEAD /en-EN/security/sessions -> 200`
  - `HEAD /en-EN/login -> 200`
- Targeted partner Vitest rerun:
  - `npm run test:run -- 'src/app/[locale]/(dashboard)/security/sessions/__tests__/page.test.tsx' src/features/security/components/__tests__/security-sessions-console.test.tsx`
  - Result: `2 passed`, `6 passed`.
- Browser smoke final result: `PASS`.
  - Summary `pass=true`.
  - `pageErrors=[]`.
  - `failedResponses=[]`.
  - Initial render: current badge count `1`, remote logout buttons `2`, expected device labels/IPs present, device limit `3/5`.
  - Selected-device revoke: `DELETE /api/v1/auth/devices/dev_remote_android` once; selected remote IP absent afterward; other remote IP still present.
  - `logout-others`: `POST /api/v1/auth/devices/logout-others` once; remaining remote IP absent; current device still present.
  - `logout-all`: `POST /api/v1/auth/logout-all` once; redirected to `/en-EN/login`.
- Evidence:
  - Summary: `evidence/partner/CYBA-610/playwright-security-sessions-summary.json`
  - Final log: `evidence/partner/CYBA-610/playwright-security-sessions-rerun-after-CYBA-621-final.log`
  - Targeted Vitest log: `evidence/partner/CYBA-610/targeted-vitest-rerun-after-CYBA-621.log`
  - Screenshots:
    - `evidence/partner/CYBA-610/screenshots/CYBA-610__partner-security-sessions__safe-fixture__en-EN__desktop-1440__initial__pass__20260609.png`
    - `evidence/partner/CYBA-610/screenshots/CYBA-610__partner-security-sessions__safe-fixture__en-EN__desktop-1440__after-revoke-device__pass__20260609.png`
    - `evidence/partner/CYBA-610/screenshots/CYBA-610__partner-security-sessions__safe-fixture__en-EN__desktop-1440__after-logout-others__pass__20260609.png`
    - `evidence/partner/CYBA-610/screenshots/CYBA-610__partner-security-sessions__safe-fixture__en-EN__desktop-1440__after-logout-all__pass__20260609.png`

Context7 docs checked: MCP quota exceeded. ctx7 fallback evidence remains `/microsoft/playwright` for route mocks/navigation/screenshot/response capture and `/vercel/next.js/v16.2.2` for App Router route behavior. No external docs were newly required for this pure retest.
