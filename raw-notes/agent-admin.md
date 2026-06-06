# Заметки ручного QA admin panel

## CYBA-574 - admin panel manual/session recheck после CYBA-568

Дата: `2026-06-06`

Область: post-fix local-stage recheck для [CYBA-568](/CYBA/issues/CYBA-568): anonymous direct URL guards, approved synthetic owner login + 2FA, read-only protected admin routes, UI `Sign Out`, post-logout session and direct dashboard behavior.

Окружение:

- Admin panel: `http://127.0.0.1:13001`
- Backend/API: `http://127.0.0.1:18080`
- Browser: Playwright Chromium headless, viewport `1440x1000`, locale `en-EN`
- Paperclip execution workspace: `currentExecutionWorkspace=null`; used local checkout/runtime.
- Состояние пользователя: approved synthetic `CYBA451_ADMIN_OWNER`, role `owner/super_admin`, realm `admin`
- Источник секретов: protected runtime secret file `/srv/paperclip/data/instances/default/runtime-secrets/cyba-451-stage1-qa.env`; credential values, TOTP values, cookies, JWTs, refresh tokens, headers, HAR, trace, video, storage state, `.env` values, payment data, production PII и Telegram `initData` не сохранялись.

| Сценарий | Поток | Статус | Заметки |
|---|---|---:|---|
| `CYBA574-UNAUTH-*` | Fresh anonymous context -> dashboard/customers/customer 360/payments/wallets/withdrawals/partners/referrals/plans/sessions/audit-log direct URLs | PASS | Все tested routes redirected to `/en-EN/login`; `/api/v1/auth/session -> 401`. |
| `CYBA574-AUTH-*` | Owner login + 2FA -> read-only protected route navigation | PASS | Login `200`, 2FA complete `200`, pre-logout session `200`; tested read-only routes did not redirect to login. No mutation performed. |
| `CYBA574-LOGOUT-001` | Owner login + 2FA -> `/en-EN/dashboard` -> user menu `Sign Out` -> session/direct dashboard checks | FAIL | UI logout now returns `POST /api/v1/auth/logout -> 204`, but post-logout `/api/v1/auth/session -> 200`; direct `/en-EN/dashboard` remained authenticated. Old `403 CSRF origin validation failed` symptom is gone, but server session revocation still fails. |
| `CYBA574-POST581-RUNTIME-001` | Retest after [CYBA-581](/CYBA/issues/CYBA-581) done on `13001/18080` local-stage runtime | BLOCKED/FAIL | Browser result still shows `logout 204`, post-logout session `200`, direct dashboard authenticated. Runtime freshness check found `13001`/`18080` are Docker containers `Up 32 hours`, while [CYBA-581](/CYBA/issues/CYBA-581) source files changed around `2026-06-06 07:34 UTC`; this proves stale local-stage container runtime, not current-source fix failure. |
| `CYBA574-FINAL-LOGOUT-001` | Retest after [CYBA-585](/CYBA/issues/CYBA-585) refreshed current-source local-stage runtime | PASS | Runtime containers were `Up 6 minutes (healthy)`. Login `200`, 2FA complete `200`, pre-logout session `200`, UI logout `204`, post-logout session `401`, direct `/en-EN/dashboard` redirected to login. |

Доказательства:

- Sanitized JSON: `evidence/admin/cyba-574/notes/cyba-574-admin-session-recheck__20260606T072039Z.json`
- Summary: `evidence/admin/cyba-574/notes/cyba-574-admin-session-recheck__20260606T072039Z.md`
- Post-[CYBA-581] runtime recheck summary: `evidence/admin/cyba-574/notes/cyba-574-post-cyba581-runtime-recheck__20260606T074027Z.md`
- Post-[CYBA-581] sanitized JSON: `evidence/admin/cyba-574/notes/cyba-574-admin-session-recheck__20260606T074027Z.json`
- Final pass summary: `evidence/admin/cyba-574/notes/cyba-574-final-pass__20260606T075949Z.md`
- Final pass sanitized JSON: `evidence/admin/cyba-574/notes/cyba-574-admin-session-recheck__20260606T075949Z.json`
- QA harness: `evidence/admin/cyba-574/admin-session-recheck.mjs`
- Screenshots:
  - `evidence/admin/cyba-574/screenshots/CYBA-574__admin-panel__anonymous__en-EN__desktop-1440__login__20260606T072039Z.png`
  - `evidence/admin/cyba-574/screenshots/CYBA-574__admin-panel__anonymous__en-EN__desktop-1440__dash-pass__20260606T072039Z.png`
  - `evidence/admin/cyba-574/screenshots/CYBA-574__admin-panel__owner__en-EN__desktop-1440__dash-pass__20260606T072039Z.png`
  - `evidence/admin/cyba-574/screenshots/CYBA-574__admin-panel__owner__en-EN__desktop-1440__before-logout__20260606T072039Z.png`
  - `evidence/admin/cyba-574/screenshots/CYBA-574__admin-panel__owner__en-EN__desktop-1440__after-sign-out__20260606T072039Z.png`
  - `evidence/admin/cyba-574/screenshots/CYBA-574__admin-panel__owner__en-EN__desktop-1440__dashboard-after-logout__20260606T072039Z.png`

Проверка sensitive data: PASS - text evidence scan не нашёл bearer/JWT-shaped values, raw token assignments, raw cookie headers, password values или TOTP secret values. Screenshots contain approved local-stage synthetic UI only.

Context7 docs checked: Context7 MCP monthly quota exceeded; fallback `ctx7 docs /microsoft/playwright` checked `chromium.launch`, `browser.newContext`, `page.goto`, `waitForResponse`, locator click and `page.screenshot`. Manual finding itself is UI/business-flow behavior; no framework root cause asserted.

Post-[CYBA-581] Context7 docs checked: N/A - manual UI/business-flow retest and runtime freshness finding; no code/config/library behavior was changed in this heartbeat.

Final pass Context7 docs checked: N/A - final manual UI/business-flow retest only; no code/config/library behavior was changed in this heartbeat.

Не тестировалось в этом heartbeat: customer mutations, payments/wallet/manual top-up/refund/capture/withdrawal moderation/payout/settlement mutations, permission changes, admin invite/role assignment, destructive 2FA/passkey operations, Remnawave/VPN provisioning, production systems/data/secrets.

## CYBA-508 - ретест admin logout/session revocation

Дата: `2026-06-04`

Область: точечная проверка, что fix из `CYBA-507` отзывает серверную admin-сессию после UI `Sign Out`.

Окружение:

- Admin panel: `http://127.0.0.1:13001`
- Backend/API: `http://127.0.0.1:18080`, `/health -> 200`
- Browser: Chromium headless через Playwright, viewport `1440x1000`, locale `en-EN`
- Состояние пользователя: approved synthetic `CYBA451_ADMIN_OWNER`, role `owner/super_admin`, realm `admin`
- Источник секретов: protected runtime secret file; credential values, TOTP values, cookies, JWTs, refresh tokens, headers, HAR, trace, video, storage state, `.env` values, payment data, production PII и Telegram `initData` не сохранялись.

| Сценарий | Поток | Статус | Заметки |
|---|---|---:|---|
| `CYBA-508-LOGOUT-001` | Fresh context -> `/en-EN/login` -> synthetic owner login + 2FA -> `/en-EN/dashboard` -> user menu `Sign Out` -> session/direct dashboard checks | FAIL | Login `200`, 2FA pending `204`, 2FA complete `200`, pre-logout session `200`; UI `POST /api/v1/auth/logout -> 403` с `CSRF origin validation failed`; post-logout `GET /api/v1/auth/session -> 200`; direct `/en-EN/dashboard` остался authenticated. |
| `CYBA-508-FOREIGN-001` | Отдельная synthetic session, unsafe `POST /api/v1/auth/logout` с foreign `Origin: https://evil.example` | FAIL | Ожидался backend CSRF reject; фактически response `204`. Browser session check после запроса вернул `200` в synthetic context. |

Доказательства:

- Sanitized JSON: `evidence/admin/cyba-508/notes/cyba-508-admin-logout-retest__20260604T182855Z.json`
- Screenshots:
  - `evidence/admin/cyba-508/screenshots/CYBA-508__admin-panel__owner__en-EN__desktop-1440__before-logout__20260604T182855Z.png`
  - `evidence/admin/cyba-508/screenshots/CYBA-508__admin-panel__owner__en-EN__desktop-1440__after-sign-out__20260604T182855Z.png`
  - `evidence/admin/cyba-508/screenshots/CYBA-508__admin-panel__owner__en-EN__desktop-1440__dashboard-after-logout__20260604T182855Z.png`
- QA harness: `evidence/admin/cyba-508/logout-retest.mjs`

Проверка sensitive data: PASS - text evidence scan не нашёл bearer/JWT-shaped values, raw token assignments, raw cookie headers или credential values в published notes/JSON.

Context7 docs checked: MCP quota exceeded; fallback `ctx7 docs /microsoft/playwright` checked `chromium.launch`, `browser.newContext`, `page.goto`, locators, `waitForResponse` и screenshot APIs.

Не тестировалось в этом heartbeat: broader customers/payments/wallets/withdrawals/partners/referrals/pricing regression. `CYBA-508` scoped только на admin logout/session revocation.

## CYBA-514 - ретест admin logout/session revocation после CYBA-511

Дата: `2026-06-04`

Область: точечная проверка, что remediation из `CYBA-511` отзывает server admin session после UI `Sign Out`.

Окружение:

- Admin panel: `http://127.0.0.1:13001`
- Backend/API: `http://127.0.0.1:18080`, `/health -> 200`
- Browser: Chromium headless через Playwright, viewport `1440x1000`, locale `en-EN`
- Состояние пользователя: approved synthetic `CYBA451_ADMIN_OWNER`, role `owner/super_admin`, realm `admin`
- Источник секретов: protected runtime secret file; credential values, TOTP values, cookies, JWTs, refresh tokens, headers, HAR, trace, video, storage state, `.env` values, payment data, production PII и Telegram `initData` не сохранялись.

| Сценарий | Поток | Статус | Заметки |
|---|---|---:|---|
| `CYBA-514-LOGOUT-001` | Fresh context -> `/en-EN/login` -> synthetic owner login + 2FA -> `/en-EN/dashboard` -> user menu `Sign Out` -> session/direct dashboard checks | FAIL | Login `200`, 2FA pending `204`, 2FA complete `200`, pre-logout session `200`; UI `POST /api/v1/auth/logout -> 403` с `CSRF origin validation failed`; post-logout `GET /api/v1/auth/session -> 200`; direct `/en-EN/dashboard` остался authenticated. |

Доказательства:

- Sanitized JSON: `evidence/admin/cyba-514/notes/cyba-514-admin-logout-retest__20260604T183846Z.json`
- Screenshots:
  - `evidence/admin/cyba-514/screenshots/CYBA-514__admin-panel__owner__en-EN__desktop-1440__before-logout__20260604T183846Z.png`
  - `evidence/admin/cyba-514/screenshots/CYBA-514__admin-panel__owner__en-EN__desktop-1440__after-sign-out__20260604T183846Z.png`
  - `evidence/admin/cyba-514/screenshots/CYBA-514__admin-panel__owner__en-EN__desktop-1440__dashboard-after-logout__20260604T183846Z.png`
- QA harness: `evidence/admin/cyba-514/logout-retest.mjs`

Проверка sensitive data: PASS - text evidence scan не нашёл bearer/JWT-shaped values, raw token assignments, raw cookie headers или credential values в published notes/JSON/script.

Context7 docs checked: Context7 MCP quota exceeded; fallback `ctx7 library Playwright` and `ctx7 docs /microsoft/playwright` checked `chromium.launch`, `browser.newContext`, `page.goto`, `waitForResponse`, locator click and screenshot APIs.

Не тестировалось в этом heartbeat: broader customers/payments/wallets/withdrawals/partners/referrals/pricing regression. `CYBA-514` scoped только на admin logout/session revocation after `CYBA-511`.
