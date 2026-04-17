# CyberVPN: полное досье проекта для разработки партнёрской программы

**Дата:** 2026-04-16  
**Статус:** рабочий discovery-документ  
**Назначение:** собрать в одном месте фактическую информацию о проекте CyberVPN, которая нужна для проектирования и разработки партнёрской программы, а также связанной тарифной, реферальной и payout-логики.

---

## 1. Что это за документ

Этот документ не является PRD и не задаёт окончательное решение по партнёрской программе.  
Его задача:

- собрать подтверждённые факты по проекту;
- показать, какие каналы продукта уже существуют;
- зафиксировать текущую тарифную и growth-инфраструктуру;
- отделить уже реализованное от частично реализованного и от устаревшей документации;
- дать базу для следующего этапа: проектирования партнёрской программы.

Базовый принцип документа:

- **Факт** = подтверждается кодом, моделями данных, текущими API, UI или миграциями;
- **Частично** = интерфейс или документация есть, но реализация неполная или расходится между слоями;
- **Legacy / устаревшее** = встречается в старых docs, но уже не выглядит канонической текущей моделью.

---

## 2. Executive Summary

### 2.1 Что представляет собой проект

CyberVPN — это не один сайт, а полноценная multi-channel платформа для VPN-бизнеса:

- публичный маркетинговый frontend;
- приватный пользовательский web-dashboard;
- Telegram Mini App;
- Telegram Bot;
- мобильное приложение на Flutter;
- backend API на FastAPI;
- admin panel;
- task worker для фоновой обработки;
- Helix stack для desktop-first transport/runtime сценариев.

### 2.2 Что уже есть для партнёрской программы

По состоянию на **16 апреля 2026 года** в проекте уже существуют:

- канонический backend-owned каталог тарифов;
- SKU-модель `plan_code + duration_days`;
- add-ons (`extra_device`, `dedicated_ip`);
- unified checkout с промокодом, wallet и partner markup;
- invite-коды, генерируемые из `invite_bundle` плана;
- referral commission с конфигурируемой длительностью атрибуции;
- partner-коды с наценкой;
- partner earnings + wallet credits + withdrawals;
- admin-поверхности для каталогов, кошельков, выплат, партнёров и referral-сигналов;
- пользовательские UI для referral / partner / wallet в web и mini app.

### 2.3 Ключевой вывод

Для разработки партнёрской программы **не нужно начинать с нуля**.  
В проекте уже есть почти весь фундамент для двух разных моделей:

- **Referral / affiliate**: пользователь приводит пользователя и получает комиссию;
- **Partner / reseller**: партнёр ведёт клиента через свой код, может задавать markup и зарабатывать и на markup, и на комиссии.

Главная задача следующего этапа не в создании инфраструктуры с нуля, а в:

- канонизации бизнес-правил;
- устранении противоречий между docs и кодом;
- выравнивании каналов продаж и оплаты;
- добавлении отчётности, антифрода и payout-policy.

---

## 3. Проект в целом

## 3.1 Монорепозиторий

Структура проекта:

- `frontend/` — пользовательский Next.js frontend;
- `admin/` — отдельная Next.js admin panel;
- `backend/` — FastAPI backend API;
- `cybervpn_mobile/` — Flutter mobile app;
- `services/telegram-bot/` — Telegram bot;
- `services/task-worker/` — фоновые задачи;
- `services/helix-adapter/`, `services/helix-node/` — Helix control/runtime слой;
- `apps/desktop-client/` — desktop client;
- `infra/` — локальная и dev-инфраструктура;
- `docs/` — проектные документы, планы, runbooks, audits.

Корневой `package.json` подтверждает npm workspaces для `admin`, `frontend`, `apps/*`, `services/*`, `packages/*`.

## 3.2 Основной стек

Подтверждено кодом:

- frontend/admin: `Next.js 16.2.x`, `React 19.2.x`, `TypeScript 5.9.x`, `Tailwind CSS 4`, `TanStack Query`, `Three.js`;
- backend: `Python 3.13`, `FastAPI 0.135.3`, `Pydantic 2.12.5`, `SQLAlchemy 2`, `Alembic`;
- Telegram bot: `aiogram 3`, `httpx`, `Redis`, `Fluent`;
- mobile: Flutter feature-монолит с отдельными модулями `auth`, `subscription`, `vpn`, `wallet`, `referral`, `partner`, `profile`, `settings`, `notifications`, `servers`;
- infra: `PostgreSQL 17.7`, `Valkey 8.1`, `Remnawave 2.7.4`, `Prometheus`, `Grafana`, `Loki`, `Tempo`, `OTel`.

## 3.3 Локализация

Пользовательский frontend работает на **38 локалях** с RTL-поддержкой для части языков.  
Admin panel на текущем слое локализации ограничена `ru-RU` и `en-EN`.

Практический вывод для партнёрской программы:

- публичные тексты партнёрки и тарифов должны сразу проектироваться как мультиязычные;
- admin tooling может быть менее глобальным на первом релизе;
- Telegram bot уже имеет много локалей в Fluent-структуре и является сильным каналом для growth.

---

## 4. Пользовательские каналы и поверхности продукта

## 4.1 Публичный web frontend

Подтверждено кодом:

- публичная pricing-страница `/pricing`;
- контентные страницы `/features`, `/security`, `/help`, `/status`, `/telegram-widget`;
- pricing page получает данные из backend API и имеет fallback-каталог, если API недоступен.

Практическое значение:

- тарифная витрина уже существует;
- будущая партнёрская программа может получить отдельный публичный landing, не ломая текущую архитектуру;
- pricing-каталог уже рассчитан на канальную отдачу через API.

## 4.2 Приватный web-dashboard

Подтверждено маршрутизацией и компонентами:

- `/subscriptions`
- `/referral`
- `/partner`
- `/wallet`
- `/payment-history`
- `/servers`
- `/settings`

Что уже есть по growth/monetization:

- referral dashboard с кодом, статистикой и recent commissions;
- partner dashboard с bind по коду, собственными partner-кодами и earnings;
- subscriptions section с планами, trial, кодами и rewards;
- wallet и payment history.

Важно:

- часть subscription UI ещё опирается на несовершенно выровненные API-ответы; в коде прямо есть комментарии, что текущий endpoint возвращает template-данные, а не полноценную user subscription history.

## 4.3 Telegram Mini App

Подтверждено маршрутами:

- `/miniapp/home`
- `/miniapp/plans`
- `/miniapp/payments`
- `/miniapp/devices`
- `/miniapp/referral`
- `/miniapp/wallet`
- `/miniapp/profile`

Что важно для партнёрки:

- mini app уже умеет работать с планами, quote/checkout, add-ons, trial, referral, wallet;
- referral page уже показывает код, QR, stats, recent commissions;
- partner-функции частично встроены в `profile` через partner dashboard / bind code;
- mini app является сильным growth-каналом, потому что живёт рядом с Telegram Bot.

## 4.4 Telegram Bot

Подтверждено README и структурой handlers:

- `/start`
- меню и навигация;
- подписки и выбор плана;
- payment flow;
- config delivery;
- referral;
- promocode;
- support;
- trial;
- админские handlers для планов, промо, рефералок, referral settings, payment gateways, users, broadcasts, stats.

Практическое значение:

- bot уже не просто support-канал, а реальный sales/activation канал;
- бот должен учитываться в дизайне партнёрской программы наравне с web/mini app;
- deep-link / code-based acquisition здесь особенно важны.

## 4.5 Mobile app

Подтверждено деревом `cybervpn_mobile/lib/features`:

- `subscription`
- `vpn`
- `wallet`
- `referral`
- `partner`
- `profile`
- `settings`
- `notifications`
- `servers`
- `onboarding`

Практический вывод:

- mobile app уже заложен как полноценный будущий канал продажи и удержания;
- партнёрская программа не должна проектироваться только под web/Telegram;
- доменные сущности referral/partner/wallet уже учитываются в мобильной архитектуре.

## 4.6 Admin panel

Подтверждено кодом:

- commerce workspace:
  - plans console
  - subscription templates
  - payments console
  - wallet operations
  - withdrawals moderation
- growth workspace:
  - partners console
  - referral signals console
- customers:
  - customer 360 card с wallet, payments, referral, partner, notes, subscription snapshot.

Практический вывод:

- у проекта уже есть staff tooling для поддержки партнёрки;
- для MVP партнёрской программы не обязательно отдельно проектировать новую админку с нуля;
- скорее нужно расширять существующие growth/commerce/customers-поверхности.

---

## 5. Канонический тарифный каталог

## 5.1 Что сейчас является source of truth

На дату документа наиболее канонический источник по тарифам — backend seed:

- `backend/src/application/services/pricing_catalog_seed.py`
- миграция `20260416_pricing_catalog`
- API `/api/v1/plans` и `/api/v1/addons/catalog`

Это важнее старых текстовых описаний, потому что именно этот слой:

- определяет фактические `plan_code`;
- задаёт цены;
- задаёт каналы продажи;
- задаёт invite-bundle;
- задаёт add-ons.

## 5.2 Текущие plan families

### Публичные планы

| Plan code | Display name | Devices | Traffic | Modes | Pool | Dedicated IP | Support |
|---|---|---:|---|---|---|---|---|
| `basic` | Basic | 2 | Unlimited / fair use | `standard` | `shared` | add-on | standard |
| `plus` | Plus | 5 | Unlimited / fair use | `standard`, `stealth` | `shared_plus` | add-on | standard |
| `pro` | Pro | 10 | Unlimited / fair use | `standard`, `stealth`, `manual_config` | `premium_shared` | add-on | priority |
| `max` | Max | 15 | Unlimited / fair use | `standard`, `stealth`, `manual_config`, `dedicated_ip` | `premium`, `exclusive` | 1 included | vip |

### Скрытые планы

| Plan code | Display name | Назначение | Visibility |
|---|---|---|---|
| `start` | Start | скрытый entry-tier | hidden |
| `test` | Test | скрытый экспериментальный premium | hidden |
| `development` | Development | внутренний unrestricted | hidden |

## 5.3 Периоды и SKU

Стандартные длительности:

- `30`
- `90`
- `180`
- `365`

Каждый plan family существует как отдельный SKU:

- `basic_30`, `basic_90`, `basic_180`, `basic_365`
- `plus_30`, `plus_90`, `plus_180`, `plus_365`
- `pro_30`, `pro_90`, `pro_180`, `pro_365`
- `max_30`, `max_90`, `max_180`, `max_365`
- плюс hidden SKU для `start`, `test`, `development`

Всего seed-тестом подтверждено:

- **28 plan SKU**
- **7 plan families**
- **4 периода**

## 5.4 Цены в seed-каталоге

### Публичные цены, USD

| Plan | 30 days | 90 days | 180 days | 365 days |
|---|---:|---:|---:|---:|
| Basic | 5.99 | 14.99 | 27.99 | 49.99 |
| Plus | 8.99 | 22.99 | 39.99 | 79.00 |
| Pro | 11.99 | 29.99 | 49.99 | 89.00 |
| Max | 14.99 | 36.99 | 59.99 | 99.00 |

### Hidden / internal

| Plan | 30 days | 90 days | 180 days | 365 days |
|---|---:|---:|---:|---:|
| Start | 4.99 | 11.99 | 21.99 | 39.99 |
| Test | 14.99 | 36.99 | 59.99 | 99.00 |
| Development | 0.00 | 0.00 | 0.00 | 0.00 |

## 5.5 Invite bundles в тарифах

Invite logic уже сидит прямо в плане, а не только в глобальном rule-set.

Текущая матрица:

- `start_365` -> `1` invite, `7` friend days, expiry `30`
- `basic_365` -> `1` invite, `7` friend days, expiry `30`
- `plus_180` -> `1` invite, `7` friend days, expiry `30`
- `plus_365` -> `2` invites, `14` friend days, expiry `60`
- `pro_180` -> `1` invite, `14` friend days, expiry `60`
- `pro_365` -> `2` invites, `14` friend days, expiry `60`
- `max_180` -> `1` invite, `14` friend days, expiry `60`
- `max_365` -> `3` invites, `14` friend days, expiry `60`
- `test_365` -> `3` invites, `14` friend days, expiry `60`

Практический вывод:

- invite bundle уже является частью экономической модели SKU;
- annual и semi-annual планы уже выделены как growth-driven продукты;
- это напрямую влияет на дизайн партнёрки, потому что invite и affiliate не должны конфликтовать.

## 5.6 Add-ons v1

Текущий каталог add-ons:

| Code | Название | Цена USD | Стекуемость | Особенности |
|---|---|---:|---|---|
| `extra_device` | +1 device | 6.00 | да | увеличивает `device_limit` на 1 |
| `dedicated_ip` | Dedicated IP | 24.00 | да | требует `location_code`, увеличивает `dedicated_ip_count` |

Лимиты `extra_device` по планам:

- `start`: +1
- `basic`: +2
- `plus`: +3
- `pro`: +5
- `max`: +10
- `test`: +10
- `development`: 0

Практический вывод:

- проект уже поддерживает upsell beyond base plan;
- партнёрская программа должна учитывать не только базовый plan sale, но и add-on sale;
- желательно заранее решить, начисляется ли комиссия на add-ons и на какую базу.

---

## 6. Текущая монетизация и growth-механики

## 6.1 Unified checkout

В backend уже реализован единый quote/commit flow.

Логика расчёта:

1. базовая цена плана;
2. плюс add-ons;
3. плюс partner markup;
4. минус promo;
5. минус wallet;
6. остаток отправляется в gateway.

Что важно:

- entitlement snapshot считается сразу в quote;
- payment сохраняет `addons_snapshot` и `entitlements_snapshot`;
- `commission_base_amount` считается от базовой цены плана;
- post-payment processing запускает invites, referral commission, partner earning, wallet debit.

Практический вывод:

- экономика партнёрки уже завязана на существующий checkout;
- при проектировании новой партнёрской программы критично не сломать этот порядок вычислений;
- отдельно нужно решить, на что именно начислять выплаты: на base, displayed, gateway или net revenue.

## 6.2 Invite system

Фактически реализовано:

- `invite_codes` table;
- генерация invite-кодов после оплаты по `plan.invite_bundle`;
- redeem invite endpoint;
- admin create invite endpoint;
- ownership, expiry, source payment, used_by tracking.

Состояние:

- **реализовано в backend**;
- **документировано шире, чем реализовано**;
- старый глобальный `invite.plan_rules` ещё существует в config и документах как legacy.

## 6.3 Referral system

Фактически реализовано:

- у `mobile_users` есть `referral_code` и `referred_by_user_id`;
- API:
  - `/referral/status`
  - `/referral/code`
  - `/referral/stats`
  - `/referral/recent`
- ledger `referral_commissions`;
- credit в wallet при успешной комиссии.

Системные дефолты через `system_config`:

- `referral.enabled = true`
- `referral.commission_rate = 0.10`
- `referral.duration_mode = indefinite`

Поддерживаемые режимы атрибуции:

- `indefinite`
- `time_limited`
- `payment_count`
- `first_payment_only`

Практический вывод:

- простая affiliate/referral программа уже почти существует;
- для полноценной партнёрки нужно только канонизировать бизнес-правила и аналитику.

## 6.4 Partner / reseller system

Фактически реализовано:

- `mobile_users.partner_user_id`
- `mobile_users.is_partner`
- `partner_codes`
- `partner_earnings`
- bind пользователя к партнёру по коду;
- создание партнёром собственных кодов;
- configurable markup;
- tier-based commission;
- dashboard с кодами, клиентами и earnings;
- admin promote partner.

Дефолтные системные настройки:

- `partner.max_markup_pct = 300`
- `partner.base_commission_pct = 10`
- `partner.tiers = [{ min_clients: 0, commission_pct: 20 }]`

Важно:

- в текущем коде фактический расчёт earning использует `partner.tiers`;
- `partner.base_commission_pct` присутствует в config, но в показанном расчёте не является основной величиной;
- это означает, что partner economy уже работает, но конфигурация требует канонизации.

## 6.5 Wallet и выплаты

Фактически реализовано:

- `wallets`
- `wallet_transactions`
- `withdrawal_requests`
- credit/debit/frozen amounts;
- referral commission и partner earning начисляются в wallet;
- пользователь может запросить withdrawal;
- admin approves/rejects withdrawal;
- admin может делать manual top-up.

Системные дефолты:

- minimum withdrawal: `5.0 USD`
- withdrawals enabled: `true`
- withdrawal fee: `0%`

Практический вывод:

- payout foundation для партнёрской программы уже есть;
- для production-grade партнёрки нужно скорее добавить правила удержания, холд периода, anti-fraud и refund clawback, чем переписывать wallet с нуля.

---

## 7. Платёжные каналы: факт против ожиданий

| Канал | Где виден | Реальный статус на 2026-04-16 |
|---|---|---|
| CryptoBot | backend checkout, webhooks, Telegram bot | **реально реализован и каноничен** |
| Wallet | backend checkout | **реально участвует в расчёте и списании** |
| YooKassa | docs, bot config, bot services | **частично: бот и docs знают о канале, но канонический backend checkout сейчас не вокруг него** |
| Telegram Stars | bot config/services/keyboards | **частично: есть бот-слой, но не текущий канон backend checkout** |
| Stripe | enum/docs/bot toggles | **скорее planned / not canonical** |

Критически важный факт:

- `backend` для Telegram bot checkout на текущем каноническом endpoint прямо ограничивает `payment_method` значением `cryptobot`.

Практический вывод:

- при разработке партнёрской программы нельзя предполагать, что все payment methods одинаково готовы;
- payout и attribution logic лучше проектировать payment-provider-agnostic, но rollout делать вокруг реально работающих каналов;
- сегодня safest baseline — `CryptoBot + Wallet`.

---

## 8. Trial: текущее состояние и противоречия

Код подтверждает:

- trial хранится в `mobile_users.trial_activated_at` и `trial_expires_at`;
- backend use case даёт **7 дней**;
- entitlements для trial:
  - `1` device
  - `fair_use`
  - `standard`
  - `shared`
  - no dedicated IP
- bot README также описывает canonical trial как `7 days, 1 device, shared-only access`.

Но в старых docs встречаются другие формулировки:

- `2 дня / 2 ГБ`
- другие marketing-вариации trial-модели

Практический вывод:

- для партнёрской программы и тарифной воронки trial должен быть зафиксирован как единая каноническая сущность;
- на дату документа канонический operational baseline выглядит как **7-дневный trial**, а старые упоминания 2-day trial нужно считать legacy.

---

## 9. Основные сущности данных, важные для партнёрской программы

## 9.1 Пользователь

`mobile_users`

Ключевые поля:

- `id`
- `email`
- `telegram_id`
- `telegram_username`
- `remnawave_uuid`
- `subscription_url`
- `referral_code`
- `referred_by_user_id`
- `partner_user_id`
- `is_partner`
- `partner_promoted_at`
- `trial_activated_at`
- `trial_expires_at`

## 9.2 Каталог

`subscription_plans`

Ключевые поля:

- `plan_code`
- `display_name`
- `catalog_visibility`
- `duration_days`
- `device_limit`
- `price_usd`
- `sale_channels`
- `traffic_policy`
- `connection_modes`
- `server_pool`
- `support_sla`
- `dedicated_ip`
- `invite_bundle`
- `trial_eligible`
- `features`

## 9.3 Add-ons

- `plan_addons`
- `subscription_addons`

## 9.4 Платежи и скидки

- `payments`
- `promo_codes`
- `promo_code_usages`

## 9.5 Growth-объекты

- `invite_codes`
- `referral_commissions`
- `partner_codes`
- `partner_earnings`

## 9.6 Wallet / payout

- `wallets`
- `wallet_transactions`
- `withdrawal_requests`

## 9.7 Системные настройки

`system_config`

Ключи, важные для будущей партнёрки:

- `invite.plan_rules` (legacy)
- `invite.default_expiry_days`
- `referral.enabled`
- `referral.commission_rate`
- `referral.duration_mode`
- `partner.max_markup_pct`
- `partner.base_commission_pct`
- `partner.tiers`
- `wallet.min_withdrawal`
- `wallet.withdrawal_enabled`
- `wallet.withdrawal_fee_pct`

---

## 10. API и технические точки интеграции

## 10.1 Тарифы и add-ons

- `GET /api/v1/plans`
- `GET /api/v1/plans/admin`
- `POST /api/v1/plans`
- `PUT /api/v1/plans/{uuid}`
- `GET /api/v1/addons/catalog`
- `GET /api/v1/addons`
- `POST /api/v1/addons`
- `PUT /api/v1/addons/{addon_id}`

## 10.2 Checkout и payments

- `POST /api/v1/payments/checkout/quote`
- `POST /api/v1/payments/checkout/commit`
- `GET /api/v1/payments/history`
- `POST /api/v1/webhooks/cryptobot`

## 10.3 Subscriptions

- `GET /api/v1/subscriptions/current/entitlements`
- `POST /api/v1/subscriptions/current/upgrade/quote`
- `POST /api/v1/subscriptions/current/upgrade`
- `POST /api/v1/subscriptions/current/addons/quote`
- `POST /api/v1/subscriptions/current/addons`

## 10.4 Referral / invite / partner / wallet

- `GET /api/v1/referral/status`
- `GET /api/v1/referral/code`
- `GET /api/v1/referral/stats`
- `GET /api/v1/referral/recent`
- `POST /api/v1/invites/redeem`
- `GET /api/v1/invites/my`
- `POST /api/v1/partner/codes`
- `GET /api/v1/partner/codes`
- `PUT /api/v1/partner/codes/{code_id}`
- `GET /api/v1/partner/dashboard`
- `GET /api/v1/partner/earnings`
- `POST /api/v1/partner/bind`
- `GET /api/v1/wallet`
- `GET /api/v1/wallet/transactions`
- `POST /api/v1/wallet/withdraw`
- `GET /api/v1/wallet/withdrawals`

## 10.5 Admin

- `POST /api/v1/admin/partners/promote`
- `POST /api/v1/admin/invite-codes`
- `POST /api/v1/admin/promo-codes`
- `POST /api/v1/admin/wallets/{user_id}/topup`
- `GET /api/v1/admin/wallets/{user_id}`
- `GET /api/v1/admin/withdrawals`
- `PUT /api/v1/admin/withdrawals/{withdrawal_id}/approve`
- `PUT /api/v1/admin/withdrawals/{withdrawal_id}/reject`

---

## 11. Главные несоответствия и риски

## 11.1 Trial-документация расходится с кодом

- код и bot baseline говорят про 7-day trial;
- старые docs местами говорят про 2-day / 2GB trial.

## 11.2 Платёжные каналы не выровнены между слоями

- бот и docs знают про YooKassa / Telegram Stars;
- канонический backend checkout сейчас завязан на CryptoBot;
- Stripe виден в enum/docs, но не выглядит текущим operational baseline.

## 11.3 Legacy и новый pricing-standard сосуществуют

- старые docs оперируют `basic / pro / ultra / cyber`;
- новый backend seed живёт в модели `start / basic / plus / pro / max / test / development`.

## 11.4 Некоторые пользовательские UI ещё частично выровнены

- часть subscription UI в web/miniapp явно помечена комментариями о несовпадении endpoint-ов и фактической user subscription model;
- часть miniapp-copy по partner-программе всё ещё звучит как “contact support”, хотя partner API и dashboards уже есть.

## 11.5 Конфигурация partner-commission требует канонизации

- есть и `partner.base_commission_pct`, и `partner.tiers`;
- текущий расчёт earning опирается на tiers;
- это нужно явно зафиксировать до старта новой партнёрской программы.

---

## 12. Что уже готово для разработки партнёрской программы

Готово и подтверждено:

- user-to-user binding по partner/referral;
- кодовая модель acquisition;
- расчёт partner markup;
- расчёт referral commission;
- ledger earnings;
- wallet accrual;
- withdrawal requests и moderation;
- admin-поверхности;
- multi-channel surfaces;
- тарифный каталог и entitlement model;
- add-ons и post-payment hooks.

То есть сейчас можно проектировать не “можно ли сделать партнёрку”, а:

- какой именно тип партнёрки нужен;
- какие бизнес-правила для attribution, payouts и anti-abuse будут каноническими;
- как развести `invite`, `referral`, `affiliate`, `partner`, `reseller`.

---

## 13. Вопросы, которые нужно зафиксировать до реализации новой партнёрской программы

Ниже список решений, без которых реализация почти наверняка уйдёт в повторные переделки.

### 13.1 Модель программы

- Это будет одна программа или две:
  - referral / affiliate
  - partner / reseller
- Может ли обычный пользователь стать партнёром self-service или только через promote/admin?

### 13.2 Экономика

- Комиссия считается от `base_price`, `displayed_price`, `gateway_amount` или `net revenue`?
- Начисляется ли комиссия на add-ons?
- Что происходит при refund / chargeback / manual cancellation?
- Нужен ли hold period перед доступностью вывода?

### 13.3 Атрибуция

- Referral и partner могут сосуществовать на одном платеже или нет?
- Кто имеет приоритет:
  - invite owner
  - referrer
  - partner
- Как атрибутируется клиент:
  - first-touch
  - last-touch
  - permanent bind
  - bind с TTL

### 13.4 UX

- Нужен ли отдельный публичный partner landing?
- Нужен ли self-serve partner onboarding?
- Нужны ли промо-материалы, QR, deep links, UTM support, статистика по каналам?

### 13.5 Выплаты и compliance

- Какие методы выплат поддерживаются реально:
  - cryptobot
  - manual
  - bank / card / USDT / Stars / YooKassa payout-like flows
- Нужна ли KYC/verification для партнёров?
- Нужны ли налоговые/договорные статусы по странам?

---

## 14. Практический вывод для следующего этапа

Если следующий шаг — проектировать и разрабатывать новую партнёрскую программу, то разумная последовательность такая:

1. Зафиксировать каноническую бизнес-модель партнёрки поверх уже существующих `referral`, `partner`, `wallet`, `withdrawals`.
2. Принять единые правила по attribution, payout, anti-fraud и coexistence с invite/promo.
3. Составить отдельный PRD и implementation plan по каналам:
   - backend
   - admin
   - frontend web
   - mini app
   - Telegram bot
4. Только после этого расширять схемы и UI.

Иными словами:

- **архитектурная база уже есть**;
- **тарифный каталог уже есть**;
- **growth primitives уже есть**;
- следующая реальная работа — не “изобретать платформу”, а **довести её до единой коммерческой и продуктовой модели**.

---

## 15. Основные источники

Ключевые файлы, на которых основан этот документ:

- `README.md`
- `docs/PROJECT_OVERVIEW.md`
- `docs/CYBERVPN_FULL_DESCRIPTION.md`
- `docs/plans/2026-04-16-pricing-plans-and-partner-program-discovery.md`
- `docs/plans/2026-04-16-canonical-pricing-standard-and-phase-roadmap.md`
- `docs/plans/2026-01-24-invite-system-design.md`
- `docs/plans/2026-01-24-loyalty-program-design.md`
- `frontend/src/i18n/config.ts`
- `frontend/src/widgets/pricing/catalog.ts`
- `frontend/src/app/[locale]/(marketing)/pricing/page.tsx`
- `frontend/src/app/[locale]/(dashboard)/subscriptions/components/SubscriptionsClient.tsx`
- `frontend/src/app/[locale]/(dashboard)/referral/components/ReferralClient.tsx`
- `frontend/src/app/[locale]/(dashboard)/partner/components/PartnerClient.tsx`
- `frontend/src/app/[locale]/miniapp/home/page.tsx`
- `frontend/src/app/[locale]/miniapp/plans/page.tsx`
- `frontend/src/app/[locale]/miniapp/referral/page.tsx`
- `frontend/src/app/[locale]/miniapp/wallet/page.tsx`
- `frontend/src/app/[locale]/miniapp/profile/page.tsx`
- `admin/src/features/commerce/components/plans-console.tsx`
- `admin/src/features/commerce/components/wallet-ops-console.tsx`
- `admin/src/features/commerce/components/withdrawals-console.tsx`
- `admin/src/features/growth/components/partners-console.tsx`
- `admin/src/features/growth/components/referral-signals-console.tsx`
- `admin/src/features/customers/components/customer-detail.tsx`
- `backend/src/domain/enums/enums.py`
- `backend/src/infrastructure/database/models/mobile_user_model.py`
- `backend/src/infrastructure/database/models/subscription_plan_model.py`
- `backend/src/infrastructure/database/models/plan_addon_model.py`
- `backend/src/infrastructure/database/models/payment_model.py`
- `backend/src/infrastructure/database/models/invite_code_model.py`
- `backend/src/infrastructure/database/models/referral_commission_model.py`
- `backend/src/infrastructure/database/models/partner_model.py`
- `backend/src/infrastructure/database/models/wallet_model.py`
- `backend/src/infrastructure/database/models/withdrawal_request_model.py`
- `backend/src/application/services/pricing_catalog_seed.py`
- `backend/src/application/services/entitlements_service.py`
- `backend/src/application/services/config_service.py`
- `backend/src/application/use_cases/payments/checkout.py`
- `backend/src/application/use_cases/payments/commit_checkout.py`
- `backend/src/application/use_cases/payments/post_payment.py`
- `backend/src/application/use_cases/referrals/process_referral_commission.py`
- `backend/src/application/use_cases/partners/process_partner_earning.py`
- `backend/src/application/use_cases/invites/generate_invites.py`
- `backend/src/application/use_cases/trial/activate_trial.py`
- `backend/src/presentation/api/v1/plans/routes.py`
- `backend/src/presentation/api/v1/addons/routes.py`
- `backend/src/presentation/api/v1/payments/routes.py`
- `backend/src/presentation/api/v1/subscriptions/routes.py`
- `backend/src/presentation/api/v1/referral/routes.py`
- `backend/src/presentation/api/v1/partners/routes.py`
- `backend/src/presentation/api/v1/invites/routes.py`
- `backend/src/presentation/api/v1/wallet/routes.py`
- `backend/src/presentation/api/v1/trial/routes.py`
- `backend/src/presentation/api/v1/telegram/routes.py`
- `backend/alembic/versions/20260210_add_codes_wallet_foundation.py`
- `backend/alembic/versions/20260416_010000_pricing_catalog_standard.py`
- `services/telegram-bot/README.md`
- `services/telegram-bot/src/handlers/`
- `services/task-worker/README.md`
- `infra/docker-compose.yml`

