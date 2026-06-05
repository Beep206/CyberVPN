# CYBA-489 Backend Data Support Notes

Дата проверки: 2026-06-04

## Scope

Read-only backend/API/test-data support for [CYBA-489](/CYBA/issues/CYBA-489), child of [CYBA-456](/CYBA/issues/CYBA-456). Backend code, migrations, contracts, seeds, `.env` files, production data and secrets were not modified.

## Safe Handling

- Secret values were not copied from `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`; only variable names were inspected.
- Temporary cookie jars and login payload files were deleted after smoke checks.
- No JWT, cookies, refresh tokens, passwords, `.env` values, payment provider secrets, provider transaction secrets, Telegram `initData`, subscription URLs, config links, device secrets, provider tokens or production PII are stored in this artifact.

## Current Runtime Target

- API target: `http://127.0.0.1:8014`
- Upstream target through proxy: `http://127.0.0.1:18080`
- Proxy artifact: `qa-artifacts/CYBA-480/customer_qa_proxy.py`
- Protected credential handoff: `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`

The `CYBA-480` proxy injects `X-Auth-Realm: customer` and rewrites auth cookies for local HTTP. It does not rewrite `Origin` or `Referer`, so unsafe cookie-authenticated POST requests still depend on the upstream `CORS_ORIGINS`/CSRF allowlist.

## Live Smoke Summary

Commands were run against `http://127.0.0.1:8014` with the protected customer web fixture. Values below are sanitized.

### Resume Revalidation - 2026-06-04T20:08:20Z

Operator resumed the issue after a usage-limit stall and asked for blocker-aware continuation. A fresh smoke against `8014` shows that the target changed after the first pass: several earlier `USER_NOT_FOUND` and `404` blockers are now cleared.

| Probe | Result | Sanitized body/header evidence |
|---|---:|---|
| `GET /readiness` | `200` | target alive |
| `GET /api/v1/status` | `200` | target alive |
| `POST /api/v1/auth/login` | `200` | cookie-backed session established; token values not stored |
| cookie-backed `GET /api/v1/auth/session` | `200` | `auth_realm_key=customer`, `principal_type=customer` |
| cookie-backed `GET /api/v1/auth/devices` | `200` | keys `devices,total` |
| cookie-backed `GET /api/v1/subscriptions/active` | `200` | `status=none` |
| cookie-backed `GET /api/v1/wallet` | `200` | keys `balance,currency,frozen,id` |
| cookie-backed `GET /api/v1/wallet/transactions` | `200` | empty array |
| cookie-backed `GET /api/v1/payments/history` | `200` | key `payments` |
| cookie-backed `GET /api/v1/referral/status` | `200` | keys `commission_rate,enabled,friend_discount_pct,reward_hold_days` |
| cookie-backed `GET /api/v1/miniapp/bootstrap` | `200` | full bootstrap shape present |
| cookie-backed `GET /api/v1/miniapp/config` | `404` | `Subscription config not found` |
| cookie-backed `GET /api/v1/entitlements/current` | `200` | `status=none` |
| cookie-backed `GET /api/v1/customer-subscriptions/` | `200` | `items_count=0` |
| public `GET /api/v1/client/capabilities` | `200` | keys `auth,growth,partner,payments,subscriptions` |
| public `GET /api/v1/auth/passkeys/policy` | `403` | `Passkey origin is required` when called without `Origin` |
| cookie-backed `POST /api/v1/payments/checkout/quote` | `403` | `CSRF origin validation failed` |
| cookie-backed `POST /api/v1/access-delivery-channels/current/service-state` | `403` | `CSRF origin validation failed` |
| cookie-backed `POST /api/v1/auth/refresh` | `403` | `CSRF origin validation failed` |

Current blocker delta:

- Cleared: wallet balance, wallet transactions empty state, payment history empty state, referral status, Mini App bootstrap, current entitlements empty state, customer-subscriptions empty list, client capabilities route.
- Still blocked: checkout quote/service-state/refresh cookie-auth POST by CSRF; Mini App config by missing subscription/config fixture; passkey policy by origin handling; active/trial/expired subscription/VPN config states still need explicit fixtures beyond empty states.

Historical smoke from the first pass remains below for traceability.

| Probe | Result | Sanitized body/header evidence |
|---|---:|---|
| `GET /readiness` | `200` | readiness target is alive |
| `GET /api/v1/status` | `200` | status target is alive |
| `POST /api/v1/auth/login` | `200` | token fields present, values not stored |
| cookie-backed `GET /api/v1/auth/session` | `200` | `auth_realm_key=customer`, `principal_type=customer` |
| cookie-backed `GET /api/v1/auth/devices` | `200` | keys `devices,total` |
| cookie-backed `GET /api/v1/subscriptions/active` | `200` | `status=none` |
| cookie-backed `GET /api/v1/wallet` | `401` | `detail.code=USER_NOT_FOUND` |
| cookie-backed `GET /api/v1/wallet/transactions` | `401` | `detail.code=USER_NOT_FOUND` |
| cookie-backed `GET /api/v1/payments/history` | `401` | `detail.code=USER_NOT_FOUND` |
| cookie-backed `GET /api/v1/referral/status` | `401` | `detail.code=USER_NOT_FOUND` |
| cookie-backed `GET /api/v1/miniapp/bootstrap` | `401` | `detail.code=USER_NOT_FOUND` |
| cookie-backed `GET /api/v1/miniapp/config` | `401` | `detail.code=USER_NOT_FOUND` |
| cookie-backed `GET /api/v1/entitlements/current` | `401` | `detail.code=USER_NOT_FOUND` |
| cookie-backed `GET /api/v1/customer-subscriptions/` | `404` | not JSON |
| cookie-backed `GET /api/v1/customer-subscriptions` | `404` | not JSON |
| cookie-backed `POST /api/v1/payments/checkout/quote` | `403` | `{"detail":"CSRF origin validation failed"}` |
| cookie-backed `POST /api/v1/access-delivery-channels/current/service-state` | `403` | CSRF gate before service-state logic |
| cookie-backed `POST /api/v1/auth/refresh` | `403` | CSRF gate before refresh logic |
| public `GET /api/v1/client/capabilities` | `404` | live target missing route |
| public `GET /api/v1/auth/passkeys/policy` | `404` | live target missing route |

## Source / Contract Context

The source and generated contracts contain the scoped API surfaces, but the current live target does not expose or satisfy all of them:

- `backend/src/presentation/dependencies/auth.py:424` defines `get_current_mobile_user_id`; it accepts cookie auth but then looks up the JWT subject in `mobile_users`. If the `mobile_users` row is missing, it returns `401` with `USER_NOT_FOUND`.
- `backend/src/presentation/api/v1/auth/routes.py:336` contains `_ensure_customer_web_mobile_shadow`, and `backend/src/presentation/api/v1/auth/routes.py:690` calls it after successful customer web login. The current `8014` target still returns `USER_NOT_FOUND` after login, so the local-stage fixture/runtime is missing the mobile shadow row or is not behaving like the current source.
- `backend/src/presentation/api/v1/wallet/routes.py:50`, `backend/src/presentation/api/v1/payments/routes.py:229`, `backend/src/presentation/api/v1/referral/routes.py:95`, `backend/src/presentation/api/v1/miniapp/routes.py:595`, and `backend/src/presentation/api/v1/entitlements/routes.py:119` depend on `get_current_mobile_user_id`.
- `backend/src/presentation/api/v1/customer_subscriptions/routes.py:86` defines `GET /customer-subscriptions/`, and `backend/docs/api/openapi.json` includes `/api/v1/customer-subscriptions/`; the live `8014` target returns `404`.
- `backend/src/presentation/middleware/csrf.py:43` rejects unsafe cookie-authenticated methods when `Origin`/`Referer` is not in `allowed_origins`; `backend/src/main.py:397` enables this in staging/production-like runtime.
- `backend/docs/api/openapi.json` includes `/api/v1/client/capabilities`, but the live `8014` target returns `404`.

## Remaining Fixture Requirements

Provide a new secret-free manifest and approved local/stage fixture pack for these states. Protected values, if any, must remain in the runtime secret handoff file or another approved protected channel.

After the 2026-06-04T20:08:20Z resume smoke, wallet/payment/referral/customer-subscription empty states are partially available. The rows below now mean "needed for full release-gate coverage beyond the newly available empty/synthetic shapes."

| Area | Fixture required | Safe expected outcome |
|---|---|---|
| Checkout quote safe-mode | Mobile-backed customer row matching the authenticated web customer, public plan id, CSRF-compatible local preview origin, and explicit no-capture payment policy. | `POST /api/v1/payments/checkout/quote` reaches quote logic and returns a quote or route-appropriate non-500 validation response. No real payment capture. |
| Checkout commit | Board/billing decision: either explicitly out of scope for this release gate, or a sandbox-only provider fixture with no external capture. | Legacy `POST /api/v1/payments/checkout/commit` is deprecated/disabled in source; do not test real commit unless a safe approved path is provided. |
| Wallet balance/history | `mobile_users` row for the customer id plus wallet row and non-production wallet transactions. | `GET /api/v1/wallet` and `/wallet/transactions` return `200` with sanitized balance/history rows. |
| Payment history | Non-production payment attempts/history rows tied to the same customer id. | `GET /api/v1/payments/history` returns `200` with provider ids redacted or synthetic. |
| Referral/promo/partner-code | Runtime flags and synthetic invite/referral/promo/partner code rows, including accepted/rejected/disabled outcomes. | `/referral/status` and relevant code resolution endpoints return deterministic enabled/disabled and code-result states. |
| Subscription states | Active, trial and expired entitlement/subscription rows beyond `/subscriptions/active` `status=none`. | Dashboard and Mini App subscription/entitlement surfaces can test active/trial/expired/empty states. |
| VPN config/service access | Non-production service identity, entitlement grant, access delivery channel/provisioning profile/device credential rows. | Service-state/config routes return safe redacted shapes. Do not publish subscription URLs, config links, device secrets or provider tokens. |
| Telegram Mini App | Approved signed synthetic `initData` generation or a Board-approved local bypass. | Mini App auth/bootstrap/config can be tested without storing raw real `initData`. |
| Local-stage CSRF | Upstream `CORS_ORIGINS` includes the frontend preview origin, or the local-only proxy safely rewrites `Origin`/`Referer` for approved QA. | Cookie-authenticated POST routes are not blocked at CSRF before fixture logic. |
| Live route parity | Stage image exposes current source/OpenAPI routes for `client/capabilities`, `customer-subscriptions`, and passkey policy. | Runtime route inventory matches frontend-generated contract for client QA scope. |

## Owner / Action Needed

Backend/test-data owner must provide the fixture rows or a new protected fixture manifest. QA Lead/Board must confirm whether checkout commit, VPN config delivery, and Telegram Mini App signed entry are in scope for this release gate or explicitly accepted as not-tested/out-of-scope.

## Context7 Evidence

Context7 docs checked: unavailable - monthly quota exceeded. Fallback official docs checked: FastAPI middleware docs `https://fastapi.tiangolo.com/tutorial/middleware/` and FastAPI CORS docs `https://fastapi.tiangolo.com/tutorial/cors/`. Repo-local source remains the primary evidence for CyberVPN-specific CSRF and fixture behavior.
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
