# ADM-BUG-002: Authenticated operator session is valid but protected admin routes redirect to login

Related issue: [CYBA-458](/CYBA/issues/CYBA-458)

Follow-up issue: [CYBA-484](/CYBA/issues/CYBA-484)

Severity: `P1`

Environment: local-stage admin `http://127.0.0.1:13001`, backend `http://127.0.0.1:18080`, Chromium headless, desktop `1440x1000`, locale `en-EN`.

User role/state: synthetic admin `operator` from protected runtime secret file `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`. Credential values, TOTP, cookies, JWTs, refresh tokens, and storage state were not stored.

## Steps To Reproduce

1. Open `http://127.0.0.1:13001/en-EN/login` in a fresh browser context.
2. Sign in with the approved synthetic admin `operator` credentials from the protected secret channel.
3. Complete the 2FA challenge with the approved synthetic TOTP secret.
4. Verify `/api/v1/auth/session` after 2FA.
5. Navigate to `/en-EN/dashboard`.
6. Repeat for `/en-EN/customers`, `/en-EN/commerce/payments`, `/en-EN/commerce/wallets`, `/en-EN/commerce/withdrawals`, `/en-EN/growth/partners`, `/en-EN/growth/referrals`, `/en-EN/commerce/plans`, `/en-EN/security/sessions`, and `/en-EN/governance/audit-log`.

## Expected

- The synthetic `operator` can access permitted admin shell/dashboard after successful login + 2FA.
- Routes outside the role's permission set should show a stable access-denied state without invalidating or looping the authenticated admin session.
- Cleanup/logout should not repeatedly fail with `403` during route guard handling.

## Actual

- Login + 2FA completed.
- `/api/v1/auth/session` returned `200`, role `operator`, `is_active=true`.
- Every tested protected admin route redirected to `/en-EN/login?<redacted-query>` with access-denied state.
- Sanitized network notes show repeated `GET /api/v1/auth/session -> 200` and repeated `POST /api/v1/auth/logout -> 403`.

## Evidence

- Summary: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-authenticated-readonly-smoke__20260604T164711Z.md`
- Raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-authenticated-readonly-smoke__20260604T164711Z.json`
- Login screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-AUTH-LOGIN-001__admin-panel__operator__en-EN__desktop-1440__pass__20260604T164711Z.png`
- Dashboard failure screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-AUTH-DASH-001__admin-panel__operator__en-EN__desktop-1440__fail__20260604T164711Z.png`

Sensitive-data review: PASS - credentials, TOTP, cookies, JWTs, refresh tokens, storage state, headers, payment secrets, and production PII were not stored. Screenshots contain only approved local-stage synthetic UI state.

Context7 docs checked: MCP quota exceeded; fallback `ctx7 docs /microsoft/playwright` checked for `chromium.launch`, `newContext`, `page.goto`, locators, `waitForResponse`, `waitForURL`, and screenshot APIs.
