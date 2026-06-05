# ADM-BUG-003: Post-fix local-stage runtime still serves stale/bypassed admin auth behavior

Related issue: [CYBA-458](/CYBA/issues/CYBA-458)

Related fixes: [CYBA-463](/CYBA/issues/CYBA-463), [CYBA-484](/CYBA/issues/CYBA-484)

Follow-up issue: [CYBA-498](/CYBA/issues/CYBA-498)

Severity: `P1`

Status: `blocked - needs frontend/runtime owner action`

## Environment

- Admin: `http://127.0.0.1:13001`
- Backend: `http://127.0.0.1:18080`
- Browser: Playwright Chromium headless
- Viewport: desktop `1440x1000`
- Locale: `en-EN`
- Date: `2026-06-04`

## User Role / State

- Anonymous invalid-login retest.
- Approved synthetic `owner/super_admin` credentials from protected runtime secret file `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`.
- Credential values, TOTP, cookies, JWTs, refresh tokens, storage state, headers, and `.env` contents were not stored.

## Steps To Reproduce

1. Confirm child fixes [CYBA-463](/CYBA/issues/CYBA-463) and [CYBA-484](/CYBA/issues/CYBA-484) are `done`.
2. Open `http://127.0.0.1:13001/en-EN/login` in a fresh browser context.
3. Submit an invalid synthetic admin login.
4. Observe sanitized network sequence for `/api/v1/auth/login` and `/api/v1/auth/refresh`.
5. Open a fresh browser context and sign in with the approved synthetic `owner/super_admin` credentials.
6. Attempt 2FA only if the UI reaches the 2FA step.
7. Verify `/api/v1/auth/session`.
8. Navigate to protected read-only admin routes:
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

## Expected Result

- Fixed admin runtime is served on `http://127.0.0.1:13001`.
- Invalid login does not call `/api/v1/auth/refresh` after `/api/v1/auth/login -> 401`.
- Approved synthetic `owner/super_admin` can complete login + 2FA and `/api/v1/auth/session` returns `200`.
- Protected routes render permitted read-only admin UI or a clear role-specific access-denied state.
- Browser `/api/v1/*` calls use the fixed admin frontend proxy/route-handler behavior needed for admin realm testing.

## Actual Result

- Invalid login still produced `POST /api/v1/auth/login -> 401` followed by `POST /api/v1/auth/refresh -> 401`.
- Owner/super_admin login returned `401`; 2FA page was not reached.
- `/api/v1/auth/session` returned `401`.
- All tested protected routes redirected to `/en-EN/login?<redacted-query>`.
- Logout cleanup returned `422`.
- Direct local checks showed backend-style `/api/v1/*` responses, suggesting the currently served runtime is stale or bypassing the expected Next.js route-handler proxy.

## Evidence

- Summary: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-postfix-auth-smoke__20260604T171556Z.md`
- Raw sanitized JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/notes/admin-postfix-auth-smoke__20260604T171556Z.json`
- Screenshots: `docs/qa/manual-flow-audit/2026-06-04/evidence/admin/screenshots/MF-ADM-POSTFIX-*__20260604T171556Z.png`

## Sensitive-Data Review

PASS - strict scan found no bearer credentials, JWT-shaped values, access-token keys, refresh-token keys, password keys, or TOTP secret keys in the text artifacts. Screenshots contain approved local-stage synthetic UI only. No HAR, trace, video, storage state, cookies, headers, payment secrets, production PII, or real Telegram data were stored.

## Docs Evidence

Context7 docs checked: MCP quota exceeded; fallback `ctx7 docs /vercel/next.js` checked for Next.js catch-all route handling, `NextResponse.rewrite`, and `next.config.js` rewrites; fallback `ctx7 docs /microsoft/playwright` checked for browser smoke capture APIs.

## Recommended Owner / Action

`Prism Admin Partner Frontend Engineer` should refresh or fix the served admin local-stage runtime so `admin/src/app/api/v1/[...path]/route.ts` behavior and the latest auth client bundle are active on `http://127.0.0.1:13001`, then hand back to QA for browser retest of [CYBA-463](/CYBA/issues/CYBA-463), [CYBA-484](/CYBA/issues/CYBA-484), and remaining authenticated admin flows.
