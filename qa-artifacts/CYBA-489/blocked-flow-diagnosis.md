# CYBA-489 Blocked Flow Diagnosis

Дата проверки: 2026-06-04

## Executive Status

[CYBA-456](/CYBA/issues/CYBA-456) can continue minimum auth/session/devices/empty-subscription checks on `http://127.0.0.1:8014`. After operator resume on 2026-06-04, a fresh smoke shows partial unblock: wallet empty state, payment-history empty shape, referral status, Mini App bootstrap, current entitlements empty state, customer-subscriptions empty list, and client capabilities now return `200`.

The issue is still blocked for full checkout/VPN/TMA fixture closure because cookie-authenticated POST flows fail CSRF before business logic, `GET /api/v1/miniapp/config` returns `404 Subscription config not found`, passkey policy requires origin handling, and no active/trial/expired subscription or VPN config/service-access fixture has been provided.

## Resume Revalidation Delta - 2026-06-04T20:08:20Z

| Flow | Current status | Blocking evidence | Owner/action |
|---|---|---|---|
| Wallet balance/history | Partially unblocked | `/wallet 200`, `/wallet/transactions 200 array_len=0` | QA can test empty/synthetic state; backend/test-data owner still needed for non-empty transaction rows. |
| Payment history | Partially unblocked | `/payments/history 200` with `payments` key | QA can test empty/history container; backend/test-data owner still needed for payment rows. |
| Referral status | Partially unblocked | `/referral/status 200` | QA can test status; growth/test-data owner still needed for accepted/rejected promo/referral/partner-code outcomes. |
| Mini App bootstrap | Partially unblocked | `/miniapp/bootstrap 200` | QA can test bootstrap shape; Telegram owner still needed for signed synthetic entry coverage if required. |
| Mini App config / VPN config | Blocked | `/miniapp/config 404 Subscription config not found`; service-state POST still CSRF-blocked | VPN/service owner: provide non-production subscription/config/service identity fixture without publishing secrets. |
| Customer subscriptions | Partially unblocked | `/customer-subscriptions/ 200 items_count=0` | QA can test empty list; backend/test-data owner still needed for active/trial/expired rows. |
| Checkout quote safe-mode | Blocked | `/payments/checkout/quote 403 CSRF origin validation failed` | Backend/runtime owner: make approved local preview origin CSRF-compatible; billing/test-data owner: provide no-capture quote fixture. |
| Auth refresh and service-state POST | Blocked | `/auth/refresh 403`, `/access-delivery-channels/current/service-state 403` | Backend/runtime owner: fix approved local preview origin allowlist/proxy behavior. |
| Runtime capabilities | Unblocked | `/client/capabilities 200` | QA can retest capability-gated UI. |
| Passkey policy | Blocked/needs frontend-origin context | `/auth/passkeys/policy 403 Passkey origin is required` when called without `Origin` | Backend/frontend runtime owner: ensure frontend proxy preserves/supplies expected origin for this route. |

## Root Cause

The first pass showed a missing mobile-backed fixture row for many resource APIs. The resume smoke indicates that this was partially corrected on the live `8014` target. The remaining root cause is narrower:

Unsafe cookie-authenticated POST routes are additionally blocked by CSRF before business logic. The proxy does not rewrite `Origin`/`Referer`, and the upstream staging-like runtime rejects `Origin: http://127.0.0.1:9001`.

Mini App/VPN config still lacks a non-production subscription/config fixture. Active/trial/expired subscription states and non-empty wallet/payment/referral rows also remain missing.

Historical first-pass flow matrix remains below for traceability.

## Flow Matrix

| Flow | Current status | Blocking evidence | Owner/action |
|---|---|---|---|
| Public status/readiness | Unblocked | `GET /readiness 200`, `GET /api/v1/status 200` | QA can use `8014`. |
| Login/session restore | Unblocked for minimum QA | `POST /api/v1/auth/login 200`, cookie-backed `/auth/session 200` | QA can use protected secret handoff; do not publish credentials/tokens. |
| Auth devices | Unblocked | `GET /api/v1/auth/devices 200` | QA can test device-list UI state. |
| Empty subscription state | Unblocked only for `status=none` | `GET /api/v1/subscriptions/active 200 status=none` | QA can test empty/no-active state. |
| Checkout quote safe-mode | Blocked | `POST /api/v1/payments/checkout/quote 403 CSRF origin validation failed`; after CSRF, route also depends on `get_current_mobile_user_id`. | Backend/runtime owner: allow approved local preview origin; backend/test-data owner: provide mobile-backed customer row and no-capture quote fixture. |
| Checkout commit | Blocked/out-of-scope pending decision | Source disables legacy `/payments/checkout/commit`; safe provider commit fixture not supplied. | Board/billing owner: explicitly declare out of scope or provide sandbox-only commit path with no real capture. |
| Wallet balance/history | Blocked | `/wallet` and `/wallet/transactions` return `401 USER_NOT_FOUND`. | Backend/test-data owner: provide mobile shadow plus wallet and transaction rows. |
| Payment history | Blocked | `/payments/history` returns `401 USER_NOT_FOUND`. | Backend/test-data owner: provide synthetic payment history rows tied to the same customer id. |
| Referral/promo/partner-code | Blocked | `/referral/status` returns `401 USER_NOT_FOUND`; code rows/feature flags not verified. | Growth/backend test-data owner: provide enabled/disabled feature states and synthetic code outcomes. |
| Active/trial/expired subscription states | Blocked except empty state | `/subscriptions/active` only has `status=none`; `/customer-subscriptions/` returns `404`; `/entitlements/current` returns `401 USER_NOT_FOUND`. | Backend/test-data owner: provide active/trial/expired entitlement/subscription rows and runtime route parity. |
| VPN config/service access | Partially blocked | `/auth/devices` works; `/access-delivery-channels/current/service-state` returns `403 CSRF`; no service identity/config fixture is published. | Backend/runtime owner: fix CSRF QA origin; VPN/service owner: provide redacted non-production service identity/provisioning/device credential fixtures. |
| Telegram Mini App | Blocked | `/miniapp/bootstrap` and `/miniapp/config` return `401 USER_NOT_FOUND`; no approved signed synthetic `initData` or bypass exists. | Telegram/backend owner: provide signed synthetic entry or Board-approved bypass without raw real `initData`. |
| Refresh/session renewal | Blocked for cookie POST | `/auth/refresh` returns `403 CSRF origin validation failed`. | Backend/runtime owner: allow approved preview origin or safe local proxy behavior. |
| Runtime capabilities | Blocked on live target | `/client/capabilities` returns `404` although source/OpenAPI contains it. | Backend/runtime owner: align stage image or publish route-not-available note. |
| Passkey policy | Blocked on live target | `/auth/passkeys/policy` returns `404` on `8014`. | Backend/runtime owner: align stage image or publish route-not-available note. |

## Minimal Unblock Criteria

1. Approved local frontend preview origin is accepted by CSRF for cookie-authenticated POST QA, or the local-only proxy provides an explicitly approved origin rewrite.
2. Checkout quote reaches business logic and returns a route-appropriate no-capture result for the protected customer fixture.
3. Safe non-empty fixture rows are provided where release-gate scope requires wallet transactions, payment history, referral/promo/partner-code outcomes, and active/trial/expired subscription states.
4. VPN/service-access fixture provides non-production service identity/config state without publishing subscription URLs, config links, device secrets or provider tokens.
5. Passkey policy request from the frontend preview supplies/preserves the expected origin and returns route-appropriate policy output.
6. Checkout commit is either explicitly out of scope or backed by a sandbox-only provider path with no real capture.
7. Telegram Mini App entry is synthetic and signed, or Board-approved bypass is documented. Raw real `initData` remains forbidden.

## Remaining Owner / Action

This issue should remain blocked until Backend/test-data and runtime owners provide the remaining fixture/runtime updates or Board/QA Lead accepts the listed areas as out of scope for the release gate.

Named unblock owner/action:

- Backend/runtime owner: make approved local preview origin CSRF-compatible for cookie-authenticated POST routes and ensure passkey policy receives expected origin context.
- Backend/test-data owner: provide secret-free manifest for no-capture checkout quote, non-empty wallet/payment/referral/code rows if required, active/trial/expired subscription states, and VPN/service-access config fixture.
- QA Lead/Board: decide whether checkout commit, VPN config delivery, and Telegram Mini App signed entry are required for this release gate or accepted as not-tested.

## Context7 Evidence

Context7 docs checked: unavailable - monthly quota exceeded. Fallback official docs checked: FastAPI middleware docs `https://fastapi.tiangolo.com/tutorial/middleware/` and FastAPI CORS docs `https://fastapi.tiangolo.com/tutorial/cors/`. Pure fixture availability findings are manual API/source observations.
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
