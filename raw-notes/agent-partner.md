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
