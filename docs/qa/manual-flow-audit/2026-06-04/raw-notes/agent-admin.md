# CYBA-458 Raw Notes: Admin Panel Manual QA

Date: `2026-06-04`
Owner: `qa-admin-panel-manual`
Parent audit: [CYBA-451](/CYBA/issues/CYBA-451)
Issue: [CYBA-458](/CYBA/issues/CYBA-458)

## Scope And Safety

- Environment used: local-stage admin `http://127.0.0.1:13001`.
- Backend health was available at `http://127.0.0.1:18080/health` and returned `{"status":"ok"}`.
- Browser: Playwright Chromium headless.
- Locales/viewports: `en-EN`, desktop `1440x1000`, mobile `390x844`.
- User role/state: anonymous; one synthetic invalid login attempt using `test-admin-001@example.test`; approved synthetic admin `operator` from protected runtime secret file for authenticated read-only smoke.
- No real credentials, cookies, storage state, JWTs, payment data, production PII, Telegram `initData`, traces, videos, HAR files, or `.env` values were stored.
- No payment capture/refund/payout, wallet top-up, withdrawal moderation action, permission change, customer mutation, VPN provisioning, or infrastructure mutation was performed.

## Executed Cases

| Case | Area | Route | Role/state | Result | Notes |
|---|---|---|---|---|---|
| MF-ADM-LOGIN-001 | Auth | `/en-EN/login` | anonymous | PASS | Login page rendered on desktop. |
| MF-ADM-MOBILE-LOGIN-001 | Auth | `/en-EN/login` | anonymous | PASS | Login page rendered on mobile. |
| MF-ADM-UNAUTH-001 | Direct URL | `/en-EN/dashboard` | anonymous | PASS | Redirected to `/en-EN/login?redirect=%2Fen-EN%2Fdashboard`; private content not visible. |
| MF-ADM-UNAUTH-002 | Customers | `/en-EN/customers` | anonymous | PASS | Redirected to login with redirect target. |
| MF-ADM-UNAUTH-003 | Customer 360 | `/en-EN/customers/test-user-001` | anonymous | PASS | Redirected to login with sanitized synthetic id in redirect target. |
| MF-ADM-UNAUTH-004 | Payments | `/en-EN/commerce/payments` | anonymous | PASS | Redirected to login with redirect target. |
| MF-ADM-UNAUTH-005 | Wallets | `/en-EN/commerce/wallets` | anonymous | PASS | Redirected to login with redirect target. |
| MF-ADM-UNAUTH-006 | Withdrawals | `/en-EN/commerce/withdrawals` | anonymous | PASS | Redirected to login with redirect target. |
| MF-ADM-UNAUTH-007 | Partners | `/en-EN/growth/partners` | anonymous | PASS | Redirected to login with redirect target. |
| MF-ADM-UNAUTH-008 | Referrals | `/en-EN/growth/referrals` | anonymous | PASS | Redirected to login with redirect target. |
| MF-ADM-UNAUTH-009 | Pricing/plans | `/en-EN/commerce/plans` | anonymous | PASS | Redirected to login with redirect target. |
| MF-ADM-UNAUTH-010 | Sessions | `/en-EN/security/sessions` | anonymous | PASS | Redirected to login with redirect target. |
| MF-ADM-UNAUTH-011 | Audit log | `/en-EN/governance/audit-log` | anonymous | PASS | Redirected to login with redirect target. |
| MF-ADM-MOBILE-UNAUTH-001 | Direct URL mobile | `/en-EN/dashboard` | anonymous | PASS | Mobile direct URL redirected to login. |
| MF-ADM-LOGIN-NEG-001 | Negative login | `/en-EN/login` | anonymous + synthetic invalid credentials | FAIL UX | Login stays on page but shows `Refresh token not provided` instead of a clear invalid credentials message. |
| MF-ADM-DEV-BYPASS-001 | Dev bypass probe | `/en-EN/dashboard` | local cookie `DEV_BYPASS_AUTH=true`, role `admin` | PASS | Follow-up probe confirmed bypass did not open admin shell; redirected to login. |
| MF-ADM-DEV-BYPASS-002 | Dev bypass probe | `/en-EN/dashboard` | local cookie `DEV_BYPASS_AUTH=true`, role `user` | PASS after correction | Initial generated summary expected `access_denied`; follow-up probe showed cookie ignored and login redirect. No product bug filed from this case. |
| MF-ADM-LOGIN-NEG-POSTFIX-001 | Negative login post-fix retest | `/en-EN/login` | anonymous + synthetic invalid credentials | FAIL VERIFY | Unit regression for [CYBA-463](/CYBA/issues/CYBA-463) passed, but current local-stage browser still made `/api/v1/auth/refresh` after invalid login. Alert text was not captured in this retest. |
| MF-ADM-AUTH-LOGIN-001 | Auth + 2FA | `/en-EN/login` | synthetic admin `operator` | PASS | Login + 2FA completed; `/api/v1/auth/session` returned `200`, role `operator`, active state true. |
| MF-ADM-AUTH-DASH-001 | Authenticated dashboard | `/en-EN/dashboard` | synthetic admin `operator` | FAIL | Redirected to `/en-EN/login?<redacted-query>` after valid session. |
| MF-ADM-AUTH-CUST-001 | Authenticated customers | `/en-EN/customers` | synthetic admin `operator` | FAIL | Redirected to `/en-EN/login?<redacted-query>` after valid session. |
| MF-ADM-AUTH-PAY-001 | Authenticated payments | `/en-EN/commerce/payments` | synthetic admin `operator` | FAIL | Redirected to `/en-EN/login?<redacted-query>` after valid session. No payment action performed. |
| MF-ADM-AUTH-WALLET-001 | Authenticated wallets | `/en-EN/commerce/wallets` | synthetic admin `operator` | FAIL | Redirected to `/en-EN/login?<redacted-query>` after valid session. No wallet action performed. |
| MF-ADM-AUTH-WITHDRAW-001 | Authenticated withdrawals | `/en-EN/commerce/withdrawals` | synthetic admin `operator` | FAIL | Redirected to `/en-EN/login?<redacted-query>` after valid session. No moderation action performed. |
| MF-ADM-AUTH-PARTNER-001 | Authenticated partners | `/en-EN/growth/partners` | synthetic admin `operator` | FAIL | Redirected to `/en-EN/login?<redacted-query>` after valid session. |
| MF-ADM-AUTH-REF-001 | Authenticated referrals | `/en-EN/growth/referrals` | synthetic admin `operator` | FAIL | Redirected to `/en-EN/login?<redacted-query>` after valid session. |
| MF-ADM-AUTH-PLANS-001 | Authenticated pricing/plans | `/en-EN/commerce/plans` | synthetic admin `operator` | FAIL | Redirected to `/en-EN/login?<redacted-query>` after valid session. No pricing mutation performed. |
| MF-ADM-AUTH-SESS-001 | Authenticated sessions | `/en-EN/security/sessions` | synthetic admin `operator` | FAIL | Redirected to `/en-EN/login?<redacted-query>` after valid session. |
| MF-ADM-AUTH-AUDIT-001 | Authenticated audit log | `/en-EN/governance/audit-log` | synthetic admin `operator` | FAIL | Redirected to `/en-EN/login?<redacted-query>` after valid session. |
| MF-ADM-POSTFIX-LOGIN-NEG-002 | Negative login post-fix smoke | `/en-EN/login` | anonymous + synthetic invalid credentials | FAIL VERIFY | After [CYBA-463](/CYBA/issues/CYBA-463) done, current `13001` still made `POST /api/v1/auth/refresh -> 401` after invalid login `401`; alert was not captured. |
| MF-ADM-POSTFIX-AUTH-LOGIN-002 | Owner auth post-fix smoke | `/en-EN/login` | synthetic `owner/super_admin` | FAIL BLOCKER | Login returned `401`; 2FA page was not reached; `/api/v1/auth/session` remained `401`. |
| MF-ADM-POSTFIX-ROUTES-001 | Protected route post-fix smoke | dashboard/customers/customer 360/payments/wallets/withdrawals/partners/referrals/plans/sessions/audit | synthetic `owner/super_admin` after failed auth | FAIL BLOCKER | All tested routes redirected to `/en-EN/login?<redacted-query>`; used only read-only navigation, no mutation performed. |
| MF-ADM-POST498C-LOGIN-NEG-001 | Negative login after runtime refresh | `/en-EN/login` | anonymous + synthetic invalid credentials | PASS | Invalid login returned `401`, did not call `/api/v1/auth/refresh`, and displayed `Invalid credentials.` |
| MF-ADM-POST498C-AUTH-OWNER-LOGIN-001 | Owner auth after runtime refresh | `/en-EN/login` | synthetic `owner/super_admin` | PASS | Login `200`, 2FA `200`, `/api/v1/auth/session -> 200`, role `owner/super_admin`, active true. |
| MF-ADM-POST498C-ROUTES-001 | Owner protected read-only routes | dashboard/customers/customer 360/payments/wallets/withdrawals/partners/referrals/plans/sessions/audit | synthetic `owner/super_admin` | PASS | All tested routes rendered without login redirect or fatal runtime error. Customer 360 synthetic id showed route-level failure state but did not break auth/session. No mutation performed. |
| MF-ADM-POST498C-UILOGOUT-001 | UI logout | user menu `Sign Out` | synthetic `owner/super_admin` | FAIL | `POST /api/v1/auth/logout -> 403`, post-logout `/api/v1/auth/session -> 200`, direct `/en-EN/dashboard` after logout still opened dashboard. Follow-up: [CYBA-507](/CYBA/issues/CYBA-507). |
| MF-ADM-POST507-LOGOUT-RETEST-001 | UI logout post-[CYBA-507] retest | user menu `Sign Out` | synthetic `owner/super_admin` | FAIL | [CYBA-507](/CYBA/issues/CYBA-507) closed, but retest still shows `POST /api/v1/auth/logout -> 403`, post-logout session `200`, direct dashboard still opens. New follow-up: [CYBA-511](/CYBA/issues/CYBA-511). |

## Evidence

- Capture summary: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-browser-capture-summary__20260604T155644Z.md`
- Raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-browser-capture-summary__20260604T155644Z.json`
- Authenticated read-only smoke summary: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-authenticated-readonly-smoke__20260604T164711Z.md`
- Authenticated read-only smoke raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-authenticated-readonly-smoke__20260604T164711Z.json`
- Invalid-login post-fix retest raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-login-negative-postfix-summary__20260604T164231Z.json`
- Post-fix admin auth/runtime smoke summary: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-postfix-auth-smoke__20260604T171556Z.md`
- Post-fix admin auth/runtime smoke raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-postfix-auth-smoke__20260604T171556Z.json`
- Post-fix runtime blocker packet: `docs/qa/manual-flow-audit/2026-06-04/evidence/bug-packets/ADM-BUG-003.md`
- Corrected post-[CYBA-498] auth/read-only smoke summary: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-post498c-auth-readonly-smoke__20260604T175402Z.md`
- Corrected post-[CYBA-498] auth/read-only smoke raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-post498c-auth-readonly-smoke__20260604T175402Z.json`
- UI logout verification summary: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-post498c-ui-logout__20260604T175704Z.md`
- UI logout verification raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-post498c-ui-logout__20260604T175704Z.json`
- Post-[CYBA-507] logout retest summary: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-post507-logout-retest__20260604T182429Z.md`
- Post-[CYBA-507] logout retest raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-post507-logout-retest__20260604T182429Z.json`
- UI logout bug packet: `docs/qa/manual-flow-audit/2026-06-04/evidence/bug-packets/ADM-BUG-004.md`
- Screenshots: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/`

## Network And Console Notes

- Anonymous direct admin routes call `/api/v1/auth/session`, receive `401`, then redirect to login as expected.
- Public login and redirected login pages repeatedly send `POST /api/analytics/web-vitals`, `POST /api/analytics/traffic`, or `POST /api/analytics/frontend-runtime`; local-stage responses were `403`, creating browser console errors.
- Invalid login produced this sequence: `POST /api/v1/auth/login -> 401`, then `POST /api/v1/auth/refresh -> 401`, and the UI alert showed `Refresh token not provided`.
- Post-fix invalid-login browser retest still observed `POST /api/v1/auth/login -> 401` followed by `POST /api/v1/auth/refresh -> 401` on current local-stage, but no visible alert was captured during that retest.
- Synthetic `operator` login produced `POST /api/v1/auth/login -> 200`, `POST /api/auth/2fa/pending -> 204`, `POST /api/auth/2fa/complete -> 200`, then `/api/v1/auth/session -> 200`.
- During protected-route checks after that valid session, each route redirected to login/access-denied; network notes repeatedly show `/api/v1/auth/session -> 200` followed by repeated `/api/v1/auth/logout -> 403`.
- Post-fix smoke after [CYBA-463](/CYBA/issues/CYBA-463) and [CYBA-484](/CYBA/issues/CYBA-484) were `done` still observed invalid-login refresh behavior and owner login `401`. Direct local `/api/v1/*` checks returned backend-style responses, so the current `13001` runtime appears stale or bypassing the expected admin route-handler proxy.
- After [CYBA-498](/CYBA/issues/CYBA-498), corrected smoke used the email fixture for the `type=email` login field and passed invalid-login regression, owner/super_admin login + 2FA, `/api/v1/auth/session -> 200`, and owner read-only protected route navigation.
- UI logout verification after owner login showed `POST /api/v1/auth/logout -> 403` with sanitized body `{"detail":"CSRF origin validation failed"}`; `/api/v1/auth/session` remained `200`, and direct `/en-EN/dashboard` after logout still opened the dashboard.
- Post-[CYBA-507] retest repeated the same logout/session failure on current local-stage; [CYBA-511](/CYBA/issues/CYBA-511) created for SecurityEngineer.

## Blocked / Not Tested

- Authenticated owner/super_admin dashboard, customers, payments, wallets, withdrawals, partners, referrals, plans, sessions, and audit-log read-only pages: passed after [CYBA-498](/CYBA/issues/CYBA-498).
- Logout behavior: blocked by `ADM-BUG-004` / [CYBA-511](/CYBA/issues/CYBA-511); [CYBA-507](/CYBA/issues/CYBA-507) failed retest and UI `Sign Out` still does not revoke the server session.
- RBAC comparison for support/finance/viewer/security roles: not completed in this heartbeat because logout/session persistence is a P1 blocker for reliable auth/session lifecycle closure; remaining role checks should resume after `ADM-BUG-004` is fixed/cleared.
- Customer/customer 360 mutations: not tested; destructive/customer mutation approval not provided.
- Payments, wallets, manual top-up, refunds/captures, withdrawals moderation, payouts/settlement: not tested; real financial operations prohibited and no explicit sandbox mutation approval.
- Remnawave/provisioning, real Telegram/OAuth/email operations: not tested; out of scope without separate approval.

## Docs Evidence

Context7 docs checked: attempted MCP `Playwright`, blocked by monthly quota. Fallback `ctx7` docs checked: `/microsoft/playwright` `Page.screenshot`, `Page.response`, `waitForLoadState`, `waitForURL`, request/response events. For `ADM-BUG-003`, fallback `ctx7 docs /vercel/next.js` checked catch-all route handling, `NextResponse.rewrite`, and `next.config.js` rewrites. For `ADM-BUG-004`, no framework root cause is asserted; fallback Playwright docs were used for browser interaction evidence. Pure UI/business-flow findings use `Context7 docs checked: N/A - manual UI/business-flow finding`.
