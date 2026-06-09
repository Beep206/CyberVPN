# CYBA-609 admin security sessions browser QA

Дата: `2026-06-09`

Issue: [CYBA-609](/CYBA/issues/CYBA-609)
Parent: [CYBA-597](/CYBA/issues/CYBA-597)
Owner: `qa-admin-panel-manual`

## Окружение и границы

- Admin app: `http://127.0.0.1:9101`, локальный `Next.js` dev server из текущего checkout.
- Paperclip `currentExecutionWorkspace`: `null`; Paperclip runtime service для issue не был доступен, поэтому использован локальный checkout.
- Browser: Playwright Chromium headless.
- Viewport: `1440x1000`.
- Locale: `ru-RU`.
- User role/state: synthetic dev admin через `DEV_BYPASS_AUTH=true` и `USER_ROLE=admin`.
- Data boundary: все `/api/v1/auth/*` session-device endpoints были перехвачены Playwright route stubs; реальные backend sessions, cookies, JWT, refresh tokens и customer/payment данные не читались и не изменялись.
- Destructive boundary: `logout-others`, `DELETE /auth/devices/{device_id}` и `logout-all` проверялись только как synthetic network calls to stubs.

## Выполненные проверки

| Case | Flow | Status | Notes |
|---|---|---:|---|
| `CYBA609-UNIT-001` | `npm run test:run -- src/features/security/components/__tests__/security-sessions-console.test.tsx` | PASS | `1` файл, `4` теста passed. Проверены backend totals, один current marker, action-lock для double confirm, selected device revoke by stable `device_id`, hard-stop redirect. |
| `CYBA609-UNAUTH-001` | Fresh anonymous context -> `/ru-RU/security/sessions` with `/api/v1/auth/session -> 401` | PASS | Redirected to `/ru-RU/login?redirect=%2Fru-RU%2Fsecurity%2Fsessions`; private session console did not render. |
| `CYBA609-SESS-001` | Synthetic admin -> sessions console with `3` devices, `2` backend `is_current=true` flags | PASS | Scoped table recheck found exactly one `Текущая` badge and one table `Текущее устройство` action chip. Metrics showed `3` unique devices, `2` remote devices, current IP `203.0.113.10`, limit `3/7`. |
| `CYBA609-SESS-002` | `Завершить другие` dialog, double-click confirm | PASS | Stubbed `POST /api/v1/auth/devices/logout-others` was called once; feedback showed `Завершено удалённых сессий: 2.` |
| `CYBA609-SESS-003` | Remote device `Завершить сессию` dialog, double-click confirm | PASS | Stubbed `DELETE /api/v1/auth/devices/dev_second_flag_beta` was called once; selected device id was stable and matched the dialog subject. |
| `CYBA609-SESS-004` | `Завершить все` hard-stop dialog, double-click confirm | PASS | Stubbed `POST /api/v1/auth/logout-all` was called once; UI redirected current console to `/ru-RU/login`. |
| `CYBA609-SESS-LAYOUT-001` | Desktop table action-column visibility probe | PRODUCT GAP | At `1440x1000`, table width was `1487.5px` inside a `707.3px` scroll container; first revoke button bbox was `left=1597.5`, `right=1773.5`, outside viewport. Functional actions still worked via DOM and scroll container, but the action column is not visible on first paint. |

## Bugs

No new functional `P0/P1/P2` bug was confirmed for the scoped session flows.

The first browser JSON contains one failed broad text-count check for `Текущее устройство`; it was a harness false positive because it counted the right-side current-device panel title in addition to the table chip. The scoped recheck supersedes that result and passed.

## Product gaps

### ADM-GAP-CYBA609-001: session table action column is off initial desktop viewport

Severity: `P3 UX`

Environment: local admin `http://127.0.0.1:9101`, Chromium headless, viewport `1440x1000`, locale `ru-RU`, synthetic dev admin.

Steps to reproduce:

1. Open `/ru-RU/security/sessions` as a synthetic admin with at least one current and one remote device.
2. Observe the session table at `1440x1000`.
3. Try to find per-row `Завершить сессию` action without horizontal table scrolling.

Expected result:

- Per-row action affordance is visible or clearly discoverable in the initial desktop table layout.

Actual result:

- The table scroll container is `707.3px` wide while the table is `1487.5px` wide.
- The first revoke action button is positioned outside the viewport (`left=1597.5`, `right=1773.5` on a `1440px` viewport).
- Screenshots show the visible table area ending before IP/last-used/created/action columns.

Evidence:

- Screenshot: `evidence/admin/cyba-609/screenshots/CYBA-609__admin-sessions__synthetic__ru-RU__desktop-1440__sessions-loaded__20260609T190544Z.png`
- Layout probe: `evidence/admin/cyba-609/notes/cyba-609-admin-sessions-scoped-recheck__20260609T190756Z.json`

Recommended owner/action: admin frontend owner should consider sticky/frozen action column, denser table columns, or a row action menu that remains visible at desktop widths.

Context7 docs checked: N/A - manual UI/business-flow finding.

## Evidence

- Browser QA JSON: `evidence/admin/cyba-609/notes/cyba-609-admin-sessions-browser-qa__20260609T190544Z.json`
- Scoped recheck JSON: `evidence/admin/cyba-609/notes/cyba-609-admin-sessions-scoped-recheck__20260609T190756Z.json`
- Screenshots:
  - `evidence/admin/cyba-609/screenshots/CYBA-609__admin-sessions__synthetic__ru-RU__desktop-1440__unauth-direct-url-redirect__20260609T190544Z.png`
  - `evidence/admin/cyba-609/screenshots/CYBA-609__admin-sessions__synthetic__ru-RU__desktop-1440__sessions-loaded__20260609T190544Z.png`
  - `evidence/admin/cyba-609/screenshots/CYBA-609__admin-sessions__synthetic__ru-RU__desktop-1440__logout-others-confirm__20260609T190544Z.png`
  - `evidence/admin/cyba-609/screenshots/CYBA-609__admin-sessions__synthetic__ru-RU__desktop-1440__revoke-device-confirm__20260609T190544Z.png`
  - `evidence/admin/cyba-609/screenshots/CYBA-609__admin-sessions__synthetic__ru-RU__desktop-1440__logout-all-confirm__20260609T190544Z.png`
  - `evidence/admin/cyba-609/screenshots/CYBA-609__admin-sessions__synthetic__ru-RU__desktop-1440__logout-all-login-redirect__20260609T190544Z.png`

## Network and console notes

- Scoped session-device network counts: `GET /api/v1/auth/devices` `3`, `POST /api/v1/auth/devices/logout-others` `1`, `DELETE /api/v1/auth/devices/dev_second_flag_beta` `1`, `POST /api/v1/auth/logout-all` `1`.
- No Playwright `pageerror` was captured.
- Console/network noise from admin shell background reporters and action-queue hooks was observed because this local dev run had no backend at `127.0.0.1:8000`: analytics endpoints returned `403`; unrelated action-queue endpoints returned `500 ECONNREFUSED`. These were not filed as [CYBA-609](/CYBA/issues/CYBA-609) bugs because scoped session-device endpoints were stubbed and the session console checks completed.

## Safety review

PASS. Evidence contains only synthetic reserved documentation IPs, synthetic device ids, synthetic local URLs, screenshots of dev UI, and route-stub counts. No JWT, cookies, refresh tokens, passwords, `.env` values, production PII, payment secrets, real Telegram `initData`, HAR, trace, video, or storage state were stored.

Context7 docs checked: N/A - manual UI/business-flow QA and no source-code/config/library change in this heartbeat.
