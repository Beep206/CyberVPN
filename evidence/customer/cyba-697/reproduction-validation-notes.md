# CYBA-697 Reproduction Validation Notes

## Executive summary

Final reproduction validation for `CYBA-697` passed after child blockers `CYBA-710` and `CYBA-711` were completed. The final parent run on synthetic/local data produced 20 checks, 20 PASS, 0 FAIL.

Context7 docs checked: Playwright via ctx7 fallback `/microsoft/playwright.dev` and `/microsoft/playwright`; Context7 MCP quota exceeded. Manual UI/business-flow findings otherwise N/A.

## Environment

- App: local frontend dev server `http://127.0.0.1:9001`
- Browser: Playwright `chromium`
- Locale: `ru-RU`
- Viewport: `1440x1000`
- User role/state: synthetic authenticated customer, viewer role
- Test data: synthetic `QA Customer CYBA-697`, public UID `14677650`, mocked `/api/**`
- Final evidence timestamp: `20260616T183338Z`

## PASS validation summary

- Account UID: `14677650` visible in settings; UUID4 pattern not visible to customer.
- Account nav: user menu contains `Безопасность`; security controls separated under `/settings/security`.
- Language/timezone: language shows human labels and timezone shows `Europe/Moscow (UTC+03:00)`.
- Delete account: cabinet route localized, no `:3000`; synthetic request returns `PRIV-CYBA697`.
- Dashboard: active subscription switcher visible; no false provisioning warning.
- Servers: full subscription URL visible; active service state does not show false blocking warning.
- Subscriptions: duration/devices/traffic filters visible and functional; filtered result includes `Pro Quarterly`.
- Header currency selector: customer header shows `₽` visual selector and no standalone raw `RUB` in closed trigger.
- Telegram fresh link: synthetic fresh magic token reaches `/ru-RU/dashboard`.
- Telegram expired link: synthetic expired magic token shows `Запрос на вход через Telegram истёк. Запустите вход заново на сайте.`
- Sign out: header sign out calls logout and protected dashboard redirects to `/ru-RU/login?<redacted-query>`.

## Resolved blocker 1: customer dashboard header currency selector

- Linked issue: `CYBA-710`
- Final status: PASS on parent retest.
- Route/state: authenticated customer header on `/ru-RU/settings` and `/ru-RU/dashboard`.
- Expected result: customer portal header includes visual currency representation, for example `₽`, without exposing raw closed-selector code like `RUB`.
- Actual final result: runner check `header-currency-symbol-not-raw-code` passed with actual `header shows ₽ and no visible RUB code in closed selector`.
- Evidence:
  - `evidence/customer/cyba-697/screenshots/CYBA-697__customer-portal__synthetic__ru-RU__desktop-1440__settings-user-menu-open__20260616T183338Z.png`
  - `evidence/customer/cyba-697/notes/cyba-697-customer-portal-regression__20260616T183338Z.json`
- Sanitization: screenshot/JSON use synthetic data only; no secrets or real PII.

## Resolved blocker 2: expired Telegram synthetic magic link copy

- Linked issue: `CYBA-711`
- Final status: PASS on parent retest.
- Route/state: `/ru-RU/telegram-link?magic=expired-magic-cyba697`.
- Expected result: UI shows localized expired-specific copy `Запрос на вход через Telegram истёк. Запустите вход заново на сайте.`
- Actual final result: runner check `telegram-expired-synthetic-link-fails` passed with actual `expired-link copy matches Auth.telegram.botLinkExpired`.
- Evidence:
  - `evidence/customer/cyba-697/screenshots/CYBA-697__customer-portal__synthetic__ru-RU__desktop-1440__telegram-expired-synthetic-link-error__20260616T183338Z.png`
  - `evidence/customer/cyba-697/notes/cyba-697-customer-portal-regression__20260616T183338Z.json`
  - Network note: `GET /api/v1/oauth/telegram/magic-link/expired-magic-cyba697/status` returned `200` on mocked local synthetic route.
- Sanitization: token is synthetic and non-secret; no real Telegram `initData`.

## Decisions needed from Board

- None for `CYBA-697`; previous failed items now have completed linked blockers and passing parent retest.

## Proposed next tasks

- Mark `CYBA-697` done.
- Parent `CYBA-689` owner should proceed using this evidence handoff.

## Risks

- This was local/synthetic QA, not production or staging proof.
- No trace/video captured; screenshots plus JSON notes were sufficient because final retest has no P0/P1 active failure.

## Approval requests

- No approval requested.

## Verification plan

- If parent scope changes, rerun the targeted Vitest pack and `node evidence/customer/cyba-697/cyba-697-customer-portal-regression.mjs`.
- Use final timestamp `20260616T183338Z` as the baseline for this QA handoff.

## What was not done

- No product code fixes were made by QA.
- No production/staging credentials or real customer/payment data were used.
- No cookies/storage state/JWT/passwords or real Telegram `initData` were stored.
