# Security RBAC Regression Findings

Issue: [CYBA-575](/CYBA/issues/CYBA-575) for [CYBA-568](/CYBA/issues/CYBA-568)
Date: 2026-06-06 UTC
Reviewer: `qa-security-rbac-reviewer`

## Summary

- Scope tested: direct URL access, unauthenticated private-route shells, admin/partner/customer guard wiring, session/refresh/logout unit coverage, partner storefront vs portal routing, obvious token/initData leakage signals.
- P0/P1 findings: none observed. P2 finding SRBAC-002 fixed in [CYBA-627](/CYBA/issues/CYBA-627) and retested by QA in [CYBA-606](/CYBA/issues/CYBA-606): web `/auth/refresh` больше не возвращает JS-readable token body.
- [CYBA-579](/CYBA/issues/CYBA-579) completed; host-isolation runtime gap retested as fixed, including scoped HEAD-only QA verification in [CYBA-582](/CYBA/issues/CYBA-582).
- No production data, real credentials, JWT, cookies, refresh tokens, passwords, `.env` values, payment secrets, or real Telegram `initData` were stored.

## Обновление gate - [CYBA-606](/CYBA/issues/CYBA-606) (2026-06-09)

- Исторический triage из dependency-blocked heartbeat: тогда blocked deliverable QA не возобновлялась.
- Последний supervisor note: [comment 1de94eb3-8299-4d79-9338-56ad6eb1f2f8](/CYBA/issues/CYBA-606#comment-1de94eb3-8299-4d79-9338-56ad6eb1f2f8) сообщает, что [CYBA-614](/CYBA/issues/CYBA-614) добавил mobile auth scope в [CYBA-597](/CYBA/issues/CYBA-597).
- Обязательный blocker [CYBA-616](/CYBA/issues/CYBA-616) был учтён; в текущем разблокированном heartbeat [CYBA-616](/CYBA/issues/CYBA-616), [CYBA-617](/CYBA/issues/CYBA-617), [CYBA-604](/CYBA/issues/CYBA-604) и [CYBA-603](/CYBA/issues/CYBA-603) уже `done`.
- Follow-up blocker [CYBA-627](/CYBA/issues/CYBA-627) по finding SRBAC-002 закрыт и retested; текущих gate blockers нет.
- Context7 docs checked: N/A - ручной triage issue-thread/gate; поведение framework/library/API не оценивалось.
- Evidence: `evidence/security-rbac/cyba-606-soft-blocker-triage-2026-06-09.txt`

## Finding SRBAC-002

Серьёзность: P2
Тип: sensitive token exposure / httpOnly-cookie posture regression
Статус: fixed in [CYBA-627](/CYBA/issues/CYBA-627), retested in [CYBA-606](/CYBA/issues/CYBA-606)

Окружение:

- Local [CYBA-606](/CYBA/issues/CYBA-606) workspace.
- Production data, real credentials, raw JWT, cookies, refresh tokens, passwords, `.env` values, payment secrets и real Telegram `initData` не сохранялись.
- Role/state: authenticated web admin/partner/customer session with httpOnly auth cookies.
- Context7 docs checked: MCP `context7` вернул `Monthly quota exceeded`; fallback official docs checked: FastAPI response cookies, SQLAlchemy 2.0 `with_for_update()`, Next.js `proxy.ts`.

Шаги воспроизведения:

1. Authenticate through `POST /api/v1/auth/login` on a web realm.
2. Убедиться, что login response body не содержит `access_token` и `refresh_token`, а auth cookies выставлены.
3. С теми же cookies вызвать `POST /api/v1/auth/refresh` с empty JSON body.
4. Проверить JSON response body.

Ожидаемый результат:

- Web cookie refresh возвращает cookie-only response body и не отдаёт raw `access_token` или `refresh_token` browser JavaScript.
- Token-bearing refresh остаётся на `/api/v1/mobile/auth/refresh` или другом явно non-web contract.

Фактический результат:

- `POST /api/v1/auth/refresh` выставляет auth cookies и одновременно возвращает `TokenResponse(access_token=..., refresh_token=...)` в JS-readable body.
- Frontend/admin/partner `authApi.refresh()` отдаёт этот response browser JavaScript, хотя client code comments фиксируют `SEC-01` migration web auth to httpOnly cookies.

Evidence:

- До фикса: `backend/src/presentation/api/v1/auth/routes.py` выставлял auth cookies и возвращал token-bearing `TokenResponse` на web refresh.
- После фикса: `backend/src/presentation/api/v1/auth/routes.py:983` uses `response_model=WebRefreshResponse`; `backend/src/presentation/api/v1/auth/routes.py:1143` returns `WebRefreshResponse(...)`.
- После фикса: `backend/src/presentation/api/v1/auth/schemas.py:83` defines `WebRefreshResponse` без `access_token` и `refresh_token`.
- После фикса: `frontend/src/lib/api/auth.ts:326`, `admin/src/lib/api/auth.ts:307`, `partner/src/lib/api/auth.ts:302` type `authApi.refresh()` as `WebRefreshResponse`.
- После фикса: generated OpenAPI/types for web `/auth/refresh` reference `WebRefreshResponse`; mobile `/mobile/auth/refresh` still uses mobile `TokenResponse`.
- Sanitized evidence file: `evidence/security-rbac/cyba-606-web-refresh-token-body-2026-06-09.txt`
- Retest evidence file: `evidence/security-rbac/cyba-606-web-refresh-retest-2026-06-09.txt`

Проверка:

- `uv run pytest tests/integration/test_auth_realm_sessions.py tests/unit/presentation/test_client_ip.py -q --no-cov`
  Result: 21 tests passed.
- `npm run test:run -w frontend -- src/lib/api/__tests__/auth.test.ts`
  Result: 1 file, 87 tests passed.
- `npm run test:run -w admin -- src/lib/api/__tests__/auth.test.ts`
  Result: 1 file, 85 tests passed.
- `npm run test:run -w partner -- src/lib/api/__tests__/auth.test.ts`
  Result: 1 file, 83 tests passed.
- `REDIS_URL=redis://localhost:6379/15 uv run pytest tests/integration/api/v1/mobile_auth/test_refresh_token_principal_owner.py -q --no-cov`
  Result: 2 tests skipped, потому что Docker-backed PostgreSQL at `localhost:6767` был недоступен в этом heartbeat; [CYBA-617](/CYBA/issues/CYBA-617) содержит DB-backed mobile evidence from disposable PostgreSQL.

Влияние на gate:

- [CYBA-627](/CYBA/issues/CYBA-627) fixed and retested. Finding SRBAC-002 больше не блокирует [CYBA-606](/CYBA/issues/CYBA-606).

## Finding SRBAC-001

Severity: P2
Type: Security/RBAC-adjacent host isolation regression
Status: fixed in [CYBA-579](/CYBA/issues/CYBA-579) and retested by QA in [CYBA-582](/CYBA/issues/CYBA-582)

Environment:

- Local repo workspace, no credentials, no cookies.
- Frontend dev server on `9001`.
- Heartbeat shell had `NODE_ENV=production PORT=3110`; dev smoke used explicit `NODE_ENV=development NEXT_TELEMETRY_DISABLED=1`.
- Context7 docs checked: `/vercel/next.js/v16.1.6` via `ctx7`; Next.js docs indicate `src/proxy.ts` is supported by proxy detection. Playwright CLI docs checked via `ctx7`, but Playwright was not installed.

Steps to reproduce:

1. Start frontend dev server: `NODE_ENV=development NEXT_TELEMETRY_DISABLED=1 npm run dev -w frontend`.
2. Run `curl --noproxy '*' -I --resolve 'cyber-vpn.net:9001:127.0.0.1' 'http://cyber-vpn.net:9001/en-EN/dashboard?tab=ops'`.
3. Run `curl --noproxy '*' -I --resolve 'www.cyber-vpn.net:9001:127.0.0.1' 'http://www.cyber-vpn.net:9001/en-EN/users'`.
4. Run `curl --noproxy '*' -I --resolve 'my.cyber-vpn.net:9001:127.0.0.1' 'http://my.cyber-vpn.net:9001/'`.

Expected result:

- Public-host cabinet routes redirect to `my.cyber-vpn.net` before serving cabinet HTML.
- Cabinet root redirects to localized dashboard (`/{locale}/dashboard`) per `frontend/src/proxy.ts`.

Actual result:

- Public-host cabinet routes returned `200 OK` unauthenticated cabinet shell instead of redirecting to `my.cyber-vpn.net`.
- Cabinet root returned `307` to `/{locale}` rather than `/{locale}/dashboard`.
- No private user/customer/payment data, `access_token`, `refresh_token`, or Telegram `initData` was observed in the sampled response bodies.

Evidence:

- `evidence/security-rbac/frontend-host-canonicalization-2026-06-06.txt`
- `evidence/security-rbac/frontend-host-canonicalization-retest-2026-06-06.txt`
- `evidence/security-rbac/frontend-host-canonicalization-runtime-qa-2026-06-06.txt`
- `evidence/security-rbac/direct-url-smoke-2026-06-06.txt`

Retest result:

- `cyber-vpn.net:9001/en-EN/dashboard?tab=ops` returned `307` to `https://my.cyber-vpn.net:9001/en-EN/dashboard?tab=ops`.
- `www.cyber-vpn.net:9001/en-EN/users` returned `307` to `https://my.cyber-vpn.net:9001/en-EN/users`.
- `my.cyber-vpn.net:9001/` returned `307` to `https://my.cyber-vpn.net:9001/en-EN/dashboard`.
- `admin.cyber-vpn.org:9001/en-EN/dashboard` returned `307` to `https://admin.cyber-vpn.net:9001/en-EN/dashboard`.
- Direct cabinet dashboard remained an unauthenticated `AUTHENTICATING...` shell and did not expose checked `access_token`, `refresh_token`, `initData`, customer ledger, payment attempts, or `DEV_BYPASS_AUTH` markers.

[CYBA-582](/CYBA/issues/CYBA-582) scoped verification:

- Result: PASS for all four required `curl -I` checks.
- Response bodies opened: no.
- Context7 docs checked: N/A - manual HTTP-header runtime verification against issue-defined expected statuses/locations.
- Evidence: `evidence/security-rbac/frontend-host-canonicalization-runtime-qa-2026-06-06.txt`

## Passed / Not Reproduced

- Customer dashboard direct URL without cookies rendered an `AUTHENTICATING...` shell and did not expose checked private markers.
- Customer Mini App direct URL without Telegram `initData` did not expose checked token/initData/private markers.
- Admin direct dashboard/customer detail checks did not expose checked private markers in the local response body.
- Partner storefront host redirected workspace route to storefront root; retired legacy admin route returned `404` with `Cache-Control: no-store`.
- Partner portal unauthenticated body contained only generic guard/i18n copy around `Access denied` and `Partner workspace`; no customer/payment/token/initData values observed.

## Verification

- `npm run test:run -w frontend -- src/__tests__/proxy.test.ts src/features/auth/lib/session.test.ts src/stores/__tests__/auth-store.test.ts src/lib/api/__tests__/auth.test.ts src/lib/api/__tests__/client.test.ts src/app/api/auth/optional-session/route.test.ts`
  Result: 6 files, 220 tests passed.
- `npm run test:run -w admin -- src/__tests__/proxy.test.ts src/shared/lib/__tests__/admin-rbac.test.ts src/features/auth/components/__tests__/AuthGuard.test.tsx src/features/auth/lib/session.test.ts src/app/api/v1/[...path]/route.test.ts src/lib/api/__tests__/client.test.ts src/stores/auth-store.test.ts`
  Result: 7 files, 62 tests passed.
- `npm run test:run -w partner -- src/features/partner-portal-state/components/partner-route-guard.test.tsx src/shared/lib/__tests__/surface-policy.test.ts src/__tests__/proxy.test.ts src/features/auth/components/__tests__/AuthGuard.test.tsx src/features/auth/lib/session.test.ts src/lib/api/__tests__/client.test.ts src/app/api/v1/[...path]/route.test.ts`
  Result: 7 files, 68 tests passed.
- `npm run test:run -w frontend -- src/__tests__/proxy.test.ts`
  Retest result: 1 file, 11 tests passed after [CYBA-579](/CYBA/issues/CYBA-579).

## Not Tested / Constraints

- Browser screenshots/video were not captured because Playwright is not installed in this workspace.
- Authenticated role-to-role data isolation was not exercised because no local/staging test credentials were provided in scope.
- Expired-token browser-back behavior was covered only through existing unit/client interceptor tests, not with a live authenticated browser session.
