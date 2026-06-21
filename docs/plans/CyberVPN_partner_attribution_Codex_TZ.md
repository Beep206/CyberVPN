# Техническое задание для Codex CLI: финальное завершение Partner Referral / Attribution CyberVPN

**Проект:** `Beep206/CyberVPN`
**Целевая среда:** Windows + WSL2
**Codex CLI:** stable `0.141.0`
**Обязательная модель:** `gpt-5.5`
**Обязательный reasoning effort:** `xhigh`
**Базовый commit аудита:** `5db6c17e9d13e072930c6419550a5895a681bf25`
**Приоритет:** Critical / Security / Revenue Integrity
**Результат:** merge-ready feature branch и подтверждённый production-like E2E

> В официальной конфигурации Codex значение уровня рассуждений называется `xhigh`. Значение `xhith` является опечаткой и не должно использоваться.

---

## 1. Назначение

Нужно довести текущую реализацию partner referral / attribution до состояния, при котором полный путь:

```text
partner portal
→ canonical partner link
→ anonymous capture
→ cross-domain transfer
→ authentication
→ partner attribution claim
→ commercial binding
→ quote/order attribution
→ payment completed
→ durable partner earning
→ hold/statement/payout
→ refund/dispute adjustment
```

является:

- безопасным;
- воспроизводимым;
- идемпотентным;
- устойчивым к конкурентным запросам;
- финансово детерминированным;
- полностью наблюдаемым;
- покрытым real PostgreSQL, Redis и browser E2E тестами.

Codex обязан не ограничиваться анализом. Он должен внести изменения, создать миграции, обновить OpenAPI/generated artifacts, написать тесты, прогнать полный validation suite, выполнить независимый post-implementation review и исправить все найденные P0/P1 проблемы.

---

## 2. Правила выполнения

### 2.1. Источник истины

1. Актуальный checkout репозитория и `origin/main` являются источником истины.
2. Commit `5db6c17e...` используется как контрольная точка аудита.
3. Если текущий HEAD новее, Codex обязан:
   - сравнить изменения с этой контрольной точкой;
   - не откатывать уже исправленные части;
   - проверить, не изменились ли execution paths.
4. Нельзя заменять существующую архитектуру параллельной реализацией без необходимости.

### 2.2. Git

Codex обязан:

1. выполнить:
   ```bash
   git status --short
   git fetch origin --prune
   git log -1 --oneline
   ```
2. сохранить все чужие незакоммиченные изменения;
3. не выполнять `git reset --hard`, `git clean -fd`, force push;
4. создать либо переиспользовать feature branch:
   ```text
   fix/partner-attribution-production-hardening
   ```
5. не пушить напрямую в `main`;
6. делать тематические commits;
7. в конце push feature branch;
8. открыть PR через `gh`, если `gh` установлен и авторизован;
9. не утверждать, что работа завершена, пока release gates не пройдены.

### 2.3. Работа с subagents

Использовать subagents обязательно.

#### Первая волна — параллельный read-only audit

Запустить одновременно шесть агентов:

1. `architecture_auditor`
2. `security_auditor`
3. `database_concurrency_auditor`
4. `finance_settlement_auditor`
5. `frontend_portal_auditor`
6. `test_release_auditor`

Все агенты:

```text
model = gpt-5.5
model_reasoning_effort = xhigh
sandbox = read-only
```

Каждый должен вернуть:

- подтверждённые дефекты;
- execution path;
- файлы и symbols;
- тесты, воспроизводящие дефект;
- риск;
- минимально достаточное исправление;
- возможные регрессии.

Главный агент обязан дождаться всех шести результатов.

#### Реализация

- Не запускать несколько write-capable агентов одновременно.
- Изменения выполняет главный агент последовательно.
- Допускается один `worker` за раз для строго изолированного work package.
- После каждого work package запускать targeted tests.

#### Вторая волна — независимый read-only review

После реализации повторно запустить минимум:

- security;
- database concurrency;
- finance settlement;
- frontend;
- test/release.

Они должны проверять уже готовый diff, а не пересказывать первоначальный план.

Все подтверждённые P0/P1 findings второй волны должны быть исправлены до финального отчёта.

---

## 3. Что уже реализовано и не должно быть потеряно

Сохранить и развить:

- `partner_attribution_sessions`;
- random `public_slug`;
- отдельные transfer/session tokens;
- transfer expiry;
- transfer replay detection;
- `/p/{publicToken}`;
- `/partner-attribution/capture`;
- `/partner-attribution/transfer/consume`;
- `/partner-attribution/claim`;
- HttpOnly attribution cookie;
- customer `PartnerAttributionProvider`;
- storefront-scoped claim;
- claim touchpoint;
- commercial binding metadata;
- code governance events;
- workspace code CRUD/lifecycle API;
- deep-link и QR endpoints;
- workspace commercial capabilities;
- workspace finance summary;
- order attribution result;
- canonical earning events;
- refund/dispute settlement adjustments;
- generated OpenAPI types;
- partner Codes UI actions.

Не допускается регрессия этих функций.

---

# 4. Work Package 1 — безопасный public capture

## 4.1. Trusted host и realm boundary

### Проблема

Public capture не должен доверять client-controlled:

```text
X-Auth-Realm
X-Forwarded-Host
source_host body field
```

### Требование

Создать отдельную dependency для public customer capture:

```python
get_request_public_customer_realm(...)
```

Она должна:

- вызывать realm resolver с `allow_header=False`;
- принимать forwarded host только после trusted-proxy normalization;
- отклонять неизвестный production host;
- не создавать default realm из произвольного host;
- возвращать canonical customer realm.

BFF route `/p/[publicToken]`:

- удаляет входящие forwarding headers;
- сам формирует trusted forwarding metadata;
- не пересылает произвольный client `X-Forwarded-Host`;
- source host определяется server-side.

### Acceptance tests

- forged `X-Auth-Realm=partner` не меняет realm;
- forged `X-Forwarded-Host` не меняет realm/storefront;
- unknown host получает 404/421;
- valid public host работает;
- local WSL/dev hosts работают только в development.

---

## 4.2. Rate limiting

Добавить Redis rate limits:

```text
30 captures / 10 min / normalized IP
100 captures / 10 min / public link slug
5 active attribution sessions / browser key
10 transfer consumes / 10 min / IP
10 claims / 10 min / authenticated user
```

Требования:

- fail-safe policy должна быть явной;
- `429` содержит `Retry-After`;
- Prometheus metric:
  ```text
  partner_attribution_rate_limited_total{scope}
  ```
- tests с FakeRedis и integration Redis.

---

## 4.3. Browser identity и capture idempotency

### Проблема

`browser_key_hash` сохраняется, но не участвует в выборе/обновлении session.

### Требование

Ввести first-party HttpOnly cookie:

```text
cv_partner_browser
```

В cookie хранится random opaque token. В БД — только hash.

Capture обязан:

1. определить browser key;
2. найти active session;
3. применить attribution policy;
4. не создавать новую session при reload того же link;
5. поддерживать:
   ```text
   first_eligible_touch
   last_eligible_touch
   last_eligible_click
   persistent_storefront_binding
   explicit_code_priority
   ```
6. иметь `Idempotency-Key`;
7. записывать отдельный touchpoint только при реальном новом eligible touch;
8. обновлять `last_seen_at` для duplicate reload.

### DB/API

Добавить repository methods:

```text
get_active_for_browser(...)
get_by_capture_idempotency_key(...)
```

Добавить unique/idempotency invariant.

### Tests

- reload не создаёт duplicate session/touchpoint;
- parallel duplicate capture;
- first-touch A→B остаётся A;
- last-touch A→B становится B;
- expired session создаётся заново;
- revoked code не supersede active valid owner;
- crawler traffic не влияет на human attribution при включённой bot policy.

---

# 5. Work Package 2 — persistent partner links

## 5.1. Новая сущность `partner_code_links`

Создать:

```text
partner_code_links
```

Поля:

```text
id UUID PK
public_slug VARCHAR UNIQUE NOT NULL
partner_code_id UUID NOT NULL
partner_account_id UUID NOT NULL
link_kind VARCHAR NOT NULL
destination_key VARCHAR NOT NULL
destination_path VARCHAR NOT NULL
locale VARCHAR(16) NULL
sale_channel VARCHAR(40) NULL
campaign_params JSONB NOT NULL
sub_ids JSONB NOT NULL
status VARCHAR NOT NULL
active_from TIMESTAMPTZ NULL
expires_at TIMESTAMPTZ NULL
created_by_admin_user_id UUID NULL
created_at TIMESTAMPTZ NOT NULL
updated_at TIMESTAMPTZ NOT NULL
```

### Правила

- slug создаётся CSPRNG;
- arbitrary external URL запрещён;
- разрешены destination keys:
  ```text
  register
  pricing
  checkout
  download
  approved_campaign_landing
  approved_storefront
  ```
- destination resolved server-side;
- query `to=` больше не является source of truth;
- campaign/sub IDs хранятся snapshot;
- default link создаётся для каждого code;
- QR использует конкретный link slug.

### Compatibility

Старые code-level `/p/{code_slug}`:

- работают через compatibility resolver;
- логируются;
- закрываются feature flag;
- имеют sunset date.

Deterministic `px_<uuid>` fallback:

- выключить для новых links;
- оставить временно только под migration flag;
- написать usage metric;
- удалить после documented sunset.

### Tests

- query tampering не меняет destination;
- locale сохраняется;
- wrong/expired link rejected;
- link belongs to workspace;
- QR decode совпадает с generated link.

---

# 6. Work Package 3 — eligibility policy

Создать единый сервис:

```python
EvaluatePartnerCodeEligibilityUseCase
```

Он используется в:

- capture;
- transfer consume при необходимости;
- claim;
- explicit checkout code;
- order resolution;
- admin explainability.

Проверки:

```text
code is_active
lifecycle_status
approval_status
active_from
expires_at
workspace status
lane membership status
contract effective range
allowed channel
allowed storefront
allowed geography
risk state
code/link status
```

Результат:

```python
PartnerCodeEligibilityDecision(
    eligible: bool,
    reason_codes: tuple[str, ...],
    policy_snapshot: dict,
)
```

Не должно быть разных eligibility rules в отдельных routes.

---

# 7. Work Package 4 — commercial binding invariants

## 7.1. Preflight data audit

До создания новых indexes migration обязана обнаружить duplicate active owners.

Создать migration helper/report:

```sql
SELECT
  user_id,
  auth_realm_id,
  storefront_id,
  COUNT(*) AS active_count
FROM customer_commercial_bindings
WHERE binding_status = 'active'
  AND owner_type <> 'none'
GROUP BY user_id, auth_realm_id, storefront_id
HAVING COUNT(*) > 1;
```

Если duplicates существуют:

- не выбирать owner случайно;
- deterministic resolution возможна только по утверждённой precedence;
- unresolved rows переносятся в audit table/report;
- migration должна завершиться с понятным сообщением либо выполнить безопасный backfill.

## 7.2. Правильные unique indexes

DB invariant должен запрещать более одного active commercial owner на scope независимо от `binding_type`.

### Global scope

```text
(user_id, auth_realm_id)
WHERE binding_status='active'
  AND storefront_id IS NULL
  AND owner_type <> 'none'
```

### Storefront scope

```text
(user_id, auth_realm_id, storefront_id)
WHERE binding_status='active'
  AND storefront_id IS NOT NULL
  AND owner_type <> 'none'
```

Точный набор исключений задокументировать.

## 7.3. Row locks

Claim должен блокировать:

- attribution session;
- customer row;
- active bindings relevant scope.

Repository должен поддерживать:

```python
list_active_for_user(..., for_update=True)
```

## 7.4. Conflict result

Явные результаты:

```text
claimed
already_claimed_same_owner
rejected_existing_owner
superseded_by_policy
manual_review_required
expired
no_pending
```

`rejected_existing_owner` не считается success claim.

## 7.5. Scoped precedence

При storefront claim:

1. exact storefront binding;
2. immutable global override/contract;
3. policy decision;
4. не выбирать просто первую строку по времени.

## Tests

Обязательно real PostgreSQL:

- two concurrent same-owner claims;
- two concurrent different-owner claims;
- global vs storefront;
- two storefronts;
- duplicate preflight data;
- transaction rollback;
- partial unique violation mapping to domain result.

---

# 8. Work Package 5 — корректный attribution resolver

## 8.1. Использовать все eligible touchpoints

Запрещено сначала сокращать историю до:

```text
latest explicit
latest passive
```

и затем применять first-touch.

Resolver получает все eligible touchpoints и policy strategy выбирает winner.

## 8.2. Strategy implementations

Реализовать отдельные стратегии:

```text
FirstEligibleTouchStrategy
LastEligibleTouchStrategy
LastEligibleClickStrategy
PersistentStorefrontBindingStrategy
ExplicitCodePriorityStrategy
```

Manual override и contract assignment остаются верхними immutable rules.

Persistent reseller binding не должен перебиваться обычным passive affiliate click.

## 8.3. Snapshot-only terms

Winner использует immutable snapshot touchpoint/session/binding.

Current code можно читать только для integrity checks, но нельзя менять исторические commercial terms.

## 8.4. Explainability

Сохранить:

```text
all evaluated candidates
eligibility reason per candidate
policy strategy
precedence
winner
losers
snapshot identifiers
```

## Tests

- A→B→C first touch = A;
- A→B→C last touch = C;
- last eligible click игнорирует non-click;
- persistent reseller wins;
- manual override wins;
- expired candidate excluded;
- wrong storefront excluded;
- policy snapshot survives later code changes.

---

# 9. Work Package 6 — quote/order safety net

Frontend React effect не должен быть единственной гарантией claim.

В authenticated quote/checkout creation:

1. прочитать attribution cookie;
2. вызвать:
   ```text
   EnsurePendingPartnerAttributionClaimedUseCase
   ```
3. создать либо подтвердить binding;
4. записать quote-linked touchpoint;
5. сохранить attribution/session/binding IDs в quote snapshot.

Требования:

- если claim retryable — quote возвращает controlled retryable error либо выполняет безопасный fallback по policy;
- terminal invalid attribution не блокирует обычную покупку;
- financial owner никогда не зависит только от client-side state.

Tests:

- JS provider не запущен, но quote сохраняет attribution;
- cookie only;
- expired cookie;
- concurrent quote/claim;
- OAuth return then immediate quote.

---

# 10. Work Package 7 — immutable commission contract

## 10.1. Contract model

Создать либо завершить canonical:

```text
partner_commission_contracts
```

Поля:

```text
id
partner_account_id
version
owner_type
commission_model
commission_rate
markup_rate
markup_cap
hold_days
currency_policy
renewal_policy
refund_policy
rounding_mode
effective_from
effective_to
status
created_at
```

`commission_contract_id` должен иметь настоящий FK.

## 10.2. Order snapshot

До order commit зафиксировать:

```json
{
  "calculation_version": "partner_earning_v3",
  "commission_contract_id": "...",
  "commission_model": "percentage",
  "commission_rate": "10.0000",
  "markup_rate": "5.0000",
  "hold_days": 14,
  "currency_policy": "order_currency",
  "rounding_mode": "ROUND_HALF_UP",
  "renewal_policy": "...",
  "refund_policy": "..."
}
```

## 10.3. Earning processor

Запрещён fallback на:

```text
current config tiers
current client count
current code markup
current hold settings
```

Если обязательный snapshot отсутствует:

```text
PARTNER_EARNING_SNAPSHOT_INCOMPLETE
```

и event остаётся retryable/manual-review, cash payout не создаётся.

## 10.4. Decimal

Все financial ORM annotations:

```python
Mapped[Decimal]
```

Использовать достаточный `Numeric`, например `Numeric(20, 8)`.

Не преобразовывать money в `float` внутри domain/application.

Rounding выполняется централизованно по currency.

Tests:

- config изменился после order;
- tier изменился после order;
- code markup изменился;
- earning остаётся прежним;
- USD/EUR/XTR precision;
- rounding boundaries.

---

# 11. Work Package 8 — durable payment-to-earning

## 11.1. Transactional outbox

Payment webhook transaction:

1. verifies provider;
2. updates payment/attempt/order terminal state;
3. appends:
   ```text
   payment.completed
   ```
4. commits;
5. returns provider acknowledgement.

Не создавать partner earning как обязательный synchronous webhook side effect.

## 11.2. Worker

В `services/task-worker` создать consumer:

```text
ProcessPartnerEarningFromPaymentTask
```

Порядок:

1. load payment/order;
2. load immutable order attribution;
3. evaluate no-double-payout policy;
4. create earning idempotently;
5. create hold;
6. emit earning event;
7. ack.

Retry schedule:

```text
1m
5m
15m
1h
6h
```

После max attempts:

```text
DLQ
alert
reconciliation item
```

## 11.3. Fail-closed policy

Если payout policy evaluation недоступна:

- referral cash reward не создаётся;
- partner earning не создаётся;
- job остаётся retryable;
- payment остаётся completed;
- entitlement handling не откатывается;
- alert/metric создаются.

## 11.4. Idempotency

DB unique:

```text
source_event_key
payment_id + beneficiary + earning_component
```

Повтор webhook и повтор worker не создают duplicate.

## 11.5. Legacy cutover

Для canonical order:

```text
legacy PartnerEarningModel = disabled
legacy wallet credit = disabled
canonical earning_events = only source of truth
```

Legacy path разрешён только для явно legacy payment без order под feature flag.

Tests:

- worker transient failure;
- retry success;
- duplicate event;
- concurrent workers;
- DLQ;
- policy service failure;
- no referral/partner double payout;
- refund/dispute adjustment after asynchronous earning.

---

# 12. Work Package 9 — finance summary

Backend summary должен учитывать:

```text
pending
on_hold
available
reserved
paid
reversed
adjustments
statement inclusion
payout instructions
```

Ответ группируется по currency и возвращает decimal strings.

Нельзя:

- ставить `reserved_amount=0` без расчёта;
- считать next payout только как available;
- использовать первую currency для всего portal.

Partner UI:

- отображает карточку на каждую currency;
- не суммирует разные currencies;
- не делает fallback на reduce первой страницы statements;
- форматирует по current locale.

---

# 13. Work Package 10 — partner portal hardening

## 13.1. Runtime provider

Создать:

```tsx
<PartnerPortalRuntimeProvider>
```

Он владеет:

- bootstrap;
- workspace queries;
- finance summary;
- capabilities;
- одной SSE subscription;
- normalized resource states.

Pages/guards не создают независимые runtime graphs.

## 13.2. Resource state

Использовать:

```typescript
type ResourceState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; data: T }
  | { status: 'empty'; data: T }
  | { status: 'forbidden'; code: string }
  | { status: 'unavailable'; code: string }
  | { status: 'error'; error: PortalApiError };
```

Не превращать 403/404 в `null`.

## 13.3. Permissions fail-closed

Canonical:

```text
current_permission_keys = []
```

означает deny.

Legacy fallback возможен только при `undefined` и должен быть удалён после migration.

## 13.4. Retry

Bootstrap и safe GET:

```text
network/502/503/504 → максимум 2 retries
429 → Retry-After
401/403/404 → no retry
```

## 13.5. Codes UI

Сохранить уже реализованные actions и добавить:

- Web Share API с fallback;
- clipboard success/error toast;
- QR download;
- mutation-specific pending state;
- confirmation modal для revoke/archive;
- version conflict recovery;
- backend capability list вместо local capability display;
- actor audit.

## 13.6. Dates

`due_date` не участвует в `updatedAt`.

Backend должен отдавать `updated_at` review request.

## 13.7. Production fixtures

В production:

- no local scenario finance/codes;
- явные bootstrap/no-workspace/error states;
- simulation только development + explicit flag.

---

# 14. Work Package 11 — migrations

## 14.1. Не переписывать потенциально применённые migrations

Если migration уже могла быть применена:

- создать новую corrective migration;
- не менять старую историю.

## 14.2. Обязательные исправления

- `partner_codes.public_slug` → `NOT NULL` после backfill;
- safe downgrade для sessions с `session_token_hash IS NULL`;
- transfer hash очищать после consume;
- touchpoint idempotency unique indexes;
- correct active owner indexes;
- duplicate preflight;
- FK для commission contract;
- Decimal precision migrations;
- link table;
- lifecycle/audit indexes.

## 14.3. Проверка

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

Дополнительно:

- upgrade production-like snapshot;
- migration на data с duplicate active bindings;
- migration на pending unconsumed sessions.

---

# 15. Work Package 12 — legacy cleanup

Исправить:

```python
class UpdateMarkupRequest:
    markup_pct: Decimal = Field(ge=0)
```

Legacy routes:

```text
/partner/dashboard
/partner/codes
/partner/earnings
/partner/bind
```

Добавить:

```text
Deprecation
Sunset
Link successor-version
```

Убрать legacy API imports из canonical partner portal.

Deterministic UUID public links:

- metric;
- feature flag;
- sunset;
- removal test.

---

# 16. OpenAPI и generated artifacts

После финального API:

```bash
cd backend
python scripts/export_openapi.py

cd ../frontend
npm run generate:api-types
npm run prepare:i18n

cd ../partner
npm run generate:api-types
npm run prepare:i18n

cd ../admin
npm run generate:api-types
npm run prepare:i18n
```

Generated files вручную не редактировать.

Ручные partner attribution API types заменить generated types.

---

# 17. Test matrix

## 17.1. Backend unit

- eligibility;
- first/last attribution strategy;
- contract snapshot;
- Decimal calculations;
- lifecycle matrix;
- token replay/expiry;
- deep-link resolution;
- rate-limit keys;
- error mapping.

## 17.2. PostgreSQL integration

- concurrent consume;
- concurrent claim;
- active owner unique indexes;
- idempotent capture;
- touchpoint unique keys;
- code create idempotency;
- immutable order result;
- earning duplicate;
- concurrent workers;
- migration preflight.

## 17.3. Redis/task-worker

- rate limit;
- outbox claim;
- retry;
- DLQ;
- worker restart;
- duplicate delivery.

## 17.4. Frontend

- provider StrictMode;
- retry and online recovery;
- query cleanup;
- no raw token localStorage;
- cookie-only claim;
- error states;
- permission deny;
- one SSE;
- multi-currency;
- Codes mutations.

## 17.5. Full E2E

Обязательный сценарий:

```text
partner login
→ create code
→ create deep link
→ copy link
→ anonymous browser
→ delete query
→ reload
→ OAuth/email registration
→ claim
→ quote
→ order
→ payment webhook
→ outbox
→ worker
→ one earning
→ hold
→ statement
→ portal
→ refund
→ adjustment
```

SQL assertions:

```text
partner_code_links
partner_attribution_sessions
attribution_touchpoints
customer_commercial_bindings
order_attribution_results
event_outbox
earning_events
earning_holds
partner_statements
settlement_adjustments
```

---

# 18. Обязательные validation commands

Codex обязан сначала определить штатные команды репозитория и затем выполнить минимум:

## Backend

```bash
cd backend
python -m ruff check src tests
python -m pytest tests/unit -q
python -m pytest tests/integration -q
python -m pytest tests/e2e -q
```

## Frontend

```bash
cd frontend
npm ci
npm run prepare:i18n
npm run lint
npx tsc --noEmit
npm run test:run
npm run build
```

## Partner

```bash
cd partner
npm ci
npm run prepare:i18n
npm run lint
npx tsc --noEmit
npm run test:run
npm run build
```

## Admin

```bash
cd admin
npm ci
npm run prepare:i18n
npm run lint
npx tsc --noEmit
npm run test:run
npm run build
```

## Contracts

```bash
bash scripts/check-api-contract.sh --verbose
bash scripts/check-generated-artifacts.sh
git diff --check
```

## Infrastructure

Запустить штатный PostgreSQL/Redis/task-worker stack через существующий compose.

Нельзя заменять PostgreSQL concurrency tests SQLite-тестами.

---

# 19. Release gates

Работа не завершена, если существует хотя бы одно:

```text
P0/BLOCKER finding
P1/HIGH finding без documented product decision
failing required test
failing lint/typecheck/build
OpenAPI drift
migration failure
unverified concurrent claim
unverified worker retry
earning dependent on mutable config
double payout path
mixed-currency UI aggregation
403 displayed as empty
```

---

# 20. Артефакты, которые Codex обязан создать

```text
docs/implementation/partner-attribution-initial-audit.md
docs/implementation/partner-attribution-execution-plan.md
docs/implementation/partner-attribution-migration-preflight.md
docs/implementation/partner-attribution-test-matrix.md
docs/implementation/partner-attribution-completion-report.md
```

Completion report:

1. branch/commit;
2. changed components;
3. migrations;
4. tests with exit codes;
5. PostgreSQL/Redis versions;
6. E2E result;
7. subagent review findings;
8. resolved findings;
9. remaining limitations;
10. rollout/rollback plan.

При полном выполнении пункт `remaining limitations` должен содержать только явно утверждённые non-blocking ограничения.

---

# 21. Codex project configuration

Разместить до запуска в корне репозитория.

## `.codex/config.toml`

```toml
model = "gpt-5.5"
model_reasoning_effort = "xhigh"
model_verbosity = "high"

[agents]
max_threads = 6
max_depth = 1
job_max_runtime_seconds = 3600
```

Все custom agents также обязаны явно указывать:

```toml
model = "gpt-5.5"
model_reasoning_effort = "xhigh"
```

---

# 22. Запуск в WSL2

## Проверка

```bash
codex --version
codex debug models | grep -i 'gpt-5.5'
```

Версия должна содержать:

```text
0.141.0
```

## Рекомендуемый interactive запуск

```bash
cd ~/projects/CyberVPN

codex \
  -C "$PWD" \
  -m gpt-5.5 \
  -c 'model_reasoning_effort="xhigh"' \
  -c 'model_verbosity="high"' \
  -c 'agents.max_threads=6' \
  -c 'agents.max_depth=1' \
  --sandbox workspace-write \
  --ask-for-approval on-request \
  --strict-config \
  --search \
  "$(cat docs/tasks/CyberVPN_partner_attribution_Codex_PROMPT.md)"
```

Не использовать `--yolo` для основной рабочей копии.

---

# 23. Финальный критерий

Codex имеет право написать `COMPLETE` только после того, как:

1. весь текущий HEAD повторно проаудирован;
2. первая волна subagents завершена;
3. все work packages реализованы;
4. targeted и full tests пройдены;
5. реальный PostgreSQL concurrency подтверждён;
6. Redis/outbox retry подтверждён;
7. full E2E подтверждён;
8. вторая волна subagents не нашла P0/P1;
9. branch pushed;
10. completion report создан.

Любой пропущенный gate означает:

```text
INCOMPLETE
```
