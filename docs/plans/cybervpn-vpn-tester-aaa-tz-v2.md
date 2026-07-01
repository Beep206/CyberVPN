# Техническое задание: CyberVPN VPN Tester AAA+ Enterprise v2

**Документ:** `cybervpn-vpn-tester-aaa-tz-v2.md`
**Версия:** 2.0
**Дата:** 2026-07-01
**Статус:** готово к реализации
**Цель:** спроектировать полноценную enterprise-систему проверки VPN-шаблонов, тарифов, Remnawave squads, node plugins, маршрутизации, runtime-доступности и будущей безопасной балансировки нагрузки. Версия v2 дополняет базовую концепцию обязательной интеграцией в админку, проверкой всех тарифов, периодическим запуском через Task Worker и набором must-have функций, без которых продукт будет сложно сопровождать на масштабе.

---

## 0. Executive Summary

CyberVPN нужен не набор ручных smoke-команд и не разовый YAML-linter. Нужен отдельный продуктовый модуль:

```text
CyberVPN VPN Tester
```

Он должен позволять из админки:

1. Проверить конкретный VPN-шаблон до публикации.
2. Проверить конкретный Remnawave template после загрузки.
3. Проверить все активные тарифы и их фактические Remnawave subscription outputs.
4. Создать synthetic/canary пользователя под тариф, получить подписку, прогнать runtime route matrix и удалить/заморозить тестового пользователя.
5. Проверить, что `Premium Smart RU` реально работает так:
   - default/non-RU -> DE/EU;
   - RU services -> RU Moscow/RU SPB;
   - YouTube/Discord/AI/GitHub -> EU;
   - ads/trackers -> reject;
   - Torrent/TOR -> block/reject;
   - DNS/IPv6 leaks -> отсутствуют.
6. Запускать проверки вручную из админки.
7. Запускать проверки периодически через Task Worker.
8. Хранить evidence по каждому запуску.
9. Отдавать результаты в Admin UI, API, Prometheus, Telegram/SSE/WebSocket alerts.
10. В будущем питать Smart Balancer рекомендациями по распределению нагрузки.

Целевая планка: **AAA+ enterprise**.

Это означает:

- воспроизводимые тесты;
- строгая типизация;
- audit trail;
- evidence reports;
- безопасное обращение с subscription URL и токенами;
- отсутствие прямых Remnawave-запросов в обход существующего клиента;
- отсутствие тяжёлых runtime-проверок внутри FastAPI request lifecycle;
- fail-closed для premium routing;
- canary-first перед любой автоматической балансировкой;
- поддержка всех тарифов, а не только `premium_smart_ru`.

---

## 1. Что изменилось в v2

По сравнению с первой версией ТЗ добавить обязательные блоки:

1. **Admin UI как основной интерфейс управления.**
   Раздел в админке: `/infrastructure/vpn-tester`.

2. **Проверка всех тарифов.**
   Тестер должен уметь построить matrix по всем активным тарифам из каталога и проверить, что каждый тариф выдаёт корректную подписку, squad, template, лимиты, device policy и routing expectations.

3. **Периодические проверки через Task Worker.**
   Добавить scheduled tasks:
   - lightweight synthetic smoke;
   - hourly all-plan contract test;
   - daily deep runtime suite;
   - post-template-change run;
   - post-remnawave-upgrade run.

4. **Must-have функция №1: Golden Route Registry.**
   Версионированный источник истины для route expectations: какие домены, IP, процессы и категории должны идти через EU/RU/DIRECT/BLOCK и почему.

5. **Must-have функция №2: CyberVPN Probe Network.**
   Собственные probe endpoints и DNS canary-домены в DE/NL/RU, чтобы не зависеть от публичных `2ip`, `ipinfo`, `ipwho` при проверке маршрута.

6. **Must-have функция №3: Template Release Gate.**
   Нельзя промотить новый VPN-шаблон в production, если tester не выдал `PASS` по обязательным suites.

7. **Must-have функция №4: Abuse Sentinel.**
   Сквозная проверка, что client-side Torrent/TOR block, Remnawave Node Plugins и webhook/business-reaction работают согласованно.

8. **Conflict-proof design.**
   В ТЗ явно описаны потенциальные конфликты с текущей архитектурой и как их избежать.

---

## 2. Текущие точки интеграции в репозитории

### 2.1. Backend architecture

Проект уже описан как монорепозиторий с:

```text
backend/               FastAPI + Clean Architecture + DDD
services/task-worker/  TaskIQ фоновые задачи
admin/                 Next.js admin portal
infra/                 compose/ansible infrastructure
scripts/remnawave/     Remnawave seed scripts
```

Новый модуль должен следовать текущему разделению:

```text
backend/src/domain/          чистые сущности и value objects
backend/src/application/     use cases
backend/src/infrastructure/  БД, Redis, Remnawave, runner clients
backend/src/presentation/    FastAPI routes/schemas
```

Запрещено класть бизнес-логику в FastAPI route handlers.

### 2.2. Remnawave client

В репозитории уже есть `RemnawaveClient`, который:

- нормализует base URL и API path;
- добавляет `Authorization: Bearer ...`;
- имеет retry для 5xx/transport errors;
- нормализует envelope `response`;
- поддерживает validated methods.

Новый tester не должен делать raw `httpx.AsyncClient` запросы к Remnawave напрямую. Все Remnawave calls идут через:

```text
backend/src/infrastructure/remnawave/client.py
```

или специализированные gateways поверх него.

### 2.3. Admin navigation

В админке уже есть группа `infrastructure` с разделами:

```text
/infrastructure
/infrastructure/servers
/infrastructure/hosts
/infrastructure/config-profiles
/infrastructure/node-plugins
/infrastructure/xray
/infrastructure/helix
/infrastructure/inbounds
/infrastructure/squads
/infrastructure/snippets
```

`VPN Tester` должен появиться рядом с ними:

```text
/infrastructure/vpn-tester
```

Логически это эксплуатационный модуль инфраструктуры, а не commerce-модуль. Commerce участвует только как источник тарифов.

### 2.4. Admin RBAC

Сейчас в admin RBAC есть permissions:

```text
server_read
server_create
server_update
server_delete
monitoring_read
audit_read
webhook_read
manage_plans
subscription_create
vpn_credential_regenerate
view_analytics
```

Чтобы не сломать существующую модель доступа, реализация должна быть двухфазной:

**Фаза A — без миграции RBAC:**

| Действие | Требования |
|---|---|
| Просмотр dashboard/results | `server_read` OR `monitoring_read` |
| Запуск ручного теста | `server_update` OR `monitoring_read` |
| Запуск all-plan tests | `server_update` + `manage_plans` |
| Изменение schedules | `server_update` + `manage_plans` |
| Template Release Gate approve override | `owner/super_admin` или `super_admin` |

**Фаза B — отдельные permissions:**

```text
vpn_tester_read
vpn_tester_run
vpn_tester_manage
vpn_tester_release_override
```

Фазу B делать отдельной миграцией, чтобы не блокировать первую реализацию.

### 2.5. API router

`backend/src/presentation/api/v1/router.py` уже подключает:

```text
monitoring_router
admin_remnawave_diagnostics_router
hosts_router
config_profiles_router
inbounds_router
node_plugins_router
squads_router
xray_router
settings_router
```

Новый router должен быть подключён рядом с admin/monitoring/VPN management:

```python
from src.presentation.api.v1.admin.vpn_tester import router as admin_vpn_tester_router
...
api_router.include_router(admin_vpn_tester_router)
```

Префикс:

```text
/api/v1/admin/vpn-tester
```

### 2.6. Task Worker

Task Worker уже построен на TaskIQ + Redis Streams и имеет:

```text
services/task-worker/src/broker.py
services/task-worker/src/schedules/definitions.py
services/task-worker/src/utils/constants.py
services/task-worker/src/tasks/monitoring/
services/task-worker/src/services/
services/task-worker/src/metrics.py
```

Новый periodic tester должен подключаться через тот же scheduler mechanism, а не через отдельный cron вне проекта.

### 2.7. Premium Smart RU state

В `settings.py` уже есть:

```python
remnawave_smart_ru_external_squad_uuid: str = ""
remnawave_smart_ru_internal_squad_uuid: str = ""
remnawave_smart_ru_plan_codes: str = "premium_smart_ru"
remnawave_smart_ru_subscription_template_name: str = "CyberVPN Premium Smart RU"
```

Первый эталонный suite должен быть именно:

```text
suite_id: premium_smart_ru_v1
plan_code: premium_smart_ru
expected_template: CyberVPN Premium Smart RU
expected_external_squad: CYBERVPN_PREMIUM_SMART_RU
expected_internal_squad: CYBERVPN_PREMIUM_SMART_RU_NODES
```

### 2.8. Remnawave seed

В `scripts/remnawave/seed-cybervpn-premium-smart-ru.sql` уже зашиты:

```text
Template: CyberVPN Premium Smart RU
External squad: CYBERVPN_PREMIUM_SMART_RU
Internal squad: CYBERVPN_PREMIUM_SMART_RU_NODES
Expected nodes:
  🇩🇪 DE Frankfurt 01 25G
  🇳🇱 NL Amsterdam 01 10G
  🇷🇺 RU Moscow 01 25G
  🇷🇺 RU SPB 01 25G
Node plugin:
  CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION
```

Tester должен проверять, что seed не просто был выполнен, а реально привёл систему в ожидаемое состояние.

---

## 3. Архитектурная цель

### 3.1. Высокоуровневая схема

```text
Admin UI
  |
  | /api/v1/admin/vpn-tester/*
  v
FastAPI Backend
  |
  | creates run / reads results / schedules task
  v
PostgreSQL + Redis
  |
  | TaskIQ job
  v
Task Worker
  |
  | orchestrates checks
  +--> Static/Semantic Template Analyzer
  +--> Remnawave Contract Gateway
  +--> Subscription Fetcher
  +--> Runtime Agent Orchestrator
  +--> Probe Network
  +--> Evidence Builder
  +--> Metrics/Alerts
```

### 3.2. Главный принцип

FastAPI backend не выполняет долгие проверки. Backend только:

- валидирует запрос;
- создаёт `vpn_test_run`;
- ставит задачу в Task Worker;
- отдаёт `run_id`;
- возвращает результаты по мере готовности.

Runtime проверки выполняет Task Worker и/или отдельный isolated runner.

---

## 4. Новые backend-модули

### 4.1. Domain layer

Создать пакет:

```text
backend/src/domain/vpn_testing/
```

Файлы:

```text
backend/src/domain/vpn_testing/entities.py
backend/src/domain/vpn_testing/enums.py
backend/src/domain/vpn_testing/value_objects.py
backend/src/domain/vpn_testing/policies.py
backend/src/domain/vpn_testing/exceptions.py
```

#### Основные сущности

```python
class VpnTestSuite: ...
class VpnTestCase: ...
class VpnTestRun: ...
class VpnTestResult: ...
class VpnRouteExpectation: ...
class VpnTariffCoverageProfile: ...
class VpnBalancerRecommendation: ...
class VpnEvidenceArtifact: ...
```

#### Enums

```python
class VpnTestRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    DEGRADED = "degraded"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"

class VpnTestSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class VpnExpectedRoute(StrEnum):
    EU = "eu"
    DE = "de"
    NL = "nl"
    RU = "ru"
    DIRECT = "direct"
    BLOCK = "block"
    REJECT = "reject"

class VpnTestMode(StrEnum):
    STATIC_TEMPLATE = "static_template"
    REMNAWAVE_CONTRACT = "remnawave_contract"
    GENERATED_SUBSCRIPTION = "generated_subscription"
    RUNTIME_ROUTE = "runtime_route"
    ALL_TARIFFS = "all_tariffs"
    BALANCER_DRY_RUN = "balancer_dry_run"
```

### 4.2. Application layer

Создать:

```text
backend/src/application/use_cases/vpn_testing/
```

Use cases:

```text
create_vpn_test_run.py
cancel_vpn_test_run.py
get_vpn_test_run.py
list_vpn_test_runs.py
get_vpn_test_overview.py
get_vpn_tariff_coverage.py
build_vpn_test_suite_preview.py
validate_vpn_template_static.py
validate_vpn_template_semantic.py
validate_remnawave_contract.py
validate_generated_subscription.py
request_runtime_route_test.py
build_vpn_test_evidence.py
build_balancer_recommendations.py
```

### 4.3. Infrastructure layer

Создать:

```text
backend/src/infrastructure/vpn_testing/
```

Компоненты:

```text
repositories.py                  SQLAlchemy repositories
suite_loader.py                  загрузка YAML/JSON suite definitions
golden_route_registry.py          versioned route expectations
remnawave_contract_checker.py     проверки template/squad/plugin/user contracts
subscription_fetcher.py           безопасное получение подписок synthetic/canary users
runtime_agent_client.py           HTTP/gRPC client к vpn-test-agent
probe_network_client.py           CyberVPN probe endpoints
metrics.py                        доменные метрики tester-а
evidence_builder.py               markdown/json evidence artifacts
balancer_engine.py                recommendation-only scoring
redaction.py                      secret/subscription URL redaction
```

### 4.4. Presentation layer

Создать:

```text
backend/src/presentation/api/v1/admin/vpn_tester.py
backend/src/presentation/api/v1/admin/vpn_tester_schemas.py
```

Префикс:

```text
/api/v1/admin/vpn-tester
```

---

## 5. База данных

### 5.1. Новые таблицы

#### `vpn_test_suites`

```sql
create table vpn_test_suites (
    uuid uuid primary key,
    suite_id text not null unique,
    name text not null,
    description text not null default '',
    version text not null,
    target_plan_codes text[] not null default '{}',
    target_template_names text[] not null default '{}',
    mode text not null,
    definition_json jsonb not null,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
```

#### `vpn_test_runs`

```sql
create table vpn_test_runs (
    uuid uuid primary key,
    run_key text not null unique,
    suite_id text not null,
    requested_by_admin_uuid uuid null,
    requested_by_source text not null, -- admin_ui / task_worker / release_gate / api
    mode text not null,
    status text not null,
    target_plan_codes text[] not null default '{}',
    target_template_names text[] not null default '{}',
    environment text not null,
    started_at timestamptz null,
    finished_at timestamptz null,
    duration_ms integer null,
    summary_json jsonb not null default '{}',
    failure_reason text null,
    evidence_artifact_uuid uuid null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
```

#### `vpn_test_results`

```sql
create table vpn_test_results (
    uuid uuid primary key,
    run_uuid uuid not null references vpn_test_runs(uuid) on delete cascade,
    case_id text not null,
    case_name text not null,
    category text not null,
    severity text not null,
    status text not null,
    expected_json jsonb not null default '{}',
    actual_json jsonb not null default '{}',
    diagnostics_json jsonb not null default '{}',
    evidence text null,
    started_at timestamptz null,
    finished_at timestamptz null,
    duration_ms integer null,
    created_at timestamptz not null default now()
);
```

#### `vpn_route_registry_entries`

```sql
create table vpn_route_registry_entries (
    uuid uuid primary key,
    registry_version text not null,
    entry_key text not null,
    matcher_type text not null, -- domain / domain_suffix / keyword / ip_cidr / process / rule_set
    matcher_value text not null,
    expected_route text not null, -- eu/de/nl/ru/direct/block/reject
    priority integer not null,
    owner text not null,
    reason text not null,
    source text not null, -- manual / support_case / remnawave_template / rule_provider
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(registry_version, entry_key)
);
```

#### `vpn_test_schedules`

```sql
create table vpn_test_schedules (
    uuid uuid primary key,
    schedule_key text not null unique,
    suite_id text not null,
    cron text not null,
    enabled boolean not null default true,
    max_runtime_seconds integer not null default 900,
    concurrency_policy text not null default 'skip_if_running',
    target_plan_codes text[] not null default '{}',
    target_template_names text[] not null default '{}',
    created_by_admin_uuid uuid null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
```

#### `vpn_test_evidence_artifacts`

```sql
create table vpn_test_evidence_artifacts (
    uuid uuid primary key,
    run_uuid uuid not null references vpn_test_runs(uuid) on delete cascade,
    artifact_type text not null, -- markdown/json/html/junit
    storage_kind text not null, -- db/file/object_storage
    content_redacted text null,
    content_sha256 text not null,
    metadata_json jsonb not null default '{}',
    created_at timestamptz not null default now()
);
```

#### `vpn_balancer_recommendations`

```sql
create table vpn_balancer_recommendations (
    uuid uuid primary key,
    recommendation_key text not null unique,
    source_run_uuid uuid null references vpn_test_runs(uuid) on delete set null,
    status text not null, -- draft/recommended/approved/rejected/applied/expired
    scope text not null, -- world_eu/ru_sites/youtube/discord/plan/template
    recommendation_json jsonb not null,
    safety_checks_json jsonb not null default '{}',
    created_at timestamptz not null default now(),
    expires_at timestamptz null
);
```

### 5.2. Индексы

```sql
create index idx_vpn_test_runs_status_created on vpn_test_runs(status, created_at desc);
create index idx_vpn_test_runs_suite_created on vpn_test_runs(suite_id, created_at desc);
create index idx_vpn_test_results_run_status on vpn_test_results(run_uuid, status);
create index idx_vpn_route_registry_active on vpn_route_registry_entries(registry_version, is_active, priority);
create index idx_vpn_test_schedules_enabled on vpn_test_schedules(enabled, schedule_key);
```

### 5.3. Retention policy

| Данные | Retention |
|---|---:|
| Full run results | 90 дней |
| Evidence markdown | 180 дней |
| Aggregated summary | 365 дней |
| Failed critical runs | 365 дней |
| Release gate evidence | бессрочно или до архивирования релиза |

---

## 6. Admin API

### 6.1. Overview

```http
GET /api/v1/admin/vpn-tester/overview
```

Возвращает:

```json
{
  "status": "healthy|degraded|critical|unknown",
  "last_run": {},
  "last_all_tariffs_run": {},
  "critical_failures": 0,
  "active_schedules": 3,
  "template_gate_status": "pass|fail|not_run",
  "coverage": {
    "plans_total": 8,
    "plans_tested_24h": 8,
    "plans_failed_24h": 0
  }
}
```

### 6.2. Suites

```http
GET /api/v1/admin/vpn-tester/suites
POST /api/v1/admin/vpn-tester/suites/preview
```

`preview` принимает YAML/JSON suite definition и возвращает нормализованный план запуска без выполнения runtime-тестов.

### 6.3. Запуск теста

```http
POST /api/v1/admin/vpn-tester/runs
```

Request:

```json
{
  "suite_id": "premium_smart_ru_v1",
  "mode": "generated_subscription",
  "target_plan_codes": ["premium_smart_ru"],
  "target_template_names": ["CyberVPN Premium Smart RU"],
  "runtime": {
    "enabled": true,
    "agent_pool": "default",
    "max_runtime_seconds": 900
  },
  "synthetic_user": {
    "enabled": true,
    "cleanup_policy": "delete_after_run"
  }
}
```

Response:

```json
{
  "run_id": "uuid",
  "run_key": "vpnrun_20260701_001",
  "status": "queued"
}
```

### 6.4. Запуск проверки всех тарифов

```http
POST /api/v1/admin/vpn-tester/runs/all-tariffs
```

Request:

```json
{
  "catalog_visibility": "all",
  "include_hidden": true,
  "include_inactive": false,
  "runtime_mode": "contract_then_runtime_for_critical",
  "synthetic_user_cleanup_policy": "delete_after_run"
}
```

Поведение:

1. Backend получает все активные тарифы из pricing catalog.
2. Строит coverage matrix.
3. Для каждого тарифа определяет expected subscription contract:
   - default template;
   - smart RU template;
   - XHTTP flags;
   - squad expectations;
   - traffic limit/device limit;
   - allowed subscription types.
4. Ставит один parent run и дочерние case groups по каждому тарифу.

### 6.5. Runs

```http
GET /api/v1/admin/vpn-tester/runs
GET /api/v1/admin/vpn-tester/runs/{run_id}
GET /api/v1/admin/vpn-tester/runs/{run_id}/results
GET /api/v1/admin/vpn-tester/runs/{run_id}/events
POST /api/v1/admin/vpn-tester/runs/{run_id}/cancel
GET /api/v1/admin/vpn-tester/runs/{run_id}/evidence.md
GET /api/v1/admin/vpn-tester/runs/{run_id}/evidence.json
```

### 6.6. Schedules

```http
GET /api/v1/admin/vpn-tester/schedules
POST /api/v1/admin/vpn-tester/schedules
PATCH /api/v1/admin/vpn-tester/schedules/{schedule_id}
POST /api/v1/admin/vpn-tester/schedules/{schedule_id}/run-now
```

Пример schedule:

```json
{
  "schedule_key": "premium_smart_ru_lightweight_15m",
  "suite_id": "premium_smart_ru_lightweight",
  "cron": "*/15 * * * *",
  "enabled": true,
  "concurrency_policy": "skip_if_running",
  "target_plan_codes": ["premium_smart_ru"]
}
```

### 6.7. Tariff coverage

```http
GET /api/v1/admin/vpn-tester/tariff-coverage
```

Response:

```json
{
  "plans": [
    {
      "plan_code": "premium_smart_ru",
      "display_name": "Premium Smart RU",
      "active": true,
      "expected_template": "CyberVPN Premium Smart RU",
      "expected_external_squad": "CYBERVPN_PREMIUM_SMART_RU",
      "last_test_status": "passed",
      "last_test_at": "2026-07-01T07:30:00Z",
      "coverage_level": "runtime"
    }
  ]
}
```

### 6.8. Balancer preview

```http
GET /api/v1/admin/vpn-tester/balancer/recommendations
POST /api/v1/admin/vpn-tester/balancer/dry-run
POST /api/v1/admin/vpn-tester/balancer/recommendations/{id}/approve
POST /api/v1/admin/vpn-tester/balancer/recommendations/{id}/reject
```

В v1 реализации approval **не применяет изменения в Remnawave автоматически**. Он только фиксирует решение. Реальное применение — отдельный future milestone.

---

## 7. Admin UI

### 7.1. Новый раздел

Добавить в `admin/src/features/admin-shell/config/admin-navigation.ts`:

```ts
{
  id: 'infrastructure-vpn-tester',
  href: '/infrastructure/vpn-tester',
  icon: ClipboardCheck,
  labelKey: 'item.vpnTester',
  hintKey: 'item.vpnTesterHint',
  requiredPermissions: ['server_read', 'monitoring_read'],
  permissionMode: 'any',
}
```

Добавить fallback labels:

```ts
'item.vpnTester': 'VPN Tester',
'item.vpnTesterHint': 'Routing, tariffs, templates and probe evidence',
```

### 7.2. Страница

Путь:

```text
admin/src/app/[locale]/(dashboard)/infrastructure/vpn-tester/page.tsx
```

Компоненты:

```text
admin/src/features/vpn-tester/components/vpn-tester-page.tsx
admin/src/features/vpn-tester/components/vpn-tester-overview-cards.tsx
admin/src/features/vpn-tester/components/vpn-test-run-builder.tsx
admin/src/features/vpn-tester/components/vpn-tariff-coverage-table.tsx
admin/src/features/vpn-tester/components/vpn-test-runs-table.tsx
admin/src/features/vpn-tester/components/vpn-test-run-detail-drawer.tsx
admin/src/features/vpn-tester/components/vpn-test-schedule-panel.tsx
admin/src/features/vpn-tester/components/vpn-route-registry-table.tsx
admin/src/features/vpn-tester/components/vpn-balancer-preview.tsx
admin/src/features/vpn-tester/components/vpn-evidence-viewer.tsx
```

### 7.3. Tabs

```text
Overview
Suites
Run Builder
All Tariffs
Live Runs
Evidence
Schedules
Route Registry
Balancer Preview
Settings
```

### 7.4. Overview cards

Карточки:

```text
Global VPN Tester Status
Last Premium Smart RU Runtime Run
All Tariffs Coverage
Critical Failures 24h
Probe Network Health
Node Plugin Compliance
Template Release Gate
Balancer Recommendations
```

### 7.5. Run Builder

Поля:

```text
Suite
Mode
Template
Plan codes
Synthetic user mode
Runtime agent pool
Probe network profile
Max runtime
Fail-fast
Evidence format
Notify on completion
```

Кнопки:

```text
Run static checks
Run contract checks
Run generated subscription checks
Run runtime route matrix
Run all tariffs
Run deep suite
Cancel run
Download evidence
```

### 7.6. All Tariffs tab

Таблица:

| Поле | Описание |
|---|---|
| plan_code | код тарифа |
| display_name | название |
| visibility | public/hidden |
| active | активен |
| expected_template | ожидаемый template |
| expected_squad | expected external/internal squad |
| last_contract_status | последний contract result |
| last_runtime_status | последний runtime result |
| last_test_at | дата |
| actions | run contract / run runtime / evidence |

### 7.7. Live Runs

Показывать поток событий:

```text
queued -> resolving tariffs -> creating synthetic user -> fetching subscription -> starting runtime agent -> route matrix -> evidence -> cleanup -> passed/failed
```

Использовать polling или existing websocket/realtime infrastructure. В первой версии допустим polling каждые 3–5 секунд, чтобы не усложнять интеграцию.

### 7.8. Evidence Viewer

Поддержать:

```text
Markdown preview
JSON raw
JUnit XML download
Diff expected/actual
Redacted subscription metadata
Route map table
Failed cases only toggle
```

### 7.9. UX guardrails

1. Для deep runtime suite показывать предупреждение о длительности.
2. Для all-tariffs runtime требовать подтверждение.
3. Для production synthetic users показывать cleanup policy.
4. Для release override требовать `owner/super_admin`.
5. Никогда не показывать raw subscription URL целиком — только fingerprint/hash.

---

## 8. Task Worker интеграция

### 8.1. Новый queue

Добавить в `services/task-worker/src/utils/constants.py`:

```python
QUEUE_VPN_TESTING: Final[str] = "vpn_testing"
```

### 8.2. Новые schedules

Добавить:

```python
SCHEDULE_VPN_TESTER_LIGHTWEIGHT: Final[str] = "*/15 * * * *"      # каждые 15 минут
SCHEDULE_VPN_TESTER_ALL_TARIFFS: Final[str] = "10 * * * *"        # каждый час в :10
SCHEDULE_VPN_TESTER_DEEP: Final[str] = "30 2 * * *"               # ежедневно 02:30 UTC
SCHEDULE_VPN_TESTER_BALANCER: Final[str] = "*/10 * * * *"         # каждые 10 минут recommendation-only
SCHEDULE_VPN_TESTER_CLEANUP: Final[str] = "15 3 * * *"            # daily cleanup
```

### 8.3. Новые задачи

```text
services/task-worker/src/tasks/vpn_testing/run_suite.py
services/task-worker/src/tasks/vpn_testing/run_all_tariffs.py
services/task-worker/src/tasks/vpn_testing/run_scheduled_suites.py
services/task-worker/src/tasks/vpn_testing/cleanup_old_runs.py
services/task-worker/src/tasks/vpn_testing/build_balancer_recommendations.py
services/task-worker/src/tasks/vpn_testing/check_probe_network.py
services/task-worker/src/tasks/vpn_testing/post_template_change_gate.py
```

### 8.4. Scheduler registration

В `services/task-worker/src/schedules/definitions.py` добавить секцию:

```python
# =============================================================================
# VPN Testing Tasks
# =============================================================================

from src.tasks.vpn_testing.run_scheduled_suites import run_vpn_tester_lightweight
run_vpn_tester_lightweight = _schedule_task(
    run_vpn_tester_lightweight,
    [{"cron": SCHEDULE_VPN_TESTER_LIGHTWEIGHT}],
)

from src.tasks.vpn_testing.run_all_tariffs import run_vpn_tester_all_tariffs
run_vpn_tester_all_tariffs = _schedule_task(
    run_vpn_tester_all_tariffs,
    [{"cron": SCHEDULE_VPN_TESTER_ALL_TARIFFS}],
)

from src.tasks.vpn_testing.run_suite import run_vpn_tester_deep_suite
run_vpn_tester_deep_suite = _schedule_task(
    run_vpn_tester_deep_suite,
    [{"cron": SCHEDULE_VPN_TESTER_DEEP}],
)

from src.tasks.vpn_testing.build_balancer_recommendations import build_vpn_balancer_recommendations
build_vpn_balancer_recommendations = _schedule_task(
    build_vpn_balancer_recommendations,
    [{"cron": SCHEDULE_VPN_TESTER_BALANCER}],
)
```

### 8.5. Concurrency policy

Нельзя запускать несколько deep runtime тестов одновременно на один template/plan.

Redis locks:

```text
cybervpn:vpn-tester:lock:suite:{suite_id}
cybervpn:vpn-tester:lock:plan:{plan_code}
cybervpn:vpn-tester:lock:agent:{agent_id}
```

Policy:

```text
skip_if_running       default for scheduled
cancel_previous       allowed only admin manual
queue_after_current   allowed for release gate
```

### 8.6. Retry policy

Добавить в `RETRY_POLICIES`:

```python
"vpn_testing": {
    "max_retries": 2,
    "backoff": "exponential",
    "delays": [60, 300],
}
```

Runtime route failures не ретраить бесконечно: если route mismatch подтверждён двумя попытками — фиксировать `FAILED`.

---

## 9. Проверка всех тарифов

### 9.1. Цель

Проверить, что каждый тариф в каталоге:

1. Создаёт/обновляет Remnawave пользователя с правильными лимитами.
2. Получает правильные active internal squads.
3. Получает правильный external squad/template override.
4. Генерирует корректные subscription outputs.
5. Не получает чужие premium-фичи случайно.
6. Не ломается при renewal/update существующего пользователя.

### 9.2. Режимы проверки тарифов

#### Mode A: Catalog Contract

Без Remnawave. Проверяет pricing seed/DB:

```text
plan_code
visibility
active
sale_channels
device_limit
traffic_limit_bytes
features.remnawave_external_squad
features.remnawave_subscription_template
features.smart_routing
features.torrent_policy
features.tor_policy
```

#### Mode B: Provisioning Contract

Через fake gateway / unit-compatible path:

```text
build_stage1_paid_provisioning_request
RemnawaveStage1PaidProvisioningGateway
RemnawaveStage1ManualSubscriptionGateway
```

Проверяет payload:

```text
external_squad_uuid
active_internal_squads
expire_at
trafficLimitBytes
hwidDeviceLimit
trafficLimitStrategy
```

#### Mode C: Synthetic Remnawave User

Создаёт временного пользователя:

```text
username: cvpn_tester_{plan_code}_{run_id_short}
email: cvpn-tester+{run_id}@cyber-vpn.net
expireAt: now + 1 hour
trafficLimitBytes: minimum safe limit
hwidDeviceLimit: 1
```

После проверки:

```text
cleanup_policy = delete_after_run | disable_after_run | keep_canary
```

Production default:

```text
delete_after_run
```

Canary accounts:

```text
keep_canary
```

#### Mode D: Generated Subscription

Забирает subscription URL с user-agent matrix:

```text
ClashMetaForAndroid
Mihomo
Happ
V2RayTun
Sing-box
Browser
```

Проверяет:

```text
content-type
template markers
proxy-groups
rule-providers
rules
node names
unsupported transports
no secrets leakage
```

#### Mode E: Runtime Route

Запускает runtime agent и прогоняет домены.

### 9.3. All Tariffs matrix

Минимально проверять:

| Тариф | Проверка |
|---|---|
| public basic/plus/pro/max | default subscription contract, no Smart RU unless configured |
| hidden ru_start/ru_basic | old RU bundle compatibility, if still active |
| premium_smart_ru | full static + contract + generated + runtime |
| test/development | internal-only, no public leakage |

### 9.4. Fail conditions

All-tariffs run должен падать, если:

1. Активный тариф имеет `features.remnawave_subscription_template`, но template не существует.
2. Активный тариф имеет `features.remnawave_external_squad`, но external squad не существует.
3. `premium_smart_ru` не получает `CyberVPN Premium Smart RU`.
4. `premium_smart_ru` не получает `CYBERVPN_PREMIUM_SMART_RU_NODES`.
5. Любой non-premium тариф случайно получает Premium Smart RU template без явной настройки.
6. Generated subscription пустой.
7. Generated subscription содержит ноды вне разрешённого internal squad.
8. Runtime route для critical domains не совпадает.

---

## 10. Golden Route Registry — must-have №1

### 10.1. Проблема

Сейчас route expectations спрятаны внутри YAML и ручных объяснений. Это опасно:

- сложно понять, почему домен идёт через RU/EU;
- сложно ревьюить изменения;
- сложно тестировать регрессии;
- support requests будут приводить к хаотичным правкам YAML.

### 10.2. Решение

Создать **Golden Route Registry** — версионированный источник истины.

Файл:

```text
backend/src/application/vpn_testing/route_registry/premium_smart_ru_v1.yaml
```

Пример:

```yaml
registry_version: premium_smart_ru_v1
owner: infrastructure
entries:
  - key: gosuslugi_ru
    matcher_type: domain_suffix
    matcher_value: gosuslugi.ru
    expected_route: ru
    priority: 100
    reason: "Госуслуги требуют российский IP для стабильного доступа"
    severity: critical

  - key: yandex_market
    matcher_type: domain_suffix
    matcher_value: market.yandex.ru
    expected_route: ru
    priority: 100
    reason: "Российский маркетплейс"
    severity: critical

  - key: youtube
    matcher_type: domain_suffix
    matcher_value: youtube.com
    expected_route: eu
    priority: 90
    reason: "Глобальный сервис, не должен идти через RU"
    severity: critical

  - key: openai
    matcher_type: domain_suffix
    matcher_value: openai.com
    expected_route: eu
    priority: 90
    reason: "AI сервис"
    severity: critical

  - key: torrent_process
    matcher_type: process_regex
    matcher_value: '(?i).*torrent.*'
    expected_route: reject
    priority: 100
    reason: "Abuse policy"
    severity: critical
```

### 10.3. Использование

Route Registry используется:

1. Static analyzer — проверяет, что YAML содержит нужные rule-providers/rules.
2. Runtime agent — строит test matrix.
3. Admin UI — показывает, почему домен ожидается через RU/EU/BLOCK.
4. Support — добавляет candidates в registry через review process.
5. Balancer — не может рекомендовать маршруты, нарушающие registry.

### 10.4. Change control

Любое изменение registry должно иметь:

```text
owner
reason
support_case_id optional
risk_level
review_status
effective_from
```

---

## 11. CyberVPN Probe Network — must-have №2

### 11.1. Проблема

Проверять route через публичные сервисы типа `2ip`, `ipinfo`, `ipwho` ненадёжно:

- rate limits;
- блокировки;
- разные CDN;
- privacy issues;
- нестабильные ответы;
- нет контроля над DNS.

### 11.2. Решение

Развернуть собственные probe endpoints:

```text
https://probe-de.cyber-vpn.net/whoami
https://probe-nl.cyber-vpn.net/whoami
https://probe-ru-msk.cyber-vpn.net/whoami
https://probe-ru-spb.cyber-vpn.net/whoami
```

Ответ:

```json
{
  "probe_id": "de-frankfurt-01",
  "observed_ip": "203.0.113.10",
  "observed_asn": "AS...",
  "country": "DE",
  "region": "Hesse",
  "timestamp": "2026-07-01T07:00:00Z",
  "request_id": "...",
  "headers_hash": "..."
}
```

### 11.3. DNS canary

Добавить controlled domains:

```text
route-eu.probe.cyber-vpn.net
route-ru.probe.cyber-vpn.net
route-block.probe.cyber-vpn.net
route-dns-canary.probe.cyber-vpn.net
```

Использование:

- проверить DNS route;
- проверить fake-ip behavior;
- проверить no direct DNS leak;
- проверить IPv6 leak.

### 11.4. Probe service implementation

Минимальный сервис:

```text
services/vpn-probe/
```

Функции:

```text
GET /health
GET /whoami
GET /headers
GET /dns-canary/{token}
GET /latency
```

Security:

- no cookies;
- no PII;
- logs redact IP by default or store only /24 bucket;
- rate limit;
- allow test runner UA.

---

## 12. Template Release Gate — must-have №3

### 12.1. Цель

Нельзя выкатывать VPN template, который не прошёл тесты.

### 12.2. Gate states

```text
not_evaluated
running
passed
failed
overridden
expired
```

### 12.3. Gate policy

Для `CyberVPN Premium Smart RU` обязательны:

```text
static_template: PASS
semantic_route: PASS
remnawave_contract: PASS
generated_subscription: PASS
runtime_route_critical: PASS
node_plugin_contract: PASS
all_tariffs_no_regression: PASS
```

### 12.4. Интеграция с seed

После изменения:

```text
scripts/remnawave/seed-cybervpn-premium-smart-ru.sql
```

нужно запускать:

```text
POST /api/v1/admin/vpn-tester/runs
suite_id=premium_smart_ru_release_gate
```

Пока gate не passed:

- не показывать template как production-ready;
- не включать его для новых публичных продаж;
- разрешить только owner/super_admin override с mandatory reason.

### 12.5. CI/CD

Добавить GitHub/CI job:

```text
vpn-template-static-gate
```

Он запускает static/semantic checks без реального Remnawave.

Runtime gate запускается на staging/prod вручную или scheduled.

---

## 13. Abuse Sentinel — must-have №4

### 13.1. Цель

Проверять, что политика Torrent/TOR работает на нескольких слоях:

```text
client template
Remnawave node plugin
webhook logging
business reaction
admin visibility
```

### 13.2. Client-side checks

Проверить в YAML:

```text
torrent-clients -> 🧲 Torrents
тorrent-trackers -> 🧲 Torrents
тorrent-websites -> 🧲 Torrents
🧲 Torrents default -> REJECT
Tor inline -> ⛔ BLOCK
.onion -> ⛔ BLOCK
process regex tor/torbrowser/obfs4proxy/snowflake -> ⛔ BLOCK
```

### 13.3. Server-side checks

Проверить Remnawave Node Plugin:

```text
CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION
  torrentBlocker.enabled = true
  torrentBlocker.blockDuration >= 3600
  egressFilter.enabled = true
  egressFilter.blockedIps contains ext:tor-exit-nodes or ext:tor-relays
```

### 13.4. Safe TOR checks

Не выполнять реальные подключения к TOR network в production runtime suite.

Допустимые тесты:

- static rule check;
- DNS `.onion` expectation -> block;
- process-name synthetic check in controlled runner;
- egress list non-empty check;
- canary blocked IP from internal test list.

### 13.5. Safe torrent checks

Не скачивать torrent и не подключаться к swarm.

Допустимые тесты:

- static rule check;
- process-name synthetic check;
- tracker domain DNS/route expectation -> reject;
- Remnawave plugin config check;
- optional lab-only bittorrent signature test в изолированной среде, не в production.

### 13.6. Business reaction

Сейчас Remnawave webhook обрабатывается, валидируется, логируется и broadcast-ится. Добавить отдельную реакцию на:

```text
event = torrent_blocker.report
scope = torrent_blocker
```

Policy:

```text
1-е нарушение: warning + ticket/support note
2-е нарушение за 7 дней: temporary disable 24h или manual review
3-е нарушение: disable subscription + admin review
```

Эта бизнес-реакция должна быть отдельным feature flag:

```text
REMNAWAVE_ABUSE_AUTO_DISABLE_ENABLED=false
```

Default: `false` до ручного утверждения.

---

## 14. Runtime VPN Test Agent

### 14.1. Почему отдельный агент

Нельзя запускать Mihomo/TUN/Xray runtime тесты внутри FastAPI backend:

- нужны сетевые capabilities;
- возможны DNS/TUN side effects;
- тесты долгие;
- может быть conflict с production network namespace;
- нужно ограничение ресурсов.

Создать отдельный сервис:

```text
services/vpn-test-agent/
```

### 14.2. Режимы агента

#### Mode 1: Proxy-only

Без TUN. Агент запускает Mihomo с mixed-port и делает HTTP/DNS запросы через proxy.

Использовать для production scheduled checks.

#### Mode 2: TUN lab

С `NET_ADMIN`, отдельный network namespace, disposable container.

Использовать для staging/deep/lab checks.

#### Mode 3: Parser-only

Не запускает сеть, только анализирует YAML.

### 14.3. Agent API

```http
POST /v1/runs
GET /v1/runs/{id}
POST /v1/runs/{id}/cancel
GET /v1/health
```

Request:

```json
{
  "run_id": "uuid",
  "config_yaml_base64": "...",
  "mode": "proxy_only",
  "route_tests": [
    {
      "case_id": "gosuslugi_ru",
      "url": "https://gosuslugi.ru",
      "expected_route": "ru",
      "probe": "https://probe-ru-msk.cyber-vpn.net/whoami"
    }
  ],
  "timeout_seconds": 900
}
```

### 14.4. Agent outputs

```json
{
  "status": "passed|failed|degraded",
  "cases": [
    {
      "case_id": "gosuslugi_ru",
      "expected_route": "ru",
      "actual_exit_country": "RU",
      "actual_proxy_group": "🇷🇺 RU Sites",
      "actual_node": "🇷🇺 RU Moscow 01 25G",
      "latency_ms": 142,
      "dns_server_observed": "ru",
      "passed": true
    }
  ]
}
```

### 14.5. Resource limits

```text
CPU: 0.5–1.0
RAM: 256–512 MB
timeout: 15 min default
max parallel runs per agent: 1
max suite parallelism: configurable
```

---

## 15. Test Suite DSL

### 15.1. Suite file location

```text
backend/src/application/vpn_testing/suites/premium_smart_ru_v1.yaml
backend/src/application/vpn_testing/suites/all_tariffs_contract_v1.yaml
backend/src/application/vpn_testing/suites/default_subscription_smoke_v1.yaml
```

### 15.2. Example suite

```yaml
suite_id: premium_smart_ru_v1
name: CyberVPN Premium Smart RU Route Matrix
version: 1.0.0
modes:
  - static_template
  - remnawave_contract
  - generated_subscription
  - runtime_route

targets:
  plan_codes: [premium_smart_ru]
  templates: [CyberVPN Premium Smart RU]

synthetic_user:
  enabled: true
  cleanup_policy: delete_after_run

required_remnawave:
  external_squad: CYBERVPN_PREMIUM_SMART_RU
  internal_squad: CYBERVPN_PREMIUM_SMART_RU_NODES
  nodes:
    - 🇩🇪 DE Frankfurt 01 25G
    - 🇳🇱 NL Amsterdam 01 10G
    - 🇷🇺 RU Moscow 01 25G
    - 🇷🇺 RU SPB 01 25G
  node_plugin: CYBERVPN_PREMIUM_SMART_RU_ABUSE_PROTECTION

route_cases:
  - id: default_google
    type: domain
    value: google.com
    expected_route: eu
    expected_group: 🌍 World / EU
    severity: critical

  - id: gosuslugi
    type: domain
    value: gosuslugi.ru
    expected_route: ru
    expected_group: 🇷🇺 RU Sites
    severity: critical

  - id: yandex_market
    type: domain
    value: market.yandex.ru
    expected_route: ru
    expected_group: 🇷🇺 RU Sites
    severity: critical

  - id: youtube
    type: domain
    value: youtube.com
    expected_route: eu
    expected_group: 📺 YouTube
    severity: critical

  - id: openai
    type: domain
    value: openai.com
    expected_route: eu
    expected_group: 🤖 AI
    severity: critical

  - id: ads
    type: domain
    value: doubleclick.net
    expected_route: reject
    expected_group: REJECT
    severity: warning

  - id: torrent_process
    type: process_regex
    value: '(?i).*torrent.*'
    expected_route: reject
    expected_group: 🧲 Torrents
    severity: critical

leak_tests:
  dns: true
  ipv6: true
  direct_ip: true
```

---

## 16. Static Template Checks

### 16.1. YAML parse

Проверить:

```text
valid YAML
root object
required sections: dns, proxy-groups, rule-providers, rules
no duplicate proxy-group names
no duplicate rule-provider names
no undefined proxy-group references
no undefined rule-set references
no invalid remnawave custom fields
```

### 16.2. Premium Smart RU mandatory checks

```text
proxy-groups contains 🌍 World / EU
proxy-groups contains 🇩🇪 DE Auto
proxy-groups contains 🇳🇱 NL Auto
proxy-groups contains 🇷🇺 RU Sites
proxy-groups contains 🇷🇺 Moscow Auto
proxy-groups contains 🇷🇺 SPB Auto
World / EU default first proxy is 🇩🇪 DE Auto
RU Sites default first proxy is ⚡ RU Auto
MATCH final rule is MATCH,🌍 World / EU
ru-services-inline routes to 🇷🇺 RU Sites
geosite-ru routes to 🇷🇺 RU Sites
geoip-for-ru routes to 🇷🇺 RU Sites
ru-bundle/refilter/ru-inside routes to 🌍 World / EU
torrent routes to 🧲 Torrents
🧲 Torrents default is REJECT
tor-inline routes to ⛔ BLOCK
ads rules route to REJECT
```

### 16.3. Filters

Проверить, что location filters покрывают expected node names:

```text
🇩🇪 DE Frankfurt 01 25G -> DE Auto
🇳🇱 NL Amsterdam 01 10G -> NL Auto
🇷🇺 RU Moscow 01 25G -> RU Auto + Moscow Auto
🇷🇺 RU SPB 01 25G -> RU Auto + SPB Auto
```

---

## 17. Remnawave Contract Checks

### 17.1. Templates

Проверить:

```text
subscription_templates.name = CyberVPN Premium Smart RU
subscription_templates.template_type = MIHOMO
template_yaml hash matches expected seed/source hash or approved drift hash
```

### 17.2. External squad

Проверить:

```text
external_squads.name = CYBERVPN_PREMIUM_SMART_RU
external_squads_templates.template_type = MIHOMO
external_squads_templates.template_uuid -> CyberVPN Premium Smart RU
```

### 17.3. Internal squad

Проверить:

```text
internal_squads.name = CYBERVPN_PREMIUM_SMART_RU_NODES
contains expected inbounds
contains or enables expected nodes
```

### 17.4. Nodes

Проверить:

```text
DE node exists and connected
NL node exists and connected
RU Moscow node exists and connected
RU SPB node exists and connected
node versions compatible
xray versions compatible
node plugin assigned
```

### 17.5. Node Plugin

Проверить:

```text
plugin exists
torrentBlocker.enabled = true
egressFilter.enabled = true
sharedLists contain tor lists
plugin assigned to all Premium Smart RU nodes
```

---

## 18. Generated Subscription Checks

### 18.1. User-Agent matrix

Минимально:

```text
ClashMetaForAndroid
Mihomo
Happ
v2rayN
V2RayTun
Browser
```

Для каждого user-agent проверить expected response type.

### 18.2. Mihomo generated output

Для `premium_smart_ru`:

```text
YAML not empty
contains generated proxies
contains expected node remarks
contains proxy-groups
contains rule-providers
contains rules
contains DNS-OUT
contains Premium Smart RU marker
contains no raw secret/token
contains no local-only URL except allowed controller
```

### 18.3. Cross-plan regression

Для всех тарифов:

```text
non-smart plans should not accidentally receive CyberVPN Premium Smart RU template
smart plan must receive CyberVPN Premium Smart RU template
legacy ru_start/ru_basic behavior remains as configured
hidden/internal plans not exposed in public catalog unless intended
```

---

## 19. Runtime Route Matrix

### 19.1. Critical matrix для Premium Smart RU

| Case | Expected |
|---|---|
| google.com | EU/DE |
| cloudflare.com | EU/DE |
| youtube.com | EU/DE |
| discord.com | EU/DE |
| github.com | EU/DE |
| openai.com | EU/DE |
| chatgpt.com | EU/DE |
| gosuslugi.ru | RU |
| nalog.gov.ru | RU |
| yandex.ru | RU |
| market.yandex.ru | RU |
| ozon.ru | RU |
| wildberries.ru | RU |
| sberbank.ru | RU |
| tinkoff.ru/tbank.ru | RU |
| doubleclick.net | REJECT/BLOCK |
| torrent tracker domain | REJECT/BLOCK |
| `.onion` synthetic | BLOCK |
| IPv6 test | no leak/reject |
| DNS canary | expected resolver path |

### 19.2. How to identify actual route

Источники данных:

1. Mihomo controller current connections.
2. Selected proxy group.
3. Observed exit IP from CyberVPN Probe Network.
4. DNS canary observation.
5. Response status/error.
6. Optional pcap/lab only for deep diagnostics.

### 19.3. Pass/fail logic

`PASS` только если:

```text
expected group matched OR expected route country matched
AND no DNS leak
AND no IPv6 leak
AND no unexpected DIRECT
AND latency under threshold or warning only
```

Для critical cases route mismatch = `FAILED`.

Для non-critical latency degradation = `DEGRADED`.

---

## 20. Smart Balancer — future-ready, safe by design

### 20.1. Что делаем сейчас

В v1/v2 реализации балансир работает только как:

```text
recommendation-only
```

Он не меняет Remnawave и не правит YAML автоматически.

### 20.2. Inputs

```text
node availability
node latency
probe success rate
online users
load average
bandwidth utilization
route mismatch rate
subscription error rate
country/route constraints
capacity weights: DE 25G, NL 10G, RU Moscow 25G, RU SPB 25G
```

### 20.3. Hard constraints

Балансир не имеет права рекомендовать:

```text
RU services -> EU, если expected_route=ru
EU/global services -> RU, если expected_route=eu
blocked categories -> allow
premium_smart_ru -> node outside CYBERVPN_PREMIUM_SMART_RU_NODES
```

### 20.4. Recommendation examples

```json
{
  "scope": "world_eu",
  "recommendation": "keep_de_primary",
  "reason": "DE 25G healthy, latency lower than NL, no route failures",
  "confidence": 0.93
}
```

```json
{
  "scope": "ru_sites",
  "recommendation": "prefer_ru_spb_for_northwest_users",
  "reason": "SPB lower p95 latency for RU route probes",
  "confidence": 0.78
}
```

### 20.5. Future actuation stages

```text
Stage 0: metrics only
Stage 1: recommendations only
Stage 2: admin-approved canary changes
Stage 3: automatic canary with rollback
Stage 4: production automatic balancing with strict policy gates
```

---

## 21. Observability

### 21.1. Backend metrics

Добавить в `backend/src/infrastructure/monitoring/metrics.py`:

```python
vpn_tester_runs_total = Counter(
    "cybervpn_vpn_tester_runs_total",
    "VPN tester runs by suite, mode and status",
    ["suite_id", "mode", "status"],
)

vpn_tester_case_results_total = Counter(
    "cybervpn_vpn_tester_case_results_total",
    "VPN tester case results by category and status",
    ["category", "severity", "status"],
)

vpn_tester_run_duration_seconds = Histogram(
    "cybervpn_vpn_tester_run_duration_seconds",
    "VPN tester run duration",
    ["suite_id", "mode"],
)

vpn_tester_tariff_coverage_current = Gauge(
    "cybervpn_vpn_tester_tariff_coverage_current",
    "Current tariff coverage by plan_code and level",
    ["plan_code", "coverage_level", "status"],
)

vpn_tester_route_mismatch_total = Counter(
    "cybervpn_vpn_tester_route_mismatch_total",
    "Route mismatches by expected and actual route",
    ["suite_id", "expected_route", "actual_route", "severity"],
)

vpn_tester_probe_health_current = Gauge(
    "cybervpn_vpn_tester_probe_health_current",
    "Probe endpoint health",
    ["probe_id", "region"],
)
```

### 21.2. Avoid high cardinality

Нельзя добавлять в labels:

```text
run_id
user_uuid
subscription_url
domain
node uuid, если нод много и динамично
raw error
```

`run_id` и domain остаются в БД/evidence, не в Prometheus labels.

### 21.3. Alerts

Alert rules:

```text
Premium Smart RU critical route failed
All tariffs coverage failed
Node plugin missing on smart node
Probe network down
DNS leak detected
IPv6 leak detected
Template release gate failed
Synthetic user cleanup failed
Runtime agent unavailable
```

---

## 22. Security and Privacy

### 22.1. Secrets

Никогда не хранить raw:

```text
subscription URL
Remnawave token
user UUID in public evidence
short UUID
proxy password/uuid/private key
```

Хранить:

```text
sha256 fingerprint
redacted preview
last 6 chars only for operator correlation
```

### 22.2. Synthetic users

Production synthetic users:

```text
username prefix: cvpn_tester_
email domain: cyber-vpn.net
expire short
traffic minimal
not visible to public users
cleanup mandatory
```

Если cleanup failed:

```text
status = DEGRADED
create support/operator alert
retry cleanup task
```

### 22.3. Runtime agent isolation

```text
separate container
no host network unless lab mode
resource limits
network egress allowlist when possible
no access to main DB
receives only redacted/minimal config payload
short-lived job token
```

### 22.4. Admin audit

Audit events:

```text
vpn_tester.run.created
vpn_tester.run.cancelled
vpn_tester.schedule.created
vpn_tester.schedule.updated
vpn_tester.release_gate.override
vpn_tester.balancer.recommendation.approved
vpn_tester.balancer.recommendation.rejected
```

---

## 23. Conflict Analysis and Prevention

### 23.1. FastAPI blocking conflict

**Риск:** runtime-тесты блокируют API.
**Решение:** API только создаёт run и ставит TaskIQ job. Runtime делает worker/agent.

### 23.2. Raw Remnawave calls conflict

**Риск:** новый код начнёт ходить в Remnawave в обход existing client.
**Решение:** только gateways поверх `RemnawaveClient`.

### 23.3. Admin RBAC conflict

**Риск:** новые permissions сломают навигацию и доступ.
**Решение:** первая версия использует существующие `server_read`, `monitoring_read`, `server_update`, `manage_plans`; отдельные `vpn_tester_*` permissions — позже.

### 23.4. OpenAPI/generated types conflict

**Риск:** admin API client types не обновлены.
**Решение:** после добавления routes обязательно обновить:

```text
backend/docs/api/openapi.json
admin/src/lib/api/generated/types.ts
frontend/src/lib/api/generated/types.ts, если affected
```

И прогнать generated artifacts guardrail.

### 23.5. Task Worker queue conflict

**Риск:** новые tasks перегружают monitoring queue.
**Решение:** отдельная queue `vpn_testing`; ограничение concurrency; skip-if-running locks.

### 23.6. Production network conflict

**Риск:** TUN runtime тест ломает сеть контейнера/хоста.
**Решение:** production default = proxy-only mode; TUN mode только в isolated lab/staging runner.

### 23.7. Remnawave node plugin conflict

**Риск:** tester случайно меняет plugin config.
**Решение:** tester по умолчанию read-only. Любые remediation actions — отдельный manual approve flow.

### 23.8. Synthetic user conflict

**Риск:** тестовые пользователи попадут в аналитику/биллинг/support.
**Решение:** username prefix, internal flag/metadata, short expiry, cleanup, exclude from business analytics where possible.

### 23.9. Metrics cardinality conflict

**Риск:** Prometheus взорвётся от labels по domain/run_id.
**Решение:** bounded labels only; details in DB/evidence.

### 23.10. Balancer unsafe mutation conflict

**Риск:** балансир начнёт менять routing и ломать пользователей.
**Решение:** v1/v2 recommendation-only; actuation только после отдельного approved ТЗ.

### 23.11. Abuse test legal/abuse conflict

**Риск:** реальные TOR/torrent действия в production.
**Решение:** только safe synthetic checks; lab-only deep abuse tests.

### 23.12. Subscription leakage conflict

**Риск:** evidence содержит рабочие subscription links.
**Решение:** redaction layer mandatory; tests fail если artifact содержит `/api/sub/` с full token/short uuid.

---

## 24. Implementation Plan

### Milestone 0 — Foundation alignment

- Утвердить v2 ТЗ.
- Создать feature flag:

```text
VPN_TESTER_ENABLED=false
VPN_TESTER_RUNTIME_ENABLED=false
VPN_TESTER_SYNTHETIC_USERS_ENABLED=false
VPN_TESTER_SCHEDULED_ENABLED=false
VPN_TESTER_BALANCER_RECOMMENDATIONS_ENABLED=false
```

### Milestone 1 — Backend DB/domain/API skeleton

- Миграции таблиц.
- Domain entities.
- Repositories.
- API endpoints overview/runs/suites/results.
- Basic static run без runtime.
- Tests.

### Milestone 2 — Admin UI

- Navigation item.
- API client methods.
- Page `/infrastructure/vpn-tester`.
- Overview, Runs, All Tariffs, Evidence tabs.
- Basic manual run.

### Milestone 3 — Task Worker

- Queue constants.
- Tasks.
- Schedules.
- Locks.
- Metrics.
- On-demand run from backend.

### Milestone 4 — Static/Semantic Analyzer

- YAML parser.
- Reference validation.
- Premium Smart RU semantic checks.
- Route Registry integration.

### Milestone 5 — Remnawave Contract + All Tariffs

- Remnawave contract checker.
- Tariff coverage builder.
- Synthetic user contract mode.
- All active tariff matrix.

### Milestone 6 — Runtime Agent

- `services/vpn-test-agent`.
- Proxy-only runtime.
- Mihomo controller/log parser.
- Route matrix critical suite.

### Milestone 7 — Probe Network

- `services/vpn-probe`.
- Probe endpoints in DE/NL/RU.
- DNS canary.
- Probe health dashboard.

### Milestone 8 — Release Gate

- Gate policy.
- Evidence requirement.
- Admin override with audit.
- CI static gate.

### Milestone 9 — Abuse Sentinel

- Plugin contract checks.
- Safe TOR/torrent tests.
- Webhook business-reaction design behind feature flag.

### Milestone 10 — Balancer Preview

- Recommendation-only engine.
- Admin preview.
- No actuation.

---

## 25. Acceptance Criteria

### 25.1. Admin

- Admin sees `/infrastructure/vpn-tester`.
- Admin can run `Premium Smart RU` suite manually.
- Admin can run `All Tariffs` check manually.
- Admin sees live status and historical runs.
- Admin can download evidence markdown/json.
- Admin can enable/disable schedules.
- Viewer/support roles cannot run destructive/deep actions.

### 25.2. Backend

- All endpoints protected by roles/permissions.
- No long-running checks in request lifecycle.
- Runs persisted.
- Results persisted.
- Evidence redacted.
- OpenAPI regenerated.
- Unit/integration/security tests added.

### 25.3. Task Worker

- Scheduled lightweight suite runs every 15 min when enabled.
- All-tariffs contract suite runs hourly when enabled.
- Deep suite runs daily when enabled.
- Locks prevent duplicate runs.
- Failed scheduled tests alert admins.

### 25.4. Premium Smart RU

Must pass:

```text
DE is default World/EU route
RU services route to RU Sites
YouTube/Discord/AI/GitHub route to EU
RU exceptions route to EU
Ads reject
Torrent reject
TOR block
DNS no leak
IPv6 no leak
Node plugin assigned
Expected squads present
Expected nodes present
```

### 25.5. All Tariffs

- Every active tariff has at least contract coverage.
- Critical/smart tariffs have runtime coverage.
- Non-smart tariffs do not accidentally receive Smart RU template.
- Hidden/internal tariffs are not public unless explicitly configured.

### 25.6. Conflict-free

- No raw Remnawave calls outside gateways/client.
- No TUN in backend container.
- No high-cardinality metrics.
- No subscription URL leakage.
- No automatic balancer mutation.
- No real torrent/TOR production abuse tests.

---

## 26. Test Plan

### 26.1. Backend tests

```text
backend/tests/unit/vpn_testing/test_route_registry.py
backend/tests/unit/vpn_testing/test_template_static_analyzer.py
backend/tests/unit/vpn_testing/test_template_semantic_analyzer.py
backend/tests/unit/vpn_testing/test_tariff_coverage_builder.py
backend/tests/unit/vpn_testing/test_evidence_redaction.py
backend/tests/integration/api/v1/admin/test_vpn_tester_routes.py
backend/tests/security/test_vpn_tester_rbac.py
backend/tests/security/test_vpn_tester_secret_redaction.py
backend/tests/contract/remnawave/test_vpn_tester_remnawave_contract.py
```

### 26.2. Task Worker tests

```text
services/task-worker/tests/unit/tasks/vpn_testing/test_run_suite.py
services/task-worker/tests/unit/tasks/vpn_testing/test_run_all_tariffs.py
services/task-worker/tests/unit/tasks/vpn_testing/test_locks.py
services/task-worker/tests/integration/test_vpn_testing_schedules.py
```

### 26.3. Admin tests

```text
admin/src/features/vpn-tester/__tests__/vpn-tester-page.test.tsx
admin/src/features/vpn-tester/__tests__/run-builder.test.tsx
admin/src/features/vpn-tester/__tests__/tariff-coverage-table.test.tsx
admin/src/features/admin-shell/config/__tests__/admin-navigation.test.ts
```

### 26.4. Runtime agent tests

```text
services/vpn-test-agent/tests/test_config_loader.py
services/vpn-test-agent/tests/test_mihomo_runner.py
services/vpn-test-agent/tests/test_route_result_parser.py
services/vpn-test-agent/tests/test_redaction.py
```

---

## 27. Definition of Done

Готовность считается достигнутой, если:

1. ТЗ реализовано по milestones 1–5 минимум.
2. Admin может вручную проверить `CyberVPN Premium Smart RU`.
3. Admin может вручную проверить все тарифы.
4. Task Worker может запускать scheduled checks.
5. Evidence скачивается из админки.
6. Premium Smart RU проходит static/contract/generated subscription checks.
7. Runtime route checks проходят на staging.
8. Production scheduled lightweight checks включаются feature flag-ом.
9. Нет утечек subscription URLs/secrets в логах/evidence.
10. Release gate блокирует promotion при critical fail.

---

## 28. Рекомендуемый первый scope реализации

Чтобы получить пользу быстро и без риска, реализовать в таком порядке:

```text
1. Backend DB + API runs/results/evidence
2. Static/Semantic analyzer
3. Admin UI basic page
4. All Tariffs contract mode
5. Task Worker scheduled contract mode
6. Runtime agent proxy-only для Premium Smart RU
7. Probe Network
8. Release Gate
9. Balancer Preview
```

Минимальный полезный MVP:

```text
Admin UI -> Run Premium Smart RU static+contract+generated subscription
Admin UI -> Run All Tariffs contract
Task Worker -> hourly All Tariffs contract
Evidence markdown download
```

После MVP переходить к runtime agent и probe network.

---

## 29. Критическое замечание

Не пытаться сразу делать автоматическую балансировку, которая меняет production routing. Сначала tester должен накопить достоверную историю:

```text
latency
availability
route correctness
node load
subscription generation failures
probe health
```

Только после этого можно переходить к canary balancing. Иначе балансир будет автоматизировать неизвестное состояние.
