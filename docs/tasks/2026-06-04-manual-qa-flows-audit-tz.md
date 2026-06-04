# Техническое задание: ручной QA-аудит всех пользовательских flow

**Дата:** 2026-06-04  
**Репозиторий:** `Beep206/CyberVPN`  
**Задача для:** Paperclip AI / QA-агенты / нанятые сотрудники  
**Режим работы:** ручное exploratory/manual testing через UI, без исправления кода  
**Итоговый артефакт:** один подробный `.md`-отчёт с найденными ошибками, блокерами, непроверенными зонами и evidence

---

## 1. Краткая постановка задачи

Нужно провести ручную проверку всех доступных пользовательских сценариев в трёх web-поверхностях проекта:

1. **Client frontend** — публичный сайт, приватный пользовательский dashboard, auth, pricing/checkout, subscriptions, wallet, referral, partner, servers, settings, Telegram Mini App routes, если доступны.
2. **Partner portal** — партнёрская поверхность, onboarding, partner codes, markup, clients, earnings, withdrawals, wallet, analytics, disabled/suspended states.
3. **Admin panel** — staff/admin tooling: customers, payments, pricing/plans, subscriptions, wallet operations, withdrawals moderation, partners console, referral/growth, promo/invite, settings, audit/support flows.

Цель — не писать автотесты и не чинить найденные баги. Цель — пройти приложение как живой человек, собрать фактические дефекты и оформить их в структурированный Markdown-документ для дальнейшего анализа и планирования исправлений.

---

## 2. Важное ограничение

Агентам запрещено исправлять source code, менять бизнес-логику, переписывать компоненты, обновлять зависимости, менять `.env`, миграции, API-контракты или тесты.

Разрешено:

- запускать приложение;
- открывать UI в браузере;
- использовать Playwright/Browser tools для ручного управления, screenshots, traces, videos, console/network evidence;
- читать документацию, исходники и роутинг для построения карты flow;
- создавать или обновлять только QA-документы и evidence-файлы в `docs/qa/...`;
- фиксировать баги, вопросы, блокеры, расхождения между docs/UI/API.

---

## 3. Текущий контекст проекта

Проект является npm workspaces монорепозиторием. В корневом `package.json` есть workspaces `admin`, `frontend`, `partner`, `apps/*`, `services/*`, `packages/*`.

Основные web-команды из корня:

```powershell
npm install

npm run dev
npm run dev:admin
npm run dev:partner

npm run build
npm run build:admin
npm run build:partner

npm run lint
npm run lint:admin
npm run lint:partner
```

Ожидаемые dev-порты по текущим scripts:

| Поверхность | Workspace | Команда | URL |
|---|---|---|---|
| Client frontend | `frontend` | `npm run dev` | `http://localhost:9001` |
| Admin panel | `admin` | `npm run dev:admin` | `http://localhost:3001` |
| Partner portal | `partner` | `npm run dev:partner` | `http://localhost:3002` |

Требование Node.js: `>=20`.

---

## 4. Что нужно подготовить до старта

### 4.1. Окружение

Минимальный набор:

- Git доступ к репозиторию.
- Node.js 20+.
- npm.
- Playwright с установленными browser binaries.
- Возможность запускать браузер в headed mode.
- Windows 11 / WSL Ubuntu / Git Bash, потому что в проекте есть bash-скрипты.
- Docker Desktop или WSL Docker, если тестирование идёт на локальной инфраструктуре.
- Доступ к staging/dev API или локальному backend.
- Read-only доступ к логам backend/frontend, если он есть.
- Отдельная test/staging база данных, не production.

Для Windows PowerShell:

```powershell
node -v
npm -v

npm install

npx playwright install
# Для WSL/Linux окружения можно:
# npx playwright install --with-deps
```

Запуск трёх web-поверхностей лучше делать в отдельных терминалах:

```powershell
# Terminal 1
npm run dev

# Terminal 2
npm run dev:admin

# Terminal 3
npm run dev:partner
```

Если используются bash-based conformance/staging scripts, запускать их в WSL или Git Bash, а не в чистом PowerShell.

### 4.2. Доступы и тестовые аккаунты

Нужны отдельные тестовые аккаунты для каждой роли:

#### Client frontend

- anonymous visitor;
- new user without subscription;
- user with active subscription;
- user with expired/cancelled subscription;
- user with wallet balance;
- user with zero wallet balance;
- user with referral code;
- user referred by another user;
- user bound to partner code;
- user with promo/invite code;
- user with failed/declined payment;
- user with generated VPN config/device;
- user with maximum device limit reached;
- user with 2FA/TOTP/passkey state, если включено;
- user with email/password auth;
- user with Telegram OAuth auth, если доступно;
- user with OAuth providers, если dev credentials настроены;
- user for Telegram Mini App flow, если доступен test initData.

#### Partner portal

- user not approved as partner;
- newly approved partner;
- active partner with zero clients;
- active partner with clients;
- partner with existing partner codes;
- partner with custom markup;
- partner with earnings;
- partner with pending withdrawal;
- partner with approved/rejected withdrawal;
- disabled/suspended partner, если состояние реализовано.

#### Admin panel

- super admin;
- support/admin read-only, если RBAC реализован;
- finance/admin payments role, если RBAC реализован;
- growth/partner manager, если RBAC реализован;
- unauthorized user;
- expired session user.

### 4.3. Тестовые интеграции

Для полноценной проверки нужны sandbox/dev-аналоги:

- email inbox / Mailhog / Resend sandbox / SMTP sandbox для OTP, magic links, password reset;
- payment sandbox или mock gateway для success/fail/cancel/refund-like сценариев;
- Telegram test bot / Mini App test environment;
- OAuth dev credentials или явно зафиксировать, что OAuth flows blocked;
- Sentry/Grafana/Prometheus/Loki read-only links, если используются;
- backend admin/test endpoint или seed script для подготовки состояний;
- reset procedure для тестовой базы после мутирующих сценариев.

### 4.4. Evidence-инструменты

Playwright установлен — это хорошо, но для этой задачи он нужен не только как test runner. Нужны:

- browser headed mode;
- screenshots;
- video recording;
- trace recording;
- console logs;
- network logs / HAR, если доступно;
- HTML report, если какие-то проверки всё же запускаются через Playwright test runner;
- единый каталог evidence.

Рекомендуемая структура evidence:

```text
docs/qa/manual-flow-audit/2026-06-04/
  manual-flow-audit-report.md
  evidence/
    client/
      BUG-CLIENT-001/
        screenshot.png
        trace.zip
        console.log
        network.har
        notes.md
    partner/
      BUG-PARTNER-001/
    admin/
      BUG-ADMIN-001/
  raw-notes/
    agent-client.md
    agent-partner.md
    agent-admin.md
```

---

## 5. Как именно тестировать: manual mode

Manual mode означает:

1. Агент открывает реальное приложение в браузере.
2. Переходит по UI, меню, ссылкам, кнопкам, формам, модалкам, mobile navigation, locale switcher, theme switcher.
3. Вводит данные руками или через browser automation как пользователь.
4. Проверяет состояние UI после действия.
5. Проверяет ошибки формы, loading states, disabled states, empty states, permission states.
6. Фиксирует фактический результат.
7. Для бага собирает evidence.
8. Не исправляет код.

Playwright можно использовать как “руки и глаза” агента: browser control, codegen, headed mode, screenshots, traces, video, console/network capture. Но нельзя считать задачу выполненной только потому, что автотесты зелёные.

---

## 6. Метод поиска всех flow

Агенты должны комбинировать четыре подхода.

### 6.1. UI crawl

Пройти приложение через navigation/sidebar/header/footer/buttons/cards/links. Все видимые действия должны быть нажаты минимум один раз, если они не опасны для тестовой среды.

### 6.2. Route discovery

Изучить маршруты в workspaces:

```text
frontend/src/app/**
partner/src/app/**
admin/src/app/**
```

Найти:

- публичные страницы;
- auth pages;
- dashboard pages;
- nested routes;
- dynamic routes;
- error/not-found pages;
- locale routes;
- miniapp routes;
- admin workspaces.

### 6.3. Документация и PRD

Сопоставить UI с проектными документами:

- auth flows;
- pricing/checkout;
- subscriptions;
- wallet;
- referral;
- partner/reseller;
- invite/promo codes;
- admin operations;
- miniapp;
- observability/release evidence.

Если UI и docs расходятся, фиксировать как `DOCS_CONTRACT_MISMATCH` или `PRODUCT_GAP`.

### 6.4. Data-state testing

Проверить не только happy path, но и разные состояния данных:

- пустые списки;
- большие списки;
- отсутствующий API;
- 401/403;
- 404;
- 500;
- slow network;
- expired session;
- insufficient balance;
- invalid promo/referral/partner code;
- duplicate actions;
- double click;
- page refresh after submit;
- browser back/forward;
- mobile viewport.

---

## 7. Scope: Client frontend

### 7.1. Public/marketing

Проверить:

- home page;
- pricing;
- features;
- security;
- help/support;
- status;
- telegram widget;
- legal pages, если доступны;
- header/footer links;
- CTA buttons;
- locale switcher;
- theme/dark/light behavior, если есть;
- responsive layout;
- SEO-critical pages visually load without hydration errors;
- 404/not found.

### 7.2. Auth

Проверить все доступные auth flows:

- registration;
- login;
- logout;
- session restore after refresh;
- expired session handling;
- email/password;
- username/password, если доступно;
- OTP verification;
- magic link, если доступно;
- forgot password / reset password, если доступно;
- Telegram auth, если доступно;
- OAuth providers, если доступны;
- passkey/WebAuthn, если доступно;
- TOTP/2FA, если доступно;
- invalid credentials;
- empty fields;
- malformed email;
- weak password;
- duplicate registration;
- rate-limit/too many attempts, если можно безопасно проверить;
- redirect after login;
- redirect when unauthorized user opens private route.

### 7.3. Dashboard

Проверить:

- dashboard landing;
- sidebar/header navigation;
- user profile;
- settings;
- notifications;
- servers;
- VPN config display/download/copy;
- device management;
- credential regeneration, если доступно;
- usage display;
- subscription status;
- subscription history;
- empty subscription state;
- expired subscription state;
- active subscription state;
- plan upgrade/downgrade/change, если доступно;
- locale behavior in private pages;
- mobile navigation.

### 7.4. Pricing / checkout / payments

Проверить:

- pricing page API/fallback behavior;
- plan selection;
- duration selection: 30/90/180/365, если доступны;
- add-ons: extra device, dedicated IP, если доступны;
- promo code;
- referral/invite code;
- partner code;
- quote calculation;
- wallet partial/full payment;
- zero balance;
- insufficient wallet balance;
- external payment redirect;
- payment success;
- payment cancel/fail;
- payment history update;
- duplicate submit protection;
- refresh/back after checkout;
- loading skeletons;
- error messages.

### 7.5. Referral / invite / partner user-side

Проверить:

- referral status;
- referral code generation/display;
- copy referral code;
- QR/share, если есть;
- recent commissions;
- bind referral code;
- invalid/expired code;
- invite code redeem;
- partner dashboard/bind code inside client UI, если доступно;
- interaction between referral and partner attribution.

### 7.6. Wallet

Проверить:

- wallet balance;
- transactions;
- wallet debit during checkout;
- wallet credit after referral/partner earning, если можно подготовить state;
- withdrawal request, если user-side доступен;
- empty state;
- error state.

### 7.7. Telegram Mini App routes, если доступны в frontend

Проверить:

- `/miniapp/home`;
- `/miniapp/plans`;
- `/miniapp/payments`;
- `/miniapp/devices`;
- `/miniapp/referral`;
- `/miniapp/wallet`;
- `/miniapp/profile`;
- launch without valid Telegram initData;
- launch with test initData;
- back button behavior;
- viewport/safe-area;
- Telegram-specific buttons/deep links.

---

## 8. Scope: Partner portal

Проверить все flow партнёра:

### 8.1. Access and onboarding

- login/access;
- unauthorized state;
- not-a-partner state;
- pending approval state;
- approved partner state;
- disabled/suspended state, если есть;
- empty dashboard.

### 8.2. Partner codes

- create code;
- copy code;
- edit markup;
- disable/enable code;
- invalid markup;
- max markup boundary;
- duplicate code;
- code attribution from client checkout;
- code attribution from registration/bind, если доступно.

### 8.3. Clients

- clients list;
- empty clients list;
- search/filter/sort;
- client details;
- pagination;
- privacy boundaries: partner must not see чужие клиенты.

### 8.4. Earnings and analytics

- earnings overview;
- commission calculation display;
- markup earnings display;
- pending/available balance;
- filters by period;
- export/download, если есть;
- chart empty/loading/error states;
- mismatch between UI and backend values.

### 8.5. Withdrawals

- create withdrawal request;
- minimum amount boundary;
- insufficient balance;
- pending withdrawal;
- rejected withdrawal;
- approved withdrawal;
- form validation;
- duplicate submit.

### 8.6. Cross-surface partner checks

После действий в partner portal проверить:

- что client UI видит корректную partner attribution;
- что checkout учитывает partner code/markup;
- что admin panel видит partner, client, earnings, withdrawal;
- что disabled partner/code больше не работает для новых клиентов.

---

## 9. Scope: Admin panel

### 9.1. Auth/RBAC

- admin login;
- logout;
- expired session;
- unauthorized access;
- role-based hidden/disabled pages, если RBAC есть;
- direct URL access without permission;
- audit/security warning states.

### 9.2. Customers

- customers list;
- search/filter/sort;
- customer 360;
- wallet section;
- payments section;
- referral section;
- partner section;
- notes;
- subscription snapshot;
- empty/error/loading states.

### 9.3. Pricing / plans / subscription templates

- plans console;
- create/edit/disable plan, если UI позволяет;
- validate durations/prices;
- add-ons;
- hidden/public visibility;
- subscription templates;
- pricing API reflection on client frontend.

### 9.4. Payments / wallet operations

- payments console;
- payment details;
- statuses: pending/success/failed/cancelled/refunded-like, если есть;
- manual wallet top-up;
- wallet debit/credit/freeze;
- validation;
- auditability of manual operations.

### 9.5. Withdrawals moderation

- list pending withdrawals;
- approve;
- reject;
- invalid state transition;
- double approve/reject;
- balance update after moderation;
- partner/user notification state, если отображается.

### 9.6. Partners / growth

- promote user to partner;
- partner list;
- partner details;
- partner codes;
- partner earnings;
- disable/enable partner;
- referral signals console;
- suspicious/anti-fraud states, если есть;
- admin visibility into referral/partner attribution.

### 9.7. Promo / invite / support, если доступно

- create promo code;
- expire/disable promo code;
- invite creation;
- invalid code states;
- support-related surfaces;
- admin settings.

---

## 10. Cross-surface сценарии

Обязательно проверить минимум эти end-to-end цепочки:

### 10.1. New client purchase

1. Anonymous user opens pricing.
2. Registers/logs in.
3. Chooses plan.
4. Applies promo/referral/partner code.
5. Gets quote.
6. Pays via sandbox/wallet.
7. Sees active subscription.
8. Payment appears in history.
9. Admin sees customer/payment/subscription.

### 10.2. Partner attribution

1. Admin promotes user to partner.
2. Partner creates partner code.
3. New client uses partner code.
4. Checkout reflects code/markup/attribution.
5. Partner sees client/earning.
6. Admin sees attribution and earning.
7. Wallet/withdrawal state is consistent.

### 10.3. Referral attribution

1. Existing user has referral code.
2. New user registers/redeems/uses code.
3. New user pays.
4. Referrer sees commission/recent entry.
5. Admin sees referral signal/commission.
6. Wallet transaction is correct.

### 10.4. Wallet payment

1. Admin tops up user wallet or test state provides balance.
2. User buys plan using wallet.
3. Balance changes correctly.
4. Payment/transaction history is consistent.
5. Admin customer 360 reflects wallet/payment.

### 10.5. Withdrawal

1. Partner/user has available balance.
2. Withdrawal request created.
3. Admin approves/rejects.
4. Partner/user sees final status.
5. Balances and transactions are consistent.

### 10.6. Auth/session robustness

1. Login.
2. Open protected page.
3. Refresh.
4. Open same page in new tab.
5. Logout.
6. Browser back.
7. Direct URL to private page.
8. Expired/invalid session behavior.

---

## 11. Browser / viewport / locale matrix

Минимальная матрица:

| Category | Required |
|---|---|
| Browser primary | Chromium / Chrome |
| Browser secondary | Firefox |
| Optional | WebKit, Edge |
| Desktop | 1440x900 |
| Laptop | 1366x768 |
| Tablet | 768x1024 |
| Mobile | 390x844 |
| Locale primary | `en-EN` |
| Locale secondary | `ru-RU` |
| RTL smoke | `ar-SA` или `he-IL` или `fa-IR`, если доступно |
| Network | normal + slow 3G smoke for critical flows |

Не нужно прогонять каждую комбинацию для каждого flow. Но critical flows должны иметь минимум desktop + mobile, en + ru, Chromium. UI/layout smoke — на нескольких viewport и минимум одном RTL locale.

---

## 12. Формат фиксации дефектов

Каждый баг должен иметь уникальный ID:

```text
BUG-CLIENT-001
BUG-PARTNER-001
BUG-ADMIN-001
BUG-CROSS-001
```

Формат записи:

```md
### BUG-CLIENT-001: Краткое название

- **Surface:** Client frontend
- **Area:** Checkout / Wallet / Auth / etc.
- **Severity:** P0 / P1 / P2 / P3
- **Status:** Open
- **Environment:** local/staging, commit SHA, browser, viewport, locale
- **User role/state:** active user / partner / admin / etc.
- **Preconditions:** что должно быть подготовлено
- **Steps to reproduce:**
  1. ...
  2. ...
  3. ...
- **Expected result:** ...
- **Actual result:** ...
- **Impact:** почему это важно
- **Evidence:**
  - screenshot: `evidence/client/BUG-CLIENT-001/screenshot.png`
  - trace: `evidence/client/BUG-CLIENT-001/trace.zip`
  - console: `evidence/client/BUG-CLIENT-001/console.log`
  - network: `evidence/client/BUG-CLIENT-001/network.har`
- **Suspected area:** optional, только если очевидно
- **Notes:** optional
```

---

## 13. Severity

| Severity | Meaning |
|---|---|
| P0 / Blocker | Critical user/business flow is impossible: login broken, checkout impossible, admin cannot moderate payouts, data corruption/security issue. |
| P1 / High | Major functionality broken but workaround exists: payment status wrong, partner earnings inconsistent, private page accessible incorrectly, critical mobile layout unusable. |
| P2 / Medium | Non-critical bug: validation message wrong, filter broken, empty state misleading, secondary browser issue. |
| P3 / Low | Cosmetic/content issue: typo, minor spacing, non-blocking visual glitch. |
| Product Gap | UI/docs/product expectation exists, but feature is missing or incomplete. |
| Blocked | Could not test due to missing credentials, missing seed data, unavailable service, unclear requirement. |

---

## 14. Итоговый отчёт

Итоговый документ должен быть создан здесь:

```text
docs/qa/manual-flow-audit/2026-06-04/manual-flow-audit-report.md
```

Структура отчёта:

```md
# Manual Flow Audit Report — CyberVPN

**Date:** 2026-06-04
**Repository:** Beep206/CyberVPN
**Commit SHA:** ...
**Environment:** local/staging
**Agents:** ...
**Scope:** client frontend, partner portal, admin panel
**Mode:** manual UI testing, no source code fixes

## 1. Executive Summary

- Total flows checked:
- Passed:
- Failed:
- Blocked:
- Product gaps:
- P0:
- P1:
- P2:
- P3:

## 2. Environment

- URLs:
  - Client:
  - Partner:
  - Admin:
- Browser/version:
- Viewports:
- Locales:
- Test accounts:
- Backend/API:
- Payment sandbox:
- Email sandbox:
- Telegram test data:

## 3. Coverage Matrix

| Surface | Area | Flow | Status | Bug IDs | Notes |
|---|---|---|---|---|---|
| Client | Auth | Login | Pass/Fail/Blocked | BUG-... | ... |

## 4. Critical Findings

## 5. Client Frontend Findings

## 6. Partner Portal Findings

## 7. Admin Panel Findings

## 8. Cross-surface Findings

## 9. Product Gaps / Requirement Questions

## 10. Blocked / Not Tested

| Area | Reason | Needed to unblock |
|---|---|---|

## 11. Evidence Index

| Bug ID | Evidence path |
|---|---|

## 12. Recommended Fix Order

Не чинить в рамках этой задачи. Только предложить порядок:
1. P0
2. P1
3. High-risk cross-surface consistency bugs
4. UX/data quality
5. Cosmetic
```

---

## 15. Definition of Done

Задача считается выполненной, когда:

- создан итоговый `.md` отчёт;
- заполнена coverage matrix по client, partner, admin;
- каждый найденный баг имеет steps, expected, actual, severity, evidence;
- отдельно перечислены blocked/not tested области;
- отдельно перечислены product gaps и docs/code/UI mismatches;
- critical cross-surface flows проверены минимум один раз;
- отчёт не содержит секретов, токенов, cookies, private auth state;
- не внесены изменения в application source code;
- если был создан PR, он содержит только QA-документы и evidence.

---

## 16. Распределение между агентами Paperclip AI

Рекомендуемая схема:

### Agent 1 — QA Lead / Flow Mapper

- строит карту routes и flow;
- распределяет задачи;
- контролирует coverage matrix;
- объединяет отчёт.

### Agent 2 — Client Frontend QA

- public site;
- auth;
- dashboard;
- pricing/checkout;
- wallet;
- referral;
- miniapp.

### Agent 3 — Partner Portal QA

- partner onboarding/access;
- partner codes;
- clients;
- earnings;
- withdrawals;
- cross-check with client/admin.

### Agent 4 — Admin Panel QA

- auth/RBAC;
- customer 360;
- pricing/plans;
- payments/wallet;
- withdrawals moderation;
- partners/referrals.

### Agent 5 — Evidence Curator / Reproduction Validator

- проверяет воспроизводимость багов;
- нормализует severity;
- собирает screenshots/traces/logs;
- удаляет секреты из evidence;
- финализирует Markdown.

---

## 17. Правила безопасности evidence

Запрещено коммитить:

- real passwords;
- auth cookies;
- JWT;
- refresh tokens;
- Telegram initData с реальными пользователями;
- payment provider secrets;
- private customer data;
- `.env`;
- Playwright storage state files из `playwright/.auth`.

Если trace/video содержит токены или персональные данные, его нужно либо не прикладывать, либо предварительно санитизировать. В отчёте можно указать, что evidence хранится вне репозитория.

---

## 18. Короткий prompt для Paperclip AI

Скопировать в Paperclip AI как основную задачу:

```text
You are QA agents working in repository Beep206/CyberVPN.

Task: perform a full manual exploratory QA audit of client frontend, partner portal, and admin panel.

Important:
- Do not fix source code.
- Do not change business logic.
- Do not update dependencies.
- Do not create implementation PRs.
- Use browser/manual UI interaction as a human user.
- Playwright may be used only for browser control, screenshots, traces, videos, console/network evidence, and optional codegen notes.
- Build a route/flow map from UI, source routes, and docs.
- Test happy paths, negative paths, edge cases, permission states, empty states, loading/error states, mobile viewports, locales, and cross-surface consistency.
- Record every bug in Markdown with steps, expected result, actual result, severity, environment, user role/state, and evidence path.
- Create final report at docs/qa/manual-flow-audit/2026-06-04/manual-flow-audit-report.md.
- Commit only QA docs/evidence. Do not modify application code.

Surfaces:
1. Client frontend: public pages, auth, dashboard, pricing/checkout, subscriptions, wallet, referral, partner, servers/devices/config, settings, miniapp routes if available.
2. Partner portal: partner access, onboarding, codes, markup, clients, earnings, withdrawals, disabled/suspended states.
3. Admin panel: auth/RBAC, customers, pricing/plans, payments, wallet ops, withdrawals moderation, partners, referrals, promo/invite, settings.

Definition of Done:
- coverage matrix completed;
- all found bugs documented;
- blocked/not tested areas documented;
- product gaps documented;
- evidence collected;
- no source code fixes.
```

---

## 19. Быстрый ответ на вопрос “Playwright установлен — что ещё нужно?”

Playwright — это только инструмент. Для качественной ручной проверки ещё нужны:

1. staging/local environment with backend and database;
2. seeded test data for all roles/states;
3. test accounts for client, partner, admin;
4. payment sandbox or mock payment flow;
5. email sandbox for OTP/magic links/password reset;
6. Telegram test environment for Mini App/Bot flows;
7. OAuth dev credentials or explicit blocked status;
8. browser binaries installed with `npx playwright install`;
9. evidence convention: screenshots, traces, videos, console, network;
10. final Markdown template and severity rules;
11. read-only logs/observability access;
12. reset plan for mutated test data;
13. strict rule: no fixes in this task, only report.
