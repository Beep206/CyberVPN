# CYBA-457 raw notes - partner portal

Дата: `2026-06-04`

Агент: `qa-partner-portal-manual`

## Контекст heartbeat

- Issue: `CYBA-457 Manual QA: partner portal flows`
- Operator handoff: `PARTIAL-GO local-stage QA`
- Approved local-stage endpoints:
  - client frontend: `http://127.0.0.1:13000`
  - admin frontend: `http://127.0.0.1:13001`
  - backend health: `http://127.0.0.1:18080/health`
- Partner stage container отсутствует; partner QA разрешена только как source/local-dev, если безопасный local preview можно поднять без production data.
- Authenticated/RBAC/payment/VPN/OAuth/email/Telegram flows remain `blocked/not-tested` без синтетических local fixtures/credentials.
- QA Lead comment at `2026-06-04T15:52:43Z` restored the task to readiness `NO-GO`: this packet is diagnostic source/local-dev evidence only, not a full manual QA start and not an unblock of `CYBA-452`.

## Environment

- Repo path: `VPNBussiness-main`
- Partner app: `partner/`
- Dev server command used:
  - first run inherited `NODE_ENV=production` from heartbeat env, marked superseded.
  - accepted rerun used `NODE_ENV=development NEXT_TELEMETRY_DISABLED=1 HOST=127.0.0.1 PORT=3002 NEXT_PUBLIC_SITE_URL=http://127.0.0.1:3002 npm run dev -w partner`
- Partner local URL: `http://127.0.0.1:3002`
- Browser: Playwright Chromium headless
- Sensitive artifacts: no cookies, storageState, HAR, trace, JWT, refresh tokens, payment data, production PII, or Telegram initData saved.

## Checks executed

1. Verified approved local-stage endpoints:
   - `GET http://127.0.0.1:13000/en-EN/login` -> `200`
   - `GET http://127.0.0.1:13001/en-EN/login` -> `200`
   - `GET http://127.0.0.1:18080/health` -> `200`
2. Direct backend unauthenticated partner probes:
   - `GET /api/v1/partner-session/bootstrap` on `18080` -> `401`
   - `GET /api/v1/partner-workspaces/me` on `18080` -> `401`
   - `GET /api/v1/partner-notifications` on `18080` -> `401`
   - Interpretation: backend requires session as expected; no authenticated fixture was available.
3. Partner local public auth pages:
   - `GET /en-EN/login` -> rendered `Sign In`
   - `GET /ru-RU/login` mobile -> rendered `Вход`
4. Partner protected routes with `NODE_ENV=development`:
   - `/en-EN/dashboard` anonymous -> `SYSTEM FAILURE`
   - `/en-EN/codes` with `DEV_BYPASS_AUTH=true` and synthetic active local state -> `SYSTEM FAILURE`
   - `/en-EN/finance` with `DEV_BYPASS_AUTH=true` and synthetic active local state -> `SYSTEM FAILURE`
   - `/en-EN/team` with synthetic analyst local state -> `SYSTEM FAILURE`

## Key observations

- `partner/next.config.ts` rewrites `/api/v1/:path*` to `http://localhost:8000/api/v1/:path*`.
- The approved local-stage backend for this heartbeat is `http://127.0.0.1:18080`; no service was listening on `localhost:8000`.
- Through the partner dev origin, `GET /api/v1/partner-session/bootstrap`, `GET /api/v1/partner-workspaces/me`, and `GET /api/v1/partner-notifications` returned `500`.
- The page-level error shown in screenshots is `No QueryClient set, use QueryClientProvider to set one`, surfaced as `SYSTEM FAILURE`.
- Because protected partner routes crash before rendering, partner access states, codes, markup, earnings, balances, withdrawals, client attribution, and cross-surface consistency could not be tested end-to-end in this heartbeat.

## Accepted evidence

- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-CAPTURE-RERUN-DEVENV__partner-portal__manual-qa__20260604T160419Z.json`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RERUN-AUTH-001__partner-portal__anonymous__en-EN__desktop-1440__pass__20260604T160359Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RERUN-AUTH-002__partner-portal__anonymous__en-EN__desktop-1440__fail__20260604T160406Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RERUN-CODES-001__partner-portal__dev-bypass-owner-active__en-EN__desktop-1440__fail__20260604T160410Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RERUN-FIN-001__partner-portal__dev-bypass-owner-active__en-EN__desktop-1440__fail__20260604T160415Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RERUN-ROLE-001__partner-portal__dev-bypass-analyst-active__en-EN__desktop-1440__fail__20260604T160419Z.png`

## Superseded evidence

The earlier `MF-PART-CAPTURE-RESULTS__partner-portal__manual-qa__20260604T155953Z.json` run is not used for findings because it inherited `NODE_ENV=production` from the heartbeat environment while running `next dev`. It is retained only as diagnostic context and is superseded by the `RERUN-DEVENV` evidence.

## Blocked / not tested

- Real partner login/session: blocked by missing synthetic partner credentials/session fixture.
- Partner access states backed by canonical API: blocked by missing partner stage container and local browser API rewrite mismatch.
- Partner codes and markup boundaries backed by real API: blocked.
- Client list and partner attribution consistency against admin/client surfaces: blocked.
- Earnings, balances, payouts, withdrawals, payout approval: blocked; no payment/payout mutations attempted.
- OAuth/email/Telegram/initData flows: blocked by explicit safety constraints and missing test fixtures.

## Resume heartbeat retest after CYBA-464

Wake reason: `issue_children_completed`; [CYBA-464](/CYBA/issues/CYBA-464) was `done`, [CYBA-452](/CYBA/issues/CYBA-452) was `done` with `GO - local-stage synthetic QA`.

Updated safe inputs:

- Partner local-dev/source-level QA remains required; no deployed partner stage container.
- Protected synthetic credentials exist outside git at `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`.
- Only key names were printed during discovery; credential values were not logged or copied into evidence.
- Partner portal host must be a portal host (`portal.localhost:*`), not raw `127.0.0.1`, because raw loopback is treated as storefront and redirects workspace routes to storefront root.

Runtime notes:

- Paperclip `currentExecutionWorkspace.runtimeServices` was empty, so no managed partner runtime URL was available.
- Existing partner process on `127.0.0.1:13012` was `NODE_ENV=production` and storefront-hosted, not suitable for `DEV_BYPASS_AUTH`.
- Existing `127.0.0.1:3002` was occupied by frontend, not partner.
- Temporary partner dev preview used:
  - `NODE_ENV=development NEXT_TELEMETRY_DISABLED=1 HOST=127.0.0.1 PORT=3004 NEXT_DIST_DIR=/tmp/cyba457-partner-next-3004 NEXT_PUBLIC_SITE_URL=http://portal.localhost:3004 NEXT_PUBLIC_PARTNER_PORTAL_SIMULATION_ENABLED=true PARTNER_API_URL=http://127.0.0.1:18080 API_URL=http://127.0.0.1:18080 NEXT_PUBLIC_API_URL=http://127.0.0.1:18080 node node_modules/next/dist/bin/next dev -p 3004 -H 127.0.0.1`
- Temporary server was stopped before heartbeat end.
- Next added `/tmp/cyba457-partner-next-3004/**` entries to `partner/tsconfig.json`; these were removed after the run.

Retest checks:

1. `MF-PART-PORTAL-CAPTURE__partner-portal__manual-qa__20260604T164039Z.json`
   - `9/9` passed on `http://portal.localhost:3004`.
   - Public EN login and mobile RU login rendered.
   - Anonymous `/en-EN/dashboard` redirected to login without `SYSTEM FAILURE`.
   - Simulated `DEV_BYPASS_AUTH=true` owner active `/dashboard`, `/codes`, `/finance`, `/conversions` rendered without `SYSTEM FAILURE`.
   - Simulated analyst `/team` and restricted owner `/finance` rendered without `SYSTEM FAILURE`.
   - Result: `MF-PART-001` retested fixed for route crash.
2. `MF-PART-AUTHED-CAPTURE__partner-portal__manual-qa__20260604T164525Z.json`
   - UI login automation stayed on login and protected pages redirected back to login.
   - Backend direct probe showed synthetic partner owner credentials are valid and require 2FA.
3. `MF-PART-AUTHED-API-CAPTURE__partner-portal__manual-qa__20260604T164832Z.json`
   - Same-origin `POST /api/v1/auth/login` -> `200`, `requires_2fa=true`.
   - `POST /api/auth/2fa/pending` -> `204`.
   - `POST /api/auth/2fa/complete` -> `200`, `redirect_to=/en-EN/dashboard`.
   - Subsequent protected routes redirected to `/en-EN/login?redirect=...`.
   - `GET /api/v1/auth/session` stayed `401`.
4. Sanitized cookie probe:
   - after pending: only `pending_2fa` existed for `portal.localhost`, `HttpOnly`, `SameSite=Lax`.
   - after complete: no cookies remained in browser context.
   - no cookie values were printed or stored.

New finding:

- `MF-PART-002` P1: partner 2FA complete succeeds but does not leave a usable session. This blocks canonical authenticated dashboard, codes, finance, conversions, clients/attribution and payout/read-only settlement checks.

Updated accepted evidence:

- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-PORTAL-CAPTURE__partner-portal__manual-qa__20260604T164039Z.json`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-AUTHED-API-CAPTURE__partner-portal__manual-qa__20260604T164832Z.json`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/bug-packets/MF-PART-002.md`

Updated blocked / not tested:

- Canonical authenticated partner dashboard/workspace data: blocked by `MF-PART-002`.
- Canonical partner codes and markup boundaries: blocked by `MF-PART-002`.
- Canonical client list and attribution consistency: blocked by `MF-PART-002`.
- Canonical earnings, balances, withdrawals and payout approval/rejection: blocked by `MF-PART-002`; no payment/payout mutations attempted.
- Suspended/disabled workspace state: no listed fixture.
- OAuth, email, Telegram, real payment capture/refund/payout, production Remnawave/provisioning: explicitly blocked/not-tested by [CYBA-452](/CYBA/issues/CYBA-452) safety decisions.

## Resume heartbeat retest after CYBA-483

Wake reason: `issue_children_completed`; [CYBA-483](/CYBA/issues/CYBA-483) was marked `done` and [CYBA-457](/CYBA/issues/CYBA-457) resumed for partner QA.

Retest environment:

- Partner local-dev preview: `http://portal.localhost:3004`
- Backend local-stage API: `http://127.0.0.1:18080`
- Account: protected synthetic `CYBA451_PARTNER_OWNER` fixture from `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`
- Browser: Playwright Chromium headless
- Secret handling: credential, token, cookie, TOTP secret, and TOTP code values were not stored.
- Temporary partner dev server was stopped after the run; port `3004` was confirmed closed.
- `partner/tsconfig.json` had no retained `/tmp/cyba457...` Next side-effect diff after shutdown.

Retest result:

1. `MF-PART-RETEST-AUTHED-CAPTURE__partner-portal__manual-qa__20260604T171101Z.json`
   - UI login + 2FA smoke ended at `/en-EN/login?redirect=%2Fen-EN%2Fdashboard`.
   - UI session status remained `401`.
   - Same-origin API auth probe:
     - `POST /api/v1/auth/login` -> `200`, `requires2fa=true`
     - `POST /api/auth/2fa/pending` -> `204`
     - `POST /api/auth/2fa/complete` -> `200`, `redirectTo=/en-EN/dashboard`
     - `GET /api/v1/auth/session` -> `401`
   - Cookie probe after pending: only `pending_2fa` existed for `portal.localhost`, `HttpOnly`, `SameSite=Lax`.
   - Cookie probe after complete: `[]`; no usable session cookie remained.
2. Protected owner routes after the 2FA complete step:
   - `/en-EN/dashboard` -> `/en-EN/login?redirect=%2Fen-EN%2Fdashboard`
   - `/en-EN/codes` -> `/en-EN/login?redirect=%2Fen-EN%2Fcodes`
   - `/en-EN/finance` -> `/en-EN/login?redirect=%2Fen-EN%2Ffinance`
   - `/en-EN/conversions` -> `/en-EN/login?redirect=%2Fen-EN%2Fconversions`
   - `/en-EN/team` -> `/en-EN/login?redirect=%2Fen-EN%2Fteam`
   - Network notes include repeated `401` for `/api/v1/auth/session` and `/api/v1/auth/refresh`.
   - No `SYSTEM FAILURE` was observed.

Latest finding status:

- `MF-PART-002` remains reproducible after [CYBA-483](/CYBA/issues/CYBA-483) was marked `done`.
- Canonical authenticated partner dashboard, partner codes, finance, conversions/attribution, team/access, earnings/balances/withdrawals, and cross-surface attribution checks remain blocked/not-tested until the partner portal keeps a usable session after 2FA.

Latest accepted evidence:

- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RETEST-AUTHED-CAPTURE__partner-portal__manual-qa__20260604T171101Z.json`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RETEST-UI-LOGIN-001__partner-portal__synthetic-owner-ui-login__en-EN__desktop-1440__fail__20260604T171101Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RETEST-OWNER-DASH-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T171101Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RETEST-OWNER-CODES-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T171101Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RETEST-OWNER-FIN-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T171101Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RETEST-OWNER-CONV-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T171101Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-RETEST-OWNER-TEAM-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T171101Z.png`

## Resume heartbeat retest after CYBA-495

Wake reason: `issue_children_completed`; [CYBA-495](/CYBA/issues/CYBA-495) was marked `done` and [CYBA-457](/CYBA/issues/CYBA-457) resumed for manual QA.

Runtime notes:

- Paperclip `currentExecutionWorkspace` was `null`; no managed runtime service URL was available.
- Existing partner preview was already running on `127.0.0.1:3004` from `partner/` with `NODE_ENV=development`, `API_URL=http://127.0.0.1:18080`, `NEXT_PUBLIC_API_URL=http://127.0.0.1:18080`.
- This heartbeat did not start that server and did not stop it.
- Backend health `GET http://127.0.0.1:18080/health` -> `200`.
- Protected synthetic credentials were read from `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`; secret values were not printed or stored.

Retest result:

1. `MF-PART-FINAL-UI-LOGIN-RETRY-CAPTURE__partner-portal__manual-qa__20260604T204530Z.json`
   - UI login form filled after hydration wait.
   - UI reached `2fa=true`, submitted synthetic TOTP, landed on `/en-EN/dashboard`.
   - `GET /api/v1/auth/session` -> `200`.
   - No `SYSTEM FAILURE`.
   - Result: `MF-PART-002` retested fixed after [CYBA-495](/CYBA/issues/CYBA-495).
2. `MF-PART-FINAL-AUTHED-CAPTURE__partner-portal__manual-qa__20260604T204240Z.json`
   - Same-origin `POST /api/v1/auth/login` -> `200`, `requires2fa=true`.
   - `POST /api/auth/2fa/pending` -> `204`.
   - `POST /api/auth/2fa/complete` -> `200`, `redirectTo=/en-EN/dashboard`.
   - `GET /api/v1/auth/session` -> `200`.
   - Session identity metadata: `auth_realm_key=partner`, `audience=cybervpn:partner`, `principal_type=partner_operator`.
   - Protected owner routes `/dashboard`, `/codes`, `/finance`, `/conversions`, `/team`, `/settings`, `/analytics`, `/programs` rendered without login redirect or `SYSTEM FAILURE`.
3. New blocker found:
   - Authenticated routes repeatedly called canonical partner endpoints that returned `404`:
     - `/api/v1/partner-workspaces/me`
     - `/api/v1/partner-session/bootstrap`
     - `/api/v1/partner-notifications/preferences`
   - Repo contract/source contains these endpoints in `partner/src/lib/api/partner-portal.ts`, `partner/src/lib/api/generated/types.ts`, and `backend/src/presentation/api/v1/partners/routes.py`.
   - Because bootstrap/workspace APIs are `404`, canonical partner access states, workspace data, codes/markup, finance, conversions/attribution, team/access, and client/cross-surface checks cannot be verified end-to-end against backend data even though the route shell renders.

New finding:

- `MF-PART-003` P1: authenticated partner shell renders, but canonical partner workspace/bootstrap APIs return `404` in local-stage.

Latest accepted evidence:

- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-AUTHED-CAPTURE__partner-portal__manual-qa__20260604T204240Z.json`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-UI-LOGIN-RETRY-CAPTURE__partner-portal__manual-qa__20260604T204530Z.json`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-UI-LOGIN-RETRY-001__partner-portal__synthetic-owner-ui-login__en-EN__desktop-1440__pass__20260604T204530Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-OWNER-DASH-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__pass__20260604T204240Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-OWNER-CODES-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__pass__20260604T204240Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-OWNER-FIN-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__pass__20260604T204240Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-OWNER-CONV-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__pass__20260604T204240Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-FINAL-OWNER-TEAM-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__pass__20260604T204240Z.png`

Updated blocked / not tested:

- Canonical partner business data end-to-end: blocked by `MF-PART-003`.
- Partner access states backed by `/partner-session/bootstrap`: blocked by `MF-PART-003`.
- Workspace-backed codes, markup boundaries, finance, conversions/attribution, team/access, clients/cross-surface attribution: blocked by `MF-PART-003`.
- Withdrawals/payout mutations/payment capture/refund/provisioning/OAuth/email/Telegram/production data: not attempted by safety constraints.

## Resume heartbeat retest after CYBA-525

Wake reason: `issue_children_completed`; [CYBA-525](/CYBA/issues/CYBA-525) was reported complete in the wake summary, while live Paperclip API still showed [CYBA-525](/CYBA/issues/CYBA-525) as `in_progress`. I ran read-only retest against the live local-stage backend and partner preview to leave durable QA evidence.

Runtime notes:

- Paperclip `currentExecutionWorkspace` was `null`; no managed runtime service URL was available.
- Existing partner preview was already running on `127.0.0.1:3004` from `partner/` with `NODE_ENV=development`, `API_URL=http://127.0.0.1:18080`, `NEXT_PUBLIC_API_URL=http://127.0.0.1:18080`.
- This heartbeat did not start that server and did not stop it.
- Backend health `GET http://127.0.0.1:18080/health` -> `200`.
- Protected synthetic credentials were read from `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`; secret values were not printed or stored.

Retest result:

1. `MF-PART-POST525-API-PROBE__partner-portal__manual-qa__20260604T213206Z.json`
   - Auth flow still passes: `loginStatus=200`, `pendingStatus=204`, `completeStatus=200`, `sessionStatus=200`.
   - Base canonical endpoints pass with `X-Auth-Realm: partner`:
     - `/api/v1/partner-workspaces/me` -> `200`
     - `/api/v1/partner-session/bootstrap` -> `200`
     - `/api/v1/partner-notifications/preferences` -> `200`
     - `/api/v1/partner-notifications/counters` -> `200`
   - Result: `MF-PART-003` retested fixed for the original workspace/bootstrap/notification `404` blocker.
2. `MF-PART-POST525-AUTHED-CAPTURE__partner-portal__manual-qa__20260604T213002Z.json`
   - UI route network now shows `200` for `/partner-workspaces/me`, `/partner-session/bootstrap`, workspace `codes`, `statements`, `payout-accounts`, `payout-history`, `conversion-records`, `analytics-metrics`, `members`, `roles`, `settings`, `programs/lane-applications`, `report-exports`, `review-requests`, `traffic-declarations`, `integration-credentials`, `integration-delivery-logs`, `cases`, and partner notifications.
   - Remaining route errors are workspace-scoped:
     - `/api/v1/partner-workspaces/:workspace_id/reseller-voucher-batches` -> `404`, repeated on owner pages.
     - `/api/v1/partner-workspaces/:workspace_id/security/passkeys/policy` -> `500`, observed on settings.
     - `/api/v1/partner-workspaces/:workspace_id/security/passkeys/compliance` -> `500`, observed on settings.
   - The capture JSON was redacted so workspace UUIDs are stored as `:workspace_id`.
3. New finding:
   - `MF-PART-004` P1: authenticated partner flows still emit backend route failures on reseller voucher batches and partner passkey policy/compliance.

Latest accepted evidence:

- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST525-AUTHED-CAPTURE__partner-portal__manual-qa__20260604T213002Z.json`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST525-API-PROBE__partner-portal__manual-qa__20260604T213206Z.json`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST525-OWNER-DASH-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T213002Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST525-OWNER-FIN-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T213002Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST525-OWNER-SETTINGS-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T213002Z.png`

Updated blocked / not tested:

- Authenticated partner workspace/bootstrap, codes, finance, conversions, team/access, notifications, and core reporting endpoints are no longer blocked by `MF-PART-003`.
- Reseller voucher batch coverage is blocked by `MF-PART-004`.
- Settings/security passkey policy and compliance coverage are blocked by `MF-PART-004`.
- Full done status remains blocked until workspace-scoped backend errors are resolved or explicitly approved as not in scope for this manual audit.
- Withdrawals/payout mutations/payment capture/refund/provisioning/OAuth/email/Telegram/production data: not attempted by safety constraints.

## Context7/docs evidence

Context7 docs checked: unavailable - quota exceeded. Fallback official docs checked: Playwright navigation/screenshots/network events, TanStack Query provider/devtools docs, and browser cookie/session behavior references.

## CYBA-510 retest after CYBA-509

Wake reason: `issue_blockers_resolved`; [CYBA-509](/CYBA/issues/CYBA-509) was `done`, so [CYBA-510](/CYBA/issues/CYBA-510) retested the partner 2FA session cookie path after the backend cookie `Secure`/request fix.

Retest environment:

- Partner local-dev preview: `http://portal.localhost:3004`
- Backend local-stage API: `http://127.0.0.1:18080`
- Browser: Playwright Chromium headless, desktop `1440x1000`, locale `en-EN`
- Account: protected synthetic `CYBA451_PARTNER_OWNER` fixture from `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`
- Host handling: Chromium `--host-resolver-rules=MAP portal.localhost 127.0.0.1`, because this runner resolves `portal.localhost` to `::1` while `next dev -H 127.0.0.1` listens on IPv4.
- Dev server note: `npm run dev -w partner` was not usable in this dirty workspace because `prepare:workspace`/`npm ci` reported `partner/package.json` and `partner/package-lock.json` out of sync for `@simplewebauthn/browser`. For parity with prior accepted evidence, the retest used direct `node node_modules/next/dist/bin/next dev -p 3004 -H 127.0.0.1` with `NEXT_DIST_DIR=/tmp/cyba510-partner-next-3004` and local-stage API env.
- Cleanup: temporary `next dev` process was stopped; port `3004` was confirmed closed. Next.js temporary `/tmp/cyba510-partner-next-3004/**` `tsconfig.json` include side-effect was removed.
- Secret handling: credential, token, cookie value, TOTP secret, TOTP code, storageState, HAR, trace, payment secrets, production PII, and Telegram initData were not stored.

Retest result: `FAIL`; `MF-PART-002` remains reproducible after [CYBA-509](/CYBA/issues/CYBA-509).

Same-origin API auth probe:

- `POST /api/v1/auth/login` -> `200`, `requires_2fa=true`
- `POST /api/auth/2fa/pending` -> `204`
- Cookie probe after pending: `NEXT_LOCALE` plus `pending_2fa` for `portal.localhost`, `pending_2fa` is `HttpOnly`, `SameSite=Lax`, `secure=false`
- `POST /api/auth/2fa/complete` -> `200`, `redirect_to=/en-EN/dashboard`
- Cookie probe after complete: only `NEXT_LOCALE`; no realm session cookie names remained
- `GET /api/v1/auth/session` -> `401`

Protected owner routes after the 2FA complete step:

- `/en-EN/dashboard` -> `/en-EN/login?redirect=%2Fen-EN%2Fdashboard`
- `/en-EN/codes` -> `/en-EN/login?redirect=%2Fen-EN%2Fcodes`
- `/en-EN/finance` -> `/en-EN/login?redirect=%2Fen-EN%2Ffinance`
- `/en-EN/conversions` -> `/en-EN/login?redirect=%2Fen-EN%2Fconversions`
- `/en-EN/team` -> `/en-EN/login?redirect=%2Fen-EN%2Fteam`
- No `SYSTEM FAILURE` was observed.

Latest accepted evidence:

- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST509-AUTHED-CAPTURE__partner-portal__manual-qa__20260604T183538Z.json`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST509-OWNER-DASH-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T183538Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST509-OWNER-CODES-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T183538Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST509-OWNER-FIN-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T183538Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST509-OWNER-CONV-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T183538Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST509-OWNER-TEAM-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T183538Z.png`

Current blocked/not-tested:

- Canonical authenticated partner dashboard/workspace data remains blocked by `MF-PART-002`.
- Canonical partner codes, markup boundaries, finance, conversions/attribution, team/access, earnings, balances, withdrawals, and cross-surface attribution checks remain blocked by `MF-PART-002`; no payment/payout mutations attempted.

Context7 docs checked: N/A - manual UI/business-flow finding; reused existing Playwright QA tooling and sanitized browser cookie probe.

## CYBA-520 retest after CYBA-519

Wake reason: `issue_blockers_resolved`; [CYBA-519](/CYBA/issues/CYBA-519) was `done`, so [CYBA-520](/CYBA/issues/CYBA-520) retested the partner 2FA session path after Security review of frontend `Set-Cookie Domain` normalization.

Retest environment:

- Partner local-dev preview: `http://portal.localhost:3004`
- Backend local-stage API: `http://127.0.0.1:18080`
- Existing preview process: `next-server (v16.2.4)` listening on `127.0.0.1:3004`, `NODE_ENV=development`, `API_URL=http://127.0.0.1:18080`, `NEXT_PUBLIC_API_URL=http://127.0.0.1:18080`
- Browser: Playwright Chromium headless, desktop `1440x1000`, locale `en-EN`
- Account: protected synthetic `CYBA451_PARTNER_OWNER` fixture from `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`
- Host handling: Chromium `--host-resolver-rules=MAP portal.localhost 127.0.0.1`
- Secret handling: credential, token, cookie value, TOTP secret, TOTP code, storageState, HAR, trace, payment secrets, production PII, and Telegram initData were not stored.

Retest result: `FAIL`; `MF-PART-002` remains unresolved after [CYBA-519](/CYBA/issues/CYBA-519), with an earlier first failing transition than the post-[CYBA-509](/CYBA/issues/CYBA-509) run.

Same-origin API auth probe:

- `POST /api/v1/auth/login` -> `200`, `requires_2fa=true`, `hasTfaToken=true`
- `POST /api/auth/2fa/pending` -> `204`
- Cookie probe after pending: only `pending_2fa` for `portal.localhost`, `HttpOnly`, `SameSite=Lax`, `secure=false`
- `POST /api/auth/2fa/complete` -> `401`, no `redirect_to`
- Cookie probe after complete: `[]`; no realm session cookie names remained
- `GET /api/v1/auth/session` -> `401`

Protected owner routes after the failed 2FA complete step:

- `/en-EN/dashboard` -> `/en-EN/login?redirect=%2Fen-EN%2Fdashboard`
- `/en-EN/codes` -> `/en-EN/login?redirect=%2Fen-EN%2Fcodes`
- `/en-EN/finance` -> `/en-EN/login?redirect=%2Fen-EN%2Ffinance`
- `/en-EN/conversions` -> `/en-EN/login?redirect=%2Fen-EN%2Fconversions`
- `/en-EN/team` -> `/en-EN/login?redirect=%2Fen-EN%2Fteam`
- Network notes include repeated `401` for `/api/v1/auth/session` and `/api/v1/auth/refresh`.
- No `SYSTEM FAILURE` was observed.

Latest accepted evidence:

- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-520__partner-2fa-session-retest__20260604T202139Z.json`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-520-screenshots/CYBA-520__partner-portal__synthetic-owner__en-EN__desktop-1440__dashboard-fail__20260604T202139Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-520-screenshots/CYBA-520__partner-portal__synthetic-owner__en-EN__desktop-1440__codes-fail__20260604T202139Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-520-screenshots/CYBA-520__partner-portal__synthetic-owner__en-EN__desktop-1440__finance-fail__20260604T202139Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-520-screenshots/CYBA-520__partner-portal__synthetic-owner__en-EN__desktop-1440__conversions-fail__20260604T202139Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-520-screenshots/CYBA-520__partner-portal__synthetic-owner__en-EN__desktop-1440__team-fail__20260604T202139Z.png`

Current blocked/not-tested:

- Canonical authenticated partner dashboard/workspace data remains blocked by `MF-PART-002`.
- Canonical partner codes, markup boundaries, finance, conversions/attribution, team/access, earnings, balances, withdrawals, and cross-surface attribution checks remain blocked by `MF-PART-002`; no payment/payout mutations attempted.

Context7 docs checked: unavailable - quota exceeded. Fallback official docs checked: Playwright `browser.newContext`, `context.cookies`, `page.goto`, `page.screenshot`, and `chromium.launch`.

## CYBA-523 ретест path-matched cookie после CYBA-522

Причина wake: `issue_blockers_resolved`; [CYBA-522](/CYBA/issues/CYBA-522) перешла в `done`, поэтому в [CYBA-523](/CYBA/issues/CYBA-523) повторно проверена partner 2FA authenticated session с исправленным путём cookie probe.

Окружение ретеста:

- Partner local-dev preview: `http://portal.localhost:3004`
- Backend local-stage API: `http://127.0.0.1:18080`
- Browser: Playwright Chromium headless, desktop `1440x1000`, locale `en-EN`
- Account: protected synthetic `CYBA451_PARTNER_OWNER` fixture from `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`
- Host handling: Chromium `--host-resolver-rules=MAP portal.localhost 127.0.0.1`
- Обращение с секретами: credential, token, cookie value, TOTP secret, TOTP code, storageState, HAR, trace, payment secrets, production PII и Telegram initData не сохранялись.

Результат ретеста: `PASS`; `MF-PART-002` остаётся исправленным при проверке через path-matched cookie probe.

Same-origin API auth probe:

- `POST /api/v1/auth/login` -> `200`, `requires_2fa=true`, `hasTfaToken=true`
- `POST /api/auth/2fa/pending` -> `204`
- Fresh TOTP был сгенерирован непосредственно перед `POST /api/auth/2fa/complete`
- `POST /api/auth/2fa/complete` -> `200`, `redirect_to=/en-EN/dashboard`
- Повтор после `401` не использовался.
- `GET /api/v1/auth/session` -> `200`, `auth_realm_key=partner`, `principal_type=partner_operator`, `scope_family=partner`

Cookie probe:

- Root-origin probe `context.cookies('http://portal.localhost:3004')` после 2FA complete -> `[]`
- Path-matched probe `context.cookies('http://portal.localhost:3004/api/v1/auth/session')` после 2FA complete -> `partner_access_token`, `partner_refresh_token`
- Обе session cookies записаны только как metadata: `domain=portal.localhost`, `path=/api`, `HttpOnly=true`, `SameSite=Lax`, `secure=false`; значения не сохранялись.

Protected owner routes после шага 2FA complete:

- `/en-EN/dashboard` -> `200`, без login redirect, без `SYSTEM FAILURE`
- `/en-EN/codes` -> `200`, без login redirect, без `SYSTEM FAILURE`
- `/en-EN/finance` -> `200`, без login redirect, без `SYSTEM FAILURE`
- `/en-EN/conversions` -> `200`, без login redirect, без `SYSTEM FAILURE`
- `/en-EN/team` -> `200`, без login redirect, без `SYSTEM FAILURE`

Новое принятое evidence:

- JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-523__partner-2fa-path-cookie-retest__20260604T210730Z.json`
- Runner: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba523-partner-2fa-path-cookie-retest.mjs`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-523-screenshots/CYBA-523__partner-portal__synthetic-owner__en-EN__desktop-1440__dashboard-pass__20260604T210730Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-523-screenshots/CYBA-523__partner-portal__synthetic-owner__en-EN__desktop-1440__codes-pass__20260604T210730Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-523-screenshots/CYBA-523__partner-portal__synthetic-owner__en-EN__desktop-1440__finance-pass__20260604T210730Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-523-screenshots/CYBA-523__partner-portal__synthetic-owner__en-EN__desktop-1440__conversions-pass__20260604T210730Z.png`
- Screenshot: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-523-screenshots/CYBA-523__partner-portal__synthetic-owner__en-EN__desktop-1440__team-pass__20260604T210730Z.png`

Blocked/not-tested после этого ретеста:

- Scope `CYBA-523` закрыт; по 2FA session blocker остатка нет.
- Canonical partner business data end-to-end не входила в этот ретест и по-прежнему отслеживается под `MF-PART-003`.
- Withdrawals/payout mutations/payment capture/refund/provisioning/OAuth/email/Telegram/production data не выполнялись из-за safety constraints.

Context7 MCP проверен: quota exceeded. ctx7 fallback проверен: `/microsoft/playwright` `BrowserContext.cookies(urls)` и `page.screenshot` path option.

## Resume heartbeat retest after CYBA-528

Wake reason: `issue_children_completed`; [CYBA-528](/CYBA/issues/CYBA-528) was marked `done`, so [CYBA-457](/CYBA/issues/CYBA-457) resumed for a post-fix partner portal retest.

Runtime notes:

- Paperclip `currentExecutionWorkspace` was `null`; no managed runtime service URL was available.
- Existing partner preview was already running on `127.0.0.1:3004` from `partner/` with `NODE_ENV=development`, `API_URL=http://127.0.0.1:18080`, `NEXT_PUBLIC_API_URL=http://127.0.0.1:18080`.
- This heartbeat did not start that server and did not stop it.
- Backend health `GET http://127.0.0.1:18080/health` -> `200`.
- Protected synthetic credentials were read from `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`; secret values were not printed or stored.

Retest result: `FAIL`; `MF-PART-004` remains reproducible after [CYBA-528](/CYBA/issues/CYBA-528).

1. `MF-PART-POST528-FINAL-CAPTURE__partner-portal__manual-qa__20260604T215018Z.json`
   - Auth flow passes: `loginStatus=200`, `pendingStatus=204`, `completeStatus=200`, `sessionStatus=200`.
   - Base canonical endpoints pass:
     - `/api/v1/partner-workspaces/me` -> `200`
     - `/api/v1/partner-session/bootstrap` -> `200`
     - `/api/v1/partner-notifications/preferences` -> `200`
     - `/api/v1/partner-notifications/counters` -> `200`
     - `/api/v1/partner-notifications` -> `200`
   - Workspace endpoint direct probes mostly pass, including `settings`, `members`, `roles`, `programs`, `lane-applications`, `codes`, `campaign-assets`, `statements`, `payout-accounts`, `payout-history`, `conversion-records`, `analytics-metrics`, `report-exports`, `review-requests`, `traffic-declarations`, `cases`, `integration-credentials`, `integration-delivery-logs`, and `postback-readiness`.
2. Remaining direct probe failures:
   - `GET /api/v1/partner-workspaces/:workspace_id/reseller-voucher-batches` -> `404`
   - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/policy` -> `500`
   - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/compliance` -> `500`
   - Observed contract/method gap: `GET /api/v1/partner-workspaces/:workspace_id/creative-approvals` -> `405`; route network did not show this as the primary blocker, but backend/frontend should confirm whether `GET` is expected or replace the probe/contract.
3. Route network failures:
   - `GET /api/v1/partner-workspaces/:workspace_id/reseller-voucher-batches` -> `404`, repeated on all 12 owner route checks.
   - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/policy` -> `500`, observed twice on `/en-EN/settings`.
   - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/compliance` -> `500`, observed twice on `/en-EN/settings`.
   - `GET /api/v1/partner-workspaces/:workspace_id/support/tickets?limit=50` -> `500`, observed on `/en-EN/cases`.
4. Route outcomes:
   - `/en-EN/dashboard`, `/codes`, `/finance`, `/conversions`, `/team`, `/settings`, `/analytics`, `/programs`, `/campaigns`, `/cases`, `/integrations`, `/reseller` all stayed authenticated and did not show `SYSTEM FAILURE`, but each was marked `fail` because blocking partner API failures remained.

Latest accepted evidence:

- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST528-FINAL-CAPTURE__partner-portal__manual-qa__20260604T215018Z.json`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST528-OWNER-DASH-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T215018Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST528-OWNER-SETTINGS-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T215018Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST528-OWNER-CASES-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T215018Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/MF-PART-POST528-OWNER-RESELLER-001__partner-portal__synthetic-owner-authenticated__en-EN__desktop-1440__fail__20260604T215018Z.png`

Sensitive-data review:

- PASS - no cookie values, storageState, HAR, trace, JWT, refresh tokens, passwords, TOTP secret, TOTP code, payment secrets, production PII, or Telegram initData saved.
- Redaction check for the latest JSON: UUID-like strings count `0`.
- Workspace ids are redacted as `:workspace_id` in JSON evidence.

Updated blocked / not tested:

- Full partner business-flow QA remains blocked by `MF-PART-004` / [CYBA-532](/CYBA/issues/CYBA-532) until reseller voucher batch, passkey policy/compliance, and support tickets workspace APIs stop returning backend errors or are replaced by an approved contract.
- Partner codes, finance, conversions/attribution, team/access, analytics, campaigns, integrations, and cases route shells are reachable, but final pass cannot be recorded while shared route bootstrap calls still emit blocking API failures.
- Withdrawals, payout approval/rejection, payment capture/refund, provisioning, OAuth, email, Telegram, and production-data mutations were not attempted by safety constraints.

Context7 docs checked: unavailable - quota exceeded. Fallback official docs checked: Playwright navigation/screenshots/network events and MDN Set-Cookie cookie attributes.

## CYBA-536 retest after CYBA-532 partner workspace API work

Wake reason: `issue_assigned`; [CYBA-536](/CYBA/issues/CYBA-536) requested a focused retest for [CYBA-532](/CYBA/issues/CYBA-532) / `MF-PART-004`.

Runtime notes:

- Paperclip `currentExecutionWorkspace` was `null`; no managed runtime service URL was available.
- Existing partner preview was reachable at `http://portal.localhost:3004/en-EN/login` -> `200`.
- Existing backend local-stage health was reachable at `GET http://127.0.0.1:18080/health` -> `200`.
- This heartbeat did not start or stop preview/backend services.
- Protected synthetic credentials were read from `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`; secret values were not printed or stored.
- Browser: Playwright Chromium headless, desktop `1440x1000`, locale `en-EN`, host mapping `MAP portal.localhost 127.0.0.1`.

Retest runner:

- Added `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba536-partner-workspace-api-retest.mjs`.
- Context7 MCP result: quota exceeded.
- `ctx7` CLI docs checked: `/microsoft/playwright` `BrowserContext.cookies(urls)`, `Page.goto`, `page.screenshot({ path, fullPage })`, and network response examples.
- Runner stores only cookie metadata, endpoint templates, sanitized payload summaries/errors, and screenshots; no HAR, trace, storageState, token values, cookie values, credentials, TOTP secret/code, payment secrets, production PII, or Telegram initData.

Retest result: `FAIL`; `MF-PART-004` remains reproducible after [CYBA-532](/CYBA/issues/CYBA-532) backend work.

1. Auth flow passes:
   - `POST /api/v1/auth/login` -> `200`, `requires2fa=true`
   - `POST /api/auth/2fa/pending` -> `204`
   - `POST /api/auth/2fa/complete` -> `200`
   - `GET /api/v1/auth/session` -> `200`, `authRealmKey=partner`, `principalType=partner_operator`
2. Base canonical endpoints pass:
   - `GET /api/v1/partner-workspaces/me` -> `200`
   - `GET /api/v1/partner-session/bootstrap` -> `200`
   - `GET /api/v1/partner-notifications/preferences` -> `200`
   - `GET /api/v1/partner-notifications/counters` -> `200`
   - `GET /api/v1/partner-notifications` -> `200`
3. Targeted direct probe failures:
   - `GET /api/v1/partner-workspaces/:workspace_id/reseller-voucher-batches` -> `404`, sanitized detail `Reseller voucher batches are not enabled for this workspace`; expected `200` list response, including allowed `[]`.
   - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/policy` -> `500`, sanitized detail `Internal server error`.
   - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/compliance` -> `500`, sanitized detail `Internal server error`.
   - `GET /api/v1/partner-workspaces/:workspace_id/support/tickets?limit=50` -> `500`, sanitized detail `Internal server error`; expected `200` with `{ tickets: [], nextCursor: null }` or synthetic tickets.
   - `GET /api/v1/partner-workspaces/:workspace_id/creative-approvals` -> `405`, sanitized detail `Method Not Allowed`; expected `200` list response per retest request.
4. Route network failures:
   - `GET /api/v1/partner-workspaces/:workspace_id/reseller-voucher-batches` -> `404` on `/en-EN/dashboard`, `/codes`, `/finance`, `/conversions`, `/team`, `/settings`, `/analytics`, `/programs`, `/campaigns`, `/cases`, `/integrations`, `/reseller`.
   - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/policy` -> `500`, observed on `/en-EN/settings`.
   - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/compliance` -> `500`, observed on `/en-EN/settings`.
   - `GET /api/v1/partner-workspaces/:workspace_id/support/tickets?limit=50` -> `500`, observed on `/en-EN/cases`.
5. Route outcomes:
   - `/en-EN/dashboard`, `/codes`, `/finance`, `/conversions`, `/team`, `/settings`, `/analytics`, `/programs`, `/campaigns`, `/cases`, `/integrations`, `/reseller` all returned document `200`, stayed authenticated, and did not show `SYSTEM FAILURE`, but each was marked `fail` because targeted partner workspace API failures remained.

Latest accepted evidence:

- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-536__partner-workspace-api-retest__20260604T222151Z.json`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba536-partner-workspace-api-retest.mjs`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/` (`13` PNGs: login plus 12 owner routes)
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/CYBA-536__partner-portal__synthetic-owner__en-EN__desktop-1440__dashboard-fail__20260604T222151Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/CYBA-536__partner-portal__synthetic-owner__en-EN__desktop-1440__settings-fail__20260604T222151Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/CYBA-536__partner-portal__synthetic-owner__en-EN__desktop-1440__cases-fail__20260604T222151Z.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/CYBA-536__partner-portal__synthetic-owner__en-EN__desktop-1440__reseller-fail__20260604T222151Z.png`

Sensitive-data review:

- PASS - no cookie values, storageState, HAR, trace, JWT, refresh tokens, passwords, TOTP secret, TOTP code, payment secrets, production PII, or Telegram initData saved.
- JSON redaction check: no JWT/Bearer/UUID strings found.
- Workspace ids are redacted as `:workspace_id` in JSON evidence; cookie names are recorded as metadata only.

Updated blocked / not tested:

- Full partner business-flow QA remains blocked by `MF-PART-004` / [CYBA-532](/CYBA/issues/CYBA-532) until reseller voucher batches, passkey policy/compliance, support tickets, and creative approvals return approved read-only/list contract responses for authenticated partner realm sessions.
- Partner codes, finance, conversions/attribution, team/access, analytics, campaigns, integrations, reseller, and cases route shells are reachable, but final pass cannot be recorded while targeted workspace API calls still emit blocking failures.
- Withdrawals, payout approval/rejection, payment capture/refund, provisioning, OAuth, email, Telegram, and production-data mutations were not attempted by safety constraints.

## CYBA-457 final retest after CYBA-532 done

Wake reason: `issue_children_completed`; [CYBA-532](/CYBA/issues/CYBA-532) was marked `done`, so [CYBA-457](/CYBA/issues/CYBA-457) resumed for final partner portal retest.

Runtime notes:

- Paperclip `currentExecutionWorkspace` was `null`; no managed runtime service URL was available.
- Existing partner preview was reachable at `http://portal.localhost:3004/en-EN/login` -> `200`.
- Existing backend local-stage health was reachable at `GET http://127.0.0.1:18080/health` -> `200`.
- This heartbeat did not start or stop preview/backend services.
- Protected synthetic credentials were read from `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`; secret values were not printed or stored.
- Browser: Playwright Chromium headless, desktop `1440x1000`, locale `en-EN`, host mapping `MAP portal.localhost 127.0.0.1`.

Retest runner:

- Reused `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba536-partner-workspace-api-retest.mjs` with fresh `CYBA457` timestamp.
- Runner stores only cookie metadata, endpoint templates, sanitized payload summaries/errors, and screenshots; no HAR, trace, storageState, token values, cookie values, credentials, TOTP secret/code, payment secrets, production PII, or Telegram initData.

Retest result: `PASS`; `MF-PART-004` no longer reproduces after [CYBA-532](/CYBA/issues/CYBA-532).

1. Auth flow passes:
   - `POST /api/v1/auth/login` -> `200`, `requires2fa=true`
   - `POST /api/auth/2fa/pending` -> `204`
   - `POST /api/auth/2fa/complete` -> `200`
   - `GET /api/v1/auth/session` -> `200`
   - No retry after `complete 401` was used.
2. Base canonical endpoints pass:
   - `GET /api/v1/partner-workspaces/me` -> `200`
   - `GET /api/v1/partner-session/bootstrap` -> `200`
   - `GET /api/v1/partner-notifications/preferences` -> `200`
   - `GET /api/v1/partner-notifications/counters` -> `200`
   - `GET /api/v1/partner-notifications` -> `200`
3. Targeted direct probes pass:
   - `GET /api/v1/partner-workspaces/:workspace_id/reseller-voucher-batches` -> `200`, array `count=0`
   - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/policy` -> `200`
   - `GET /api/v1/partner-workspaces/:workspace_id/security/passkeys/compliance` -> `200`
   - `GET /api/v1/partner-workspaces/:workspace_id/support/tickets?limit=50` -> `200`, `{ tickets: [], nextCursor: null }`
   - `GET /api/v1/partner-workspaces/:workspace_id/creative-approvals` -> `200`, array `count=0`
4. Route outcomes:
   - `/en-EN/dashboard`, `/codes`, `/finance`, `/conversions`, `/team`, `/settings`, `/analytics`, `/programs`, `/campaigns`, `/cases`, `/integrations`, `/reseller` all returned document `200`, stayed authenticated, avoided `SYSTEM FAILURE`, and had no targeted backend failures.

Latest accepted evidence:

- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-536__partner-workspace-api-retest__20260604T224847ZCYBA457.json`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/` (`13` PNGs ending `20260604T224847ZCYBA457.png`: login plus 12 owner routes)
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/CYBA-536__partner-portal__synthetic-owner__en-EN__desktop-1440__dashboard-pass__20260604T224847ZCYBA457.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/CYBA-536__partner-portal__synthetic-owner__en-EN__desktop-1440__settings-pass__20260604T224847ZCYBA457.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/CYBA-536__partner-portal__synthetic-owner__en-EN__desktop-1440__cases-pass__20260604T224847ZCYBA457.png`
- `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/cyba-536-screenshots/CYBA-536__partner-portal__synthetic-owner__en-EN__desktop-1440__reseller-pass__20260604T224847ZCYBA457.png`

Sensitive-data review:

- PASS - no cookie values, storageState, HAR, trace, JWT, refresh tokens, passwords, TOTP secret, TOTP code, payment secrets, production PII, or Telegram initData saved.
- Final JSON redaction check: JWT/Bearer/UUID-like strings count `0`.
- Workspace ids are redacted as `:workspace_id`; cookie names are recorded as metadata only.

Final blocked / not tested:

- No active P1 partner portal blocker remains after final post-[CYBA-532](/CYBA/issues/CYBA-532) retest.
- Read-only partner owner flows for auth/session, base endpoints, workspace APIs, codes, finance, conversions/attribution, team/access, analytics, campaigns, cases, integrations, reseller, settings/security, and notifications were covered through authenticated route/API retest.
- Withdrawals, payout approval/rejection, payment capture/refund, provisioning, OAuth, email, Telegram, production Remnawave/provisioning, and production-data mutations were not attempted by [CYBA-452](/CYBA/issues/CYBA-452) safety constraints.
- Suspended/disabled workspace state remains not-tested because no listed fixture was provided.

Context7 docs checked: N/A - manual API/business-flow contract finding. Runner docs: Context7 MCP quota exceeded; `ctx7` CLI checked `/microsoft/playwright` `BrowserContext.cookies(urls)`, `Page.goto`, `page.screenshot({ path, fullPage })`, and network response examples.
