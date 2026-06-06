# CYBA-456 Raw Notes - Client Frontend Manual QA

Agent: `qa-client-frontend-manual`
Timestamp: `2026-06-04T16:07:45Z`
Issue: [CYBA-456](/CYBA/issues/CYBA-456)
Workspace: `/srv/paperclip/data/instances/default/projects/b412bbf0-42d3-4803-913b-15951083d2fb/55092778-1c70-4f8a-aa61-869c6d0f33ae/_default/VPNBussiness-main`

## Environment

- Browser: Playwright Chromium headless.
- Frontend: Next dev server confirmed at `http://127.0.0.1:9001` during survey.
- Viewports:
  - Desktop: `1440x1000`.
  - Mobile: `390x844`.
- Locales smoked: `en-EN`, `ru-RU`.
- User role/state: unauthenticated public/client visitor.
- Test data: fake emails only, for example `qa-reset@example.test`. No real PII, passwords, cookies, JWT, payment data, or Telegram `initData` stored.
- Code/source changes: none intended. QA artifacts only.

## Setup Notes

- `currentExecutionWorkspace` from Paperclip heartbeat context was `null`, so no managed runtime service was available.
- Started `frontend` manually for QA with `NEXT_TELEMETRY_DISABLED=1 npm run dev`.
- `frontend/next.config.ts` rewrites `/api/v1/:path*` to `API_INTERNAL_ORIGIN`, `API_URL`, or default `http://localhost:8000`.
- `127.0.0.1:8000` refused connections in this run, so API-backed flows are blocked until a local/staging backend and sanitized fixtures are provided.
- Context7 docs checked: unavailable - quota exceeded. Fallback official docs checked for Next.js rewrites: `https://nextjs.org/docs/pages/api-reference/config/next-config-js/rewrites`.

## Route Survey

Evidence:

- Route/network JSON: `evidence/client/network/route-survey.json`
- Redirect stability JSON: `evidence/client/network/redirect-stability.json`
- Auth interaction JSON: `evidence/client/network/auth-interactions.json`
- Screenshots: `evidence/client/screenshots/*.png`

Public pages:

- `GET /en-EN`, `/pricing`, `/features`, `/download`, `/network`, `/help`, `/contact`, `/status` returned `200`.
- `GET /ru-RU` and `/ru-RU/pricing` returned `200` in mobile viewport.
- `/en-EN/network` returned `200`, but telemetry endpoints returned `500`, leaving public metrics as `—`.

Auth pages:

- `GET /en-EN/login`, `/register`, `/forgot-password`, `/magic-link`, `/telegram-link` returned `200`.
- `GET /ru-RU/login` returned `200` in mobile viewport.
- Login submit with fake credentials showed visible `Login failed` after `500 /api/v1/auth/login`.
- Magic link submit showed visible `Failed to send magic link` after `500 /api/v1/auth/magic-link`.
- Forgot password submit incorrectly showed success/reset-code state after `500 /api/v1/auth/forgot-password`.
- Register terms-required check kept `Create Account` disabled when terms were not accepted. Full register submit was not completed because checkbox automation hit a locator/pointer interception limitation; no user-visible register bug filed from that.

Dashboard/auth guard:

- Initial dashboard/subscription/wallet/payment/referral/server/settings/support pages returned `200` but displayed `REDIRECTING TO LOGIN...`.
- After 7 seconds, `/en-EN/dashboard` redirected to `/en-EN/login?redirect=%2Fen-EN%2Fdashboard`.
- After 7 seconds, `/en-EN/wallet` redirected to `/en-EN/login?redirect=%2Fen-EN%2Fwallet`.
- No unauthenticated dashboard data exposure found in this smoke.
- Console/network still showed `500 /api/v1/auth/session` due missing backend target.

Miniapp:

- `GET /en-EN/miniapp/home`, `/plans`, `/wallet`, `/payments`, `/referral`, `/devices`, `/profile` returned `200` in mobile viewport.
- Without Telegram WebApp context / `initData`, pages stayed on `Signing you in via Telegram...`.
- `miniapp/home` was still in the same loading state after 7 seconds, with no retry, open-in-Telegram, login, or support path.

## Findings Handed Off

- [CYBA-465](/CYBA/issues/CYBA-465): forgot-password shows success after API `500`.
- [CYBA-466](/CYBA/issues/CYBA-466): miniapp routes hang without Telegram `initData`.
- [CYBA-467](/CYBA/issues/CYBA-467): public network page silently blanks metrics when API fails.
- [CYBA-468](/CYBA/issues/CYBA-468): QA unblock for API/test fixtures to complete integrated flows.

## Resume After API Fixture Unblock - 2026-06-04T17:03:48Z

Wake reason: `issue_blockers_resolved`.

Setup:

- `CYBA-468` and `CYBA-480` were `done`.
- Paperclip `currentExecutionWorkspace` was still `null`, so no managed runtime service existed.
- Started local `frontend` manually on `http://127.0.0.1:9001` with `API_INTERNAL_ORIGIN=http://127.0.0.1:8014`, `API_URL=http://127.0.0.1:8014`, `NEXT_TELEMETRY_DISABLED=1`.
- `GET http://127.0.0.1:8014/readiness` returned `200` with `database=true`, `redis=true`, `queue=true`.
- Unauthenticated `GET /api/v1/auth/session` through `8014` returned route-appropriate `401 Not authenticated`.
- Used protected synthetic customer credential key group `CYBA451_CUSTOMER_WEB_*`; no credential values, cookies, JWTs, refresh tokens, payment secrets, Telegram `initData`, or production PII were written to artifacts.

Integrated login/dashboard repro:

- Browser: headless Chromium via CDP, desktop `1440x1000`, locale `en-EN`.
- Route: `http://127.0.0.1:9001/en-EN/login`.
- After typing approved synthetic credentials and clicking `Sign In`, network showed:
  - `POST /api/v1/auth/login` -> `200`.
  - `GET /api/v1/auth/session` -> `200`.
  - `GET /api/v1/users/me/profile` -> `200`.
  - `GET /api/v1/users/me/usage` -> `200`.
  - `GET /api/v1/entitlements/current` -> `401 USER_NOT_FOUND`.
  - `POST /api/v1/access-delivery-channels/current/service-state` -> `403 CSRF origin validation failed`.
  - `GET /api/v1/wallet` -> `401 USER_NOT_FOUND`.
  - `POST /api/v1/auth/refresh` -> `403 CSRF origin validation failed`.
- Final visible state was the login page at `http://127.0.0.1:9001/en-EN/login?redirect=%2Fen-EN%2Fdashboard`.
- Direct backend cookie-jar smoke confirmed the same fixture can login and restore `/api/v1/auth/session` with active customer session facts.

New evidence:

- `evidence/client/network/integrated-login-repro.json`
- `evidence/client/network/integrated-backend-cookie-jar-smoke.json`
- `evidence/client/screenshots/integrated-login-repro-before-type-en-desktop.png`
- `evidence/client/screenshots/integrated-login-repro-after-submit-en-desktop.png`

New handoff blockers:

- [CYBA-488](/CYBA/issues/CYBA-488): P1 customer login returns to login after successful session restore.
- [CYBA-489](/CYBA/issues/CYBA-489): remaining client fixtures needed for checkout, wallet/payment history rows, referral/promo/partner-code, active/trial/expired subscription states, VPN config/service access, and Telegram Mini App signed entry.

Context7 docs checked: N/A - manual UI/API integration and fixture availability findings; no library-dependent code/config changes were made.

## Blocked / Not Tested

Originally blocked by [CYBA-468](/CYBA/issues/CYBA-468). After the `8014` target became available, [CYBA-488](/CYBA/issues/CYBA-488) was handed off and later cleared by the [CYBA-497](/CYBA/issues/CYBA-497) retest. Current remaining blocker is [CYBA-489](/CYBA/issues/CYBA-489):

- Broader checkout/payment/referral/VPN fixture coverage beyond the CYBA-497 login/session restore retest.
- Logout, session expiry and cross-route session restore.
- Real registration success and verification.
- Checkout/payment, promo/referral/partner-code application, subscription lifecycle.
- Authenticated wallet balance and payment history.
- Authenticated VPN config/device surfaces.
- Telegram Mini App inside a real Telegram test context with sanitized `initData`.
- Payment capture and production/customer data were not attempted.

## CYBA-497 Retest - 2026-06-04T17:31:01Z

Issue: [CYBA-497](/CYBA/issues/CYBA-497)
Purpose: retest [CYBA-488](/CYBA/issues/CYBA-488), "customer login returns to login after successful session restore".

Setup:

- `currentExecutionWorkspace` from Paperclip heartbeat context was `null`, so no managed runtime service was available.
- Local backend target `http://127.0.0.1:8014` was already listening; unauthenticated `GET /api/v1/auth/session` returned expected `401 Not authenticated`.
- Started local `frontend` manually on `http://127.0.0.1:9001` with `NODE_ENV=development`, `NEXT_TELEMETRY_DISABLED=1`, `API_INTERNAL_ORIGIN=http://127.0.0.1:8014`, and `API_URL=http://127.0.0.1:8014`.
- Browser: Playwright Chromium headless, desktop `1440x1000`, locale `en-EN`.
- User role/state: synthetic active customer from protected `CYBA451_CUSTOMER_WEB_*` key group.
- Secret handling: credential values, cookies, JWT values, refresh-token values, request bodies, and storageState were not written to evidence.

Steps:

1. Opened `http://127.0.0.1:9001/en-EN/login`.
2. Filled protected synthetic customer identifier and credential.
3. Submitted the login form.
4. Waited for dashboard/session/resource calls.
5. Because the dashboard stayed open, reloaded `http://127.0.0.1:9001/en-EN/dashboard` once to exercise session restore persistence.

Expected:

- `POST /api/v1/auth/login -> 200`.
- `GET /api/v1/auth/session -> 200`.
- Dashboard remains at `/en-EN/dashboard`.
- `GET /api/v1/wallet -> 401 USER_NOT_FOUND` and similar resource failures render inline.
- No `POST /api/v1/auth/refresh`.
- No redirect to `/login?redirect=/dashboard`.

Actual:

- `POST /api/v1/auth/login -> 200`.
- `GET /api/v1/auth/session -> 200` during login and again after dashboard reload.
- Final URL after login: `http://127.0.0.1:9001/en-EN/dashboard`.
- Final URL after reload/session restore: `http://127.0.0.1:9001/en-EN/dashboard`.
- `GET /api/v1/wallet -> 401 USER_NOT_FOUND` occurred during login dashboard load and reload; dashboard rendered inline partial-data/retry surfaces.
- `POST /api/v1/auth/refresh` count: `0`.
- Redirect to login: `false`.

Result: PASS. The CYBA-488 regression was not reproduced in this retest.

Evidence:

- `evidence/client/cyba-497/session-restore-retest-2026-06-04T173101310Z.json`
- `evidence/client/cyba-497/login-before-submit-2026-06-04T173101310Z.png`
- `evidence/client/cyba-497/final-sanitized-2026-06-04T173101310Z.png`
- `evidence/client/cyba-497/reload-sanitized-2026-06-04T173101310Z.png`

Sanitization:

- Exact-value scan for `CYBA451_CUSTOMER_WEB_EMAIL`, `CYBA451_CUSTOMER_WEB_LOGIN`, and `CYBA451_CUSTOMER_WEB_PASSWORD` in the JSON evidence passed.
- Final screenshot was visually checked; synthetic login text is masked as `[redacted-login]`.

Context7 docs checked: unavailable - monthly quota exceeded. Fallback official docs checked: Playwright Page API at `https://playwright.dev/docs/api/class-page`.
## Final Resume Update - 2026-06-05T05:23:29Z

Fresh backend/data-support evidence from [CYBA-489](/CYBA/issues/CYBA-489) was collected against the current approved local-stage pair `http://127.0.0.1:18080` + `Origin: http://127.0.0.1:13000`:

- Evidence: `qa-artifacts/CYBA-489/cyba-489-localstage-revalidation__20260605T052329Z.md` and `qa-artifacts/CYBA-489/cyba-489-localstage-revalidation__20260605T052329Z.json`.
- Auth/session remains usable: login `200`, session `200`.
- The old browser dashboard persistence blocker remains resolved by [CYBA-497](/CYBA/issues/CYBA-497).
- Checkout quote and service-state now reach API route logic with approved Origin and return `200`; auth refresh also returns `200`. This clears the old CSRF-origin blocker for current local-stage QA.
- Wallet, payment-history, referral, Mini App bootstrap, entitlements, customer-subscriptions, client capabilities, and passkey policy-with-Origin are reachable for empty/synthetic-state QA.
- Remaining not-tested/product-data gaps: active/trial/expired subscriptions, non-empty wallet/payment rows, referral/promo/partner-code outcome rows, subscription-backed Mini App config/VPN config, service identity/device credential, and signed synthetic Telegram Mini App entry.

Final client QA disposition: complete with documented pass/fail/blocked coverage. This is a NO-GO for real production readiness until the residual fixture/product gaps and open P1/P2 findings are accepted into a fix backlog or covered by separate approved safe fixtures.

## CYBA-572 Business-Flow Recheck - 2026-06-06T07:20:26Z

Issue: [CYBA-572](/CYBA/issues/CYBA-572)
Wake reason: `issue_blockers_resolved`

Setup:

- `CYBA-569` was `done`; `currentExecutionWorkspace` from Paperclip heartbeat context was `null`, so no managed runtime service URL was available.
- Used approved local-stage frontend/API pair:
  - Frontend: `http://127.0.0.1:13000`
  - Backend: `http://127.0.0.1:18080`
- Browser evidence: Playwright Chromium headless, desktop `1440x1000`, mobile `390x844`.
- API evidence: direct local-stage API probes with `Origin` / `Referer` set to `http://127.0.0.1:13000`.
- User role/state: unauthenticated visitor plus protected synthetic customer fixture from `CYBA451_CUSTOMER_WEB_*`.
- Safe handling: credential values, cookies, JWTs, refresh tokens, request bodies, storageState, raw Telegram `initData`, VPN config links and payment secrets were not stored.
- Context7 docs checked: Context7 quota exceeded for Playwright; fallback official docs opened for Playwright Page API. Product findings below are manual UI/business-flow findings, not framework-dependent root-cause claims.

Evidence:

- `evidence/client/cyba-572/network/frontend-route-survey-20260606T072248Z.json`
- `evidence/client/cyba-572/network/direct-api-business-flow-20260606T072026Z.json`
- `evidence/client/cyba-572/network/focused-post-business-flow-20260606T072157Z.json`
- `evidence/client/cyba-572/network/focused-subscriptions-surface-20260606T072408Z.json`
- `evidence/client/cyba-572/screenshots/compact-public-pricing-en-desktop-20260606T071705Z.png`
- `evidence/client/cyba-572/screenshots/compact-login-ru-mobile-20260606T071705Z.png`
- `evidence/client/cyba-572/screenshots/compact-unauth-dashboard-en-desktop-20260606T071705Z.png`
- `evidence/client/cyba-572/screenshots/compact-miniapp-home-no-telegram-mobile-20260606T071705Z.png`

Pass / reachable:

- Backend readiness/status: `GET /readiness -> 200`, `GET /api/v1/status -> 200`.
- Frontend route survey: 27/28 checked frontend routes returned `200`; only `/en-EN/miniapp/vpn` returned `404`.
- Public/auth smoke: `/en-EN`, `/pricing`, `/features`, `/download`, `/network`, `/help`, `/contact`, `/status`, `/login`, `/register`, `/forgot-password`, `/magic-link`, `/telegram-link` returned `200`.
- Mobile/locale smoke: `/ru-RU`, `/ru-RU/pricing`, `/ru-RU/login` returned `200`.
- Unauthenticated protected route HTTP shell returned `200` and the screenshot for `/en-EN/dashboard` shows the login screen after guard handling; no unauthenticated customer data exposure was observed in the captured screenshot.
- Synthetic customer API login/session: `POST /api/v1/auth/login -> 200`, `GET /api/v1/auth/session -> 200`.
- Customer empty-state business APIs are reachable: `/wallet -> 200`, `/wallet/transactions -> 200` length `0`, `/payments/history -> 200` payments length `0`, `/referral/status -> 200` with `enabled=false`, `/miniapp/bootstrap -> 200`, `/entitlements/current -> 200` with status `none`, `/customer-subscriptions/ -> 200`.
- Checkout/service POSTs now reach business logic with approved origin: `POST /payments/checkout/quote -> 200`, `POST /access-delivery-channels/current/service-state -> 200`, `POST /auth/refresh -> 200`.
- Old Mini App outside-Telegram hang symptom was not reproduced in this smoke. `/en-EN/miniapp/home` rendered a deterministic empty state: `No Active Subscription` and `No VPN config available`.

New handoff:

- [CYBA-580](/CYBA/issues/CYBA-580): P2 Mini App VPN route returns `404` from a linked home surface.

Blocked / gaps remaining:

- Active/trial/expired subscription states were not tested because the current fixture has entitlement status `none`.
- Non-empty wallet transaction rows and payment history rows were not available.
- Referral/promo/partner-code accepted/rejected/enabled outcome fixtures were not available; current `/referral/status` is disabled.
- Subscription-backed Mini App config/VPN config remains unavailable: `/api/v1/miniapp/config -> 404 Subscription config not found`.
- Service-state route is reachable, but `service_identity`, `device_credential`, and `access_delivery_channel` are absent because entitlement status is `none`; no real VPN config/device credential was inspected.
- Signed Telegram Mini App entry with sanitized `initData` was not available and was not tested.
- Checkout quote was tested; checkout commit/payment capture was not attempted.
- A broad browser route collection run timed out before JSON output. Partial screenshots were kept, then direct API/HTTP evidence was used for durable coverage. This is a tooling limitation, not filed as a product bug.

Sanitization:

- Secret value scan in `direct-api-business-flow-20260606T072026Z.json`: 0 hits for the three protected synthetic credential values.
- Secret value scan in `focused-post-business-flow-20260606T072157Z.json`: 0 hits.
- Secret value scan in `focused-subscriptions-surface-20260606T072408Z.json`: 0 hits.
