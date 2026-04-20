# CyberVPN Partner Portal Operating Model And Workflows

**Date:** 2026-04-20  
**Status:** Operational guide  
**Purpose:** зафиксировать в одном документе, как должен работать партнёрский портал CyberVPN как продуктовая и операционная поверхность, без технических деталей реализации.

---

## 1. Что такое Partner Portal

CyberVPN Partner Portal - это отдельное внешнее рабочее пространство партнёра.

Это не:

- customer dashboard;
- реферальный кабинет;
- страница только для кодов и выплат;
- внутренний admin-интерфейс.

Это внешний operating portal для полного цикла партнёра:

1. подача заявки;
2. review и approval;
3. probation;
4. коды, кампании и tracking;
5. отчётность и explainability;
6. финансы и payout readiness;
7. compliance, governance и support.

Базовая единица доступа - `partner workspace`, а не customer account.

---

## 2. Что портал покрывает

Портал должен покрывать следующие продуктовые области:

1. Home
2. Application / Onboarding
3. Organization
4. Team & Access
5. Programs
6. Contracts & Legal
7. Codes & Tracking
8. Campaigns / Assets / Enablement
9. Conversions / Orders / Customers
10. Analytics & Exports
11. Finance
12. Traffic & Compliance
13. Integrations
14. Support & Cases
15. Notifications / Inbox
16. Settings & Security
17. Reseller Console

---

## 3. Что портал не покрывает

В портал не должны попадать:

- consumer invite / gift механики;
- consumer referral credits;
- customer viral loops;
- internal maker-checker экраны;
- global fraud search;
- raw reserve controls;
- payout execution controls внутреннего уровня;
- global moderation queues;
- internal override tooling.

Эти вещи остаются во внутренних admin-поверхностях или customer-поверхностях.

---

## 4. Основные сущности

### 4.1 Workspace

`Workspace` - это основной объект, через который партнёр входит в систему, проходит review, получает доступ к модулям, управляет командой, видит статусы, ограничения, финансы и операционные действия.

### 4.2 Lane

`Lane` - это партнёрская дорожка с отдельными правилами допуска и отдельными возможностями.

Поддерживаемые lane:

- `Creator / Affiliate`
- `Performance / Media Buyer`
- `Reseller / API / Distribution`

Один workspace может податься на несколько lane, но approval и capabilities у каждого lane независимы.

### 4.3 Code

`Code` - отдельная операционная сущность для tracking, attribution и коммерческой работы. Статус code не должен сливаться со статусом workspace или lane.

### 4.4 Readiness

Отдельно от статусов живут readiness-слои:

- finance readiness;
- compliance readiness;
- technical readiness;
- governance state.

Они могут ограничивать доступ и действия, не меняя базовый статус workspace.

---

## 5. Роли внутри workspace

Канонические внешние роли:

| Role | Назначение |
|---|---|
| `workspace_owner` | главный ответственный за workspace, юридические подтверждения, состав команды, чувствительные изменения |
| `workspace_admin` | делегированный администратор workspace |
| `finance_manager` | statements, payout accounts, finance readiness, invoice/tax context |
| `analyst` | dashboards, exports, explainability, read-only performance insight |
| `traffic_manager` | codes, links, campaigns, traffic declarations, performance operations |
| `support_manager` | cases, disputes, partner-side support follow-up |
| `technical_manager` | API tokens, postbacks, webhooks, diagnostics |
| `legal_compliance_manager` | contracts, declarations, policy acceptance, remediation |

Для первого рабочего набора ролей достаточно:

- `workspace_owner`
- `finance_manager`
- `analyst`
- `traffic_manager`
- `support_manager`

Ключевой принцип:

- доступ определяется не только ролью;
- итоговый доступ зависит от роли, статуса workspace, статуса lane и readiness/gov overlays.

---

## 6. Каналы входа в портал

Портал должен поддерживать три канала входа.

### 6.1 Public Apply

Используется в первую очередь для:

- Creator / Affiliate;
- части Reseller / API;
- self-serve партнёров с контентными, SEO или community-каналами.

### 6.2 Invite-Only Onboarding

Используется для:

- Performance / Media Buyer;
- стратегических Reseller / API / Distribution партнёров;
- партнёров, которых заводит internal team.

### 6.3 Existing User Upgrade Request

Используется для:

- сильных действующих клиентов;
- сильных consumer referrers;
- кандидатов, найденных через внутренние growth-сигналы.

Важно:

- это не перевод customer account в partner mode;
- это создание или привязка отдельного partner workspace.

---

## 7. Главные продуктовые принципы

1. Заявка может быть self-serve, активация - нет.
2. Approval - это не одно событие, а цепочка screening -> review -> probation -> activation.
3. `Workspace status`, `lane status`, `code status` и `readiness` - разные сущности.
4. Меню и действия зависят от состояния, а не только от роли.
5. Portal должен объяснять ограничения, а не просто скрывать данные.
6. Reporting и finance должны быть понятными и explainable.
7. Внутренние governance и override-инструменты остаются только в admin.

---

## 8. Канонический lifecycle партнёра

Ожидаемый основной путь:

`draft -> email_verified -> submitted -> under_review -> approved_probation -> active`

Альтернативные ветки:

- `submitted -> needs_info -> under_review`
- `under_review -> waitlisted`
- `under_review -> rejected`
- `approved_probation -> restricted`
- `active -> restricted`
- `active -> suspended`
- `suspended -> terminated`

Логика такая:

- сначала создаётся identity и workspace;
- затем собирается заявка;
- затем происходит screening и review;
- затем чаще всего даётся `approved_probation`;
- только после выполнения readiness-условий workspace становится `active`.

---

## 9. Статусная модель

### 9.1 Workspace statuses

| Status | Значение |
|---|---|
| `draft` | workspace создан, заявка ещё не готова |
| `email_verified` | identity подтверждена, можно продолжать заполнение |
| `submitted` | заявка отправлена |
| `needs_info` | запрошены уточнения или документы |
| `under_review` | активный review |
| `waitlisted` | заявка не отклонена, но активация отложена |
| `approved_probation` | одобрено с ограниченным доступом |
| `active` | workspace активирован |
| `restricted` | часть операций ограничена |
| `suspended` | существенная часть операций заблокирована |
| `rejected` | заявка отклонена |
| `terminated` | партнёрские отношения завершены |

### 9.2 Lane statuses

| Status | Значение |
|---|---|
| `not_applied` | lane не запрошен |
| `pending` | lane на рассмотрении |
| `approved_probation` | lane одобрен ограниченно |
| `approved_active` | lane полностью активен |
| `declined` | lane отклонён |
| `paused` | lane временно не работает |
| `suspended` | lane заблокирован |
| `terminated` | lane закрыт окончательно |

### 9.3 Code statuses

| Status | Значение |
|---|---|
| `draft` | код подготовлен, но не запущен |
| `pending_approval` | код ждёт approval |
| `active` | код работает |
| `paused` | код временно остановлен |
| `revoked` | код отозван |
| `expired` | код завершился естественно |

### 9.4 Readiness overlays

Отдельно живут:

- `finance_readiness`: `not_started`, `in_progress`, `ready`, `blocked`
- `compliance_readiness`: `not_started`, `declarations_complete`, `evidence_requested`, `approved`, `blocked`
- `technical_readiness`: `not_required`, `in_progress`, `ready`, `blocked`
- `governance_state`: `clear`, `watch`, `warning`, `limited`, `frozen`

Workflow-метки вроде `ready_for_active` или `blocked_pending_finance` - это не отдельные статусы, а смысловые ярлыки поверх базовой модели.

---

## 10. Базовая навигация и логика разделов

### 10.1 Home

Home должен отвечать на пять вопросов:

- какой текущий статус workspace;
- какие статусы по lane;
- что нужно сделать дальше;
- что сейчас заблокировано;
- что изменилось недавно.

Home не должен быть абстрактным дашбордом. Это status-and-action hub.

### 10.2 Application / Onboarding

Здесь живёт:

- анкета;
- история заявки;
- недостающие шаги;
- requested info;
- lane applications;
- review timeline;
- объяснение, почему доступ ограничен.

### 10.3 Organization

Здесь живёт профиль партнёра:

- business / brand identity;
- сайт, домены, соцсети;
- географии и языки;
- business model;
- контактные лица;
- baseline settlement context.

### 10.4 Team & Access

Здесь живёт:

- состав workspace;
- роли;
- приглашения;
- удаление и отключение участников;
- owner/admin-sensitive actions.

### 10.5 Programs

Здесь видно:

- какие lane запрошены;
- какие lane активны;
- какой lane в probation;
- какие ограничения и next steps есть по каждому lane.

### 10.6 Contracts & Legal

Здесь живёт:

- договорный пакет;
- policy history;
- acceptance history;
- disclosure и traffic obligations;
- требования к remediation.

### 10.7 Codes & Tracking

Здесь живёт:

- partner codes;
- deep links;
- tracking posture;
- link ownership;
- code statuses;
- запросы на новые коды.

### 10.8 Campaigns / Assets / Enablement

Здесь живёт:

- creative library;
- approved assets;
- promo calendar;
- disclosure templates;
- messaging guardrails;
- submit-for-approval flow.

### 10.9 Conversions / Orders / Customers

Здесь живёт:

- attributed conversions;
- orders;
- renewals;
- refunds;
- explainability;
- scoped customer visibility;
- reseller-specific customer/order context.

### 10.10 Analytics & Exports

Здесь живёт:

- overview metrics;
- lane / code / geo / campaign views;
- exports;
- discrepancy flags;
- explainability-oriented reporting.

### 10.11 Finance

Здесь живёт:

- earnings;
- statements;
- holds / reserves / adjustments;
- payout accounts;
- payout readiness;
- payout history;
- причины блокировок.

### 10.12 Traffic & Compliance

Здесь живёт:

- traffic declarations;
- approved sources;
- creative approvals;
- policy obligations;
- evidence requests;
- remediation tasks;
- governance последствия.

### 10.13 Integrations

Здесь живёт:

- API tokens;
- postbacks;
- webhooks;
- diagnostics;
- delivery failures;
- replay/test posture.

### 10.14 Support & Cases

Здесь живёт:

- partner messages;
- operational cases;
- disputes;
- technical support;
- application follow-up;
- compliance and finance communications.

### 10.15 Notifications / Inbox

Это событийный слой портала:

- статусы заявки;
- requested info;
- lane changes;
- legal updates;
- finance events;
- compliance events;
- cases;
- governance actions.

### 10.16 Settings & Security

Здесь живёт:

- password / passkey / MFA;
- sessions;
- notification preferences;
- security visibility;
- личные и workspace-level настройки в рамках доступных прав.

### 10.17 Reseller Console

Этот раздел существует только для `Reseller / API / Distribution` и появляется только после соответствующего lane approval.

Здесь живёт:

- storefront scope;
- domains;
- pricebook posture;
- support ownership visibility;
- integration context;
- reseller-scoped customer and order view.

---

## 11. Что видно по этапам lifecycle

### 11.1 До отправки заявки

Доступны:

- Home
- Application / Onboarding
- Organization
- Contracts & Legal
- Support & Cases
- Settings & Security
- Notifications / Inbox

### 11.2 После отправки и во время review

Доступны:

- Home
- Application / Onboarding
- Organization
- Programs
- Contracts & Legal
- Support & Cases
- Settings & Security
- Notifications / Inbox

### 11.3 На probation

Открываются:

- Team & Access
- Codes & Tracking
- Campaigns / Assets / Enablement
- Analytics & Exports
- Finance
- Traffic & Compliance

При этом доступ всё ещё ограничен.

### 11.4 В active

Открывается полный рабочий набор:

- Integrations
- Conversions / Orders / Customers
- Reseller Console при reseller lane

### 11.5 В restricted / suspended

Остаются:

- Home
- Programs
- Contracts & Legal
- Analytics & Exports
- Finance
- Traffic & Compliance
- Support & Cases
- Notifications / Inbox
- Settings & Security

Но могут блокироваться:

- новые коды;
- расширение кампаний;
- integrations;
- reseller expansion;
- payout-related actions.

---

## 12. Сквозные workflow

### 12.1 Public Apply

1. Пользователь создаёт partner identity.
2. Подтверждает email и настраивает MFA.
3. Создаёт workspace.
4. Заполняет общий профиль.
5. Заполняет lane-specific блок.
6. Принимает declarations.
7. Отправляет заявку.
8. Система прогоняет pre-screen.
9. Заявка идёт в review.
10. Результат: `approved_probation`, `needs_info`, `waitlisted` или `rejected`.

### 12.2 Invite-Only Onboarding

1. Партнёр открывает invite link.
2. Система валидирует invite и intended lane.
3. Создаётся или привязывается partner identity.
4. Часть данных предзаполняется.
5. Партнёр дозаполняет профиль, compliance и readiness-шаги.
6. При необходимости проходит manual review.
7. Получает `approved_probation` или `active` по правилам приглашения.

### 12.3 Existing User Upgrade Request

1. Сильный customer или referrer подаёт запрос на партнёрский доступ.
2. Создаётся отдельный partner workspace.
3. Существующие customer-данные могут быть подсказкой, но не становятся truth автоматически.
4. Дальше пользователь проходит обычный staged onboarding.
5. Review идёт по обычным lane-правилам.

### 12.4 Review And Approval

Review идёт в три слоя:

1. eligibility screening;
2. business fit review;
3. post-approval probation.

Hard reject применяется, если подтверждены:

- фейковые или мёртвые каналы;
- запрещённый контент;
- отказ от compliance/traffic/payout правил;
- явные abuse-сигналы;
- отсутствие обязательной legal/support/technical posture для нужного lane.

### 12.5 Needs Info Loop

Если заявке не хватает данных:

1. reviewer переводит заявку в `needs_info`;
2. партнёр получает задачу и уведомление;
3. партнёр догружает информацию или документы;
4. заявка снова возвращается в review;
5. затем следует новый decision.

### 12.6 Probation To Active

`Approved_probation` означает:

- workspace уже живой;
- часть функций уже открыта;
- партнёр может настраивать рабочую среду;
- но unrestricted launch ещё не разрешён.

Для перехода в `active` должны быть выполнены readiness-условия:

- finance readiness;
- compliance readiness;
- technical readiness, если нужен;
- отсутствие критических governance-ограничений.

### 12.7 Additional Lane Request

После запуска workspace может податься на новый lane:

1. workspace выбирает новый lane;
2. дозаполняет lane-specific поля;
3. проходит lane-specific review;
4. получает отдельный lane status;
5. capability открывается только для этого lane.

### 12.8 Codes And Commercial Operations

После probation или active партнёр:

- получает starter code или ограниченный набор кодов;
- создаёт и использует links;
- работает с asset library;
- подаёт creative submissions;
- разворачивает tracking и attribution workflows.

При governance/compliance issues эти действия могут быть ограничены без смены базового статуса workspace.

### 12.9 Reporting And Explainability

Партнёр должен видеть не только цифры, но и объяснение:

- почему конверсия была зачтена или не зачтена;
- почему earnings находятся на hold;
- почему сумма зарезервирована или скорректирована;
- почему payout недоступен;
- почему code или lane ограничен.

### 12.10 Finance And Payout Flow

Финансовый workflow выглядит так:

1. партнёр настраивает payout account;
2. заполняет нужные finance/tax данные;
3. видит statements и settlement periods;
4. видит holds, reserves, adjustments и их причины;
5. после readiness получает доступ к payout availability;
6. видит payout history и статусы блокировок.

### 12.11 Compliance, Governance And Remediation

Партнёр обязан:

- принять traffic и disclosure rules;
- подавать declarations;
- отвечать на evidence requests;
- устранять remediation tasks.

Если есть проблемы, портал должен показывать:

- что именно ограничено;
- почему ограничено;
- что нужно сделать для снятия ограничения.

### 12.12 Support, Cases And Notifications

Cases и notifications работают вместе:

- `Notifications` сообщают о событии;
- `Cases` ведут рабочий диалог и resolution;
- `Inbox` связывает партнёра с partner ops, compliance, support и finance.

Ключевые события:

- application submitted;
- needs info;
- approved probation;
- lane changed;
- legal acceptance required;
- case created;
- case reply;
- statement ready;
- payout blocked;
- payout executed;
- creative rejected;
- traffic declaration approved;
- risk review opened;
- governance action applied.

---

## 13. Отличия по lane

### 13.1 Creator / Affiliate

Основная модель:

- коды;
- ссылки;
- assets;
- analytics;
- statements и payouts.

Типичный путь:

- public self-serve application;
- manual-lite review;
- probation;
- переход в active после readiness и подтверждения качества.

### 13.2 Performance / Media Buyer

Основная модель:

- paid traffic;
- повышенный контроль;
- declarations;
- postback / tracking readiness;
- longer hold logic.

Типичный путь:

- обязательный manual review;
- обязательный probation;
- более жёсткие compliance и finance controls.

### 13.3 Reseller / API / Distribution

Основная модель:

- storefront или API resale;
- technical readiness;
- support ownership;
- legal и finance alignment;
- reseller console.

Типичный путь:

- обязательный manual review;
- contract/support/technical validation;
- reseller capabilities открываются только после полного согласования.

---

## 14. Как partner portal соотносится с другими surface

### 14.1 Customer Dashboard

Отвечает за customer account и VPN service management. Не управляет партнёрским workspace.

### 14.2 Partner Portal

Отвечает за внешние операции партнёра как revenue workspace.

### 14.3 Partner Storefront

Это customer-facing commerce surface партнёра, а не partner-admin console.

### 14.4 Admin / Internal Ops

Только здесь происходят:

- review decisions;
- governance actions;
- maker-checker;
- payout approvals;
- internal overrides;
- global search и moderation.

---

## 15. Правила показа и ограничения

1. Frontend не должен выглядеть как полностью открытый интерфейс до approval.
2. `Approved_probation` не равен unrestricted access.
3. `Active` не отменяет readiness-ограничения.
4. `Restricted` и `suspended` не должны прятать историю, но должны блокировать risky expansion.
5. Reseller Console не появляется вне reseller lane.
6. Performance lane должен оставаться самым консервативным с точки зрения traffic и finance controls.
7. Governance state должен быть виден партнёру в понятной форме.

---

## 16. Как должен выглядеть хороший рабочий опыт партнёра

Партнёр в любой момент должен понимать:

- кто он в системе;
- в каком статусе его workspace;
- какие lane у него есть и в каком они состоянии;
- что ему разрешено делать прямо сейчас;
- что у него заблокировано;
- почему это заблокировано;
- что нужно сделать дальше;
- куда идти за решением проблемы.

Если портал не даёт ответы на эти вопросы, он превращается в набор разрозненных экранов, а не в operating portal.

---

## 17. Итоговая operational truth

CyberVPN Partner Portal должен работать как:

- отдельный внешний workspace для партнёров;
- governed lifecycle от application до active operation;
- state-aware, lane-aware и role-aware поверхность;
- explainable operating portal, а не просто экран выплат;
- partner-facing слой, который показывает последствия review, finance, compliance и governance, но не раскрывает internal control panels.

Главный продуктовый смысл портала:

- дать партнёру понятную рабочую среду;
- дать внутренним командам управляемую модель взаимодействия;
- не смешивать customer semantics, partner semantics и internal ops semantics.

---

## 18. Источники канонизации

Этот документ собран как операционный конспект следующих канонических документов:

- `2026-04-18-partner-portal-prd.md`
- `2026-04-18-partner-portal-onboarding-workflow-spec.md`
- `2026-04-18-partner-portal-application-review-and-approval-policy.md`
- `2026-04-18-partner-portal-ia-and-menu-map.md`
- `2026-04-18-partner-portal-role-matrix.md`
- `2026-04-18-partner-portal-status-and-visibility-matrix.md`
- `2026-04-18-partner-portal-lane-capability-matrix.md`
- `2026-04-18-partner-portal-surface-policy-matrix.md`
- `2026-04-20-partner-notification-inbox-case-event-spec.md`

Он не заменяет их как source of truth, а даёт один цельный business-facing документ о том, как партнёрский портал должен работать.
