# MF-ADM-LOGIN-NEG-POSTFIX-001

Related issue: [CYBA-458](/CYBA/issues/CYBA-458)

Related fix: [CYBA-463](/CYBA/issues/CYBA-463)

Timestamp: `20260604T164231Z`

Environment: local-stage admin `http://127.0.0.1:13001`, backend health `http://127.0.0.1:18080/health`, Chromium headless desktop `1440x1000`, locale `en-EN`.

User role/state: anonymous visitor, synthetic invalid login attempt with `test-admin-001@example.test`.

## Result

Status: `FAIL`

- `POST /api/v1/auth/login` status: `401`
- Saw `/api/v1/auth/refresh`: `true`
- Alert text: `null`
- Refresh-token detail visible: `false`

## Evidence

- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-LOGIN-NEG-POSTFIX-001__admin-panel__anonymous__en-EN__desktop-1440__pass__20260604T164231Z.png`
- Raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-login-negative-postfix-summary__20260604T164231Z.json`

Sensitive-data review: PASS - synthetic email only; password value, cookies, JWTs, refresh tokens, storage state, headers, HAR, trace, payment data, and production PII were not stored.

Context7 docs checked: MCP quota exceeded; fallback ctx7 docs /microsoft/playwright checked for chromium.launch, newContext, page.goto, locators, waitForResponse, and screenshot APIs.
