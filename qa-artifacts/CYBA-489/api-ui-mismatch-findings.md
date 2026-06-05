# CYBA-489 API / UI Mismatch Findings

Дата проверки: 2026-06-04

## Bugs / QA Blockers

## Resume Revalidation Delta - 2026-06-04T20:08:20Z

Operator resumed the issue after a usage-limit stall. A fresh `8014` smoke changed the current finding status:

- `CYBA-489-BCK-001` is no longer current for wallet/payment/referral/bootstrap/entitlement empty-state probes: `/wallet`, `/wallet/transactions`, `/payments/history`, `/referral/status`, `/miniapp/bootstrap`, `/entitlements/current` now return `200`.
- `CYBA-489-BCK-003` is no longer current: `/api/v1/customer-subscriptions/` now returns `200` with an empty `items` list.
- `CYBA-489-BCK-004` is partially changed: `/api/v1/client/capabilities` now returns `200`; `/api/v1/auth/passkeys/policy` now returns `403` with `Passkey origin is required`, not `404`.
- `CYBA-489-BCK-002` remains current: cookie-authenticated `POST /payments/checkout/quote`, `POST /access-delivery-channels/current/service-state`, and `POST /auth/refresh` still return `403 CSRF origin validation failed`.
- New current fixture gap: cookie-backed `GET /api/v1/miniapp/config` returns `404` with `Subscription config not found`, so VPN config delivery remains not testable.

The historical findings below are retained for traceability; use this resume delta as the current `8014` status.

### CYBA-489-BCK-001 - Authenticated web customer session is accepted by `/auth/session`, but mobile-backed client APIs reject the same user as `USER_NOT_FOUND`

Severity: P1 QA gate blocker

Environment: local-stage customer API target `http://127.0.0.1:8014`, upstream `http://127.0.0.1:18080`, protected synthetic customer web fixture.

User role/state: authenticated customer web user, `auth_realm_key=customer`, `principal_type=customer`.

Steps to reproduce:

1. Login through `POST /api/v1/auth/login` using the protected customer web fixture.
2. Reuse the returned cookies against `GET /api/v1/auth/session`.
3. Reuse the same cookies against `GET /api/v1/wallet`, `GET /api/v1/payments/history`, `GET /api/v1/referral/status`, `GET /api/v1/miniapp/bootstrap`, `GET /api/v1/miniapp/config`, and `GET /api/v1/entitlements/current`.

Expected result:

- Customer dashboard APIs used by the UI return `200` fixture states, or route-appropriate `4xx` responses that represent the product state, not a missing principal.

Actual result:

- `/api/v1/auth/session` returns `200`, proving the customer cookie session.
- The scoped mobile-backed APIs return `401` with `detail.code=USER_NOT_FOUND`.

Sanitized evidence:

- `POST /api/v1/auth/login 200 token_fields_present=true`
- `GET /api/v1/auth/session 200 auth_realm_key=customer, principal_type=customer`
- `GET /api/v1/wallet 401 detail.code=USER_NOT_FOUND`
- `GET /api/v1/payments/history 401 detail.code=USER_NOT_FOUND`
- `GET /api/v1/referral/status 401 detail.code=USER_NOT_FOUND`
- `GET /api/v1/miniapp/bootstrap 401 detail.code=USER_NOT_FOUND`
- `GET /api/v1/entitlements/current 401 detail.code=USER_NOT_FOUND`
- Source: `backend/src/presentation/dependencies/auth.py:424` checks `mobile_users`; `backend/src/presentation/api/v1/auth/routes.py:690` should create a customer web mobile shadow after login.

Recommended owner/action:

- Backend/test-data owner: provide or repair a `mobile_users` shadow fixture with the same id as the authenticated customer web account, then attach wallet/payment/referral/subscription/service rows to that id.

Context7 docs checked: N/A - repo-local auth/test-data fixture mismatch.

### CYBA-489-BCK-002 - Cookie-authenticated POST flows are blocked by CSRF origin validation in local-stage QA

Severity: P1 QA gate blocker

Environment: local-stage customer API target `http://127.0.0.1:8014`, frontend preview origin simulated as `http://127.0.0.1:9001`.

User role/state: authenticated customer web user with local HTTP cookies rewritten by `qa-artifacts/CYBA-480/customer_qa_proxy.py`.

Steps to reproduce:

1. Login through `POST /api/v1/auth/login` using the protected customer web fixture.
2. Reuse the returned cookies.
3. Send `POST /api/v1/payments/checkout/quote` with a public plan id and `Origin: http://127.0.0.1:9001`.
4. Send `POST /api/v1/access-delivery-channels/current/service-state` with the default frontend service-state payload.
5. Send `POST /api/v1/auth/refresh` with cookies.

Expected result:

- POST requests from the approved local frontend QA origin reach route logic and return quote/service-state/refresh results or route-appropriate validation errors.

Actual result:

- All three probes return `403` before route logic with `{"detail":"CSRF origin validation failed"}`.

Sanitized evidence:

- `POST /api/v1/payments/checkout/quote 403 body={"detail":"CSRF origin validation failed"}`
- `POST /api/v1/access-delivery-channels/current/service-state 403`
- `POST /api/v1/auth/refresh 403`
- Source: `backend/src/presentation/middleware/csrf.py:43` validates unsafe cookie-authenticated methods by `Origin`/`Referer`; `backend/src/main.py:397` adds the middleware for staging/production-like runtime.

Recommended owner/action:

- Backend/runtime owner: add the approved local preview origin to staging `CORS_ORIGINS`, or provide a local-only QA proxy/runtime that safely rewrites `Origin`/`Referer` for the approved preview origin. Do not disable CSRF broadly.

Context7 docs checked: unavailable - monthly quota exceeded. Fallback official docs checked: FastAPI middleware docs `https://fastapi.tiangolo.com/tutorial/middleware/` and FastAPI CORS docs `https://fastapi.tiangolo.com/tutorial/cors/`.

### CYBA-489-BCK-003 - Live target returns `404` for `/api/v1/customer-subscriptions/` despite current source/OpenAPI route

Severity: P2 QA contract blocker

Environment: local-stage customer API target `http://127.0.0.1:8014`.

User role/state: authenticated customer web user.

Steps to reproduce:

1. Login through `POST /api/v1/auth/login` using the protected customer web fixture.
2. Reuse cookies against `GET /api/v1/customer-subscriptions/`.
3. Compare current source and generated OpenAPI.

Expected result:

- The runtime route exists and returns a subscription list fixture, empty list, or route-appropriate authenticated state.

Actual result:

- `GET /api/v1/customer-subscriptions/` returns `404`.
- `backend/src/presentation/api/v1/customer_subscriptions/routes.py:86` defines the route.
- `backend/docs/api/openapi.json` includes `/api/v1/customer-subscriptions/`.

Recommended owner/action:

- Backend/runtime owner: verify that the `8014` upstream image is built from the current source/OpenAPI route set, or publish an explicit route-not-available note for client QA.

Context7 docs checked: N/A - repo-local runtime/source contract drift.

### CYBA-489-BCK-004 - Live target misses public capability/passkey-policy routes used by frontend

Severity: P2 QA contract blocker

Environment: local-stage customer API target `http://127.0.0.1:8014`.

User role/state: unauthenticated public/client user.

Steps to reproduce:

1. Call `GET /api/v1/client/capabilities`.
2. Call `GET /api/v1/auth/passkeys/policy`.
3. Compare current frontend client/source/OpenAPI.

Expected result:

- `GET /api/v1/client/capabilities` returns runtime feature flags used to hide disabled checkout/growth surfaces.
- `GET /api/v1/auth/passkeys/policy` returns passkey policy or an explicit route-appropriate disabled response.

Actual result:

- Both routes return `404` on `8014`.
- `frontend/src/lib/api/client-capabilities.ts:57` calls `/client/capabilities`.
- `backend/src/presentation/api/v1/client_capabilities/routes.py:79` defines `/client/capabilities`, and `backend/docs/api/openapi.json` includes `/api/v1/client/capabilities`.
- `frontend/src/lib/api/passkeys.ts:81` calls `/auth/passkeys/policy`, and `backend/docs/api/openapi.json` includes `/api/v1/auth/passkeys/policy`.

Recommended owner/action:

- Backend/runtime owner: align the live local-stage target with current generated contract before full client QA, or provide explicit fixture notes for these unavailable public routes.

Context7 docs checked: N/A - repo-local runtime/source contract drift.

## Product Gaps / Not Bugs

- `GET /api/v1/subscriptions/active` returning `status=none` is a valid empty-subscription fixture, not a bug.
- Legacy `POST /api/v1/payments/checkout/commit` is deprecated/disabled in source; do not treat missing real commit coverage as a bug unless Board/billing declares commit testing in scope and provides a safe sandbox payment path.
- No approved Telegram Mini App signed synthetic `initData` exists in repo-safe artifacts. This is a fixture/product-decision gap, not a UI bug by itself.

## Not Tested / Blocked

- Checkout quote business logic after CSRF allowlist.
- Wallet balance/history non-empty rows beyond the current empty/synthetic shapes.
- Payment history non-empty rows.
- Referral/promo/partner-code accepted and rejected outcomes beyond referral status.
- Active/trial/expired subscription states beyond `status=none` and empty `customer-subscriptions.items`.
- VPN config delivery, service identity, service-state and device credential surfaces.
- Telegram Mini App signed auth/config; bootstrap now returns `200`, but `/miniapp/config` is `404 Subscription config not found`.
## Current Local-Stage Revalidation - 2026-06-05T05:23:29Z

A fresh smoke was run against the current approved local-stage backend `http://127.0.0.1:18080` with frontend `Origin/Referer: http://127.0.0.1:13000`. Sanitized artifacts:

- `qa-artifacts/CYBA-489/cyba-489-localstage-revalidation__20260605T052329Z.json`
- `qa-artifacts/CYBA-489/cyba-489-localstage-revalidation__20260605T052329Z.md`

Current delta versus the old `8014` proxy findings:

- Cleared: customer login/session `200/200`, wallet empty state `200`, payment history empty state `200`, referral status `200`, Mini App bootstrap `200`, entitlements empty state `200`, customer-subscriptions empty list `200`, client capabilities `200`.
- Cleared: CSRF-sensitive cookie POST routes with approved local-stage origin now reach route logic: checkout quote `200`, service-state `200`, auth refresh `200`.
- Cleared with required context: passkey policy returns `200` when called with approved `Origin`; calling without `Origin` still returns route-appropriate `403 Passkey origin is required`.
- Still not provided: active/trial/expired subscription rows, non-empty wallet transaction rows, non-empty payment-history rows, referral/promo/partner-code outcome fixtures, signed synthetic Telegram Mini App entry, and subscription-backed Mini App config/VPN config fixture. `/api/v1/miniapp/config` still returns `404 Subscription config not found`; service-state returns `200` but has no service identity or device credential because entitlement status is `none`.

Disposition: runtime/API blockers that prevented client QA from continuing are resolved. Remaining items are explicit fixture/product-scope gaps for final Scribe/Astra acceptance and fix backlog; they are not a production go.
