# ADM-BUG-004: Admin UI Sign Out redirects but leaves server session active

Related issue: [CYBA-458](/CYBA/issues/CYBA-458)

Follow-up issues: [CYBA-507](/CYBA/issues/CYBA-507), [CYBA-511](/CYBA/issues/CYBA-511)

Severity: `P1`

Status: `open - security/auth session blocker`

## Environment

- Admin: `http://127.0.0.1:13001`
- Backend: `http://127.0.0.1:18080`
- Browser: Playwright Chromium headless
- Viewport: desktop `1440x1000`
- Locale: `en-EN`
- Date: `2026-06-04`

## User Role / State

- Approved synthetic `owner/super_admin` admin.
- Credentials and TOTP came from protected runtime secret file `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`.
- Credential values, TOTP values, cookies, JWTs, refresh tokens, storage state, headers, HAR, trace, and video were not stored.

## Steps To Reproduce

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

## Expected Result

- `Sign Out` revokes the current server session.
- `POST /api/v1/auth/logout` returns a successful status or otherwise clears the authenticated session.
- `/api/v1/auth/session` returns `401` after logout.
- Direct `/en-EN/dashboard` after logout redirects to `/en-EN/login`.

## Actual Result

- UI `Sign Out` triggered `POST /api/v1/auth/logout -> 403`.
- Sanitized response body: `{"detail":"CSRF origin validation failed"}`.
- Browser was routed to `/en-EN/login`, but `/api/v1/auth/session` still returned `200`.
- Direct `/en-EN/dashboard` after logout opened `/en-EN/dashboard` instead of staying logged out.

## Evidence

- Summary: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-post498c-ui-logout__20260604T175704Z.md`
- Raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-post498c-ui-logout__20260604T175704Z.json`
- Before logout screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-UILOGOUT-BEFORE-001__admin-panel__owner__en-EN__desktop-1440__pass__20260604T175704Z.png`
- After logout click screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-UILOGOUT-AFTER-001__admin-panel__owner__en-EN__desktop-1440__fail__20260604T175704Z.png`
- Dashboard after logout screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST498C-UILOGOUT-DASH-AFTER-001__admin-panel__owner__en-EN__desktop-1440__fail__20260604T175704Z.png`
- Post-[CYBA-507] failed retest summary: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-post507-logout-retest__20260604T182429Z.md`
- Post-[CYBA-507] failed retest raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-post507-logout-retest__20260604T182429Z.json`
- Post-[CYBA-507] screenshots: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POST507-*__20260604T182429Z.png`

## Post-Fix Retest

[CYBA-507](/CYBA/issues/CYBA-507) was marked `done`, but QA retest still failed on current local-stage:

- `POST /api/v1/auth/logout -> 403`
- sanitized body: `{"detail":"CSRF origin validation failed"}`
- post-logout `/api/v1/auth/session -> 200`
- direct `/en-EN/dashboard` after logout opens dashboard

New follow-up: [CYBA-511](/CYBA/issues/CYBA-511).

## Sensitive-Data Review

PASS - no credentials, TOTP values, cookies, JWTs, refresh tokens, storage state, headers, payment secrets, customer PII, HAR, trace, video, or production data were stored. Screenshots contain approved local-stage synthetic UI only.

## Docs Evidence

Context7 docs checked: MCP quota exceeded; fallback `ctx7 docs /microsoft/playwright` checked browser interaction and screenshot APIs. No framework root cause is asserted in this QA packet; the finding is based on observed UI/network/session behavior.

## Recommended Owner / Action

Security/auth owner should triage and ensure admin `Sign Out` revokes the server session in local-stage. [CYBA-507](/CYBA/issues/CYBA-507) did not pass QA retest; active follow-up is [CYBA-511](/CYBA/issues/CYBA-511). If implementation ownership sits in admin frontend proxy/logout handling, hand off to `Prism Admin Partner Frontend Engineer` with this packet and keep security review on the session-persistence behavior.
