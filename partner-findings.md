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
