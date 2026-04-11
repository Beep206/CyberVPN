# План Полного Покрытия Админки

> Документ составлен по результатам анализа текущего проекта на 10 апреля 2026 года. Основа анализа: `backend/src/presentation/api/v1`, ORM-модели и репозитории backend, сервисный слой, текущий workspace `admin`.

**Цель:** превратить текущий минимальный `admin` в полноценную панель управления для операций, коммерции, роста, инфраструктуры, безопасности и внутреннего администрирования, не выдумывая функционал, которого реально нет в backend.

**Подход:** админка развивается как отдельный `admin` workspace, но проектируется как единая control plane. Каждый раздел должен опираться на реальные доменные сущности, реальные эндпоинты и реальные ограничения текущего backend.

**Стек:** Next.js 16 App Router, React 19, TypeScript, Zustand, TanStack Query, Next Intl, FastAPI, PostgreSQL, Redis, Remnawave.

---

## 1. Что показал анализ проекта

### 1.1 Поверхность backend уже большая

- Сейчас в `backend/src/presentation/api/v1` есть **206 HTTP endpoints**, плюс WebSocket-каналы для monitoring, notifications и ticket-based WS auth.
- Backend уже хорошо покрывает:
  - серверы и мониторинг
  - планы и subscription templates
  - платежи и кошельки
  - выводы средств
  - promo / invite / referral / partner
  - VPN-инфраструктуру
  - аудит и webhook-логи
  - Telegram bot операции
  - 2FA, сессии и anti-phishing

Это значит, что админка может быстро вырасти в реальный рабочий инструмент, а не в набор моковых экранов.

### 1.2 В проекте не один тип пользователя, а три разных домена

Это самое важное архитектурное наблюдение.

| Домен | Источник истины | Назначение |
|---|---|---|
| `admin_users` | `AdminUserModel` | сотрудники, которые входят в админку |
| `mobile_users` | `MobileUserModel` | реальные клиентские аккаунты мобильного продукта |
| Remnawave VPN users | Remnawave API | VPN-идентичность, конфиги, лимиты, сетевое состояние |

Из этого следует, что будущая админка не должна смешивать эти сущности в одну таблицу.

Нормальная админская модель должна показывать связи между ними:

| Экран | Что должен показывать |
|---|---|
| Карточка клиента | `mobile_user`, кошелёк, платежи, партнёрка, рефералка, связанный `remnawave_uuid` |
| Карточка VPN-пользователя | статус в Remnawave, трафик, конфиг, шаблон подписки |
| Карточка сотрудника | `admin_user`, роль, 2FA, активные сессии, anti-phishing, prefs |

### 1.3 Текущий `admin` уже имеет основу, но покрытие пока узкое

Сейчас в `admin` уже готовы:

- отдельный workspace
- отдельный runtime под `admin.ozoxy.ru`
- auth только через `email/password + 2FA`
- доступ только для `admin` и `super_admin`
- только `ru-RU` и `en-EN`
- минимальный dashboard shell

Также уже есть typed API modules для:

- auth
- 2FA
- security
- profile
- servers
- monitoring
- plans
- subscriptions
- wallet
- payments
- promo
- invites
- partner
- referral
- trial
- usage

Но в `admin` пока нет client layer для многих сильных backend-поверхностей:

- customer management
- audit log
- webhook log
- system config
- helix
- hosts
- config profiles
- inbounds
- node plugins
- snippets
- squads
- xray
- Telegram bot admin surface
- FCM / notification ops

### 1.4 Role model в backend богаче, чем role model в admin frontend

Backend уже поддерживает:

- `viewer`
- `support`
- `operator`
- `admin`
- `super_admin`

Текущий `admin` frontend по ранее согласованному скоупу пускает только:

- `admin`
- `super_admin`

Это нормально для текущего релиза. Но архитектуру экранов и навигации нужно строить permission-aware уже сейчас, чтобы потом не переделывать всю панель, если вы захотите ввести `support` и `operator`.

### 1.5 Два системных backend-gap мешают “максимальному покрытию”

Вот два главных пробела, которые реально блокируют полный admin coverage.

| Gap | Почему это критично |
|---|---|
| Нет полноценного admin API для `mobile_users` | без этого можно управлять VPN-артефактами и деньгами, но нельзя нормально управлять клиентской базой |
| Нет admin API для `system_config` | правила для referral / partner / invite / wallet уже живут в БД и сервисах, но админка не может ими управлять как first-class разделом |

Второй слой пробелов:

| Gap | Почему это важно |
|---|---|
| Нет полноценного staff management API | есть invite tokens для входа сотрудников, но нет нормального списка, смены роли, деактивации |
| Audit и webhook logs слишком базовые | есть только чтение с пагинацией, но нет хороших фильтров и forensic workflow |
| Payment operations неполные | нет явных refund / resync / manual correction flows |
| Wallet admin ограничен | есть topup и approval queue, но ещё не полноценный admin ledger control |
| Referral и partner analytics ориентированы больше на user-side | для business-admin нужны более сильные агрегаты и аналитика |

---

## 2. Какой должна быть удобная админка

Если цель “удобно всем управлять”, панель нельзя собирать как набор несвязанных страниц.

Она должна вести себя как operational console.

### 2.1 Базовые UX-паттерны

- Один общий паттерн list-page для всех сущностей.
- Один общий паттерн detail-page для всех сущностей.
- Один общий паттерн безопасного действия.
- Один общий паттерн очередей и инцидентов.

### 2.2 Что это означает на практике

| Паттерн | Что должно быть |
|---|---|
| List page | поиск, фильтры, сохранённые views, колонки, bulk actions |
| Detail page | summary, linked entities, history, actions |
| Safe action | confirm, impact preview, reason field, audit trail |
| Incident flow | все критичные очереди поднимаются в dashboard и nav badges |

### 2.3 Глобальные инструменты

- Global command bar для перехода по user, payment, server, promo, invite, partner, rollout, audit event.
- Global search по email, login, UUID, telegram ID, invoice ID, code.
- Header activity strip: pending withdrawals, webhook failures, offline servers, rollout alerts.
- Saved operator workspaces: infra view, commerce view, support view.

### 2.4 Правильная detail-структура сущности

Каждая важная сущность должна иметь одинаковую логику экрана:

| Зона | Назначение |
|---|---|
| Header | идентичность, статус, quick actions |
| Summary cards | главные метрики |
| Linked entities | связанные пользователи, платежи, конфиги, серверы |
| Timeline | audit, state changes, webhook events, session events |
| Action rail | операционные и destructive actions |

### 2.5 Где нужен realtime, а где нет

Realtime нужен только там, где оператор реально выигрывает от мгновенного обновления:

- health и incident ленты
- payment events
- webhook failures
- rollout status
- server state

Не нужно превращать каждую таблицу в бесконечный live-feed.

---

## 3. Рекомендуемая информационная архитектура

### 3.1 Верхний уровень навигации

| Раздел | Назначение |
|---|---|
| Overview | глобальный command center |
| Customers | клиентские аккаунты и support-операции |
| Commerce | планы, подписки, платежи, кошельки, выводы |
| Growth | promo, invites, referrals, partners |
| Infrastructure | серверы и VPN control surfaces |
| Security | доступ, сессии, 2FA, anti-phishing |
| Governance | audit, webhooks, admin invites, admin users, settings |
| Integrations | Telegram, push, realtime и интеграции |

### 3.2 Предлагаемое дерево маршрутов

| Route | Экран |
|---|---|
| `/dashboard` | Overview |
| `/customers` | Каталог клиентов |
| `/customers/[id]` | Карточка клиента |
| `/customers/vpn-users` | VPN users / Remnawave users |
| `/commerce/plans` | Планы |
| `/commerce/subscription-templates` | Subscription templates |
| `/commerce/payments` | Платежи |
| `/commerce/wallets` | Кошельки |
| `/commerce/withdrawals` | Очередь выводов |
| `/growth/promo-codes` | Промокоды |
| `/growth/invite-codes` | Клиентские invite codes |
| `/growth/referrals` | Реферальная аналитика |
| `/growth/partners` | Партнёрская программа |
| `/infrastructure/servers` | Серверы |
| `/infrastructure/hosts` | Hosts |
| `/infrastructure/config-profiles` | Config profiles |
| `/infrastructure/inbounds` | Inbounds |
| `/infrastructure/squads` | Squads |
| `/infrastructure/snippets` | Snippets |
| `/infrastructure/node-plugins` | Node plugins |
| `/infrastructure/xray` | Xray config |
| `/infrastructure/helix` | Helix rollouts |
| `/security/sessions` | Сессии и устройства |
| `/security/two-factor` | 2FA |
| `/security/anti-phishing` | Anti-phishing |
| `/governance/audit-log` | Audit explorer |
| `/governance/webhook-log` | Webhook explorer |
| `/governance/admin-invites` | Staff invite tokens |
| `/governance/admin-users` | Сотрудники |
| `/governance/system-config` | Внутренние правила и конфиги |
| `/integrations/telegram` | Telegram bot ops |
| `/integrations/push` | Push / FCM ops |

---

## 4. Проектирование разделов по доменам

## 4.1 Overview

### Задача раздела

Дать один экран, который за 15 секунд отвечает на вопросы:

- что сломано
- где нужна реакция
- что влияет на деньги
- что влияет на доступ клиентов
- что недавно изменилось

### Что должно быть на dashboard

| Виджет | Источник | Комментарий |
|---|---|---|
| System health | `/monitoring/health` | db, redis, remnawave |
| System stats | `/monitoring/stats` | users, traffic, servers |
| Server summary | `/servers/stats` | online/offline/warning/maintenance |
| Pending withdrawals | `/admin/withdrawals` | action queue |
| Recent payments | `/payments/history` | денежный pulse |
| Webhook failures | `/admin/webhook-log` | integration incidents |
| Recent audit | `/admin/audit-log` | governance visibility |
| Rollout state | `/helix/admin/rollouts/*` | если Helix включён |

### Важное замечание по текущему admin dashboard

Сейчас в `admin` ещё осталась логика `VpnUsageCard`, которая тянет `/users/me/usage`. Для админки это плохой смысловой выбор: это self-usage текущего admin account, а не operational metric.

Этот блок нужно заменить на:

- pending withdrawals
- webhook failures
- infra alerts
- payments needing attention

## 4.2 Customers

### Что должен решать раздел

Это сердце будущей админки. Именно здесь support и ops должны видеть реального клиента, а не только куски данных.

### Идеальный состав раздела

| Экран | Содержание |
|---|---|
| Customer directory | поиск по email, telegram, UUID, статусу, партнёрке, referral |
| Customer detail | профиль клиента, статусы, связанный `remnawave_uuid` |
| Wallet tab | баланс, заморозка, транзакции, выводы |
| Payments tab | история и статусы платежей |
| Subscription tab | план, trial, current entitlement |
| Partner / referral tab | привязка, код, earnings, referrals |
| Support actions | block / unblock / partner promote / wallet topup / support notes |

### Что реально уже есть в backend

| Возможность | Состояние |
|---|---|
| Promote mobile user to partner | есть `/admin/partners/promote` |
| Wallet admin view и topup | есть |
| Withdrawal approval queue | есть |
| VPN user enable / disable | есть, но это Remnawave user layer |
| Mobile users directory | нет |
| Mobile user detail и lifecycle admin actions | нет |

### Вывод

Раздел Customers обязателен, но для качественной реализации сначала нужен backend contract под `mobile_users`.

## 4.3 Commerce

### Что входит

| Подраздел | Backend support |
|---|---|
| Plans | сильный |
| Subscription templates | сильный |
| Payments | средний |
| Wallets | хороший |
| Withdrawals | сильный |
| Billing | пока user-side, не admin-grade |

### Рекомендуемые экраны

| Экран | Функционал |
|---|---|
| Plans | list / create / update / delete |
| Subscription templates | list / create / update / delete |
| Payments | фильтры по user, provider, status, amount, promo, partner |
| Payment detail | invoice, external ID, gateway amount, wallet amount, promo / partner link |
| Wallets | balance, frozen, manual topup |
| Withdrawals | approve / reject + admin note |

### Реальная оценка readiness

- `/plans/*` и `/subscriptions/*` уже дают хорошую основу.
- `/payments/history` позволяет собрать первый боевой экран.
- `/wallet/admin/withdrawals` и `/wallet/admin/wallets/{user_id}` уже полезны.
- Но полноценный finance-ops контур позже потребует refund / resync / manual correction flows.

## 4.4 Growth

### Что должно жить в этом разделе

| Подраздел | Backend support |
|---|---|
| Promo codes | сильный |
| Customer invite codes | хороший |
| Referrals | mostly user-oriented |
| Partners | частично хороший |
| Growth settings | данные есть, admin API нет |

### Рекомендуемые экраны

| Экран | Функционал |
|---|---|
| Promo codes | create, edit, deactivate, usage visibility |
| Invite codes | create for user, usage, expires, source |
| Referrals | общий объём, комиссии, recent commissions, anti-abuse visibility |
| Partners | каталог партнёров, коды, markups, earnings |
| Growth settings | referral rules, partner tiers, invite rules |

### Ключевое наблюдение

В проекте уже есть реальные конфиги в `system_config`:

- `invite.plan_rules`
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

То есть бизнес-правила уже существуют как данные. Админка пока просто не может ими управлять, потому что нет нормального admin route layer поверх `system_config`.

## 4.5 Infrastructure

Это самый сильный технический домен backend после auth и monitoring. Он особенно хорош как ранний кандидат на реализацию.

### Уже доступные control surfaces

| Подраздел | Endpoint family |
|---|---|
| Servers | `/servers` |
| Hosts | `/hosts` |
| Config profiles | `/config-profiles` |
| Inbounds | `/inbounds` |
| Squads | `/squads` |
| Snippets | `/snippets` |
| Node plugins | `/node-plugins` |
| Xray | `/xray` |
| Helix | `/helix` |
| Remnawave settings | `/settings` |

### Что нужно построить в UI

| Экран | Функционал |
|---|---|
| Servers | list, detail, create, edit, delete, stats |
| Hosts | CRUD |
| Config profiles | inventory и создание |
| Inbounds | список и detail |
| Squads | internal / external grouping |
| Snippets | config catalog |
| Node plugins | CRUD, clone, reorder, execute, torrent-blocker reports |
| Xray | current config + update flow |
| Helix | nodes, transport profiles, rollout publish / pause / revoke |
| Settings | редактор Remnawave settings |

### Почему этот раздел надо делать рано

- endpoint surface уже готов
- operational value высокий
- UI можно строить быстро без тяжёлых backend блокеров

## 4.6 Security

### Что уже есть

| Surface | Состояние |
|---|---|
| login / logout / refresh | сильный |
| session / devices | сильный |
| 2FA lifecycle | сильный |
| anti-phishing | сильный |
| brute-force / lockout logic | есть в backend |
| FCM token registration | есть, но только как self-service |

### Какие экраны нужны

| Экран | Функционал |
|---|---|
| My sessions | список устройств, revoke device, logout all |
| 2FA | reauth, setup, verify, disable, status |
| Anti-phishing | get / set / delete |
| Security posture | health текущего staff account |
| Auth event visibility | через dashboard и audit surfaces |

### Что добавить позже

- anomaly badges по IP / geo / unusual sessions
- risk markers по account lockout и failed attempts
- privileged action reasons

## 4.7 Governance

### Что сюда должно войти

| Подраздел | Состояние |
|---|---|
| Audit log | есть базовое чтение |
| Webhook log | есть базовое чтение |
| Admin invite tokens | хороший support |
| Admin users management | route layer отсутствует |
| Internal config management | route layer отсутствует |

### Нужные экраны

| Экран | Функционал |
|---|---|
| Audit explorer | фильтры по actor, action, entity, date |
| Webhook explorer | фильтры по source, validity, event_type, error |
| Admin invites | create / list / revoke |
| Admin users | список сотрудников, роли, activation state, 2FA state |
| System config | редактирование внутренних правил |

### Важная техническая деталь

`AdminUserRepository.get_all()` уже существует, но admin route family для полноценного staff management нет. То есть backend data access есть, а продукта поверх него ещё нет.

## 4.8 Integrations

### Что реально уже поддерживается

| Surface | Состояние |
|---|---|
| Telegram bot user support | сильный |
| Telegram bot plans / config / trial / referral stats | хороший |
| FCM token registration | user-self-service only |
| Notification preferences | user-self-service only |
| WebSocket monitoring | хороший foundation |

### Рекомендуемые экраны

| Экран | Функционал |
|---|---|
| Telegram ops | найти пользователя, bootstrap, config, subscriptions, trial, referral stats |
| Push ops | token visibility, registration health, delivery diagnostics |
| Live event feeds | monitoring topics, payment events, incident strips |

---

## 5. Permission strategy

### 5.1 Текущее продуктовое ограничение

По уже согласованному решению вход в `admin` пока остаётся только для:

- `admin`
- `super_admin`

### 5.2 Как всё равно нужно проектировать frontend

Даже при таком ограничении каждая страница и каждое действие должны быть описаны через capability map, а не через жёсткий `if admin`.

Причина простая: backend уже живёт в permission-модели.

### 5.3 Будущая матрица ролей

| Роль | Возможная область ответственности |
|---|---|
| `viewer` | overview, monitoring, read-only reports |
| `support` | клиенты, подписки, support actions без глобальных destructive операций |
| `operator` | infra, helix, monitoring, часть ops |
| `admin` | business + infra operations |
| `super_admin` | всё, включая staff management и global settings |

### 5.4 Текущий frontend gap

В `admin/src/features/auth/lib/admin-access.ts` и `admin/src/lib/api/auth.ts` role space описан слишком узко. Это не мешает текущему допуску, но Phase 0 должен привести typing и navigation permissions в более зрелое состояние.

---

## 6. Явные backend gaps, которые нужно учитывать в roadmap

## 6.1 Блокеры

| Приоритет | Gap | Нужный результат |
|---|---|---|
| Critical | Admin API для `mobile_users` | нормальный customer directory и customer detail |
| Critical | CRUD/list API для `system_config` | управление referral / partner / invite / wallet rules |
| High | Staff management API | полноценный раздел сотрудников |

## 6.2 Важные, но не блокирующие

| Приоритет | Gap | Нужный результат |
|---|---|---|
| High | richer audit filtering | нормальный incident / forensic workflow |
| High | richer webhook filtering | нормальный integration triage |
| High | payment ops endpoints | refund / resync / manual correction |
| Medium | admin referral / partner analytics | бизнес-аналитика и контроль злоупотреблений |
| Medium | admin push visibility | понимание состояния FCM / notifications |
| Medium | aggregated overview endpoints | чище и быстрее dashboard |

---

## 7. Фазовый roadmap

## Фаза 0. Foundation 2.0

### Цель

Подготовить `admin` к росту из одной страницы в полноценную control plane.

### Что входит

- permission-aware navigation schema
- route scaffolding верхнего уровня
- API client modules для уже существующих backend surfaces
- общие admin table primitives
- общий filter bar
- общий action rail
- global command bar shell
- future-proof role typing

### Почему это первая фаза

Если пропустить эту фазу, каждый новый раздел начнёт жить по своей UI-логике, и админка быстро распадётся на набор разнородных экранов.

## Фаза 1. Command Center

### Цель

Заменить временный dashboard на реальный operational экран.

### Что входит

- executive summary
- pending queues
- recent audit
- webhook failures
- health ribbons
- rollout / infra alerts
- замена текущего self-usage card на meaningful ops metrics

### Readiness

Backend для первой версии этой фазы в основном уже готов.

## Фаза 2. Infrastructure Operations

### Цель

Быстро выпустить первый по-настоящему сильный admin-модуль на уже существующих endpoints.

### Что входит

- servers
- hosts
- config profiles
- inbounds
- squads
- snippets
- node plugins
- xray
- helix
- remnawave settings

### Readiness

Очень хорошая. Это один из лучших кандидатов на немедленную разработку.

## Фаза 3. Commerce Operations

### Цель

Собрать finance и subscription control layer.

### Что входит

- plans
- subscription templates
- payments
- wallets
- withdrawals
- manual wallet topup

### Readiness

Хорошая. Для первой боевой версии хватает того, что уже есть.

## Фаза 4. Customer Operations

### Цель

Сделать реальную поддержку клиентов и lifecycle management.

### Что входит

- customer directory
- customer detail
- linked VPN identity
- wallet / payments / entitlement tabs
- support action toolkit

### Readiness

Сильно зависит от нового admin API для `mobile_users`. Эту фазу нужно начинать с backend contract work.

## Фаза 5. Growth Operations

### Цель

Централизовать всё, что отвечает за acquisition, discount, retention и reseller-side flows.

### Что входит

- promo codes
- invite codes
- referrals
- partners
- growth settings

### Readiness

Смешанная. Promo и invite готовы лучше всего. Growth settings и admin analytics требуют backend expansion.

## Фаза 6. Security And Governance

### Цель

Сделать админку безопасной и самоуправляемой.

### Что входит

- sessions
- devices
- 2FA
- anti-phishing
- audit explorer
- webhook explorer
- admin invites
- admin users

### Readiness

Security surfaces готовы хорошо. Governance surfaces частично упираются в backend gaps.

## Фаза 7. Integrations And Messaging

### Цель

Свести bot ops, push ops и live events в одну консоль.

### Что входит

- Telegram ops
- push visibility
- live feeds

### Readiness

Telegram готов заметно лучше, чем push.

## Фаза 8. Hardening, QA, Ergonomics

### Цель

Довести панель до состояния ежедневного рабочего инструмента.

### Что входит

- RBAC checks на уровне навигации и действий
- destructive confirms
- reason capture
- e2e smoke flows
- accessibility и mobile operator checks
- consistency polish по loading / retries / errors

---

## 8. В каком порядке лучше реализовывать

Если задача начать прямо сейчас и не упереться в лишние backend блокеры, оптимальный порядок такой:

1. Фаза 0
2. Фаза 1
3. Фаза 2
4. Фаза 3
5. Backend work для `mobile_users` admin API и `system_config`
6. Фаза 4
7. Фаза 5
8. Фаза 6
9. Фаза 7
10. Фаза 8

### Почему именно так

- Overview, Infrastructure и Commerce уже имеют сильную backend опору.
- Они быстро дадут ощутимую ценность.
- Customers и Growth стратегически очень важны, но сильнее остальных упираются в отсутствующие admin APIs.

---

## 9. Что я рекомендую как следующую реальную фазу

Лучший следующий шаг:

**Фаза 0 + Фаза 1 вместе**

### Почему

- не требуют большого backend ожидания
- задают правильный скелет для всех следующих экранов
- превращают текущий dashboard в настоящую control surface
- позволяют один раз правильно собрать nav, layouts, badges, table patterns и command bar

### Что получится на выходе

- полноценное дерево разделов в shell
- рабочий command center
- первые боевые data tables
- подготовленный frontend foundation под быстрый рост

---

## 10. Карта источников, на которых основан этот документ

### Backend route layer

- `backend/src/presentation/api/v1/router.py`
- `backend/src/presentation/api/v1/auth/routes.py`
- `backend/src/presentation/api/v1/auth/registration.py`
- `backend/src/presentation/api/v1/two_factor/routes.py`
- `backend/src/presentation/api/v1/security/routes.py`
- `backend/src/presentation/api/v1/users/*`
- `backend/src/presentation/api/v1/servers/routes.py`
- `backend/src/presentation/api/v1/monitoring/routes.py`
- `backend/src/presentation/api/v1/plans/routes.py`
- `backend/src/presentation/api/v1/subscriptions/routes.py`
- `backend/src/presentation/api/v1/payments/routes.py`
- `backend/src/presentation/api/v1/wallet/routes.py`
- `backend/src/presentation/api/v1/promo_codes/routes.py`
- `backend/src/presentation/api/v1/invites/routes.py`
- `backend/src/presentation/api/v1/referral/routes.py`
- `backend/src/presentation/api/v1/partners/routes.py`
- `backend/src/presentation/api/v1/admin/routes.py`
- `backend/src/presentation/api/v1/admin/invites.py`
- `backend/src/presentation/api/v1/helix/routes.py`
- `backend/src/presentation/api/v1/hosts/routes.py`
- `backend/src/presentation/api/v1/config_profiles/routes.py`
- `backend/src/presentation/api/v1/inbounds/routes.py`
- `backend/src/presentation/api/v1/node_plugins/routes.py`
- `backend/src/presentation/api/v1/snippets/routes.py`
- `backend/src/presentation/api/v1/squads/routes.py`
- `backend/src/presentation/api/v1/xray/routes.py`
- `backend/src/presentation/api/v1/telegram/routes.py`
- `backend/src/presentation/api/v1/fcm/routes.py`
- `backend/src/presentation/api/v1/notifications/routes.py`
- `backend/src/presentation/api/v1/ws/*`

### Domain models и repositories

- `backend/src/domain/enums/enums.py`
- `backend/src/infrastructure/database/models/admin_user_model.py`
- `backend/src/infrastructure/database/models/mobile_user_model.py`
- `backend/src/infrastructure/database/models/payment_model.py`
- `backend/src/infrastructure/database/models/wallet_model.py`
- `backend/src/infrastructure/database/models/withdrawal_request_model.py`
- `backend/src/infrastructure/database/models/promo_code_model.py`
- `backend/src/infrastructure/database/models/partner_model.py`
- `backend/src/infrastructure/database/models/referral_commission_model.py`
- `backend/src/infrastructure/database/models/invite_code_model.py`
- `backend/src/infrastructure/database/models/system_config_model.py`
- `backend/src/infrastructure/database/models/audit_log_model.py`
- `backend/src/infrastructure/database/models/webhook_log_model.py`
- `backend/src/infrastructure/database/repositories/admin_user_repo.py`
- `backend/src/infrastructure/database/repositories/audit_log_repo.py`
- `backend/src/infrastructure/database/repositories/webhook_log_repo.py`
- `backend/src/infrastructure/database/repositories/system_config_repo.py`

### Текущее состояние admin frontend

- `admin/src/widgets/dashboard-navigation.ts`
- `admin/src/stores/auth-store.ts`
- `admin/src/features/auth/lib/admin-access.ts`
- `admin/src/lib/api/*`
- `admin/src/app/[locale]/(dashboard)/dashboard/*`

