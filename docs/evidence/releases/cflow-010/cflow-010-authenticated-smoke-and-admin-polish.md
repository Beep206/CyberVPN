# CFLOW-010 Authenticated Customer/Admin Smoke And UX/API Polish

Date: 2026-05-29

## Scope

- Authenticated customer smoke on `my.cyber-vpn.net`.
- Authenticated admin smoke on `admin.cyber-vpn.net` with 2FA.
- Remaining admin UX/API noise cleanup discovered by the smoke.
- Production deploy of the fixed admin runtime.

## Fixes Applied

1. Admin 2FA completion now preserves both `access_token` and `refresh_token`.
   - The admin Next route now handles backend `Set-Cookie` forwarding and also mirrors token JSON payload cookies.
   - This prevents the admin dashboard from opening with only a short-lived access cookie and then immediately hitting `401`/refresh noise.

2. Admin dashboard recent payments now uses the admin-safe payment attempts endpoint.
   - Replaced customer-scoped `/payments/history` usage from the admin dashboard with `/admin/payment-attempts`.
   - This removes `401 /api/v1/payments/history` noise under a valid admin session.

## Production Deploy

- First admin auth deploy evidence:
  - `docs/evidence/releases/cflow-010/stage1-gitlab-deploy-cflow-010-admin-auth-91af2373-20260529T0515Z.md`
- Final admin payments deploy evidence:
  - `docs/evidence/releases/cflow-010/stage1-gitlab-deploy-cflow-010-admin-payments-91af2373-20260529T0523Z.md`
- Commit-aligned final admin deploy evidence:
  - `docs/evidence/releases/cflow-010/stage1-gitlab-deploy-cflow-010-feea5c11-20260529T0530Z.md`

## Authenticated Smoke Result

Temporary customer smoke account was created, verified via OTP, used for browser smoke, then removed.
The result below was captured again after the commit-aligned final deploy.

```json
{
  "smoke_user": "cflow10-smoke-***@cyber-vpn.net",
  "user_id_present": true,
  "customer": {
    "bad_responses": [],
    "request_failures": [],
    "console_errors": []
  },
  "admin": {
    "bad_responses": [],
    "request_failures": [],
    "console_errors": []
  },
  "customer_delete_status": 200
}
```

Additional cleanup: failed intermediate `cflow10-smoke-*` production smoke accounts were deleted after a rollback-tested SQL delete confirmed the pattern was isolated.

## Local Verification

```text
npm run test --workspace admin -- 2fa/complete
npm run lint --workspace admin
npm run build --workspace admin
```

Result: all passed.

## Notes

- Headless Chromium WebGL fallback warnings were excluded from the smoke failure criteria because they are caused by the test environment GPU backend, not by production API or auth behavior.
- No OAuth behavior was changed.
