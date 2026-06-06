# Результаты проверки admin panel

## CYBA-574 результат post-fix recheck

Общий результат: `FAIL`. Anonymous direct-route guards and owner read-only navigation passed on current [CYBA-568](/CYBA/issues/CYBA-568) baseline, but admin UI logout still does not revoke the current server session.

### ADM-CYBA574-001: Admin UI `Sign Out` returns success but leaves server session active

Серьёзность: `P1`

Окружение: admin panel `http://127.0.0.1:13001`, backend `http://127.0.0.1:18080`, Chromium headless `1440x1000`, locale `en-EN`; Paperclip `currentExecutionWorkspace=null`, used local checkout/runtime.

Состояние пользователя: approved synthetic `CYBA451_ADMIN_OWNER`, role `owner/super_admin`, realm `admin`; credentials и TOTP взяты из protected runtime secret file `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env` и не сохранялись.

Шаги воспроизведения:

1. Открыть fresh browser context на `http://127.0.0.1:13001/en-EN/login`.
2. Войти под approved synthetic `owner/super_admin`.
3. Завершить 2FA.
4. Подтвердить pre-logout `GET /api/v1/auth/session -> 200`.
5. Открыть `http://127.0.0.1:13001/en-EN/dashboard`.
6. Открыть admin user menu.
7. Нажать `Sign Out`.
8. Проверить `POST /api/v1/auth/logout`.
9. Проверить post-logout `GET /api/v1/auth/session`.
10. Напрямую перейти на `http://127.0.0.1:13001/en-EN/dashboard` в том же browser context.

Ожидаемый результат:

- `POST /api/v1/auth/logout` success реально отзывает текущую server session.
- Post-logout `GET /api/v1/auth/session -> 401`.
- Direct `/en-EN/dashboard` redirects to login и не рендерит authenticated dashboard shell.

Фактический результат:

- Login `200`, 2FA complete `200`.
- Pre-logout `GET /api/v1/auth/session -> 200`, role `owner/super_admin`.
- UI `Sign Out` triggered `POST /api/v1/auth/logout -> 204`.
- Post-logout `GET /api/v1/auth/session -> 200`, role `owner/super_admin`.
- Direct `/en-EN/dashboard` remained on `/en-EN/dashboard`.

Примечание: это отличается от старых [CYBA-508](/CYBA/issues/CYBA-508)/[CYBA-514](/CYBA/issues/CYBA-514) ретестов. Старый symptom был `POST /api/v1/auth/logout -> 403` with `CSRF origin validation failed`; current symptom is successful logout response with no effective current-session revocation.

Доказательства:

- Summary: `evidence/admin/cyba-574/notes/cyba-574-admin-session-recheck__20260606T072039Z.md`
- Sanitized JSON: `evidence/admin/cyba-574/notes/cyba-574-admin-session-recheck__20260606T072039Z.json`
- Screenshots:
  - `evidence/admin/cyba-574/screenshots/CYBA-574__admin-panel__owner__en-EN__desktop-1440__before-logout__20260606T072039Z.png`
  - `evidence/admin/cyba-574/screenshots/CYBA-574__admin-panel__owner__en-EN__desktop-1440__after-sign-out__20260606T072039Z.png`
  - `evidence/admin/cyba-574/screenshots/CYBA-574__admin-panel__owner__en-EN__desktop-1440__dashboard-after-logout__20260606T072039Z.png`
- QA harness: `evidence/admin/cyba-574/admin-session-recheck.mjs`

Рекомендуемый owner/action: `SecurityEngineer` with admin frontend/auth owner should triage current-session revocation/cookie invalidation path for admin `Sign Out`. QA acceptance requires `POST /api/v1/auth/logout` success, post-logout `/api/v1/auth/session -> 401`, and direct `/en-EN/dashboard` redirect to login in the same browser context.

Context7 docs checked: Context7 MCP monthly quota exceeded; fallback `ctx7 docs /microsoft/playwright` checked `chromium.launch`, `browser.newContext`, `page.goto`, `waitForResponse`, locator click and `page.screenshot`. Manual finding itself is UI/business-flow behavior; no framework root cause asserted.

Post-[CYBA-581](/CYBA/issues/CYBA-581) retest note:

- [CYBA-581](/CYBA/issues/CYBA-581) is `done` and reports source fixes in backend logout/session revocation plus admin proxy local-stage cookie cleanup.
- Browser retest on `http://127.0.0.1:13001` / `http://127.0.0.1:18080` still produced the same observable failure: logout `204`, post-logout session `200`, direct dashboard authenticated.
- Runtime freshness check found `cybervpn-stage1-cybervpn-admin-1` and `cybervpn-stage1-cybervpn-backend-1` are Docker containers `Up 32 hours`, while [CYBA-581](/CYBA/issues/CYBA-581) source files changed around `2026-06-06 07:34 UTC`.
- Interpretation: the post-[CYBA-581](/CYBA/issues/CYBA-581) FAIL proves the old local-stage container runtime still has the bug; it does not prove current-source [CYBA-581](/CYBA/issues/CYBA-581) code fails after rebuild/restart.
- Evidence: `evidence/admin/cyba-574/notes/cyba-574-post-cyba581-runtime-recheck__20260606T074027Z.md` and `evidence/admin/cyba-574/notes/cyba-574-admin-session-recheck__20260606T074027Z.json`.
- Updated owner/action: provide a safe current-source local-stage admin/backend runtime including [CYBA-581](/CYBA/issues/CYBA-581), then rerun [CYBA-574](/CYBA/issues/CYBA-574) browser harness.

Post-[CYBA-581] Context7 docs checked: N/A - manual UI/business-flow retest and runtime freshness finding; no code/config/library behavior was changed in this heartbeat.

Final [CYBA-585](/CYBA/issues/CYBA-585) current-runtime retest:

- Runtime refreshed and healthy: `cybervpn-stage1-cybervpn-admin-1` and `cybervpn-stage1-cybervpn-backend-1` were `Up 6 minutes (healthy)`.
- Browser retest result: `PASS`.
- Login `200`, 2FA complete `200`.
- Pre-logout `/api/v1/auth/session -> 200`, role `owner/super_admin`.
- UI `Sign Out` -> `POST /api/v1/auth/logout -> 204`.
- Post-logout `/api/v1/auth/session -> 401`.
- Direct `/en-EN/dashboard` redirected to `/en-EN/login?<redacted-query>`.
- Evidence: `evidence/admin/cyba-574/notes/cyba-574-final-pass__20260606T075949Z.md` and `evidence/admin/cyba-574/notes/cyba-574-admin-session-recheck__20260606T075949Z.json`.

Final pass Context7 docs checked: N/A - final manual UI/business-flow retest only; no code/config/library behavior was changed in this heartbeat.

### CYBA-574 pass coverage

- Anonymous direct URL guard: PASS for dashboard, customers, customer 360 synthetic id, payments, wallets, withdrawals, partners, referrals, pricing/plans, security sessions and audit-log routes; all redirected to login and unauth `/api/v1/auth/session -> 401`.
- Authenticated owner read-only route navigation: PASS for dashboard, customers, customer 360 synthetic id route, payments, wallets, withdrawals, partners, referrals redirect target, pricing/plans, security sessions and audit log; no login redirect observed.

Product gaps: no new product gaps identified in this heartbeat.

Blocked/not-tested: customer mutations, payments/wallet/manual top-up/refund/capture/withdrawal moderation/payout/settlement mutations, permission changes, admin invite/role assignment, destructive 2FA/passkey operations and Remnawave/VPN provisioning remain not tested without explicit sandbox/Board approval.

Проверка sensitive data: PASS - credentials, TOTP values, cookies, JWTs, refresh tokens, storage state, headers, payment secrets, customer PII, HAR, trace, video, `.env` values и Telegram `initData` не сохранялись; text evidence scan по `evidence/admin/cyba-574`, `raw-notes/agent-admin.md` and `admin-findings.md` found no bearer/JWT-shaped values, raw token assignments, raw cookie headers, password values or TOTP secret values.

## CYBA-508 результат проверки

Общий результат: `FAIL`. Fix из `CYBA-507` не подтверждён в approved local-stage runtime.

### ADM-CYBA508-001: Admin UI `Sign Out` всё ещё оставляет server session активной

Серьёзность: `P1`

Окружение: admin panel `http://127.0.0.1:13001`, backend `http://127.0.0.1:18080`, Chromium headless `1440x1000`, locale `en-EN`.

Состояние пользователя: approved synthetic `CYBA451_ADMIN_OWNER`, role `owner/super_admin`, realm `admin`; credentials и TOTP взяты из protected runtime secret file и не сохранялись.

Шаги воспроизведения:

1. Открыть fresh browser context на `http://127.0.0.1:13001/en-EN/login`.
2. Войти под approved synthetic `owner/super_admin`.
3. Завершить 2FA.
4. Подтвердить `GET /api/v1/auth/session -> 200`.
5. Перейти на `http://127.0.0.1:13001/en-EN/dashboard`.
6. Открыть admin user menu.
7. Нажать `Sign Out`.
8. Проверить `GET /api/v1/auth/session`.
9. Напрямую перейти на `http://127.0.0.1:13001/en-EN/dashboard`.

Ожидаемый результат:

- `POST /api/v1/auth/logout` проходит успешно, например `204`, и не отклоняется как `403 CSRF origin validation failed`.
- Current server session отозвана.
- Post-logout `GET /api/v1/auth/session -> 401`.
- Direct `/en-EN/dashboard` redirects to login и не рендерит authenticated dashboard shell.

Фактический результат:

- Login `200`, 2FA pending `204`, 2FA complete `200`.
- Pre-logout `GET /api/v1/auth/session -> 200`, role `owner/super_admin`.
- UI `POST /api/v1/auth/logout -> 403`, body `{"detail":"CSRF origin validation failed"}`.
- Post-logout `GET /api/v1/auth/session -> 200`.
- Direct `/en-EN/dashboard` остался на `/en-EN/dashboard` и отрендерил authenticated admin shell.

Доказательства:

- `evidence/admin/cyba-508/notes/cyba-508-admin-logout-retest__20260604T182855Z.json`
- `evidence/admin/cyba-508/screenshots/CYBA-508__admin-panel__owner__en-EN__desktop-1440__before-logout__20260604T182855Z.png`
- `evidence/admin/cyba-508/screenshots/CYBA-508__admin-panel__owner__en-EN__desktop-1440__after-sign-out__20260604T182855Z.png`
- `evidence/admin/cyba-508/screenshots/CYBA-508__admin-panel__owner__en-EN__desktop-1440__dashboard-after-logout__20260604T182855Z.png`

Рекомендуемый owner/action: `SecurityEngineer` / `CYBA-507` owner должен reopen или исправить QA runtime path для admin logout CSRF origin handling и session revocation.

Context7 docs checked: N/A - manual UI/business-flow finding; Playwright API usage for evidence harness checked via fallback `ctx7 docs /microsoft/playwright` after MCP quota exceeded.

### ADM-CYBA508-002: Foreign-origin logout spot-check вернул success вместо CSRF rejection

Серьёзность: `P2`

Окружение и состояние пользователя: как в `ADM-CYBA508-001`, использовалась отдельная fresh synthetic admin session.

Шаги воспроизведения:

1. Создать fresh synthetic `owner/super_admin` session через `http://127.0.0.1:13001`.
2. Отправить unsafe cookie-auth `POST /api/v1/auth/logout` через admin proxy с `Origin: https://evil.example`.
3. Записать только method/path/status и sanitized error detail.

Ожидаемый результат:

- Foreign `Origin` сохраняется admin proxy.
- Backend отклоняет unsafe cookie-auth request, expected `403 CSRF origin validation failed`.

Фактический результат:

- `POST /api/v1/auth/logout` with foreign origin вернул `204`.
- Follow-up session check в synthetic browser context всё ещё вернул `200`.

Доказательства:

- Sanitized JSON section `foreignOrigin` in `evidence/admin/cyba-508/notes/cyba-508-admin-logout-retest__20260604T182855Z.json`.

Product gaps: не выявлены в этом heartbeat.

Blocked/not-tested: full admin regression за пределами logout/session scope не тестировался в `CYBA-508`.

Проверка sensitive data: PASS - credentials, TOTP values, cookies, JWTs, refresh tokens, storage state, headers, payment secrets, customer PII, HAR, trace, video, `.env` values и Telegram `initData` не сохранялись.

## CYBA-514 результат ретеста после CYBA-511

Общий результат: `FAIL`. Remediation из `CYBA-511` не подтверждён в approved local-stage runtime.

### ADM-CYBA514-001: Admin UI `Sign Out` всё ещё оставляет server session активной

Серьёзность: `P1`

Окружение: admin panel `http://127.0.0.1:13001`, backend `http://127.0.0.1:18080`, Chromium headless `1440x1000`, locale `en-EN`.

Состояние пользователя: approved synthetic `CYBA451_ADMIN_OWNER`, role `owner/super_admin`, realm `admin`; credentials и TOTP взяты из protected runtime secret file и не сохранялись.

Шаги воспроизведения:

1. Открыть fresh browser context на `http://127.0.0.1:13001/en-EN/login`.
2. Войти под approved synthetic `owner/super_admin`.
3. Завершить 2FA.
4. Подтвердить `GET /api/v1/auth/session -> 200`.
5. Перейти на `http://127.0.0.1:13001/en-EN/dashboard`.
6. Открыть admin user menu.
7. Нажать `Sign Out`.
8. Проверить `POST /api/v1/auth/logout`.
9. Проверить `GET /api/v1/auth/session`.
10. Напрямую перейти на `http://127.0.0.1:13001/en-EN/dashboard` в том же browser context.

Ожидаемый результат:

- `POST /api/v1/auth/logout` проходит успешно, например `204`, или другой successful status реально отзывает текущую server session.
- Post-logout `GET /api/v1/auth/session -> 401`.
- Direct `/en-EN/dashboard` redirects to login и не рендерит authenticated dashboard shell.

Фактический результат:

- Login `200`, 2FA pending `204`, 2FA complete `200`.
- Pre-logout `GET /api/v1/auth/session -> 200`, role `owner/super_admin`.
- UI `POST /api/v1/auth/logout -> 403`, body `{"detail":"CSRF origin validation failed"}`.
- Post-logout `GET /api/v1/auth/session -> 200`.
- Direct `/en-EN/dashboard` остался на `/en-EN/dashboard` и отрендерил authenticated admin shell.

Доказательства:

- `evidence/admin/cyba-514/notes/cyba-514-admin-logout-retest__20260604T183846Z.json`
- `evidence/admin/cyba-514/screenshots/CYBA-514__admin-panel__owner__en-EN__desktop-1440__before-logout__20260604T183846Z.png`
- `evidence/admin/cyba-514/screenshots/CYBA-514__admin-panel__owner__en-EN__desktop-1440__after-sign-out__20260604T183846Z.png`
- `evidence/admin/cyba-514/screenshots/CYBA-514__admin-panel__owner__en-EN__desktop-1440__dashboard-after-logout__20260604T183846Z.png`
- QA harness: `evidence/admin/cyba-514/logout-retest.mjs`

Рекомендуемый owner/action: `SecurityEngineer` / `CYBA-511` owner должен продолжить remediation. QA blocker can close only when browser retest shows logout success, post-logout session `401`, and direct dashboard redirect to login.

Context7 docs checked: Context7 MCP quota exceeded; fallback `ctx7 library Playwright` and `ctx7 docs /microsoft/playwright` checked `chromium.launch`, `browser.newContext`, `page.goto`, `waitForResponse`, locator click and screenshot APIs. Manual finding itself is UI/business-flow behavior; no framework root cause asserted.

Product gaps: не выявлены в этом heartbeat.

Blocked/not-tested: full admin regression за пределами logout/session scope не тестировался в `CYBA-514`.

Проверка sensitive data: PASS - credentials, TOTP values, cookies, JWTs, refresh tokens, storage state, headers, payment secrets, customer PII, HAR, trace, video, `.env` values и Telegram `initData` не сохранялись; text evidence scan по `evidence/admin/cyba-514` clean.
