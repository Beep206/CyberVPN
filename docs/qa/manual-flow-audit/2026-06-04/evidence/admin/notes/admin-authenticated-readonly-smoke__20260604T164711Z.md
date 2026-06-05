# MF-ADM-AUTH-READONLY-SMOKE

Related issue: [CYBA-458](/CYBA/issues/CYBA-458)

Timestamp: `20260604T164711Z`

Environment: local-stage admin `http://127.0.0.1:13001`, backend `http://127.0.0.1:18080`, Chromium headless desktop `1440x1000`, locale `en-EN`.

Role/state: synthetic `operator` / `operator`; credentials came from protected runtime secret file and are not stored.

Result: `FAIL`

Login/session: `status=200`, `role=operator`, 2FA attempted `true`.

## Route Results

| Case | Area | Path | Current path | Result | Evidence |
|---|---|---|---|---|---|
| MF-ADM-AUTH-DASH-001 | Dashboard | `/en-EN/dashboard` | `/en-EN/login?<redacted-query>` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-AUTH-DASH-001__admin-panel__operator__en-EN__desktop-1440__fail__20260604T164711Z.png` |
| MF-ADM-AUTH-CUST-001 | Customers | `/en-EN/customers` | `/en-EN/login?<redacted-query>` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-AUTH-CUST-001__admin-panel__operator__en-EN__desktop-1440__fail__20260604T164711Z.png` |
| MF-ADM-AUTH-PAY-001 | Payments | `/en-EN/commerce/payments` | `/en-EN/login?<redacted-query>` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-AUTH-PAY-001__admin-panel__operator__en-EN__desktop-1440__fail__20260604T164711Z.png` |
| MF-ADM-AUTH-WALLET-001 | Wallets | `/en-EN/commerce/wallets` | `/en-EN/login?<redacted-query>` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-AUTH-WALLET-001__admin-panel__operator__en-EN__desktop-1440__fail__20260604T164711Z.png` |
| MF-ADM-AUTH-WITHDRAW-001 | Withdrawals | `/en-EN/commerce/withdrawals` | `/en-EN/login?<redacted-query>` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-AUTH-WITHDRAW-001__admin-panel__operator__en-EN__desktop-1440__fail__20260604T164711Z.png` |
| MF-ADM-AUTH-PARTNER-001 | Partners | `/en-EN/growth/partners` | `/en-EN/login?<redacted-query>` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-AUTH-PARTNER-001__admin-panel__operator__en-EN__desktop-1440__fail__20260604T164711Z.png` |
| MF-ADM-AUTH-REF-001 | Referrals | `/en-EN/growth/referrals` | `/en-EN/login?<redacted-query>` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-AUTH-REF-001__admin-panel__operator__en-EN__desktop-1440__fail__20260604T164711Z.png` |
| MF-ADM-AUTH-PLANS-001 | Pricing/plans | `/en-EN/commerce/plans` | `/en-EN/login?<redacted-query>` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-AUTH-PLANS-001__admin-panel__operator__en-EN__desktop-1440__fail__20260604T164711Z.png` |
| MF-ADM-AUTH-SESS-001 | Sessions | `/en-EN/security/sessions` | `/en-EN/login?<redacted-query>` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-AUTH-SESS-001__admin-panel__operator__en-EN__desktop-1440__fail__20260604T164711Z.png` |
| MF-ADM-AUTH-AUDIT-001 | Audit log | `/en-EN/governance/audit-log` | `/en-EN/login?<redacted-query>` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-AUTH-AUDIT-001__admin-panel__operator__en-EN__desktop-1440__fail__20260604T164711Z.png` |

Login screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-AUTH-LOGIN-001__admin-panel__operator__en-EN__desktop-1440__pass__20260604T164711Z.png`

Raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-authenticated-readonly-smoke__20260604T164711Z.json`

Logout probe: `{"status":403}`

Sensitive-data review: PASS - credentials, TOTP, cookies, JWTs, refresh tokens, storage state, headers, payment secrets, and production PII were not stored. Screenshots contain only approved local-stage synthetic UI state.

Context7 docs checked: MCP quota exceeded; fallback ctx7 docs /microsoft/playwright checked for chromium.launch, newContext, page.goto, locators, waitForResponse, waitForURL, and screenshot APIs.
