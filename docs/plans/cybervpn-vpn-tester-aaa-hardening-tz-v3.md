# Техническое задание v3: Доведение CyberVPN VPN Tester до уровня AAA+ Enterprise

**Проект:** CyberVPN  
**Модуль:** VPN Tester / VPN Quality Gate / Smart Routing Verification  
**Версия ТЗ:** v3.0  
**Дата:** 2026-07-01  
**Статус:** Ready for implementation  
**Цель:** доработать текущую реализацию VPN Tester v2 из состояния `MVP Foundation` до полноценного enterprise-grade решения, которое реально проверяет шаблоны, тарифы, Remnawave contracts, generated subscriptions, runtime маршрутизацию, abuse-policy, release-gate и будущую балансировку.

---

## 0. Executive Summary

Текущий VPN Tester v2 уже добавил важную инфраструктурную базу:

- backend admin API `/api/v1/admin/vpn-tester/*`;
- таблицы `vpn_test_*`, `vpn_route_registry_entries`, `vpn_balancer_recommendations`;
- admin UI `/infrastructure/vpn-tester`;
- Task Worker задачи и cron schedules;
- базовые suite DSL / route registry;
- release gate endpoint;
- balancer preview endpoint;
- feature flags;
- safe evidence previews.

Однако текущая версия пока **не доказывает фактическую корректность VPN-шаблонов и маршрутизации**. Основной функционал пока проверяет metadata, наличие тарифов, route registry и Remnawave nodes snapshot, но не проверяет:

- реальный Mihomo YAML semantic contract;
- generated subscription output;
- маршрутизацию доменов по Golden Route Matrix;
- DNS / IPv6 leaks;
- Torrent / TOR policy на runtime и server policy уровнях;
- фактическую выдачу template/internal/external squads по всем тарифам;
- реальное управление scheduled runs из админки;
- persistent release-gate override;
- Prometheus metrics / alerts;
- безопасный enterprise balancer recommendation lifecycle.

Цель v3 — закрыть эти пробелы без полумер.

---

## 1. Ключевые проблемы текущей реализации

### 1.1. P0: Admin schedule toggles не управляют реальными scheduled runs

Сейчас в БД есть `vpn_test_schedules.enabled`, UI умеет включать/выключать расписания, backend умеет обновлять schedule, но Task Worker scheduled tasks фактически смотрят только на ENV-флаги:

```text
VPN_TESTER_ENABLED
VPN_TESTER_SCHEDULED_ENABLED
```

И не проверяют конкретную запись `vpn_test_schedules.enabled`.

**Риск:** админ может выключить schedule в UI, но worker продолжит запускать проверки.

**Целевое поведение:** каждый scheduled task обязан проходить через backend schedule gate, который проверяет:

- глобальный `VPN_TESTER_ENABLED`;
- глобальный `VPN_TESTER_SCHEDULED_ENABLED`;
- наличие schedule в `vpn_test_schedules`;
- `vpn_test_schedules.enabled`;
- idempotency window;
- lock policy;
- next_run/last_run metadata.

---

### 1.2. P0: Runtime mode фактически не реализован

API принимает `mode=runtime`, но `VpnTesterService.execute_run()` пока отправляет runtime в обычные contract checks.

**Риск:** включение `VPN_TESTER_RUNTIME_ENABLED=true` даст ложное ощущение runtime-проверки.

**Целевое поведение:** `mode=runtime` должен запускать отдельный runtime executor через `vpn-test-agent`, а backend/worker не должны поднимать TUN или менять маршруты внутри своих контейнеров.

---

### 1.3. P0: All Tariffs mode поверхностный

Текущий `all_tariffs` проверяет только:

- `plan_code`;
- `connection_modes`;
- `server_pool` / `traffic_policy` metadata;
- visibility.

Этого недостаточно для VPN contract.

**Целевое поведение:** для каждого активного тарифа нужно проверять:

- expected `external_squad_uuid`;
- expected `active_internal_squads`;
- expected template override;
- generated subscription for MIHOMO / XRAY_BASE64 / XRAY_JSON / HAPP where applicable;
- absence of Premium Smart RU groups for non-smart tariffs;
- presence of Premium Smart RU groups only for smart tariffs;
- device limit / HWID behavior;
- traffic limit behavior;
- support of target client type;
- fail-closed behavior при missing squads/settings.

---

### 1.4. P0: Release gate override не сохраняется

Endpoint `/release-gate/override` сейчас возвращает override response, но не сохраняет факт override.

**Риск:** audit trail отсутствует; после следующего запроса override исчезает.

**Целевое поведение:** override должен быть persisted, audited, time-limited и видимым в UI.

---

### 1.5. P1: Route Registry слишком маленький

Текущий registry содержит только RU Moscow / RU SPB. Для проверки Premium Smart RU нужен полноценный Golden Route Registry.

**Целевое покрытие:**

- default internet -> DE/EU;
- NL fallback;
- RU services -> RU;
- RU exceptions -> EU;
- YouTube -> EU;
- Discord -> EU;
- Telegram -> EU/RU selector policy;
- AI -> EU;
- GitHub/dev -> EU;
- ads/trackers -> REJECT;
- Torrent -> REJECT;
- TOR -> BLOCK;
- DNS -> expected resolver policy;
- IPv6 -> REJECT / no leak.

---

### 1.6. P1: Нет полноценного Mihomo static/semantic analyzer

Сейчас не проверяется реальный YAML шаблона.

**Целевое поведение:** tester должен уметь парсить Mihomo template YAML и проверять:

- наличие обязательных proxy-groups;
- корректный default route;
- порядок правил;
- наличие rule-providers;
- наличие DNS policy;
- `remnawave.include-proxies: false` там, где требуется;
- корректность `filter`/`exclude-filter` для DE/NL/RU;
- отсутствие опасных DIRECT/MATCH ошибок;
- отсутствие секретов/URL подписок в evidence.

---

### 1.7. P1: Нет observability уровня AAA+

Нет специализированных Prometheus metrics, alert rules и structured events для VPN Tester.

**Целевое поведение:** каждая проверка, suite, schedule, release gate и balancer recommendation должны быть наблюдаемыми.

---

## 2. Целевые принципы v3

### 2.1. Safety-first

Backend и Task Worker не должны менять сетевые маршруты хоста/контейнера. Runtime-проверки выполняются только через отдельный `vpn-test-agent`.

### 2.2. Read-only by default

Все проверки по умолчанию read-only. Любые synthetic users, runtime probes, balancer actuation — только через отдельные feature flags.

### 2.3. Evidence без секретов

Никаких raw subscription URLs, UUID пользователей, JWT, cookies, private keys, passwords, tokens и полных configs в evidence.

### 2.4. Idempotency everywhere

Manual и scheduled runs должны иметь idempotency key, чтобы не создавать дубли при повторном клике, retry или cron overlap.

### 2.5. Enterprise release gate

Release gate должен быть воспроизводимым, сохраняемым, audit-grade и интегрируемым в deploy pipeline.

### 2.6. No false PASS

Если проверка не выполнена, это `skipped` или `degraded`, но не `pass`. Runtime mode без runtime agent не может возвращать pass.

---

## 3. Архитектура v3

```text
Admin UI
  /infrastructure/vpn-tester
        |
        v
Backend Admin API
  /api/v1/admin/vpn-tester/*
        |
        +--> VpnTesterService
        |       |
        |       +--> Static/Semantic Analyzer
        |       +--> Generated Subscription Checker
        |       +--> All Tariffs Contract Checker
        |       +--> Release Gate Service
        |       +--> Balancer Recommendation Service
        |       +--> Evidence Redaction Service
        |
        +--> PostgreSQL tables
        |
        +--> Remnawave API Client
        |
        +--> Task Worker internal endpoints
                |
                v
Task Worker
  scheduled tasks / queue consumer
        |
        v
vpn-test-agent fleet
  DE probe / NL probe / RU probe / local lab agent
        |
        v
Mihomo runtime / proxy-only / later TUN sandbox
```

---

## 4. P0 доработки

# 4.1. Schedule Gate v3

## 4.1.1. Новые backend endpoints

Добавить internal endpoint:

```http
POST /api/v1/admin/vpn-tester/internal/schedules/{schedule_key}/run
Headers:
  X-Backend-Internal-Secret: <secret>
Body:
{
  "trigger": "scheduled_lightweight",
  "execute_immediately": true,
  "idempotency_window": "minute"
}
```

Ответ:

```json
{
  "skipped": false,
  "reason": null,
  "run": {...},
  "schedule": {
    "schedule_key": "vpn-tester:lightweight",
    "enabled": true,
    "last_run_id": "...",
    "last_status": "pass",
    "next_run_at": "..."
  }
}
```

Если schedule выключен:

```json
{
  "skipped": true,
  "reason": "schedule_disabled",
  "run": null
}
```

## 4.1.2. Backend service logic

Добавить метод:

```python
async def run_schedule(
    schedule_key: str,
    trigger: str,
    execute_immediately: bool,
    idempotency_window: Literal["minute", "hour", "day"],
) -> ScheduledRunResult:
    ...
```

Логика:

1. `ensure_seeded()`.
2. Проверить `settings.vpn_tester_enabled`.
3. Проверить `settings.vpn_tester_scheduled_enabled`.
4. Найти schedule по `schedule_key`.
5. Если не найден — `skipped: schedule_not_found`.
6. Если `enabled=false` — `skipped: schedule_disabled`.
7. Сформировать idempotency key:

```text
scheduled:{schedule_key}:{suite_key}:{mode}:{YYYYMMDDHHMM}
```

8. Создать run или вернуть existing.
9. Если `execute_immediately=true`, выполнить run.
10. Обновить schedule:

```text
last_run_id
last_status
next_run_at
updated_at
```

## 4.1.3. Task Worker changes

Заменить текущий вызов:

```python
backend.run_scheduled_vpn_tester({...})
```

на:

```python
backend.run_vpn_tester_schedule(
    schedule_key="vpn-tester:lightweight",
    payload={"trigger": "scheduled_lightweight", "execute_immediately": True}
)
```

Task Worker не должен решать, включён schedule или нет. Он только вызывает backend schedule gate.

## 4.1.4. Acceptance criteria

- Если schedule disabled в UI, worker task возвращает `skipped:schedule_disabled`.
- Если global `VPN_TESTER_SCHEDULED_ENABLED=false`, worker task возвращает `skipped:scheduled_disabled`.
- Повторный cron в пределах idempotency window не создаёт второй run.
- `last_run_id`, `last_status`, `next_run_at` обновляются.
- UI показывает skipped reason.

---

# 4.2. Runtime Mode v3 через vpn-test-agent

## 4.2.1. Новый сервис: `services/vpn-test-agent`

Создать новый сервис:

```text
services/vpn-test-agent/
├── src/
│   ├── main.py
│   ├── config.py
│   ├── api.py
│   ├── runners/
│   │   ├── mihomo_static.py
│   │   ├── mihomo_proxy_runtime.py
│   │   └── mihomo_tun_runtime.py
│   ├── probes/
│   │   ├── dns_probe.py
│   │   ├── http_probe.py
│   │   ├── route_probe.py
│   │   ├── leak_probe.py
│   │   └── abuse_probe.py
│   ├── models.py
│   └── redaction.py
├── Dockerfile
├── pyproject.toml
└── README.md
```

## 4.2.2. Агентные режимы

### Mode 1: `static`

Без сетевого подключения. Проверяет YAML и semantic rules.

### Mode 2: `proxy-only`

Поднимает Mihomo с локальным mixed-port и отправляет probe requests через proxy. Не требует TUN.

### Mode 3: `tun-sandbox`

Опционально, только в lab/staging. Требует `NET_ADMIN`, отдельного network namespace и отдельного контейнера. В production по умолчанию выключено.

## 4.2.3. Agent API

```http
POST /internal/v1/runtime-checks
Headers:
  X-VPN-Test-Agent-Secret: <secret>
Body:
{
  "run_id": "...",
  "suite_key": "premium_smart_ru_v1",
  "mode": "proxy-only",
  "subscription_yaml": "<redacted-or-mounted-artifact-ref>",
  "route_matrix": [...],
  "timeout_seconds": 120
}
```

Response:

```json
{
  "status": "pass|fail|degraded|skipped",
  "results": [
    {
      "check_key": "runtime.route.gosuslugi_ru",
      "status": "pass",
      "expected_exit": "RU",
      "observed_exit": "RU",
      "safe_summary": "gosuslugi.ru exited via RU probe"
    }
  ],
  "evidence": [
    {
      "artifact_key": "runtime-summary",
      "sha256": "...",
      "preview": {...}
    }
  ]
}
```

## 4.2.4. Runtime branch in backend

В `VpnTesterService.execute_run()` добавить:

```python
elif run.mode == "runtime":
    results = await self._runtime_results(run, suite_spec, plans, route_entries)
```

Если `VPN_TESTER_RUNTIME_ENABLED=false`, runtime run должен возвращать `skipped`, а не contract pass.

## 4.2.5. Acceptance criteria

- Runtime mode без enabled flag не возвращает `pass`.
- Runtime mode без agent не возвращает `pass`; допустимо `degraded: agent_unavailable`.
- Runtime mode proxy-only проверяет минимум 10 доменов из Golden Route Matrix.
- Runtime evidence не содержит raw subscription URL или полный YAML.

---

# 4.3. All Tariffs Contract v3

## 4.3.1. Цель

Проверить не просто metadata тарифов, а фактическую выдачу VPN-доступа по каждому active plan.

## 4.3.2. Проверки для каждого тарифа

Для каждого `SubscriptionPlanModel.is_active=true` выполнить:

### Basic metadata

- `plan_code` exists;
- `duration_days` valid;
- `device_limit` valid;
- `traffic_policy` valid;
- `catalog_visibility` valid.

### Provisioning dry-run

Добавить backend-only dry-run function:

```python
def build_expected_remnawave_assignment(plan: SubscriptionPlanModel) -> ExpectedRemnawaveAssignment:
    ...
```

Она должна возвращать:

```python
@dataclass(frozen=True)
class ExpectedRemnawaveAssignment:
    plan_code: str
    external_squad_uuid: str | None
    active_internal_squads: list[str]
    expected_template_name: str | None
    expected_template_type: str | None
    expected_client_types: list[str]
    expected_profile_id: str
```

### Remnawave contract

- Для `premium_smart_ru`:
  - `external_squad_uuid == settings.remnawave_smart_ru_external_squad_uuid`;
  - `active_internal_squads == [settings.remnawave_smart_ru_internal_squad_uuid]`;
  - template name `CyberVPN Premium Smart RU`;
  - MIHOMO output must contain Premium Smart RU groups.

- Для обычных тарифов:
  - не должны случайно получать Premium Smart RU external squad;
  - не должны получать Premium Smart RU internal squad, если это не ожидается.

### Generated subscription checks

Для каждого plan family минимум один synthetic dry-run subject:

```text
cvpn_test_<plan_code>_<timestamp>
```

Но в production synthetic users должны быть выключены по умолчанию. Если `VPN_TESTER_SYNTHETIC_USERS_ENABLED=false`, generated subscription checks работают в mock/dry-run mode, а не создают пользователя.

## 4.3.3. Acceptance criteria

- All tariffs run ловит отсутствие `premium_smart_ru`.
- All tariffs run ловит ошибочный Premium Smart RU squad у обычного тарифа.
- All tariffs run ловит отсутствие internal squad у smart tariff.
- All tariffs run ловит отсутствие generated Mihomo groups у smart tariff.
- All tariffs run не создаёт production users без флага synthetic enabled.

---

# 4.4. Persistent Release Gate Override

## 4.4.1. Новая таблица

Добавить таблицу:

```text
vpn_test_release_gate_overrides
```

Поля:

```text
id UUID PK
latest_run_id UUID NULL FK vpn_test_runs.id ON DELETE SET NULL
overridden_by_admin_id UUID NOT NULL FK admin_users.id ON DELETE RESTRICT
previous_status VARCHAR(24) NOT NULL
previous_blocking BOOLEAN NOT NULL
reason TEXT NOT NULL
expires_at TIMESTAMPTZ NOT NULL
created_at TIMESTAMPTZ NOT NULL
request_context JSONB NOT NULL DEFAULT '{}'
```

Индексы:

```text
ix_vpn_test_release_gate_overrides_expires_at
ix_vpn_test_release_gate_overrides_created_at
ix_vpn_test_release_gate_overrides_admin
```

## 4.4.2. API changes

```http
POST /api/v1/admin/vpn-tester/release-gate/override
Body:
{
  "reason": "Emergency hotfix deployment after manual VPN Tester verification",
  "ttl_minutes": 1440
}
```

Правила:

- только `owner/super_admin` или `super_admin`;
- `reason` обязателен, минимум 20 символов;
- `ttl_minutes` максимум 1440 для super_admin, максимум 4320 для owner/super_admin;
- override visible в `/release-gate`;
- override истекает автоматически.

## 4.4.3. Audit

Добавить audit event:

```text
vpn_tester.release_gate_override.created
```

С safe payload:

```json
{
  "override_id": "...",
  "latest_run_id": "...",
  "ttl_minutes": 1440,
  "previous_status": "fail"
}
```

## 4.4.4. Acceptance criteria

- Override сохраняется в БД.
- Повторный `/release-gate` показывает active override.
- После истечения TTL gate снова считается по latest run.
- Override без reason отклоняется.
- Override не доступен admin/operator/viewer.

---

# 4.5. RBAC v3

## 4.5.1. Read endpoints

```text
GET /overview
GET /runs
GET /runs/{id}
GET /runs/{id}/evidence
GET /schedules
GET /release-gate
GET /balancer/preview
```

Permissions:

```text
SERVER_READ OR MONITORING_READ
```

## 4.5.2. Tariff matrix

```text
GET /tariffs
```

Permissions:

```text
SERVER_READ OR MONITORING_READ OR MANAGE_PLANS
```

Если нет `MANAGE_PLANS`, скрыть чувствительные коммерческие поля, но не ломать UI.

## 4.5.3. Mutations

```text
POST /runs
POST /runs/{id}/cancel
```

Permissions:

```text
SERVER_UPDATE OR MANAGE_PLANS
```

Не разрешать mutation только по `MONITORING_READ`.

## 4.5.4. Schedule mutations

```text
PUT /schedules/{schedule_key}
```

Permissions:

```text
SERVER_UPDATE AND MANAGE_PLANS
```

## 4.5.5. UI requirements

- Если нет mutation permissions — скрыть или disable queue/cancel/toggle buttons.
- 403/409 ошибки показывать человекочитаемо.
- Read-only оператор должен видеть состояние, но не менять расписания.

---

## 5. P1 доработки

# 5.1. Mihomo Static/Semantic Analyzer

## 5.1.1. Новый модуль

```text
backend/src/application/vpn_testing/analyzers/mihomo.py
```

## 5.1.2. Вход

```python
class MihomoTemplateAnalysisRequest(BaseModel):
    template_name: str
    template_yaml: str
    suite_key: str
```

## 5.1.3. Проверки

### YAML parse

- YAML валиден;
- root object dict;
- `proxy-groups` list;
- `rules` list;
- `rule-providers` dict;
- `dns` dict.

### Required groups

Для Premium Smart RU:

```text
🌍 World / EU
🇩🇪 DE Auto
🇳🇱 NL Auto
🇷🇺 RU Sites
⚡ RU Auto
🇷🇺 Moscow Auto
🇷🇺 SPB Auto
📺 YouTube
💬 Discord
➤ Telegram
🤖 AI
👨‍💻 Dev Services
🧲 Torrents
⛔ BLOCK
```

### Default route

Проверить:

```yaml
- MATCH,🌍 World / EU
```

### Rule order invariants

Должны выполняться:

```text
ads/torrent/tor before MATCH
ru-eu-exceptions before ru-services-inline
ru-bundle/refilter before geosite-ru
ru-services-inline before MATCH
geoip-for-ru before MATCH
```

### Remnawave group invariants

Для location groups:

```yaml
remnawave:
  include-proxies: false
include-all: true
filter: ...
```

### DNS policy invariants

Проверить:

- `enhanced-mode: fake-ip`;
- `fake-ip-range` exists;
- `nameserver-policy` exists;
- RU services DNS -> RU Sites;
- global services DNS -> World/EU;
- adblock DNS -> `rcode://success` or equivalent.

### Abuse policy invariants

- torrent providers exist;
- torrent rules route to `🧲 Torrents`;
- `🧲 Torrents` default path is `REJECT`;
- tor-inline exists;
- tor process regex exists;
- TOR routes to `⛔ BLOCK`.

## 5.1.4. Acceptance criteria

- Analyzer fails if `MATCH,DIRECT` appears in Premium Smart RU.
- Analyzer fails if RU services route after MATCH.
- Analyzer fails if `ru-eu-exceptions` is below `ru-services-inline`.
- Analyzer fails if location groups include all proxies without filter.
- Analyzer detects missing `🇩🇪 DE Auto`, `🇷🇺 RU Sites`, `🧲 Torrents`.

---

# 5.2. Golden Route Registry v2

## 5.2.1. Расширить registry

Файл:

```text
backend/src/application/vpn_testing/route_registry/premium_smart_ru_v2.yaml
```

Пример структуры:

```yaml
registry_key: premium_smart_ru_v2
suite_key: premium_smart_ru_v1
version: v2
routes:
  - route_key: default-google
    target: google.com
    expected_policy: EU
    expected_group: 🌍 World / EU
    preferred_exit_country: DE
    fallback_exit_countries: [NL]
    severity: error

  - route_key: ru-gosuslugi
    target: gosuslugi.ru
    expected_policy: RU
    expected_group: 🇷🇺 RU Sites
    allowed_exit_countries: [RU]
    severity: error

  - route_key: eu-youtube
    target: youtube.com
    expected_policy: EU
    expected_group: 📺 YouTube
    allowed_exit_countries: [DE, NL]
    severity: error

  - route_key: block-ads
    target: doubleclick.net
    expected_policy: BLOCK
    expected_group: REJECT
    severity: error
```

## 5.2.2. Минимальный набор маршрутов

### EU default

```text
google.com
cloudflare.com
example.com
2ip.io
ipinfo.io
```

### RU services

```text
gosuslugi.ru
esia.gosuslugi.ru
yandex.ru
market.yandex.ru
ozon.ru
wildberries.ru
sberbank.ru
tbank.ru
vtb.ru
mos.ru
nalog.gov.ru
```

### RU exceptions through EU

```text
rutracker.org
habr.com
4pda.to
meduza.io
theins.ru
archive.org
```

### Global services

```text
youtube.com
discord.com
t.me
telegram.org
openai.com
chatgpt.com
github.com
githubusercontent.com
```

### Block

```text
doubleclick.net
googlesyndication.com
tracking domains from test fixture
.onion fixture
torproject.org
torrent tracker fixture
```

## 5.2.3. Acceptance criteria

- Registry contains at least 40 route entries.
- Every route has expected policy, expected group and severity.
- Runtime mode can consume registry without code changes.
- Static analyzer can compare rules against registry.

---

# 5.3. Generated Subscription Checker

## 5.3.1. Цель

Проверять фактический output подписки, который получает пользователь.

## 5.3.2. Источник subscription output

Три режима:

### Mode A: Existing test user

Использовать заранее созданного non-customer internal test user.

### Mode B: Synthetic user

Создать временного Remnawave user, если:

```text
VPN_TESTER_SYNTHETIC_USERS_ENABLED=true
```

После теста удалить пользователя.

### Mode C: Dry-run / mocked output

Если synthetic disabled, использовать локальный generated template fixture или Remnawave raw subscription dry-run, если upstream API поддерживает.

## 5.3.3. Checks

Для Mihomo output:

- YAML parse;
- expected groups exist;
- expected rule-providers exist;
- expected rules exist;
- nodes are included and filtered;
- no hidden hosts if disabled;
- no raw secrets in evidence.

Для Xray/base64 output:

- subscription not empty;
- links count > 0;
- expected protocol/transport available;
- Premium Smart RU does not break non-Mihomo clients.

## 5.3.4. Acceptance criteria

- Premium Smart RU generated Mihomo contains `🌍 World / EU`, `🇷🇺 RU Sites`, `🇩🇪 DE Auto`, `🇳🇱 NL Auto`.
- Non-smart tariff generated Mihomo does not contain Premium Smart RU template marker unless expected.
- Broken template returns fail with safe summary.

---

# 5.4. Abuse Sentinel v3

## 5.4.1. Scope

Не запускать реальный torrent abuse в production. Проверять policy безопасно.

## 5.4.2. Checks

### Client-side

- torrent rule-providers exist;
- torrent rules route to `🧲 Torrents`;
- `🧲 Torrents` defaults to `REJECT`;
- tor-inline and process regex exist;
- `.onion` blocked.

### Server-side

- Node Plugin exists;
- `torrentBlocker.enabled=true` for target nodes;
- `egressFilter.enabled=true` if TOR lists are configured;
- expected plugin assigned to DE/NL/RU nodes;
- `NET_ADMIN` available in real edge role/compose;
- nftables preflight available.

### Webhook/business reaction

- `torrent_blocker.report` webhook is logged;
- if `REMNAWAVE_ABUSE_AUTO_DISABLE_ENABLED=true`, policy path is tested in dry-run;
- no auto-disable without feature flag.

## 5.4.3. Acceptance criteria

- Missing node plugin assignment causes fail.
- Missing torrentBlocker causes fail.
- Empty TOR egress lists causes degraded, not pass.
- No production torrent traffic is generated.

---

# 5.5. Prometheus Metrics and Alerts

## 5.5.1. Backend metrics

Add:

```python
vpn_tester_runs_total = Counter(
    "cybervpn_vpn_tester_runs_total",
    "VPN Tester runs by suite, mode, trigger and status",
    ["suite_key", "mode", "trigger", "status"],
)

vpn_tester_run_duration_seconds = Histogram(
    "cybervpn_vpn_tester_run_duration_seconds",
    "VPN Tester run duration",
    ["suite_key", "mode", "status"],
)

vpn_tester_results_total = Counter(
    "cybervpn_vpn_tester_results_total",
    "VPN Tester result checks",
    ["suite_key", "category", "check_key", "status"],
)

vpn_tester_release_gate_blocking = Gauge(
    "cybervpn_vpn_tester_release_gate_blocking",
    "Whether VPN Tester release gate is blocking",
)
```

## 5.5.2. Worker metrics

Add:

```python
vpn_tester_worker_tasks_total
vpn_tester_worker_task_duration_seconds
vpn_tester_worker_skips_total
vpn_tester_worker_lock_held_total
```

## 5.5.3. Alerts

Prometheus alert examples:

```text
VPNTesterReleaseGateBlocking
VPNTesterScheduledRunsFailing
VPNTesterQueueBacklogHigh
VPNTesterRuntimeAgentUnavailable
VPNTesterEvidenceCleanupFailing
VPNTesterBalancerRecommendationSpam
```

## 5.5.4. Acceptance criteria

- Every run increments metrics.
- Every worker skip increments skip metric.
- Release gate gauge matches `/release-gate` response.
- Alert rules documented.

---

# 5.6. Balancer Recommendations v3

## 5.6.1. Deduplication

Current recommendation key based on timestamp creates noise.

Add deterministic key:

```text
vpn-balancer:{scope}:{recommendation_hash}
```

Where hash includes:

```text
route_registry_version
node_pool_snapshot_hash
candidate_changes_hash
```

## 5.6.2. Lifecycle

Statuses:

```text
open
acknowledged
dismissed
expired
applied_manually
```

## 5.6.3. API

```http
GET /admin/vpn-tester/balancer/recommendations
POST /admin/vpn-tester/balancer/recommendations/{id}/ack
POST /admin/vpn-tester/balancer/recommendations/{id}/dismiss
```

## 5.6.4. Production safety

- No live mutations.
- No automatic route change.
- No Remnawave mutation.
- All recommendations read-only until separate approved TЗ for balancer actuation.

## 5.6.5. Acceptance criteria

- Repeated identical recommendation does not create duplicates.
- Admin can dismiss/acknowledge.
- Expired recommendations cleaned.
- Balancer preview schedule can be enabled without recommendation spam.

---

## 6. Admin UI v3

## 6.1. Required pages/components

Existing page `/infrastructure/vpn-tester` must be expanded into tabs:

```text
Overview
Runs
Route Matrix
Tariffs
Schedules
Release Gate
Evidence
Balancer
Settings
```

## 6.2. Overview

Show:

- latest status;
- release gate status;
- active schedules;
- latest failures;
- runtime agent status;
- next scheduled runs;
- balancer recommendation count;
- quick actions.

## 6.3. Runs

Filters:

```text
suite
mode
status
trigger
created_at range
```

Actions:

```text
Run Premium Smart RU contract
Run All Tariffs
Run Runtime Matrix
Cancel queued/running
Open details
Compare with last pass
Export safe evidence
```

## 6.4. Route Matrix

Table:

```text
route_key
target
expected_policy
expected_group
expected_exit
last_status
last_observed_exit
last_checked_at
severity
```

## 6.5. Tariffs

For each tariff:

```text
plan_code
visibility
expected_squad
actual_squad
expected_template
actual_template
client_types checked
last_status
failures
```

## 6.6. Schedules

Controls:

- enabled toggle;
- cron readonly or editable with validation;
- next run;
- last run;
- last status;
- skipped reason;
- manual run now.

Important: UI state must reflect backend DB schedule state, not only ENV flags.

## 6.7. Release Gate

Show:

- current gate status;
- latest blocking run;
- blocking checks;
- active override if any;
- override form only for super admin;
- override reason and expiration.

## 6.8. Evidence

Show:

- evidence list;
- SHA256;
- preview;
- diff with previous pass;
- download safe JSON;
- retention expiration.

## 6.9. Acceptance criteria

- Read-only users cannot see mutation buttons.
- 403/409 errors are shown with clear message.
- Schedule toggle corresponds to real scheduled execution.
- Release override requires reason.
- Evidence never displays raw secrets.

---

## 7. API v3 Summary

### Read

```http
GET /api/v1/admin/vpn-tester/overview
GET /api/v1/admin/vpn-tester/runs
GET /api/v1/admin/vpn-tester/runs/{run_id}
GET /api/v1/admin/vpn-tester/runs/{run_id}/evidence
GET /api/v1/admin/vpn-tester/schedules
GET /api/v1/admin/vpn-tester/tariffs
GET /api/v1/admin/vpn-tester/route-matrix
GET /api/v1/admin/vpn-tester/release-gate
GET /api/v1/admin/vpn-tester/balancer/recommendations
```

### Mutations

```http
POST /api/v1/admin/vpn-tester/runs
POST /api/v1/admin/vpn-tester/runs/{run_id}/cancel
PUT /api/v1/admin/vpn-tester/schedules/{schedule_key}
POST /api/v1/admin/vpn-tester/release-gate/override
POST /api/v1/admin/vpn-tester/balancer/recommendations/{id}/ack
POST /api/v1/admin/vpn-tester/balancer/recommendations/{id}/dismiss
```

### Internal worker

```http
POST /api/v1/admin/vpn-tester/internal/queued/execute-next
POST /api/v1/admin/vpn-tester/internal/schedules/{schedule_key}/run
POST /api/v1/admin/vpn-tester/internal/runs/{run_id}/execute
POST /api/v1/admin/vpn-tester/internal/cleanup
```

---

## 8. Data Model v3 Changes

## 8.1. Add `vpn_test_release_gate_overrides`

See section 4.4.

## 8.2. Extend `vpn_test_schedules`

Add:

```text
last_skipped_reason VARCHAR(80) NULL
last_checked_at TIMESTAMPTZ NULL
last_triggered_at TIMESTAMPTZ NULL
schedule_source VARCHAR(40) DEFAULT 'task_worker'
```

## 8.3. Extend `vpn_test_runs`

Add:

```text
agent_id VARCHAR(120) NULL
runtime_mode VARCHAR(40) NULL
route_registry_version VARCHAR(40) NULL
blocking BOOLEAN DEFAULT false
```

## 8.4. Extend `vpn_balancer_recommendations`

Add:

```text
recommendation_hash VARCHAR(64) NOT NULL
acknowledged_by_admin_id UUID NULL
acknowledged_at TIMESTAMPTZ NULL
dismissed_by_admin_id UUID NULL
dismissed_at TIMESTAMPTZ NULL
dismiss_reason TEXT NULL
```

## 8.5. Optional: Add `vpn_test_route_observations`

For runtime matrix history:

```text
id UUID PK
run_id UUID FK
target TEXT NOT NULL
expected_policy VARCHAR(40)
observed_policy VARCHAR(40)
expected_exit_country VARCHAR(8)
observed_exit_country VARCHAR(8)
latency_ms INT
status VARCHAR(24)
evidence_preview JSONB
created_at TIMESTAMPTZ
```

---

## 9. Security requirements

## 9.1. Secrets

Never store or show:

```text
subscription URL
shortUuid
user UUID if linked to real user
JWT/cookies
tokens
passwords
private keys
full proxy configs
raw YAML with generated proxy passwords
```

## 9.2. Synthetic users

Synthetic users only if:

```text
VPN_TESTER_SYNTHETIC_USERS_ENABLED=true
```

Naming:

```text
cvpn_test_<suite>_<timestamp>
```

Must be deleted after run.

If deletion fails:

- mark run `degraded`;
- create cleanup task;
- alert admin.

## 9.3. Runtime agent

- Agent has separate secret.
- Agent accepts only backend/worker internal calls.
- Agent cannot mutate Remnawave.
- Agent evidence is redacted before storing.
- Agent container does not share backend network namespace.

## 9.4. Abuse tests

- No real torrent download.
- No real TOR network usage in production.
- Only static/client config checks and controlled lab fixtures.

---

## 10. Testing Plan

This section is mandatory. The previous implementation intentionally skipped full pytest/Vitest suites; v3 must add tests.

## 10.1. Backend unit tests

```text
backend/tests/unit/vpn_testing/test_service_schedule_gate.py
backend/tests/unit/vpn_testing/test_release_gate_override.py
backend/tests/unit/vpn_testing/test_all_tariffs_contract.py
backend/tests/unit/vpn_testing/test_mihomo_analyzer.py
backend/tests/unit/vpn_testing/test_redaction.py
backend/tests/unit/vpn_testing/test_balancer_recommendations.py
```

## 10.2. Backend integration tests

```text
backend/tests/integration/api/v1/admin/test_vpn_tester_api.py
backend/tests/integration/api/v1/admin/test_vpn_tester_rbac.py
backend/tests/integration/api/v1/admin/test_vpn_tester_internal_worker.py
```

## 10.3. Worker tests

```text
services/task-worker/tests/unit/tasks/test_vpn_tester_run_checks.py
services/task-worker/tests/unit/services/test_backend_api_client_vpn_tester.py
services/task-worker/tests/integration/test_vpn_tester_schedules.py
```

## 10.4. Admin tests

```text
admin/src/features/infrastructure/components/__tests__/vpn-tester-console.test.tsx
```

Checks:

- read-only role hides mutation buttons;
- schedule toggle calls API;
- errors are displayed;
- route matrix renders;
- release override form only for super admin.

## 10.5. Migration tests

- upgrade creates tables;
- downgrade drops tables;
- indexes/constraints exist.

## 10.6. Golden route tests

- static analyzer passes current Premium Smart RU template;
- removing `🇷🇺 RU Sites` causes fail;
- moving `MATCH` above RU rules causes fail;
- removing torrent block causes fail;
- removing adblock providers causes degraded/fail.

---

## 11. Rollout Plan

## Phase 1 — P0 Hardening

Deliver:

- real schedule gate;
- RBAC fixes;
- persisted release override;
- runtime mode fail/skipped semantics;
- balancer dedup/disable spam;
- smoke tests.

Feature flags:

```text
VPN_TESTER_ENABLED=true
VPN_TESTER_SCHEDULED_ENABLED=true
VPN_TESTER_RUNTIME_ENABLED=false
VPN_TESTER_SYNTHETIC_USERS_ENABLED=false
VPN_TESTER_BALANCER_RECOMMENDATIONS_ENABLED=false initially
```

Exit criteria:

- admin schedule toggle works;
- release override persisted;
- read-only users cannot mutate;
- no duplicate scheduled runs;
- tests pass.

## Phase 2 — Static/Semantic Analyzer + Golden Route Registry

Deliver:

- Mihomo analyzer;
- Premium Smart RU route registry v2;
- static template checks;
- generated subscription dry-run checks.

Exit criteria:

- current Premium Smart RU passes;
- intentionally broken fixtures fail;
- all tariffs contract checks are meaningful.

## Phase 3 — Runtime Agent Proxy-only

Deliver:

- `services/vpn-test-agent`;
- runtime proxy-only checks;
- probe network support;
- runtime evidence.

Exit criteria:

- at least 10 route probes pass in staging;
- DNS/IPv6 leak checks implemented;
- runtime mode does not run in backend/worker network namespace.

## Phase 4 — Enterprise Admin Console

Deliver:

- route matrix tab;
- tariff detail tab;
- evidence diff;
- balancer recommendation lifecycle;
- release gate override UI;
- role-aware controls.

## Phase 5 — CI/CD Release Gate

Deliver:

- deploy pipeline reads `/release-gate`;
- blocking gate prevents release unless override active;
- release evidence attached to deployment record.

---

## 12. Definition of Done

Task is considered AAA+ complete only when:

1. Admin schedule toggles affect real scheduled worker execution.
2. Runtime mode cannot fake pass through contract branch.
3. All tariffs mode validates actual VPN assignment expectations.
4. Premium Smart RU static analyzer validates Mihomo YAML semantics.
5. Golden Route Registry covers at least 40 routes.
6. Generated subscription checks exist.
7. Release gate override is persisted and audited.
8. RBAC is consistent across backend and UI.
9. Balancer recommendations are deduplicated and reviewable.
10. Prometheus metrics and alerts are added.
11. Backend/worker/admin tests are added and passing.
12. No production synthetic users are created unless explicitly enabled.
13. No runtime TUN checks occur inside backend or task-worker containers.
14. Evidence remains safe and redacted.
15. OpenAPI and generated admin types are updated.
16. Deployment smoke confirms admin page, API, worker, scheduler and DB migration.

---

## 13. Suggested implementation file map

### Backend

```text
backend/src/application/vpn_testing/analyzers/mihomo.py
backend/src/application/vpn_testing/runtime_agent_client.py
backend/src/application/vpn_testing/generated_subscription_checker.py
backend/src/application/vpn_testing/release_gate.py
backend/src/application/vpn_testing/balancer.py
backend/src/application/vpn_testing/service.py
backend/src/presentation/api/v1/admin/vpn_tester.py
backend/src/infrastructure/database/models/vpn_tester_model.py
backend/src/infrastructure/database/repositories/vpn_tester_repo.py
backend/alembic/versions/<new>_vpn_tester_aaa_v3.py
```

### Task Worker

```text
services/task-worker/src/tasks/vpn_testing/run_checks.py
services/task-worker/src/services/backend_api_client.py
services/task-worker/src/schedules/definitions.py
services/task-worker/src/utils/constants.py
services/task-worker/src/metrics.py
```

### VPN Test Agent

```text
services/vpn-test-agent/
```

### Admin

```text
admin/src/features/infrastructure/components/vpn-tester-console.tsx
admin/src/features/infrastructure/components/vpn-tester/
admin/src/lib/api/infrastructure.ts
admin/src/features/admin-shell/config/admin-navigation.ts
admin/messages/*/infrastructure.json
admin/messages/*/navigation.json
```

### Docs

```text
docs/runbooks/VPN_TESTER_RUNBOOK.md
docs/plans/cybervpn-vpn-tester-aaa-hardening-tz-v3.md
```

---

## 14. Final Implementation Priority

Implement in this exact order:

```text
1. Schedule Gate fix
2. RBAC fix
3. Persistent release override
4. Runtime mode non-fake branch
5. Balancer dedup / disable spam
6. Backend/worker tests for P0
7. Mihomo static analyzer
8. Golden Route Registry v2
9. Generated subscription checker
10. Runtime vpn-test-agent proxy-only
11. Prometheus metrics / alerts
12. Admin UI enterprise tabs
13. CI/CD release gate integration
```

The first five items are required before the current VPN Tester can be considered operationally safe.

