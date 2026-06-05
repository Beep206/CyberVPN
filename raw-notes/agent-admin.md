# Заметки ручного QA admin panel

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
