# CYBA-458 Post-Fix Admin Smoke

Related issue: [CYBA-458](/CYBA/issues/CYBA-458)

Related fixes: [CYBA-463](/CYBA/issues/CYBA-463), [CYBA-484](/CYBA/issues/CYBA-484)

Timestamp: `20260604T171556Z`

Environment: local-stage admin `http://127.0.0.1:13001`, backend `http://127.0.0.1:18080`, Chromium headless desktop `1440x1000`, locale `en-EN`.

Overall result: `FAIL`

## Invalid Login Regression

Result: `FAIL`; login status `401`; saw `/api/v1/auth/refresh`: `true`; alert: `null`.

Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POSTFIX-LOGIN-NEG-002__admin-panel__anonymous__en-EN__desktop-1440__20260604T171556Z.png`

## Authenticated Read-Only Smoke

Role/state: synthetic `owner` / `owner/super_admin`; credentials came from protected runtime secret file and are not stored.

Login/session: `status=401`, `role=null`, 2FA attempted `false`.

| Case | Area | Path | Current path | Heading/title | Result | Evidence |
|---|---|---|---|---|---|---|
| MF-ADM-POSTFIX-DASH-001 | Dashboard | `/en-EN/dashboard` | `/en-EN/login?<redacted-query>` | `Sign In` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POSTFIX-DASH-001__admin-panel__owner-super-admin__en-EN__desktop-1440__fail__20260604T171556Z.png` |
| MF-ADM-POSTFIX-CUST-001 | Customers | `/en-EN/customers` | `/en-EN/login?<redacted-query>` | `Sign In` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POSTFIX-CUST-001__admin-panel__owner-super-admin__en-EN__desktop-1440__fail__20260604T171556Z.png` |
| MF-ADM-POSTFIX-C360-001 | Customer 360 synthetic id | `/en-EN/customers/test-user-001` | `/en-EN/login?<redacted-query>` | `Sign In` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POSTFIX-C360-001__admin-panel__owner-super-admin__en-EN__desktop-1440__fail__20260604T171556Z.png` |
| MF-ADM-POSTFIX-PAY-001 | Payments | `/en-EN/commerce/payments` | `/en-EN/login?<redacted-query>` | `Sign In` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POSTFIX-PAY-001__admin-panel__owner-super-admin__en-EN__desktop-1440__fail__20260604T171556Z.png` |
| MF-ADM-POSTFIX-WALLET-001 | Wallets | `/en-EN/commerce/wallets` | `/en-EN/login?<redacted-query>` | `Sign In` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POSTFIX-WALLET-001__admin-panel__owner-super-admin__en-EN__desktop-1440__fail__20260604T171556Z.png` |
| MF-ADM-POSTFIX-WITHDRAW-001 | Withdrawals | `/en-EN/commerce/withdrawals` | `/en-EN/login?<redacted-query>` | `Sign In` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POSTFIX-WITHDRAW-001__admin-panel__owner-super-admin__en-EN__desktop-1440__fail__20260604T171556Z.png` |
| MF-ADM-POSTFIX-PARTNER-001 | Partners | `/en-EN/growth/partners` | `/en-EN/login?<redacted-query>` | `Sign In` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POSTFIX-PARTNER-001__admin-panel__owner-super-admin__en-EN__desktop-1440__fail__20260604T171556Z.png` |
| MF-ADM-POSTFIX-REF-001 | Referrals | `/en-EN/growth/referrals` | `/en-EN/login?<redacted-query>` | `Sign In` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POSTFIX-REF-001__admin-panel__owner-super-admin__en-EN__desktop-1440__fail__20260604T171556Z.png` |
| MF-ADM-POSTFIX-PLANS-001 | Pricing/plans | `/en-EN/commerce/plans` | `/en-EN/login?<redacted-query>` | `Sign In` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POSTFIX-PLANS-001__admin-panel__owner-super-admin__en-EN__desktop-1440__fail__20260604T171556Z.png` |
| MF-ADM-POSTFIX-SESS-001 | Sessions | `/en-EN/security/sessions` | `/en-EN/login?<redacted-query>` | `Sign In` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POSTFIX-SESS-001__admin-panel__owner-super-admin__en-EN__desktop-1440__fail__20260604T171556Z.png` |
| MF-ADM-POSTFIX-AUDIT-001 | Audit log | `/en-EN/governance/audit-log` | `/en-EN/login?<redacted-query>` | `Sign In` | `FAIL` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POSTFIX-AUDIT-001__admin-panel__owner-super-admin__en-EN__desktop-1440__fail__20260604T171556Z.png` |

Logout: response `{"status":422}`, post-logout path `/en-EN/login?<redacted-query>`, screenshot `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POSTFIX-LOGOUT-001__admin-panel__owner-super-admin__en-EN__desktop-1440__pass__20260604T171556Z.png`.

Raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-postfix-auth-smoke__20260604T171556Z.json`

Sensitive-data review: PASS - credentials, TOTP, cookies, JWTs, refresh tokens, storage state, headers, payment secrets, customer PII, and production data were not stored. Screenshots contain approved local-stage synthetic UI only.

Context7 docs checked: MCP quota exceeded; fallback ctx7 docs /microsoft/playwright checked for chromium.launch, newContext, page.goto, locators, waitForResponse, waitForURL, and screenshot APIs.
