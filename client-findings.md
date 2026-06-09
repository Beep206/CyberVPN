# CYBA-456 Client Frontend Manual QA Findings

Issue: [CYBA-456](/CYBA/issues/CYBA-456)
Agent: `qa-client-frontend-manual`
Run timestamp: `2026-06-04T16:07:45Z`
Latest resume timestamp: `2026-06-04T17:03:48Z`
Latest retest timestamp: `2026-06-04T17:31:01Z`

## Summary

- Public/auth page smoke completed for `en-EN` desktop and `ru-RU` mobile.
- Dashboard protected routes redirect unauthenticated users to login; no unauthenticated data exposure found.
- After [CYBA-468](/CYBA/issues/CYBA-468) and [CYBA-480](/CYBA/issues/CYBA-480), the approved local-stage customer API target `http://127.0.0.1:8014` was available for integrated smoke.
- [CYBA-497](/CYBA/issues/CYBA-497) retest passed: [CYBA-488](/CYBA/issues/CYBA-488) was not reproduced after the frontend fix.
- Four client bugs were handed off as child issues.
- The prior browser dashboard persistence blocker [CYBA-488](/CYBA/issues/CYBA-488) is cleared by [CYBA-497](/CYBA/issues/CYBA-497) retest; remaining checkout/wallet/referral/VPN/TMA fixture scope is still blocked by [CYBA-489](/CYBA/issues/CYBA-489).

## Retest Updates

### PASS - CYBA-497 customer login stays on dashboard after session restore

- Retested issue: [CYBA-488](/CYBA/issues/CYBA-488)
- Environment: local `frontend` Next dev server at `http://127.0.0.1:9001`, `API_INTERNAL_ORIGIN=http://127.0.0.1:8014`, `API_URL=http://127.0.0.1:8014`, Chromium headless via Playwright, desktop `1440x1000`, locale `en-EN`.
- User role/state: synthetic active customer fixture from protected `CYBA451_CUSTOMER_WEB_*` key group; credential values, cookies, JWT values, refresh-token values, request bodies, and storageState were not written to evidence.
- Steps executed: opened `/en-EN/login`, submitted protected synthetic customer credentials, waited for dashboard network/resource calls, then reloaded `/en-EN/dashboard` once to exercise session restore persistence.
- Expected result: login/session return `200`; `/wallet -> 401 USER_NOT_FOUND` and similar resource failures render inline; no `POST /api/v1/auth/refresh`; no redirect to login.
- Actual result: `POST /api/v1/auth/login -> 200`, `GET /api/v1/auth/session -> 200`, `GET /api/v1/wallet -> 401 USER_NOT_FOUND`, `POST /api/v1/auth/refresh` count `0`; final URL stayed `http://127.0.0.1:9001/en-EN/dashboard` after login and after reload.
- Evidence:
  - `evidence/client/cyba-497/session-restore-retest-2026-06-04T173101310Z.json`
  - `evidence/client/cyba-497/login-before-submit-2026-06-04T173101310Z.png`
  - `evidence/client/cyba-497/final-sanitized-2026-06-04T173101310Z.png`
  - `evidence/client/cyba-497/reload-sanitized-2026-06-04T173101310Z.png`
- Sanitization: exact-value scan for `CYBA451_CUSTOMER_WEB_EMAIL`, `CYBA451_CUSTOMER_WEB_LOGIN`, and `CYBA451_CUSTOMER_WEB_PASSWORD` in JSON passed; final screenshot was visually checked with synthetic login masked.
- Context7 docs checked: unavailable - monthly quota exceeded. Fallback official docs checked: Playwright Page API at `https://playwright.dev/docs/api/class-page`.

## Bugs

### P1 - Customer login returns to login after successful session restore

- Handoff: [CYBA-488](/CYBA/issues/CYBA-488)
- Environment: local `frontend` Next dev server at `http://127.0.0.1:9001`, `API_INTERNAL_ORIGIN=http://127.0.0.1:8014`, Chromium headless/CDP, desktop `1440x1000`, locale `en-EN`.
- User role/state: synthetic active customer fixture from protected key group `CYBA451_CUSTOMER_WEB_*`; credentials, cookies, JWTs and refresh tokens were not published.
- Steps to reproduce:
  1. Start `frontend` with `NEXT_TELEMETRY_DISABLED=1 API_INTERNAL_ORIGIN=http://127.0.0.1:8014 API_URL=http://127.0.0.1:8014 npm run dev`.
  2. Open `http://127.0.0.1:9001/en-EN/login`.
  3. Enter the approved synthetic customer web credentials from the protected local secret file.
  4. Click `Sign In`.
  5. Wait about 12 seconds and observe the final URL and network.
- Expected result: after `POST /api/v1/auth/login` and cookie-backed `GET /api/v1/auth/session` return `200`, the user remains authenticated on the dashboard; non-critical dashboard widget/API failures render inline and do not end the session.
- Actual result: the browser returns to `http://127.0.0.1:9001/en-EN/login?redirect=%2Fen-EN%2Fdashboard` and shows the login form again.
- Sanitized network facts: `POST /api/v1/auth/login -> 200`, `GET /api/v1/auth/session -> 200`, then dashboard calls include `GET /api/v1/entitlements/current -> 401`, `POST /api/v1/access-delivery-channels/current/service-state -> 403`, `GET /api/v1/wallet -> 401`, and `POST /api/v1/auth/refresh -> 403`.
- Evidence:
  - `evidence/client/network/integrated-login-repro.json`
  - `evidence/client/network/integrated-backend-cookie-jar-smoke.json`
  - `evidence/client/screenshots/integrated-login-repro-before-type-en-desktop.png`
  - `evidence/client/screenshots/integrated-login-repro-after-submit-en-desktop.png`
- Context7 docs checked: N/A - manual UI/API integration finding; no external framework/library behavior or code change was used as the basis for the report.

### P1 - Forgot-password shows success after API failure

- Handoff: [CYBA-465](/CYBA/issues/CYBA-465)
- Environment: local `frontend` Next dev server at `http://127.0.0.1:9001`, Chromium headless, desktop `1440x1000`, locale `en-EN`.
- User role/state: unauthenticated customer using fake email `qa-reset@example.test`.
- Steps to reproduce:
  1. Open `http://127.0.0.1:9001/en-EN/forgot-password`.
  2. Enter `qa-reset@example.test`.
  3. Click `Send Reset Code`.
  4. Observe visible page state and network.
- Expected result: failed `POST /api/v1/auth/forgot-password` keeps the user on the request form and shows a failure/retry message.
- Actual result: page advances to `Check Your Inbox` and reset-code entry even though network shows `500 Internal Server Error`.
- Evidence:
  - `evidence/client/screenshots/forgot-password-submit-api-failure.png`
  - `evidence/client/network/auth-interactions.json`
- Context7 docs checked: N/A - manual UI/business-flow finding.

### P2 - Miniapp routes hang without Telegram initData

- Handoff: [CYBA-466](/CYBA/issues/CYBA-466)
- Environment: local `frontend` Next dev server at `http://127.0.0.1:9001`, Chromium headless, mobile `390x844`, locale `en-EN`.
- User role/state: unauthenticated browser visitor, no Telegram WebApp context or `initData`.
- Steps to reproduce:
  1. Open `http://127.0.0.1:9001/en-EN/miniapp/home` outside Telegram.
  2. Wait at least 7 seconds.
  3. Repeat smoke on `/miniapp/plans`, `/miniapp/wallet`, `/miniapp/payments`, `/miniapp/referral`, `/miniapp/devices`, `/miniapp/profile`.
- Expected result: deterministic recovery path such as open-in-Telegram, retry, login, support, or clear Telegram-required error.
- Actual result: page remains on `Signing you in via Telegram...` with no visible action or timeout.
- Evidence:
  - `evidence/client/screenshots/miniapp-home-no-telegram-after-7s.png`
  - `evidence/client/network/redirect-stability.json`
  - `evidence/client/screenshots/miniapp-*-en-mobile.png`
- Context7 docs checked: N/A - manual UI/business-flow finding.

### P2 - Network page silently blanks metrics when API fails

- Handoff: [CYBA-467](/CYBA/issues/CYBA-467)
- Environment: local `frontend` Next dev server at `http://127.0.0.1:9001`, Chromium headless, desktop `1440x1000`, locale `en-EN`.
- User role/state: public unauthenticated visitor.
- Steps to reproduce:
  1. Use a frontend environment where `API_INTERNAL_ORIGIN` / `API_URL` is unavailable.
  2. Open `http://127.0.0.1:9001/en-EN/network`.
  3. Observe visible metrics and network panel.
- Expected result: user-visible degraded/error/fallback state for unavailable telemetry.
- Actual result: page returns `200`, but metrics show `MONTHLY TRAFFIC —`, `ONLINE SERVERS —`, `LIVE USERS —`; network shows `500` for `GET /api/v1/public/network/overview` and `GET /api/v1/public/network/regions`.
- Evidence:
  - `evidence/client/screenshots/network-en-desktop.png`
  - `evidence/client/network/route-survey.json`
  - `evidence/client/network/network-overview-headers.txt`
  - `evidence/client/network/network-regions-headers.txt`
- Context7 docs checked: unavailable - quota exceeded. Fallback official docs checked: Next.js rewrites docs at `https://nextjs.org/docs/pages/api-reference/config/next-config-js/rewrites`.

## Product Gaps / Risks

- Public Russian mobile pages still expose mixed English/product terms such as `Pricing`, `Servers`, `Download`, `Terms of Service`, `PUBLIC VPN ACCESS`, and English FAQ fragments. This was observed but not filed as a bug here because the current issue scope only requested en/ru smoke, and no source/localization fix was requested.
- WebGL `GPU stall due to ReadPixels` warnings occurred on 3D-heavy pages in Chromium headless. No user-visible blank canvas was observed in this run.

## Blocked / Not Tested

Resolved unblockers:

- [CYBA-468](/CYBA/issues/CYBA-468) and [CYBA-480](/CYBA/issues/CYBA-480) provided a reachable local-stage target for minimal customer auth/session smoke: `http://127.0.0.1:8014`.

Current blockers:

- [CYBA-489](/CYBA/issues/CYBA-489): remaining fixtures are still needed for checkout, wallet/payment history rows, referral/promo/partner-code, active/trial/expired subscription states, VPN config/service access, and Telegram Mini App signed entry.

- Auth success and browser dashboard persistence are verified by [CYBA-497](/CYBA/issues/CYBA-497) retest for the customer login/session restore regression.
- Logout, session expiry and full session restore across dashboard routes remain not tested because the session is ejected back to login.
- Registration success and verification.
- OAuth/passkey/Telegram login success.
- Checkout/payment, payment history, wallet balance, subscription lifecycle.
- Referral/promo/partner-code authenticated application.
- Authenticated server/device/VPN config surfaces.
- Telegram Mini App with real sanitized Telegram test context.

Environment evidence:

- `evidence/client/network/integrated-login-repro.json`
- `evidence/client/network/integrated-backend-cookie-jar-smoke.json`
- `evidence/client/network/auth-session-headers.txt`
- `evidence/client/network/passkey-policy-headers.txt`
- `evidence/client/network/network-overview-headers.txt`
- `evidence/client/network/network-regions-headers.txt`
- `frontend/next.config.ts` rewrites `/api/v1/:path*` to `API_INTERNAL_ORIGIN`, `API_URL`, or default `http://localhost:8000`.

## Passed Smoke

- `en-EN` public pages: home, pricing, features, download, help, contact, status returned `200` and rendered visible content.
- `ru-RU` public mobile: home, pricing, login returned `200` and rendered visible content.
- Protected dashboard pages did not expose dashboard data to unauthenticated visitors; after waiting they redirected to `/login?redirect=...`.
- Login API failure showed visible `Login failed`.
- Magic-link API failure showed visible `Failed to send magic link`.
## Final Resume Update - 2026-06-05T05:23:29Z

Fresh backend/data-support evidence from [CYBA-489](/CYBA/issues/CYBA-489) was collected against the current approved local-stage pair `http://127.0.0.1:18080` + `Origin: http://127.0.0.1:13000`:

- Evidence: `qa-artifacts/CYBA-489/cyba-489-localstage-revalidation__20260605T052329Z.md` and `qa-artifacts/CYBA-489/cyba-489-localstage-revalidation__20260605T052329Z.json`.
- Auth/session remains usable: login `200`, session `200`.
- The old browser dashboard persistence blocker remains resolved by [CYBA-497](/CYBA/issues/CYBA-497).
- Checkout quote and service-state now reach API route logic with approved Origin and return `200`; auth refresh also returns `200`. This clears the old CSRF-origin blocker for current local-stage QA.
- Wallet, payment-history, referral, Mini App bootstrap, entitlements, customer-subscriptions, client capabilities, and passkey policy-with-Origin are reachable for empty/synthetic-state QA.
- Remaining not-tested/product-data gaps: active/trial/expired subscriptions, non-empty wallet/payment rows, referral/promo/partner-code outcome rows, subscription-backed Mini App config/VPN config, service identity/device credential, and signed synthetic Telegram Mini App entry.

Final client QA disposition: complete with documented pass/fail/blocked coverage. This is a NO-GO for real production readiness until the residual fixture/product gaps and open P1/P2 findings are accepted into a fix backlog or covered by separate approved safe fixtures.

## CYBA-572 Recheck Update - 2026-06-06T07:20:26Z

Post-blocker customer frontend recheck for [CYBA-572](/CYBA/issues/CYBA-572) used local-stage `http://127.0.0.1:13000` + backend `http://127.0.0.1:18080`.

Result:

- PASS: public/auth `en-EN` routes and `ru-RU` mobile smoke returned `200`.
- PASS: protected dashboard shell did not expose unauthenticated customer data in captured evidence.
- PASS: synthetic customer login/session returned `200/200`.
- PASS: wallet, wallet transactions empty state, payment history empty state, referral disabled state, Mini App bootstrap, entitlements empty state, customer subscriptions empty list, checkout quote, service-state and auth refresh are reachable with approved local-stage origin.
- PASS: old Mini App outside-Telegram indefinite `Signing you in via Telegram...` symptom was not reproduced; Mini App home now renders empty subscription/config states.
- FAIL: [CYBA-580](/CYBA/issues/CYBA-580) filed for `/en-EN/miniapp/vpn -> 404` from a linked Mini App home VPN surface.
- GAP: active/trial/expired subscriptions, non-empty wallet/payment history, referral/promo/partner-code outcomes, subscription-backed Mini App/VPN config, service identity/device credential, signed Telegram Mini App `initData`, and checkout commit/payment capture remain not tested due missing safe fixtures or explicit out-of-scope policy.

Evidence:

- `evidence/client/cyba-572/network/frontend-route-survey-20260606T072248Z.json`
- `evidence/client/cyba-572/network/direct-api-business-flow-20260606T072026Z.json`
- `evidence/client/cyba-572/network/focused-post-business-flow-20260606T072157Z.json`
- `evidence/client/cyba-572/network/focused-subscriptions-surface-20260606T072408Z.json`
- `evidence/client/cyba-572/screenshots/compact-public-pricing-en-desktop-20260606T071705Z.png`
- `evidence/client/cyba-572/screenshots/compact-login-ru-mobile-20260606T071705Z.png`
- `evidence/client/cyba-572/screenshots/compact-unauth-dashboard-en-desktop-20260606T071705Z.png`
- `evidence/client/cyba-572/screenshots/compact-miniapp-home-no-telegram-mobile-20260606T071705Z.png`

### P2 - Mini App VPN route returns 404 from linked home surface

- Handoff: [CYBA-580](/CYBA/issues/CYBA-580)
- Environment: local-stage frontend `http://127.0.0.1:13000`, backend `http://127.0.0.1:18080`, Playwright Chromium headless mobile `390x844` and HTTP route survey, locale `en-EN`.
- User role/state: Mini App visitor outside Telegram; no signed `initData`, no real customer/payment/VPN data.
- Steps to reproduce:
  1. Open `http://127.0.0.1:13000/en-EN/miniapp/home`.
  2. Use the Mini App home VPN/config quick action that links to `href="/miniapp/vpn"`.
  3. Open `http://127.0.0.1:13000/en-EN/miniapp/vpn`.
- Expected result: the implemented dedicated VPN access surface renders, or shows a clear no-subscription/no-config empty state.
- Actual result: the route returns `404 Page Not Found | CyberVPN`.
- Evidence:
  - `evidence/client/cyba-572/network/frontend-route-survey-20260606T072248Z.json`
  - `evidence/client/cyba-572/screenshots/compact-miniapp-home-no-telegram-mobile-20260606T071705Z.png`
  - Source reference: `frontend/src/app/[locale]/miniapp/home/page.tsx` links to `/miniapp/vpn`; `frontend/src/app/[locale]/miniapp/vpn/page.tsx` implements the page.
- Context7 docs checked: N/A - manual UI/business-flow finding.

### Product Gaps / Not Tested After CYBA-572

- Current synthetic customer entitlement status is `none`, so active/trial/expired subscription lifecycle UI was not covered.
- Wallet/payment history APIs are reachable but only empty states were available.
- Referral status is reachable but disabled; accepted/rejected promo/referral/partner-code outcomes were not available.
- `/api/v1/miniapp/config` still returns `404 Subscription config not found`; subscription-backed VPN config was not inspected.
- Service-state returns `200` but no `service_identity`, `device_credential`, or `access_delivery_channel` is present with the current empty entitlement state.
- Signed Telegram Mini App entry remains untested without approved sanitized `initData`.
- Payment capture/checkout commit was not attempted.

Context7 docs checked: N/A - manual UI/business-flow findings and safe-fixture coverage report. No code/config/dependency changes were made.

## CYBA-595 Final Auth UX QA / Scribe Evidence

Issue: [CYBA-595](/CYBA/issues/CYBA-595)
Timestamp: `2026-06-06T18:09:19Z`

### Summary

- PASS: final auth UX QA evidence pack is present under `evidence/client/cyba-595/`.
- PASS: successful password login no longer waits on delayed `/auth/session` before routing. Runtime smoke on current checkout `9001` measured `660ms` from accepted `/api/v1/auth/login` to `/en-EN/dashboard` with `/auth/session` delayed `2500ms`.
- PASS: invalid credentials, 2FA-only routing, deferred AuthGuard session validation, and related auth contracts are covered by targeted tests: `3 files`, `99 tests`.
- PASS: auth 3D scene remains active while login/register inputs are hover+focused at `390x844`, `768x1024`, and `1440x900`; [CYBA-593](/CYBA/issues/CYBA-593) summary is mirrored into this pack.
- PASS: passkey/OAuth layout has visible separation at `390x844`, `768x1024`, and `1440x900`; provider order remains `google`, `github`, `telegram`; [CYBA-594](/CYBA/issues/CYBA-594) summary is mirrored into this pack.
- PASS: no-secret scan over `evidence/client/cyba-595` text artifacts returned `No sensitive value hits.`
- PASS: SecurityEngineer signoff for auth redirect/session behavior completed in [CYBA-596](/CYBA/issues/CYBA-596).

### Evidence

- `evidence/client/cyba-595/manifest.md`
- `evidence/client/cyba-595/network/login-passkey-smoke-9001-20260606T1812Z.json`
- `evidence/client/cyba-595/network/targeted-auth-tests-20260606T1831Z.log`
- `evidence/client/cyba-595/network/targeted-layout-3d-tests-20260606T1814Z.log`
- `evidence/client/cyba-595/network/auth-3d-freeze-summary-from-cyba-593.json`
- `evidence/client/cyba-595/network/passkey-oauth-spacing-summary-from-cyba-594.json`
- `evidence/client/cyba-595/network/no-secret-scan-20260606T1815Z.txt`
- `evidence/client/cyba-595/screenshots/*.png`

### Environment Notes

- `http://127.0.0.1:13000` was reachable but failed the scoped passkey CTA smoke before auth submit with `Passkey CTA did not render`. This was treated as stale/not-suitable preview evidence and not filed as a product bug because the current checkout dev server passed the same smoke.
- Current checkout dev server `http://127.0.0.1:9001` was used for final runtime proof with backend target `http://127.0.0.1:18080`.
- No production testing, real customer/payment data, JWT/cookies/refresh tokens, passwords, VPN config secrets, or Telegram `initData` were stored.

### Scribe Summary

Final QA/Scribe disposition for [CYBA-595](/CYBA/issues/CYBA-595): auth UX fixes are verified at the frontend/runtime evidence level, with a clear PASS for post-login routing latency, passkey conditional identifier handling, 3D focus motion, passkey/OAuth spacing, targeted regression tests, no-secret scan, and SecurityEngineer signoff in [CYBA-596](/CYBA/issues/CYBA-596). No follow-up remains on this issue.

### Security Signoff

- [CYBA-596](/CYBA/issues/CYBA-596) completed at `2026-06-06T18:17:43Z`.
- Signoff: `Approved: auth redirect/session behavior acceptable for this scope.`
- SecurityEngineer confirmed the scoped fast-login path does not set authenticated user state before `AuthGuard` session validation, keeps `requires_2fa=true` isolated, uses `identifier: null` for conditional passkey, keeps redirects relative/sanitized, and does not persist frontend tokens.
- Residual risk remains scoped to untested real production/staging credentials, real passkey ceremony, OAuth provider round-trip, payment, VPN delivery, and Telegram signed `initData`.

## CYBA-608 Customer Device Browser QA

Issue: [CYBA-608](/CYBA/issues/CYBA-608)
Timestamp: `2026-06-09T18:58:50Z`

### Summary

- PASS: customer settings device panel consumes backend `total_devices/device_limit/remaining_devices` counters correctly for the synthetic post-dedup state.
- PASS: one current browser/device row shows exactly one `Current` badge and `1 of 3` / remaining `2` after the repeated same-browser-login fixture.
- PASS: `Revoke others` uses exactly one `POST /api/v1/auth/devices/logout-others`; no duplicate `DELETE /api/v1/auth/devices/{device_id}` calls were made.
- PASS: after `Revoke others`, the panel refetched and settled back to one current device with `1 of 3`.
- PASS: ru-RU mobile smoke rendered the device panel and `3 из 3` backend counter without page errors.
- No new bugs were found in this scoped customer frontend device browser QA.

### Environment

- Frontend: local checkout dev server `http://127.0.0.1:9001`.
- Browser: Chrome for Testing through global Playwright.
- Viewports: desktop `1440x1000`, mobile `390x844`.
- Locales: `en-EN`, `ru-RU`.
- User role/state: synthetic `DEV_BYPASS_AUTH=true` customer `user`.
- Safe handling: no production data, real cookies, JWTs, refresh tokens, passwords, payment secrets, VPN config secrets, or Telegram `initData` were stored.
- Context7 docs checked: MCP quota exceeded; fallback `ctx7` CLI checked `/microsoft/playwright` for `page.route`, `route.fulfill`, and `page.screenshot`.

### Evidence

- `evidence/client/cyba-608/network/settings-device-browser-qa-summary.json`
- `evidence/client/cyba-608/network/no-secret-scan.txt`
- `evidence/client/cyba-608/screenshots/settings-devices-deduped-en-desktop.png`
- `evidence/client/cyba-608/screenshots/settings-devices-before-logout-others-en-desktop.png`
- `evidence/client/cyba-608/screenshots/settings-devices-after-logout-others-en-desktop.png`
- `evidence/client/cyba-608/screenshots/settings-devices-ru-mobile.png`
- `evidence/client/cyba-608/device-browser-qa-runner.mjs`

### Bugs

- None filed from [CYBA-608](/CYBA/issues/CYBA-608).

### Product Gaps / Not Tested

- Real backend repeated-login creation was not executed with live credentials in this frontend manual QA; the UI was verified against synthetic post-dedup backend contract responses.
- Signed Telegram Mini App device entry was not tested because no approved sanitized `initData` was available in this heartbeat.

Context7 docs checked: MCP Context7 quota exceeded; fallback `ctx7` CLI checked `/microsoft/playwright` for `page.route`, `route.fulfill`, and `page.screenshot`. Product result is a manual UI/business-flow finding.
