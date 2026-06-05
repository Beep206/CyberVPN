# CYBA-458 Admin Findings

Date: `2026-06-04`
Owner: `qa-admin-panel-manual`
Issue: [CYBA-458](/CYBA/issues/CYBA-458)
Environment: local-stage admin `http://127.0.0.1:13001`, backend health `http://127.0.0.1:18080/health`

## Summary

Anonymous admin auth boundaries passed for the tested direct URLs: dashboard, customers, customer 360, payments, wallets, withdrawals, partners, referrals, pricing/plans, sessions, and audit log all redirected to login without exposing private content.

Readiness gate [CYBA-452](/CYBA/issues/CYBA-452) is now `GO - local-stage synthetic QA`. A synthetic `operator` admin can complete UI login + 2FA and `/api/v1/auth/session` returns `200`, but every tested protected admin route redirects back to login with `access_denied`. This blocks meaningful authenticated admin/customer/finance/RBAC page QA until fixed.

Post-fix smoke after [CYBA-498](/CYBA/issues/CYBA-498) confirmed the local-stage admin runtime is now serving the fixed bundle: invalid login no longer calls `/api/v1/auth/refresh`, synthetic `owner/super_admin` login + 2FA succeeds, `/api/v1/auth/session` returns `200`, and all tested protected read-only admin routes render without login redirects. The remaining admin auth/session blocker is logout: UI `Sign Out` redirects to login but `POST /api/v1/auth/logout` returns `403`, the server session remains active, and direct `/en-EN/dashboard` still opens after logout.

## Bugs

### ADM-BUG-004: Admin UI Sign Out redirects but leaves server session active

Severity: `P1`

Environment: local-stage admin `http://127.0.0.1:13001`, backend `http://127.0.0.1:18080`, Chromium headless, desktop `1440x1000`, locale `en-EN`.

User role/state: approved synthetic `owner/super_admin`; credentials and TOTP came from protected runtime secret file `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`; credential values, TOTP values, cookies, JWTs, refresh tokens, storage state, headers, HAR, trace, and video were not stored.

Steps to reproduce:

1. Open `http://127.0.0.1:13001/en-EN/login` in a fresh browser context.
2. Sign in with the approved synthetic `owner/super_admin` email/password.
3. Complete the 2FA challenge.
4. Confirm `/api/v1/auth/session` returns `200`.
5. Navigate to `/en-EN/dashboard`.
6. Open the admin user menu.
7. Click `Sign Out`.
8. Observe the network response for `POST /api/v1/auth/logout`.
9. After the UI redirects to login, check `/api/v1/auth/session`.
10. Navigate directly to `/en-EN/dashboard` again in the same browser context.

Expected result:

- `Sign Out` revokes the current server session.
- `POST /api/v1/auth/logout` returns a successful status or otherwise clears the authenticated session.
- `/api/v1/auth/session` returns `401` after logout.
- Direct `/en-EN/dashboard` after logout redirects to `/en-EN/login`.

Actual result:

- UI `Sign Out` triggered `POST /api/v1/auth/logout -> 403`.
- Sanitized response body: `{"detail":"CSRF origin validation failed"}`.
- Browser was routed to `/en-EN/login`, but `/api/v1/auth/session` still returned `200`.
- Direct `/en-EN/dashboard` after logout opened `/en-EN/dashboard` instead of staying logged out.

Evidence:

- Summary: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-post498c-ui-logout__20260604T175704Z.md`
- Raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-post498c-ui-logout__20260604T175704Z.json`
- Screenshots: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-UILOGOUT-*__20260604T175704Z.png`
- Bug packet: `docs/qa/manual-flow-audit/2026-06-04/evidence/bug-packets/ADM-BUG-004.md`

Sensitive-data review: PASS - no credentials, TOTP values, cookies, JWTs, refresh tokens, storage state, headers, payment secrets, customer PII, HAR, trace, video, or production data were stored. Screenshots contain approved local-stage synthetic UI only.

Context7 docs checked: MCP quota exceeded; fallback `ctx7 docs /microsoft/playwright` checked browser interaction and screenshot APIs. No framework root cause is asserted in this QA finding; it is based on observed UI/network/session behavior.

Recommended owner/action: Security/auth owner should triage and ensure admin `Sign Out` revokes the server session in local-stage. [CYBA-507](/CYBA/issues/CYBA-507) was closed but failed QA retest; active follow-up is [CYBA-511](/CYBA/issues/CYBA-511), assigned to `SecurityEngineer`. If implementation ownership sits in admin frontend proxy/logout handling, hand off to `Prism Admin Partner Frontend Engineer` with this packet and keep security review on the session-persistence behavior.

Post-[CYBA-507] verification note:

- Retest on current local-stage still failed.
- `POST /api/v1/auth/logout -> 403`, sanitized body `{"detail":"CSRF origin validation failed"}`.
- Post-logout `/api/v1/auth/session -> 200`.
- Direct `/en-EN/dashboard` after logout still opens dashboard.
- Evidence: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-post507-logout-retest__20260604T182429Z.md`.

### ADM-BUG-003: Post-fix local-stage runtime still serves stale/bypassed admin auth behavior and blocks browser verification

Severity: `P1`

Environment: local-stage admin `http://127.0.0.1:13001`, backend `http://127.0.0.1:18080`, Chromium headless, desktop `1440x1000`, locale `en-EN`.

User role/state: anonymous invalid-login retest plus approved synthetic `owner/super_admin` credentials from protected runtime secret file `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`; credential values, TOTP, cookies, JWTs, refresh tokens, and storage state were not stored.

Steps to reproduce:

1. Ensure child fixes [CYBA-463](/CYBA/issues/CYBA-463) and [CYBA-484](/CYBA/issues/CYBA-484) are `done`.
2. Open `http://127.0.0.1:13001/en-EN/login` in a fresh browser context.
3. Submit an invalid synthetic admin login.
4. Observe sanitized network sequence for `/api/v1/auth/login` and `/api/v1/auth/refresh`.
5. Open a fresh browser context and sign in with the approved synthetic `owner/super_admin` credentials.
6. Attempt 2FA only if the UI reaches the 2FA step.
7. Verify `/api/v1/auth/session`.
8. Navigate to protected read-only routes:
   - `/en-EN/dashboard`
   - `/en-EN/customers`
   - `/en-EN/customers/test-user-001`
   - `/en-EN/commerce/payments`
   - `/en-EN/commerce/wallets`
   - `/en-EN/commerce/withdrawals`
   - `/en-EN/growth/partners`
   - `/en-EN/growth/referrals`
   - `/en-EN/commerce/plans`
   - `/en-EN/security/sessions`
   - `/en-EN/governance/audit-log`

Expected result:

- Fixed admin runtime is served on `13001`.
- Invalid login does not call `/api/v1/auth/refresh` after `/api/v1/auth/login -> 401`.
- Approved synthetic `owner/super_admin` can complete login + 2FA and `/api/v1/auth/session` returns `200`.
- Protected routes either render permitted read-only admin UI or a clear role-specific access-denied state.
- `/api/v1/*` browser calls use the fixed admin frontend proxy/route-handler behavior needed for admin realm testing.

Actual result:

- Invalid login still produced `POST /api/v1/auth/login -> 401` followed by `POST /api/v1/auth/refresh -> 401`.
- Owner/super_admin login returned `401`; 2FA page was not reached.
- `/api/v1/auth/session` returned `401`.
- All tested protected routes redirected to `/en-EN/login?<redacted-query>`.
- Logout cleanup returned `422`.
- Direct local checks showed backend-style `/api/v1/*` responses, which suggests the currently served runtime is stale or bypassing the expected Next.js route-handler proxy.

Evidence:

- Summary: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-postfix-auth-smoke__20260604T171556Z.md`
- Raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-postfix-auth-smoke__20260604T171556Z.json`
- Screenshots: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POSTFIX-*__20260604T171556Z.png`
- Bug packet: `docs/qa/manual-flow-audit/2026-06-04/evidence/bug-packets/ADM-BUG-003.md`

Sensitive-data review: PASS - strict scan found no bearer credentials, JWT-shaped values, access-token keys, refresh-token keys, password keys, or TOTP secret keys in the new text artifacts; screenshots contain approved local-stage synthetic UI only.

Context7 docs checked: MCP quota exceeded; fallback `ctx7 docs /vercel/next.js` checked for Next.js catch-all route handling, `NextResponse.rewrite`, and `next.config.js` rewrites; fallback `ctx7 docs /microsoft/playwright` checked for browser smoke capture APIs.

Recommended owner/action: `Prism Admin Partner Frontend Engineer` should refresh/fix the served admin local-stage runtime so the `admin/src/app/api/v1/[...path]/route.ts` behavior and latest auth client bundle are actually active on `http://127.0.0.1:13001`, then hand back to QA for a browser retest of [CYBA-463](/CYBA/issues/CYBA-463), [CYBA-484](/CYBA/issues/CYBA-484), and remaining authenticated admin routes.

Follow-up issue: [CYBA-498](/CYBA/issues/CYBA-498), assigned to `Prism Admin Partner Frontend Engineer`.

Post-fix verification note:

- [CYBA-498](/CYBA/issues/CYBA-498) is `done`.
- Corrected browser smoke on current `13001` passed: invalid login no longer calls `/api/v1/auth/refresh`, synthetic `owner/super_admin` login + 2FA completed, `/api/v1/auth/session -> 200`, and all tested owner read-only protected routes rendered without login redirects.
- Evidence: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-post498c-auth-readonly-smoke__20260604T175402Z.md`.

### ADM-BUG-002: Authenticated operator session is valid but protected admin routes redirect to login

Severity: `P1`

Environment: local-stage admin `http://127.0.0.1:13001`, backend `http://127.0.0.1:18080`, Chromium headless, desktop `1440x1000`, locale `en-EN`.

User role/state: synthetic admin `operator` from protected runtime secret file `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`; credential values, TOTP, cookies, JWTs, and refresh tokens were not stored.

Steps to reproduce:

1. Open `http://127.0.0.1:13001/en-EN/login` in a fresh browser context.
2. Sign in with the approved synthetic admin `operator` credentials from the protected secret channel.
3. Complete the 2FA challenge with the approved synthetic TOTP secret.
4. Verify `/api/v1/auth/session` after 2FA.
5. Navigate to protected admin routes:
   - `/en-EN/dashboard`
   - `/en-EN/customers`
   - `/en-EN/commerce/payments`
   - `/en-EN/commerce/wallets`
   - `/en-EN/commerce/withdrawals`
   - `/en-EN/growth/partners`
   - `/en-EN/growth/referrals`
   - `/en-EN/commerce/plans`
   - `/en-EN/security/sessions`
   - `/en-EN/governance/audit-log`

Expected result:

- After successful login + 2FA, the synthetic admin `operator` can enter at least the permitted admin shell/dashboard.
- Routes outside the role's permissions should show an explicit access-denied state, not invalidate or loop the whole admin session.
- Logout should complete or be a no-op cleanup, not repeatedly fail as a visible auth side effect.

Actual result:

- Login + 2FA completed.
- `/api/v1/auth/session` returned `200`, role `operator`, `is_active=true`.
- All tested protected routes redirected to `/en-EN/login?<redacted-query>` with access-denied state.
- Sanitized network notes show repeated `GET /api/v1/auth/session -> 200` and repeated `POST /api/v1/auth/logout -> 403` during route checks.

Evidence:

- Summary: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-authenticated-readonly-smoke__20260604T164711Z.md`
- Raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-authenticated-readonly-smoke__20260604T164711Z.json`
- Login screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-AUTH-LOGIN-001__admin-panel__operator__en-EN__desktop-1440__pass__20260604T164711Z.png`
- Failed protected-route screenshots: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-AUTH-*__admin-panel__operator__en-EN__desktop-1440__fail__20260604T164711Z.png`

Sensitive-data review: PASS - credentials, TOTP, cookies, JWTs, refresh tokens, storage state, headers, payment secrets, and production PII were not stored. Screenshots contain only approved local-stage synthetic UI state.

Context7 docs checked: MCP quota exceeded; fallback `ctx7 docs /microsoft/playwright` checked for `chromium.launch`, `newContext`, `page.goto`, locators, `waitForResponse`, `waitForURL`, and screenshot APIs.

Recommended owner/action: Admin frontend/auth owner should fix the post-2FA authenticated route guard/logout behavior so synthetic admin roles with a valid `/auth/session` can access permitted admin routes. Follow-up: [CYBA-484](/CYBA/issues/CYBA-484).

Post-fix verification note:

- [CYBA-484](/CYBA/issues/CYBA-484) is `done`.
- Corrected owner/super_admin browser smoke on current `13001` passed for dashboard, customers, customer 360 synthetic id route, payments, wallets, withdrawals, partners, referrals redirect target, pricing/plans, sessions, and audit log.
- Logout remains a separate blocker under `ADM-BUG-004`.

### ADM-BUG-001: Invalid admin login shows refresh-token implementation error

Severity: `P2`

Environment: local-stage admin `http://127.0.0.1:13001`, backend `http://127.0.0.1:18080`, Chromium headless, desktop `1440x1000`, locale `en-EN`.

User role/state: anonymous visitor, synthetic invalid login attempt using `test-admin-001@example.test`.

Steps to reproduce:

1. Open `http://127.0.0.1:13001/en-EN/login` in a fresh browser context.
2. Enter `test-admin-001@example.test` in the email field.
3. Enter any invalid synthetic password.
4. Click `Sign In`.

Expected result:

- User remains on login.
- UI shows a clear, non-sensitive authentication error such as invalid credentials or login failed.
- The visible error does not mention refresh-token internals.

Actual result:

- User remains on `/en-EN/login`.
- Visible alert says `Refresh token not provided`.
- Network sequence observed: `POST /api/v1/auth/login -> 401`, then `POST /api/v1/auth/refresh -> 401`.

Evidence:

- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-LOGIN-NEG-001__admin-panel__anonymous__en-EN__desktop-1440__pass__20260604T155644Z.png`
- Capture notes: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-browser-capture-summary__20260604T155644Z.md`
- Raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-browser-capture-summary__20260604T155644Z.json`

Sensitive-data review: PASS - synthetic email only; no cookies, JWT, refresh token, password value, HAR, trace, payment data, or production PII stored.

Context7 docs checked: N/A - manual UI/network-observed finding; Playwright evidence capture docs checked via `ctx7` fallback.

Recommended owner/action: Admin frontend/auth owner should keep login endpoint `401` handling from surfacing refresh failure details and display the original login failure message.

Follow-up issue: [CYBA-463](/CYBA/issues/CYBA-463), assigned to `Prism Admin Partner Frontend Engineer`.

Post-fix verification note:

- Child fix [CYBA-463](/CYBA/issues/CYBA-463) is `done`; targeted unit regression `npm run test:run -- src/lib/api/__tests__/auth.test.ts` passed with `85 passed`.
- Browser retest after [CYBA-498](/CYBA/issues/CYBA-498) passed: invalid login returned `401`, did not call `/api/v1/auth/refresh`, and displayed `Invalid credentials.` Evidence: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-post498c-auth-readonly-smoke__20260604T175402Z.md`.

## Product Gaps / Environment Issues

### ADM-GAP-001: Dangerous admin mutation/payment/integration scope remains blocked/not-tested

Status: `blocked/not-tested`

Blocked areas:

- Customer create/update/delete and customer 360 mutations.
- Payments, wallet operations, manual top-up, refunds/captures, payouts, settlements, and withdrawals moderation actions.
- Permission changes, admin invite issuance, role assignment, 2FA/passkey destructive operations.
- Remnawave/provisioning and real Telegram/OAuth/email operations.

Owner/action: Board / QA Lead / admin-security-finance owners must provide explicit sandbox/mock fixtures and operation approvals for each mutation flow, or keep them out of scope. Until then, QA is limited to login, read-only UI, redirects, non-destructive RBAC boundaries, and sanitized evidence.

Context7 docs checked: N/A - manual UI/business-flow blocker.

### ADM-GAP-002: Public admin login emits repeated analytics 403 console errors

Status: `product gap / environment issue`
Severity: `P3`

Environment: local-stage admin `http://127.0.0.1:13001`, anonymous browser contexts, `en-EN`.

Steps to reproduce:

1. Open `http://127.0.0.1:13001/en-EN/login`.
2. Open anonymous direct routes such as `/en-EN/dashboard` and wait for the login redirect.
3. Inspect sanitized console/network notes.

Expected result:

- Public login and unauth redirect states should not generate noisy console errors for normal telemetry calls, or telemetry should be intentionally disabled in local-stage.

Actual result:

- Browser console records repeated `403 Forbidden` resource errors.
- Network notes show `POST /api/analytics/web-vitals -> 403`, `POST /api/analytics/traffic -> 403`, and `POST /api/analytics/frontend-runtime -> 403`.

Evidence:

- Capture notes: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-browser-capture-summary__20260604T155644Z.md`
- Screenshots under `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/` show user-visible pages still render; this gap is console/network-only.

Sensitive-data review: PASS - summarized method/path/status only; no headers, cookies, request bodies, tokens, or PII stored.

Context7 docs checked: N/A - manual UI/network-observed finding; Playwright evidence capture docs checked via `ctx7` fallback.

Recommended owner/action: Admin frontend/observability owner should decide whether anonymous local-stage telemetry should be accepted, suppressed, or mocked to avoid masking real console errors during QA.

## Passed Coverage

- Anonymous login page renders on desktop and mobile.
- Anonymous direct URL guard redirects to login for dashboard, customers, customer detail, payments, wallets, withdrawals, partners, referrals, pricing/plans, sessions, and audit log.
- Backend session endpoint returns `401 Not authenticated` for anonymous state, and private UI content was not visible in browser captures.
- Controlled local `DEV_BYPASS_AUTH=true` probe did not open the admin shell in this local-stage browser run.
- Synthetic admin `operator` UI login + 2FA completed and `/api/v1/auth/session` returned `200` before protected-route navigation failed.
- After [CYBA-498](/CYBA/issues/CYBA-498), synthetic `owner/super_admin` UI login + 2FA completed and `/api/v1/auth/session` returned `200`.
- Owner/super_admin read-only navigation passed for dashboard, customers, customer 360 synthetic id route, payments, wallets, withdrawals, partners, referrals redirect target, pricing/plans, sessions, and audit log. No financial, wallet, withdrawal, pricing, customer, permission, or provisioning mutation was performed.

## Final QA Disposition

Admin anonymous, direct-URL, invalid-login, owner/super_admin login + 2FA, and owner/super_admin read-only protected-route scope is covered with sanitized evidence. Readiness is `GO - local-stage synthetic QA`, and child fixes [CYBA-463](/CYBA/issues/CYBA-463), [CYBA-484](/CYBA/issues/CYBA-484), and [CYBA-498](/CYBA/issues/CYBA-498) are browser-verified for their non-logout acceptance surface. Current blocker: `ADM-BUG-004` / [CYBA-511](/CYBA/issues/CYBA-511) because [CYBA-507](/CYBA/issues/CYBA-507) failed QA retest and admin UI logout still leaves the server session active. Dangerous financial/admin mutation scopes remain blocked/not-tested pending explicit sandbox/mock approvals.
