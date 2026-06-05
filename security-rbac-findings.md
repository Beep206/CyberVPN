# CYBA-459 Security/RBAC QA Findings

Дата: 2026-06-04
Исполнитель: `qa-security-rbac-reviewer`

## Summary

P0 не подтверждены. Подтверждены 2 P1 security/session findings в approved local-stage synthetic scope:

1. `SEC-RBAC-001`: customer web login response exposes `access_token` and `refresh_token` field names in browser-visible JSON; immediate browser `/api/v1/auth/session` remains `401`, so customer web session is not established on the approved HTTP local-stage surface.
2. `SEC-RBAC-002`: admin `owner/super_admin` browser logout returns `403` with `CSRF origin validation failed`; `/api/v1/auth/session` remains `200` after logout.

Admin API RBAC and partner API permission smoke did not show role-boundary bypass in the tested read-only matrix. Partner browser local-dev surface was not stable enough for browser auth/logout validation and is listed under blocked/not-tested.

## Environment

- Repo: `VPNBussiness-main`
- Date/time: 2026-06-04 UTC
- Browser automation: Playwright + `/home/beep/.local/bin/chromium`
- Approved local-stage endpoints:
  - Client frontend: `http://127.0.0.1:13000`
  - Admin panel: `http://127.0.0.1:13001`
  - Backend API: `http://127.0.0.1:18080`
  - Partner local-dev attempted: `http://127.0.0.1:3004` after `3002` was unavailable
- Credentials: synthetic protected file `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`, mode `0600`; values not copied into report/evidence.
- Context7 docs checked: MCP Context7 returned quota exceeded; `ctx7` fallback checked `/microsoft/playwright` for `chromium.launch`, `newContext`, `page.goto`, `page.screenshot`, response/status capture, console/pageerror capture, and `storageState`/storage inspection. Findings below are manual UI/API behavior observations, not framework root-cause assertions.

## Evidence

- Sanitized machine-readable results: `evidence/security-rbac/cyba459-stage-security-rbac-smoke-results.json`
- QA runner used to reproduce: `evidence/security-rbac/cyba459-stage-security-rbac-smoke.mjs`
- Screenshots:
  - `evidence/security-rbac/stage-client-unauth-dashboard.png`
  - `evidence/security-rbac/stage-admin-unauth-dashboard.png`
  - `evidence/security-rbac/stage-partner-local-unauth-dashboard.png` (blocked browser surface / connection refused)
- Secret scan: no JWT/password/TOTP/token values detected in `evidence/security-rbac` or this report by the local regex scan.

## Bugs

### SEC-RBAC-001: Customer web login exposes token fields and does not establish browser session

Severity: `P1`

Type: security/session bug

Environment: client frontend `http://127.0.0.1:13000`, backend `http://127.0.0.1:18080`, clean Chromium context.

User role/state: active synthetic customer web account, realm `customer`.

Steps to reproduce:

1. Open a clean browser context at `http://127.0.0.1:13000/en-EN/login`.
2. Submit synthetic customer credentials to same-origin `POST /api/v1/auth/login` with `X-Auth-Realm: customer`.
3. Record only response status and response field names; do not store response values.
4. Immediately call same-origin `GET /api/v1/auth/session`.
5. Navigate directly to `http://127.0.0.1:13000/en-EN/dashboard`.
6. Inspect `localStorage`, `sessionStorage`, and visible cookie names for token-like data.

Expected:

- Web login should establish an authenticated httpOnly-cookie-backed browser session.
- Browser-visible response body should not expose JWT/refresh-token values for the web flow.
- `GET /api/v1/auth/session` should return `200` for the active customer after login.
- Dashboard should render authenticated customer state.
- No JWT/refresh token should be present in `localStorage` or `sessionStorage`.

Actual:

- Login returned `200`.
- Response field names included `access_token` and `refresh_token`; values were not stored.
- Immediate browser `GET /api/v1/auth/session` returned `401`.
- Dashboard remained at the login/redirect state.
- `localStorage` and `sessionStorage` had no sensitive keys and no JWT-like values.

Sanitized evidence:

- `evidence/security-rbac/cyba459-stage-security-rbac-smoke-results.json`
  - `.browser.auth.customerActive.loginResult.loginShape.keys`
  - `.browser.auth.customerActive.loginResult.loginShape.hasAccessToken=true`
  - `.browser.auth.customerActive.loginResult.loginShape.hasRefreshToken=true`
  - `.browser.auth.customerActive.loginResult.sessionStatus=401`
  - `.browser.auth.customerActive.storageAfterLogin`

Sensitive evidence handling:

- Token values, password, TOTP secret, cookies, and user identifiers were not written to the report.
- Evidence records only field names, booleans, statuses, and redacted paths.

Recommended owner/action:

- `SecurityEngineer` should review the web auth response contract/BFF behavior and decide whether web login must strip token bodies and rely only on httpOnly cookies.

### SEC-RBAC-002: Admin logout is blocked by CSRF and leaves session active

Severity: `P1`

Type: security/session bug

Environment: admin panel `http://127.0.0.1:13001`, backend `http://127.0.0.1:18080`, clean Chromium context.

User role/state: synthetic admin `owner/super_admin`, 2FA completed via approved TOTP fixture.

Steps to reproduce:

1. Open a clean browser context at `http://127.0.0.1:13001/en-EN/login`.
2. Submit synthetic `owner/super_admin` credentials to same-origin `POST /api/v1/auth/login`.
3. Complete 2FA through same-origin `/api/auth/2fa/pending` and `/api/auth/2fa/complete`.
4. Confirm same-origin `GET /api/v1/auth/session` returns `200` with role `owner/super_admin`.
5. Submit same-origin `POST /api/v1/auth/logout`.
6. Immediately call same-origin `GET /api/v1/auth/session`.
7. Use browser Back / observe final URL.

Expected:

- Logout should return success, clear/revoke the admin session, and leave subsequent `/api/v1/auth/session` at `401`.
- Browser Back after logout must not restore or preserve an active protected admin session.

Actual:

- 2FA completion returned `200`; session returned `200` for `owner/super_admin`.
- Logout returned `403`.
- Logout detail: `CSRF origin validation failed`.
- Follow-up `/api/v1/auth/session` still returned `200`.
- Browser ended at `/en-EN/login?error=access_denied`, but the backend session remained active.

Sanitized evidence:

- `evidence/security-rbac/cyba459-stage-security-rbac-smoke-results.json`
  - `.browser.auth.adminOwner.loginResult.sessionStatus=200`
  - `.browser.auth.adminOwner.logoutStatus=403`
  - `.browser.auth.adminOwner.logoutDetail`
  - `.browser.auth.adminOwner.afterLogoutSession=200`
  - `.browser.auth.adminOwner.afterBackUrl`

Sensitive evidence handling:

- TOTP secret, `tfa_token`, cookies, and JWT values were not written to evidence.
- Evidence records only response field names, statuses, role labels, and redacted URL paths.

Recommended owner/action:

- `SecurityEngineer` should review CSRF origin allowlist/session revocation behavior for admin logout on approved local-stage origins.

## Passed / Confirmed

### Unauthenticated direct URLs

Steps:

1. Open clean browser contexts.
2. Navigate directly to:
   - `http://127.0.0.1:13000/en-EN/dashboard`
   - `http://127.0.0.1:13001/en-EN/dashboard`
3. Observe final URL, DOM markers, console/pageerror state, and browser-visible storage.

Expected:

- Unauthenticated protected routes redirect to login/redirect state.
- No protected shell or token material appears in storage.

Actual:

- Client final URL: `/en-EN/login?redirect=%2Fen-EN%2Fdashboard`.
- Admin final URL: `/en-EN/login?redirect=%2Fen-EN%2Fdashboard`.
- No `SYSTEM FAILURE`.
- `localStorage` and `sessionStorage` empty; no visible cookies.

Evidence:

- `evidence/security-rbac/stage-client-unauth-dashboard.png`
- `evidence/security-rbac/stage-admin-unauth-dashboard.png`
- `evidence/security-rbac/cyba459-stage-security-rbac-smoke-results.json`

### Backend unauth/session and disabled-account smoke

Confirmed:

- `GET /health` -> `200`
- Unauth `GET /api/v1/auth/session` -> `401`
- Unauth `GET /api/v1/partner-session/bootstrap` -> `401`
- Disabled synthetic customer login -> `401`

### Admin API RBAC read-only matrix

Roles tested: `owner/super_admin`, `admin`, `operator`, `finance`, `support`, `viewer`.

Read-only routes tested:

- `GET /api/v1/users/`
- `GET /api/v1/helix/admin/nodes`
- `GET /api/v1/plans/admin`
- `GET /api/v1/provisioning-profiles/`

Result:

- No role-boundary bypass observed.
- Expected-denied roles returned `403`.
- Expected-allowed roles returned `200` or reached handler-level `404` where the same route returned `403` for denied roles.

### Partner API permission matrix

Roles tested: partner `owner`, `manager`, `finance`, `analyst`.

Read-only routes tested after `GET /api/v1/partner-session/bootstrap`:

- `GET /api/v1/partner-workspaces/[workspace-id]/lane-applications`
- `GET /api/v1/partner-workspaces/[workspace-id]/codes`
- `GET /api/v1/partner-workspaces/[workspace-id]/earnings`
- `GET /api/v1/partner-workspaces/[workspace-id]/payout-accounts`

Result:

- No partner workspace permission bypass observed.
- Expected-denied permissions returned `403` with missing-permission details.
- Expected-allowed permissions returned `200` or handler-level `404`.

Product gap noted:

- `partner-session/bootstrap` returned permission keys and active workspace id, but `currentRoleKey` was `null` for all four partner role fixtures. Since permission enforcement still matched `currentPermissionKeys`, this is recorded as a product/debuggability gap, not a confirmed RBAC bypass.

### Cross-realm isolation

Confirmed:

- Customer session cookies sent against admin realm `GET /api/v1/users/` -> `401`.
- Admin session cookies sent against partner realm `GET /api/v1/partner-session/bootstrap` -> `401`.

## Blocked / Not Tested

- Partner browser direct/auth/logout flow: local-dev surface on `3002` was unavailable; direct restart on `3004` exited without stdout/stderr, and browser probe hit `ERR_CONNECTION_REFUSED`. Backend partner API/RBAC was still covered.
- Customer authenticated dashboard/logout/back behavior: blocked by `SEC-RBAC-001` because browser session did not establish after login.
- Real payment capture/refund/payout/settlement: not tested by safety gate.
- Real Telegram `initData`: not tested by safety gate.
- Remnawave/provisioning mutations and destructive admin actions: not tested by safety gate.

## Evidence Hygiene

- No JWT, refresh token, password, `.env` value, TOTP secret, production PII, payment secret, or Telegram `initData` was stored in Markdown, JSON evidence, screenshots, or issue comments.
- Evidence uses field names, booleans, statuses, role labels, and redacted route placeholders.
- Local secret scan command found no token/password/TOTP values in `evidence/security-rbac` or this report.
