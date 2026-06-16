# CYBA-697 Evidence Index

## Executive summary

Финальная customer portal regression QA для `CYBA-697` завершена после закрытия child blockers `CYBA-710` и `CYBA-711`.

Финальный parent retest выполнен 2026-06-16 на локальном Next.js frontend `http://127.0.0.1:9001`, locale `ru-RU`, viewport `1440x1000`, browser `chromium`, user role/state: synthetic authenticated customer, viewer role, mocked local `/api/**` responses.

Итог финального retest: 20 checks, 20 PASS, 0 FAIL. Предыдущие failures закрыты:

- `header-currency-symbol-not-raw-code`: PASS, customer header показывает `₽` и не показывает standalone raw `RUB` в closed selector.
- `telegram-expired-synthetic-link-fails`: PASS, expired synthetic magic link показывает `Auth.telegram.botLinkExpired`: `Запрос на вход через Telegram истёк. Запустите вход заново на сайте.`

Context7 docs checked: Playwright via ctx7 fallback `/microsoft/playwright.dev` and `/microsoft/playwright`; Context7 MCP quota exceeded. Manual UI/business-flow findings otherwise N/A.

## Evidence set

- Runner: `evidence/customer/cyba-697/cyba-697-customer-portal-regression.mjs`
- Final machine-readable notes: `evidence/customer/cyba-697/notes/cyba-697-customer-portal-regression__20260616T183338Z.json`
- Final screenshots: `evidence/customer/cyba-697/screenshots/*20260616T183338Z.png`
- Screenshot count in final run: 13
- Historical failing run retained for audit: `evidence/customer/cyba-697/notes/cyba-697-customer-portal-regression__20260616T170924Z.json`
- Sensitive artifact review: screenshots and JSON use synthetic account data only. No JWT, cookies, refresh tokens, passwords, `.env` values, production PII, payment secrets, or real Telegram `initData` were stored.

## Screenshot index

| Route/state | Final artifact |
| --- | --- |
| `/ru-RU/settings` overview | `evidence/customer/cyba-697/screenshots/CYBA-697__customer-portal__synthetic__ru-RU__desktop-1440__settings-overview__20260616T183338Z.png` |
| `/ru-RU/settings` user menu open | `evidence/customer/cyba-697/screenshots/CYBA-697__customer-portal__synthetic__ru-RU__desktop-1440__settings-user-menu-open__20260616T183338Z.png` |
| `/ru-RU/settings/security` | `evidence/customer/cyba-697/screenshots/CYBA-697__customer-portal__synthetic__ru-RU__desktop-1440__settings-security-route__20260616T183338Z.png` |
| `/ru-RU/settings/delete-account` form | `evidence/customer/cyba-697/screenshots/CYBA-697__customer-portal__synthetic__ru-RU__desktop-1440__settings-delete-account-form__20260616T183338Z.png` |
| `/ru-RU/settings/delete-account` success | `evidence/customer/cyba-697/screenshots/CYBA-697__customer-portal__synthetic__ru-RU__desktop-1440__settings-delete-account-success__20260616T183338Z.png` |
| `/ru-RU/dashboard` | `evidence/customer/cyba-697/screenshots/CYBA-697__customer-portal__synthetic__ru-RU__desktop-1440__dashboard__20260616T183338Z.png` |
| `/ru-RU/servers` | `evidence/customer/cyba-697/screenshots/CYBA-697__customer-portal__synthetic__ru-RU__desktop-1440__servers__20260616T183338Z.png` |
| `/ru-RU/subscriptions` default | `evidence/customer/cyba-697/screenshots/CYBA-697__customer-portal__synthetic__ru-RU__desktop-1440__subscriptions-default__20260616T183338Z.png` |
| `/ru-RU/subscriptions` filtered | `evidence/customer/cyba-697/screenshots/CYBA-697__customer-portal__synthetic__ru-RU__desktop-1440__subscriptions-filtered-quarterly-devices-traffic__20260616T183338Z.png` |
| `/ru-RU/telegram-link?magic=fresh-magic-cyba697` | `evidence/customer/cyba-697/screenshots/CYBA-697__customer-portal__synthetic__ru-RU__desktop-1440__telegram-fresh-synthetic-link-dashboard__20260616T183338Z.png` |
| `/ru-RU/telegram-link?magic=expired-magic-cyba697` | `evidence/customer/cyba-697/screenshots/CYBA-697__customer-portal__synthetic__ru-RU__desktop-1440__telegram-expired-synthetic-link-error__20260616T183338Z.png` |
| Sign out after click | `evidence/customer/cyba-697/screenshots/CYBA-697__customer-portal__synthetic__ru-RU__desktop-1440__header-sign-out-after-click__20260616T183338Z.png` |
| Protected dashboard after sign out | `evidence/customer/cyba-697/screenshots/CYBA-697__customer-portal__synthetic__ru-RU__desktop-1440__protected-dashboard-after-sign-out-login__20260616T183338Z.png` |

## Test command summaries

- Playwright evidence runner:
  - Command: `node evidence/customer/cyba-697/cyba-697-customer-portal-regression.mjs`
  - Final result summary: 20 checks, 20 PASS, 0 FAIL.
  - Final note: `evidence/customer/cyba-697/notes/cyba-697-customer-portal-regression__20260616T183338Z.json`
- Targeted Vitest regression pack:
  - Command: `npm run test:run -w frontend -- src/shared/lib/__tests__/public-account-id.test.ts src/widgets/settings-cabinet/__tests__/settings-cabinet-dashboard.test.tsx src/widgets/customer-cabinet/__tests__/customer-cabinet-dashboard.test.tsx src/widgets/server-access/__tests__/server-access-dashboard.test.tsx src/widgets/subscription-cabinet/__tests__/subscription-cabinet-dashboard.test.tsx 'src/app/[locale]/(auth)/telegram-link/__tests__/telegram-link-client.test.tsx' src/features/header/__tests__/user-menu.test.tsx src/features/currency-selector/__tests__/currency-preference.test.tsx src/features/auth/components/__tests__/AuthGuard.test.tsx frontend/src/widgets/__tests__/terminal-header-controls.test.tsx`
  - Result summary: 9 test files passed, 74 tests passed, duration 21.82s.

## Console and network observations

- All customer API calls in the final evidence run were mocked local synthetic responses.
- Telegram synthetic network proof:
  - `GET /api/v1/oauth/telegram/magic-link/fresh-magic-cyba697/status` returned `200` and redirected to `/ru-RU/dashboard`.
  - `GET /api/v1/oauth/telegram/magic-link/expired-magic-cyba697/status` returned `200` with expired state and UI rendered the expired-specific copy.
- Console observations in final run:
  - Next.js dev-only cache/prerender warnings for dynamic routes.
  - WebGL `ReadPixels` performance warnings.
  - Expected `401 Unauthorized` resource logs after sign out and protected-route validation.
  - No new blocking console finding was raised for the final `CYBA-697` matrix.

## Decisions needed from Board

- None for `CYBA-697`. The two prior blockers are done and parent retest passed.

## Proposed next tasks

- Move `CYBA-697` to `done`.
- Wake/unblock the parent `CYBA-689` owner to consume this handoff and proceed with the broader customer portal gate.

## Risks

- Residual risk is limited to local dev-server behavior and synthetic mocks; production/staging parity was not tested in this heartbeat.
- Trace/video was not captured because final failures are resolved and screenshot + JSON + console/network notes are sufficient for this gate.

## Approval requests

- No Board approval requested for `CYBA-697`; QA evidence is complete on synthetic/local data.

## Verification plan

- For any later regression in `CYBA-689`, rerun:
  - `npm run test:run -w frontend -- src/shared/lib/__tests__/public-account-id.test.ts src/widgets/settings-cabinet/__tests__/settings-cabinet-dashboard.test.tsx src/widgets/customer-cabinet/__tests__/customer-cabinet-dashboard.test.tsx src/widgets/server-access/__tests__/server-access-dashboard.test.tsx src/widgets/subscription-cabinet/__tests__/subscription-cabinet-dashboard.test.tsx 'src/app/[locale]/(auth)/telegram-link/__tests__/telegram-link-client.test.tsx' src/features/header/__tests__/user-menu.test.tsx src/features/currency-selector/__tests__/currency-preference.test.tsx src/features/auth/components/__tests__/AuthGuard.test.tsx frontend/src/widgets/__tests__/terminal-header-controls.test.tsx`
  - `node evidence/customer/cyba-697/cyba-697-customer-portal-regression.mjs`

## What was not done

- QA did not change product source code, business logic, dependencies, `.env`, API contracts, migrations, or production infrastructure.
- No production testing, payment capture, destructive security testing, real customer/payment data, cookies/storage state/JWT/passwords, or real Telegram `initData` were used.
- No full workspace build/typecheck was run; targeted regression tests plus Playwright evidence were used for this customer portal QA gate.
