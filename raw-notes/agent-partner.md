# Partner portal raw notes

Дата: `2026-06-04`

Основной журнал partner manual QA ведется здесь:

- `docs/qa/manual-flow-audit/2026-06-04/raw-notes/agent-partner.md`

## CYBA-520 heartbeat snapshot

- Issue: [CYBA-520](/CYBA/issues/CYBA-520)
- Wake reason: `issue_blockers_resolved`; [CYBA-519](/CYBA/issues/CYBA-519) was `done`.
- Retest target: `http://portal.localhost:3004` against backend `http://127.0.0.1:18080`.
- Account: protected synthetic `CYBA451_PARTNER_OWNER` fixture; credentials, TOTP, tokens, cookie values, storageState, HAR, trace, payment secrets, production PII, and Telegram initData were not stored.
- Result: `FAIL`.
- First failing transition: `POST /api/auth/2fa/complete -> 401`.
- Cookie state: after `POST /api/auth/2fa/pending`, only `pending_2fa` existed for `portal.localhost`; after complete, cookies were `[]`.
- Session check: `GET /api/v1/auth/session -> 401`.
- Protected routes `/en-EN/dashboard`, `/en-EN/codes`, `/en-EN/finance`, `/en-EN/conversions`, and `/en-EN/team` redirected to login.
- Evidence JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-520__partner-2fa-session-retest__20260604T202139Z.json`

Context7 docs checked: unavailable - quota exceeded. Fallback official docs checked: Playwright `browser.newContext`, `context.cookies`, `page.goto`, `page.screenshot`, and `chromium.launch`.

## CYBA-523 heartbeat snapshot

- Issue: [CYBA-523](/CYBA/issues/CYBA-523)
- Причина wake: `issue_blockers_resolved`; [CYBA-522](/CYBA/issues/CYBA-522) перешла в `done`.
- Цель ретеста: `http://portal.localhost:3004` с backend `http://127.0.0.1:18080`.
- Account: protected synthetic `CYBA451_PARTNER_OWNER` fixture; credentials, TOTP, tokens, cookie values, storageState, HAR, trace, payment secrets, production PII и Telegram initData не сохранялись.
- Результат: `PASS`.
- Auth flow: `POST /api/v1/auth/login -> 200`, `requires_2fa=true`; `POST /api/auth/2fa/pending -> 204`; `POST /api/auth/2fa/complete -> 200`, `redirect_to=/en-EN/dashboard`; `GET /api/v1/auth/session -> 200`, `auth_realm_key=partner`.
- Cookie state после complete:
  - root-origin probe `context.cookies('http://portal.localhost:3004')` -> `[]`
  - path-matched probe `context.cookies('http://portal.localhost:3004/api/v1/auth/session')` -> `partner_access_token`, `partner_refresh_token`, both `Path=/api`
- Protected routes `/en-EN/dashboard`, `/en-EN/codes`, `/en-EN/finance`, `/en-EN/conversions` и `/en-EN/team` отрендерились без login redirect и без `SYSTEM FAILURE`.
- Evidence JSON: `docs/qa/manual-flow-audit/2026-06-04/evidence/partner/CYBA-523__partner-2fa-path-cookie-retest__20260604T210730Z.json`

Context7 MCP проверен: quota exceeded. ctx7 fallback проверен: `/microsoft/playwright` `BrowserContext.cookies(urls)` и `page.screenshot` path option.
