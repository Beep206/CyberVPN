# CYBA-595 Final Auth UX QA Evidence

Timestamp: `2026-06-06T18:09:19Z`
Issue: [CYBA-595](/CYBA/issues/CYBA-595)
Agent: `qa-client-frontend-manual`

## Environment

- Browser/runtime: local Chromium/CDP smoke via existing `frontend/scripts/login-passkey-browser-smoke.mjs`.
- Frontend checked:
  - `http://127.0.0.1:13000`: reachable but failed this passkey CTA smoke before auth submit; treated as stale/not-suitable preview for this scoped auth evidence.
  - `http://127.0.0.1:9001`: current checkout dev server, launched only for QA with `API_INTERNAL_ORIGIN=http://127.0.0.1:18080`, `API_URL=http://127.0.0.1:18080`, `NEXT_TELEMETRY_DISABLED=1`.
- Backend readiness: `http://127.0.0.1:18080/readiness` reachable.
- User role/state: mocked/synthetic customer auth browser smoke only; no production data, cookies, JWT, refresh token, passwords, payment data, VPN config secrets, or Telegram `initData` stored.

## Results

- PASS: delayed-session successful login smoke on `9001`.
  - Evidence: `network/login-passkey-smoke-9001-20260606T1812Z.json`.
  - `sessionResponseDelayMs=2500`.
  - `postLoginNavigationBudgetMs=1000`.
  - `postLoginNavigationLatencyMs=660`.
  - Passkey autocomplete: `username webauthn`.
  - Conditional passkey request body: `{ "conditional": true, "identifier": null }`.
- PASS: targeted auth regression tests.
  - Evidence: `network/targeted-auth-tests-20260606T1831Z.log`.
  - Result: `3 passed (3)`, `99 passed (99)`.
- PASS: targeted 3D/layout regression tests.
  - Evidence: `network/targeted-layout-3d-tests-20260606T1814Z.log`.
  - Result: `2 passed (2)`, `23 passed (23)`.
- PASS: auth 3D frame-delta evidence from [CYBA-593](/CYBA/issues/CYBA-593) is mirrored into this pack.
  - Evidence: `network/auth-3d-freeze-summary-from-cyba-593.json`.
  - Login/register focus+hover checked at `390x844`, `768x1024`, `1440x900`; all `frameChanged=true`, `checksPassed=true`.
- PASS: passkey/OAuth spacing evidence from [CYBA-594](/CYBA/issues/CYBA-594) is mirrored into this pack.
  - Evidence: `network/passkey-oauth-spacing-summary-from-cyba-594.json`.
  - Gap is `15.5px` mobile and `19.44px` tablet/desktop; provider order remains `google`, `github`, `telegram`.
- PASS: no-secret scan.
  - Evidence: `network/no-secret-scan-20260606T1815Z.txt`.
  - Result: `No sensitive value hits.`

## Screenshots

- 3D focus/hover:
  - `screenshots/login-mobile-390x844-3d-focused-after.png`
  - `screenshots/register-mobile-390x844-3d-focused-after.png`
  - `screenshots/login-tablet-768x1024-3d-focused-after.png`
  - `screenshots/register-tablet-768x1024-3d-focused-after.png`
  - `screenshots/login-desktop-1440x900-3d-focused-after.png`
  - `screenshots/register-desktop-1440x900-3d-focused-after.png`
- Passkey/OAuth spacing:
  - `screenshots/login-mobile-390x844-passkey-oauth-spacing.png`
  - `screenshots/login-tablet-768x1024-passkey-oauth-spacing.png`
  - `screenshots/login-desktop-1440x900-passkey-oauth-spacing.png`

## Product Gaps / Not Tested

- Real production/staging credentials and production testing were not used.
- Real passkey ceremony, OAuth provider round-trip, payment capture, VPN config delivery, and Telegram Mini App signed entry were not executed.
- Safe fixtures remain limited to synthetic/empty-state coverage already documented under prior client QA issues.
- SecurityEngineer signoff completed in [CYBA-596](/CYBA/issues/CYBA-596).

## Security Signoff

- Status: approved.
- Source: [CYBA-596](/CYBA/issues/CYBA-596) comment at `2026-06-06T18:17:43Z`.
- Summary: `Approved: auth redirect/session behavior acceptable for this scope.`
- Security review lenses: OWASP Auth Failures, Broken Access Control, Open Redirect, Sensitive Data Exposure, WebAuthn identifier disclosure, secure defaults, fail securely, complete mediation.
- Residual risk accepted for this scope: sanitized local/mock evidence only; real production/staging credentials, real passkey ceremony, OAuth provider round-trip, payment, VPN delivery, and Telegram signed `initData` were not tested.

Context7 docs checked: MCP Context7 quota exceeded; `ctx7 library Playwright` resolved `/microsoft/playwright`, but no new Playwright code was written for this pack. Manual UI/business-flow findings are `N/A - manual UI/business-flow finding`.
