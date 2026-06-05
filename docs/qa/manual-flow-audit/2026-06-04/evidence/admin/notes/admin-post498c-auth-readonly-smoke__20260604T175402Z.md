# CYBA-458 Post-CYBA-498 Corrected Admin Auth Read-Only Smoke

Related issue: [CYBA-458](/CYBA/issues/CYBA-458)

Related fixes: [CYBA-463](/CYBA/issues/CYBA-463), [CYBA-484](/CYBA/issues/CYBA-484), [CYBA-498](/CYBA/issues/CYBA-498)

Timestamp: `20260604T175402Z`

Environment: local-stage admin `http://127.0.0.1:13001`, backend `http://127.0.0.1:18080`, Chromium headless desktop `1440x1000`, locale `en-EN`.

Overall result: `PASS`

## Invalid Login Regression

Result: `PASS`; login status `401`; saw `/api/v1/auth/refresh`: `false`; alert: `Invalid credentials.`.

Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-LOGIN-NEG-001__admin-panel__anonymous__en-EN__desktop-1440__20260604T175402Z.png`

## Authenticated Fixture Attempts

Credentials came from protected runtime secret file and are not stored.

- OWNER: login `200`, 2FA attempted `true`, 2FA status `200`, session `200`, alert `null`, screenshot `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-AUTH-OWNER-LOGIN-001__admin-panel__owner__en-EN__desktop-1440__pass__20260604T175402Z.png`

Selected role for route smoke: `OWNER`.

## Protected Read-Only Routes

| Case | Area | Path | Current path | Heading/title | Result | Evidence |
|---|---|---|---|---|---|---|
| MF-ADM-POST498C-DASH-001 | Dashboard | `/en-EN/dashboard` | `/en-EN/dashboard` | `OZOXY COMMAND CENTER` | `PASS` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-DASH-001__admin-panel__owner__en-EN__desktop-1440__pass__20260604T175402Z.png` |
| MF-ADM-POST498C-CUST-001 | Customers | `/en-EN/customers` | `/en-EN/customers` | `Customer Directory` | `PASS` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-CUST-001__admin-panel__owner__en-EN__desktop-1440__pass__20260604T175402Z.png` |
| MF-ADM-POST498C-C360-001 | Customer 360 synthetic id | `/en-EN/customers/test-user-001` | `/en-EN/customers/test-user-001` | `SYSTEM FAILURE` | `PASS` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-C360-001__admin-panel__owner__en-EN__desktop-1440__pass__20260604T175402Z.png` |
| MF-ADM-POST498C-PAY-001 | Payments | `/en-EN/commerce/payments` | `/en-EN/commerce/payments` | `Payments Console` | `PASS` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-PAY-001__admin-panel__owner__en-EN__desktop-1440__pass__20260604T175402Z.png` |
| MF-ADM-POST498C-WALLET-001 | Wallets | `/en-EN/commerce/wallets` | `/en-EN/commerce/wallets` | `Wallet Operations` | `PASS` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-WALLET-001__admin-panel__owner__en-EN__desktop-1440__pass__20260604T175402Z.png` |
| MF-ADM-POST498C-WITHDRAW-001 | Withdrawals | `/en-EN/commerce/withdrawals` | `/en-EN/commerce/withdrawals` | `Withdrawal Queue` | `PASS` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-WITHDRAW-001__admin-panel__owner__en-EN__desktop-1440__pass__20260604T175402Z.png` |
| MF-ADM-POST498C-PARTNER-001 | Partners | `/en-EN/growth/partners` | `/en-EN/growth/partners` | `Partner Operations` | `PASS` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-PARTNER-001__admin-panel__owner__en-EN__desktop-1440__pass__20260604T175402Z.png` |
| MF-ADM-POST498C-REF-001 | Referrals | `/en-EN/growth/referrals` | `/en-EN/growth/risk` | `Referral Signals` | `PASS` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-REF-001__admin-panel__owner__en-EN__desktop-1440__pass__20260604T175402Z.png` |
| MF-ADM-POST498C-PLANS-001 | Pricing/plans | `/en-EN/commerce/plans` | `/en-EN/commerce/plans` | `Plan Management` | `PASS` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-PLANS-001__admin-panel__owner__en-EN__desktop-1440__pass__20260604T175402Z.png` |
| MF-ADM-POST498C-SESS-001 | Sessions | `/en-EN/security/sessions` | `/en-EN/security/sessions` | `Sessions Console` | `PASS` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-SESS-001__admin-panel__owner__en-EN__desktop-1440__pass__20260604T175402Z.png` |
| MF-ADM-POST498C-AUDIT-001 | Audit log | `/en-EN/governance/audit-log` | `/en-EN/governance/audit-log` | `Audit Explorer` | `PASS` | `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-AUDIT-001__admin-panel__owner__en-EN__desktop-1440__pass__20260604T175402Z.png` |

Logout: `403`, post-logout path `/en-EN/login`, screenshot `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-LOGOUT-001__admin-panel__owner__en-EN__desktop-1440__fail__20260604T175402Z.png`.

Raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-post498c-auth-readonly-smoke__20260604T175402Z.json`

Sensitive-data review: PASS - credentials, TOTP values, cookies, JWTs, refresh tokens, storage state, headers, payment secrets, customer PII, and production data were not stored. Screenshots contain approved local-stage synthetic UI only.

Context7 docs checked: MCP quota exceeded; fallback ctx7 docs /microsoft/playwright checked chromium.launch, newContext, page.goto, locators, waitForResponse, waitForURL, and screenshot APIs.
