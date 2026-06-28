# CyberVPN Growth Codes v6.3 Hardening — Техническое задание

**Версия документа:** v6.3.1 production-fix  
**Дата:** 2026-06-28  
**Основание:** аудит реализации `Growth Codes v6.2 Hardening`, v6.3 hardening и production-инцидент после commit `8fbc2c2a1752f9754cca2b0202f1873935583530`  
**Цель:** закрыть замечания из раздела «Что нужно поправить» перед production rollout.

---

## 1. Назначение ТЗ

Данное техническое задание описывает доработки поверх уже реализованной версии `Growth Codes v6.2`.

В v6.2 уже реализованы:

- post-registration code prompt;
- единое поле для promo / invite / gift;
- preview определения типа кода;
- connection bootstrap для Web / Mini App / Telegram Bot;
- structured `CODE_SET_REJECTED`;
- payment attempt finalizer;
- benefit fulfillment;
- FX refresh foundation;
- cabinet-only runtime policy.

Текущая итерация v6.3 не должна переписывать архитектуру v6.2. Нужно точечно закрыть найденные риски:

1. Telegram Bot `/code <код>` может не работать без заранее созданного onboarding state.
2. Backend apply path не enforcing `allowed_code_types`.
3. `/connect` в Telegram Bot зависит от `post_registration_code_prompt_enabled`.
4. Telegram Bot idempotency key сейчас привязан к `telegram_id + code`, а не к попытке.
5. В fallback-сопоставлении multi-code applications есть риск off-by-one.
6. FX refresh пока config-backed, без полноценного live provider integration.

---

## 2. Общие требования

### 2.1. Совместимость

Все изменения должны быть backward-compatible с v6.2:

- существующие Web / Mini App onboarding flows не должны сломаться;
- существующие Telegram Bot команды `/connect`, `/instructions`, `/code` должны продолжить работать;
- существующий `/customer/onboarding/growth-code/apply` contract не должен ломаться;
- существующий `/customer/onboarding/connection/bootstrap` contract не должен ломаться;
- существующий checkout quote / code basket contract должен остаться совместимым;
- миграции должны быть идемпотентными и безопасными для production/staging.

### 2.2. Безопасность

Запрещено:

- логировать raw promo / invite / gift codes;
- логировать raw VPN subscription URL;
- сохранять raw VPN subscription URL в connection session ledger;
- отправлять VPN config / QR / subscription URL в Telegram group / supergroup / channel;
- обходить flow-token protection для Web / Mini App onboarding;
- разрешать code type, запрещённый runtime-конфигурацией;
- автоматически использовать неподтверждённый live FX rate в checkout без snapshot/approval policy.

### 2.3. Наблюдаемость

Для всех новых branch/path должны быть метрики и structured logs без sensitive payload:

- onboarding state auto-created;
- onboarding code type rejected by runtime config;
- connection bootstrap disabled / unavailable / available;
- Telegram Bot `/code` attempt idempotency accepted / duplicate / failed;
- multi-code server applications fallback matched by slot / position;
- FX provider refresh success / partial / failed / stale.

---

# 3. Доработка №1 — Telegram Bot `/code <код>` без заранее созданного onboarding state

## 3.1. Проблема

Сейчас Telegram Bot вызывает:

```text
POST /customer/onboarding/growth-code/apply
source_surface = telegram_bot
telegram_id = ...
code = ...
```

Для `telegram_bot` backend не требует `flow_token`, но всё равно вызывает state repository. Если `customer_onboarding_state` для пользователя ещё не создан, repository возвращает:

```text
status = pending
message_key = onboarding.state_unavailable
commit_required = false
```

В результате пользователь может написать `/code INVITE123`, но код не применится, если ранее не был создан onboarding state через Web/Mini App.

## 3.2. Требуемое поведение

Для Telegram Bot необходимо автоматически создавать pending onboarding state перед применением кода, если:

- `source_surface == "telegram_bot"`;
- пользователь найден по `telegram_id`;
- пользователь активен;
- runtime config позволяет onboarding/code prompt или bot code apply;
- state для `flow_key/version` отсутствует.

Целевой flow:

```text
Telegram private chat
→ /code INVITE123
→ backend resolves telegram_id -> mobile_user
→ backend ensures pending onboarding state
→ backend applies code
→ если invite/gift дал entitlement:
      connection_required = true
      bot показывает connection UX
→ если promo staged:
      bot показывает, что код применится в checkout / Mini App plans
```

## 3.3. Backend изменения

### 3.3.1. Изменить endpoint

Файл:

```text
backend/src/presentation/api/v1/customer_onboarding/routes.py
```

В `apply_customer_onboarding_growth_code` после `_resolve_customer_onboarding_actor(...)` и получения `runtime_config` добавить Telegram-specific ensure state.

Псевдокод:

```python
repo = CustomerOnboardingStateSqlAlchemyRepository(db)

if payload.source_surface == "telegram_bot":
    await repo.ensure_pending(
        user_id=resolved_user_id,
        runtime_config=runtime_config,
        source_channel="telegram_bot",
        auth_channel="telegram_bot",
        referral_terminal_state=None,
    )

result = await ApplyCustomerOnboardingGrowthCodeUseCase(
    runtime_config=runtime_config,
    state_repo=repo,
    flow_tokens=CustomerOnboardingFlowTokenService(),
).execute(...)
```

Важно: не создавать state для Web/Mini App в этом месте, чтобы не ослабить текущую flow-token модель.

### 3.3.2. Не создавать state, если feature выключена

Нужно определить policy:

- если `customer_onboarding.runtime.post_registration_code_prompt_enabled == false`, но `connection_bootstrap_enabled == true`, разрешать `/connect`, но не обязательно `/code`;
- для `/code` можно добавить отдельный флаг, см. раздел 5.

Рекомендуемый вариант:

```json
{
  "post_registration_code_prompt_enabled": true,
  "telegram_bot_code_apply_enabled": true,
  "connection_bootstrap_enabled": true
}
```

Если `telegram_bot_code_apply_enabled == false`, `/code` должен вернуть:

```json
{
  "code": "TELEGRAM_ONBOARDING_CODE_APPLY_DISABLED",
  "message_key": "onboarding.telegram.codeApplyDisabled"
}
```

### 3.3.3. Добавить безопасный лог

```python
logger.info(
    "customer_onboarding_state_auto_created",
    extra={
        "surface": "telegram_bot",
        "user_id": str(resolved_user_id),
        "flow_key": runtime_config.flow_key,
        "version": runtime_config.version,
    },
)
```

Raw code не логировать.

## 3.4. Telegram Bot изменения

Файлы:

```text
services/telegram-bot/src/handlers/connection.py
services/telegram-bot/src/services/api_client.py
```

Поведение `/code`:

- если backend вернул success + `connection_required=true`, сразу открывать connection UX;
- если backend вернул success + staged promo, показать объяснение и кнопку открыть Mini App plans;
- если backend вернул state unavailable, показывать не generic `code-not-found`, а понятное сообщение:

```text
Не удалось подготовить активацию кода. Попробуйте /connect или повторите /code <код>.
```

Но после backend-доработки этот сценарий должен быть редким.

## 3.5. Тесты

### Backend unit/integration

Добавить тест:

```text
backend/tests/unit/api/v1/test_customer_onboarding.py
```

Сценарий:

```text
telegram_bot apply code
no onboarding state exists
backend creates state
code_applier called
response status completed
```

Добавить интеграционный тест:

```text
backend/tests/integration/test_customer_onboarding_persistence_postgres.py
```

Сценарий:

```text
Telegram user exists
no customer_onboarding_state
POST /customer/onboarding/growth-code/apply with X-Telegram-Bot-Secret
state created
application created
result persisted
```

### Telegram Bot tests

Добавить/расширить:

```text
services/telegram-bot/tests/unit/test_promocode_fsm_connection_flow.py
services/telegram-bot/tests/integration/test_connection_flow.py
```

Сценарий:

```text
/private chat /code INVITE123
backend has no previous state
API returns completed + connection_required
bot sends connection UX
```

## 3.6. Acceptance Criteria

- `/code <invite>` работает в Telegram private chat без Web/Mini App onboarding history.
- State создаётся один раз на `user_id + flow_key + version`.
- Повторный `/code` не создаёт дубликаты state.
- Group/supergroup/channel по-прежнему не получают VPN payload.
- Web/Mini App flow-token security не ослаблена.

---

# 4. Доработка №2 — Enforce `allowed_code_types` на apply path

## 4.1. Проблема

Preview path проверяет:

```text
allowed_code_types
allow_referral_input
allow_partner_input
```

Но apply path может применить invite/gift/promo напрямую, даже если runtime config запрещает этот тип. Preview и apply могут расходиться.

## 4.2. Требуемое поведение

Backend должен enforce-ить allowed code types не только в preview, но и при фактическом apply.

Пример:

```json
{
  "allowed_code_types": ["promo"]
}
```

Тогда:

- promo — можно;
- invite — нельзя;
- gift — нельзя.

Ответ:

```json
{
  "code": "CUSTOMER_ONBOARDING_CODE_TYPE_NOT_ALLOWED",
  "message_key": "growth_codes.code.type_not_allowed",
  "allowed_code_types": ["promo"],
  "detected_code_type": "invite"
}
```

HTTP status:

```text
422 Unprocessable Entity
```

## 4.3. Backend изменения

Файл:

```text
backend/src/application/use_cases/customer_onboarding/state.py
```

Добавить функцию:

```python
def _is_apply_code_type_allowed(
    *,
    code_type: str,
    runtime_config: CustomerOnboardingRuntimeConfig,
) -> bool:
    if code_type in {"promo", "invite", "gift"}:
        return code_type in runtime_config.allowed_code_types
    if code_type == "referral":
        return runtime_config.allow_referral_input
    if code_type == "partner":
        return runtime_config.allow_partner_input
    return False
```

Вариант 1 — проверять после `code_applier.apply_code(...)`:

```python
applied_code = await code_applier.apply_code(...)

if not _is_apply_code_type_allowed(
    code_type=applied_code.code_type,
    runtime_config=self._runtime,
):
    raise CustomerOnboardingUnavailableError(
        code="CUSTOMER_ONBOARDING_CODE_TYPE_NOT_ALLOWED",
        message_key="growth_codes.code.type_not_allowed",
        status_code=422,
    )
```

Вариант 2 — вынести в `CustomerOnboardingGrowthCodeApplier`, но предпочтительнее держать в use-case, потому что это runtime policy, а не resolver concern.

## 4.4. Важно по staged promo

Если promo в onboarding контексте возвращает `result="staged"` и `code_type="promo"`, это должно разрешаться только если `promo` есть в `allowed_code_types`.

## 4.5. Тесты

Добавить:

```text
backend/tests/unit/api/v1/test_customer_onboarding.py
```

Сценарии:

1. `allowed_code_types=["promo"]`, invite apply → `422`.
2. `allowed_code_types=["invite"]`, gift apply → `422`.
3. `allowed_code_types=["invite", "gift"]`, invite apply → success.
4. Preview and apply return consistent policy decision.

## 4.6. Acceptance Criteria

- Preview и apply не расходятся по allowed types.
- Запрещённый тип не создаёт redemption, entitlement grant, gift redemption, invite redemption.
- Ответ содержит stable error code.
- Frontend/Bot показывают понятное сообщение.

---

# 5. Доработка №3 — Разделить onboarding prompt и connection bootstrap

## 5.1. Проблема

Сейчас `CustomerOnboardingConnectionBootstrapUseCase` возвращает `disabled`, если выключен:

```text
post_registration_code_prompt_enabled
```

Но connection bootstrap нужен не только после регистрации. Команда Telegram Bot `/connect` и Web/Mini App connection panel могут быть нужны действующему пользователю всегда, даже если post-registration prompt выключен.

## 5.2. Требуемое поведение

Ввести отдельный runtime flag:

```json
{
  "connection_bootstrap_enabled": true
}
```

И, отдельно для Telegram Bot code apply:

```json
{
  "telegram_bot_code_apply_enabled": true
}
```

Логика:

| Флаг | За что отвечает |
|---|---|
| `post_registration_code_prompt_enabled` | показывать окно ввода кода после регистрации |
| `web_otp_enabled` | применять prompt после Web OTP |
| `telegram_miniapp_enabled` | применять prompt после Mini App auth |
| `telegram_bot_code_apply_enabled` | разрешить `/code <код>` в Telegram Bot |
| `connection_bootstrap_enabled` | разрешить `/connect`, QR, VPN link, instructions |

## 5.3. Backend config изменения

Файл:

```text
backend/src/application/services/config_service.py
```

Расширить:

```python
@dataclass(frozen=True)
class CustomerOnboardingRuntimeConfig:
    post_registration_code_prompt_enabled: bool = False
    web_otp_enabled: bool = False
    telegram_miniapp_enabled: bool = False
    telegram_bot_code_apply_enabled: bool = False
    connection_bootstrap_enabled: bool = False
    ...
```

`available` оставить для prompt:

```python
@property
def available(self) -> bool:
    return (
        self.post_registration_code_prompt_enabled
        and self.state_store_ready
        and (self.web_otp_enabled or self.telegram_miniapp_enabled)
    )
```

Добавить:

```python
@property
def telegram_bot_code_apply_available(self) -> bool:
    return (
        self.telegram_bot_code_apply_enabled
        and self.state_store_ready
    )

@property
def connection_bootstrap_available(self) -> bool:
    return self.connection_bootstrap_enabled
```

Default config:

```json
{
  "post_registration_code_prompt_enabled": false,
  "web_otp_enabled": false,
  "telegram_miniapp_enabled": false,
  "telegram_bot_code_apply_enabled": false,
  "connection_bootstrap_enabled": true,
  "state_store_ready": false
}
```

Рекомендация: для staging включать:

```json
{
  "post_registration_code_prompt_enabled": true,
  "web_otp_enabled": true,
  "telegram_miniapp_enabled": true,
  "telegram_bot_code_apply_enabled": true,
  "connection_bootstrap_enabled": true,
  "state_store_ready": true
}
```

## 5.4. Client capabilities

Файлы:

```text
backend/src/presentation/api/v1/client_capabilities/schemas.py
backend/src/presentation/api/v1/client_capabilities/routes.py
frontend/src/features/client-capabilities/useClientCapabilities.ts
```

Добавить в onboarding capabilities:

```json
{
  "telegram_bot_code_apply": true,
  "connection_bootstrap": true
}
```

## 5.5. Connection bootstrap use-case

Файл:

```text
backend/src/application/use_cases/customer_onboarding/connection.py
```

Заменить проверку:

```python
if not self._runtime.post_registration_code_prompt_enabled:
    return disabled
```

на:

```python
if not self._runtime.connection_bootstrap_enabled:
    return disabled
```

## 5.6. Apply use-case для Telegram Bot

Файл:

```text
backend/src/presentation/api/v1/customer_onboarding/routes.py
```

Перед apply для `telegram_bot`:

```python
if payload.source_surface == "telegram_bot" and not runtime_config.telegram_bot_code_apply_available:
    raise HTTPException(
        status_code=403,
        detail={
            "code": "TELEGRAM_ONBOARDING_CODE_APPLY_DISABLED",
            "message_key": "onboarding.telegram.codeApplyDisabled",
        },
    )
```

## 5.7. Admin UI

Если в admin уже есть onboarding runtime console, добавить поля:

- `Telegram Bot code apply enabled`;
- `Connection bootstrap enabled`.

UI должен объяснять:

```text
Connection bootstrap можно держать включённым даже при выключенном post-registration prompt.
```

## 5.8. Тесты

1. `post_registration_code_prompt_enabled=false`, `connection_bootstrap_enabled=true` → `/connect` available.
2. `connection_bootstrap_enabled=false` → `/connect` disabled.
3. `telegram_bot_code_apply_enabled=false` → `/code` rejected.
4. `post_registration_code_prompt_enabled=true`, `web_otp_enabled=true` → Web prompt works.
5. Capabilities expose both flags.

## 5.9. Acceptance Criteria

- `/connect` работает независимо от post-registration prompt.
- `/code` можно включать/выключать отдельно.
- Admin может управлять двумя флагами.
- Web/Mini App prompt не меняет поведение.
- Existing configs без новых ключей имеют safe defaults.

---

# 6. Доработка №4 — Telegram Bot idempotency key должен быть per-attempt

## 6.1. Проблема

Сейчас bot idempotency key строится как:

```text
hash(telegram_bot:{telegram_id}:{code})
```

Это делает ключ вечным для пары user+code. Это хорошо для защиты от повторного применения одного и того же кода, но плохо для retry/tracing попыток:

- новая команда `/code samecode` через неделю получит тот же key;
- сложнее отличать retry той же попытки от новой попытки;
- невозможно корректно анализировать attempt-level telemetry.

## 6.2. Требуемое поведение

Idempotency key должен быть стабильным в рамках одной попытки и новым для новой команды.

Рекомендованный формат:

```text
tg-code:{telegram_id}:{message_id}:{sha256(code)[:16]}
```

Для FSM/manual input без message_id:

```text
tg-code:{telegram_id}:{session_id}:{sha256(code)[:16]}
```

## 6.3. Telegram Bot изменения

Файл:

```text
services/telegram-bot/src/handlers/connection.py
```

Изменить:

```python
def onboarding_code_idempotency_key(telegram_id: int, code: str) -> str:
```

на:

```python
def onboarding_code_idempotency_key(
    *,
    telegram_id: int,
    code: str,
    message_id: int | None = None,
    session_id: str | None = None,
) -> str:
    attempt_ref = str(message_id or session_id or "unknown")
    digest = hashlib.sha256(code.strip().encode()).hexdigest()[:16]
    return f"tg-code:{telegram_id}:{attempt_ref}:{digest}"
```

В `/code` command:

```python
idempotency_key = onboarding_code_idempotency_key(
    telegram_id=message.from_user.id,
    code=normalized_code,
    message_id=message.message_id,
)
```

В FSM input:

```python
idempotency_key = onboarding_code_idempotency_key(
    telegram_id=message.from_user.id,
    code=normalized_code,
    session_id=fsm_session_id,
)
```

## 6.4. Backend изменения

Backend уже принимает `idempotency_key`, ограничение max length 120. Проверить, что новый формат не превышает 120 символов.

## 6.5. Тесты

1. Один и тот же message retry → same key.
2. Два разных `/code SAME` message id → different keys.
3. Raw code не попадает в logs.
4. Key length <= 120.
5. Apply retry with same key returns same persisted application result.

## 6.6. Acceptance Criteria

- Idempotency key стабилен только в пределах попытки.
- Повторная команда `/code` создаёт новый attempt key.
- Дубликаты backend side effects по-прежнему не создаются.
- Telemetry различает attempts.

---

# 7. Доработка №5 — Multi-code applications position off-by-one

## 7.1. Проблема

Backend сейчас формирует `position_entered` на базе zero-based `enumerate`. Frontend fallback сопоставляет:

```typescript
application.position_entered === index + 1
```

Если client не передал `client_slot_id`, fallback может сопоставить неправильный код.

## 7.2. Требуемое поведение

Публичный API должен использовать 1-based `position_entered`.

Пример:

```json
[
  {
    "position_entered": 1,
    "client_slot_id": "slot-1"
  },
  {
    "position_entered": 2,
    "client_slot_id": "slot-2"
  }
]
```

## 7.3. Backend изменения

Файл:

```text
backend/src/application/use_cases/payments/checkout.py
```

В `_normalize_code_basket(...)` сейчас возвращается:

```python
(index, code, client_slot_id)
```

Изменить на:

```python
(index + 1, code, client_slot_id)
```

Либо переименовать переменную:

```python
position_entered = index + 1
normalized.append((position_entered, code, item.client_slot_id))
```

Проверить все места:

- `_basket_reject_application`;
- `_basket_application_from_resolution`;
- application sorting;
- tests snapshots.

## 7.4. Frontend изменения

Файл:

```text
frontend/src/features/customer-growth-code-basket/components/GrowthCodeBasket.tsx
```

Оставить fallback:

```typescript
applications.find((application) => application.position_entered === index + 1)
```

Добавить комментарий:

```typescript
// Public API uses 1-based position_entered.
```

## 7.5. Тесты

Backend:

```text
backend/tests/unit/pricing/test_checkout_code_basket_errors.py
backend/tests/unit/presentation/api/v1/payments/test_checkout_code_set_errors.py
```

Проверить:

```text
first code -> position_entered = 1
second code -> position_entered = 2
```

Frontend:

```text
frontend/src/features/customer-growth-code-basket/components/GrowthCodeBasket.test.tsx
```

Сценарий:

```text
server applications without client_slot_id
position_entered=2 updates second visible code
```

## 7.6. Acceptance Criteria

- API contract uses 1-based positions.
- Frontend fallback без `client_slot_id` работает правильно.
- Existing clients with `client_slot_id` не ломаются.
- Tests фиксируют contract.

---

# 8. Доработка №6 — FX refresh: live provider integration и stale-rate alerts

## 8.1. Проблема

Текущий `RefreshFxProviderRatesUseCase` создаёт snapshots из provider config metadata. Это безопасно, но не полноценная live-интеграция с FX provider API.

Нужно добавить следующий уровень:

```text
provider clients
network timeout/retry/circuit breaker
rate source checksum
stale-rate alerts
fallback provider priority
admin review queue
```

## 8.2. Цель

Сделать production-ready FX lifecycle:

```text
scheduled job / admin action
→ provider client fetches rates
→ validate rate payload
→ create immutable snapshots
→ auto-approve or pending approval based on provider config
→ checkout uses only approved active non-stale snapshots
→ stale-rate alerts visible in admin and metrics
```

## 8.3. Backend architecture

### 8.3.1. Provider client protocol

Новый файл:

```text
backend/src/application/use_cases/growth_code_sets/fx_providers.py
```

Пример:

```python
class FxProviderClient(Protocol):
    provider_key: str

    async def fetch_rates(
        self,
        *,
        pairs: list[FxCurrencyPair],
        timeout_seconds: int,
    ) -> list[FxProviderRatePayload]:
        ...
```

DTO:

```python
@dataclass(frozen=True)
class FxCurrencyPair:
    base_currency: str
    quote_currency: str

@dataclass(frozen=True)
class FxProviderRatePayload:
    base_currency: str
    quote_currency: str
    rate: Decimal
    provider_rate_id: str | None
    observed_at: datetime
    fetched_at: datetime
    valid_until: datetime
    raw_payload_hash: str
```

### 8.3.2. Provider registry

```python
class FxProviderRegistry:
    def get(self, provider_key: str) -> FxProviderClient:
        ...
```

Первый production-friendly adapter можно сделать для одного provider, например:

- ExchangeRate.host;
- OpenExchangeRates;
- CurrencyLayer;
- manual HTTP JSON endpoint;
- internal configured mock для staging.

Выбор provider зависит от ваших реальных credentials.

### 8.3.3. Config-backed mode оставить

Текущий config-backed mode нужно оставить для staging/test/manual override:

```text
provider_type = "configured"
```

Live provider:

```text
provider_type = "http_json"
```

Или:

```text
source_type = "provider"
fetch_mode = "live" | "configured"
```

## 8.4. Database changes

Проверить текущие модели `FxProviderConfigModel`, `FxProviderRefreshRunModel`, `FxRateSnapshotModel`.

При необходимости добавить поля:

```text
provider_type
endpoint_url
auth_mode
secret_ref
timeout_seconds
retry_count
circuit_breaker_enabled
stale_after_seconds
auto_disable_after_failures
last_success_at
last_failure_at
consecutive_failures
```

Sensitive secrets хранить только в vault/env/secret manager, не в DB plaintext.

## 8.5. Refresh use-case changes

Файл:

```text
backend/src/application/use_cases/growth_code_sets/fx_refresh.py
```

Нужно изменить так, чтобы use-case мог:

1. определить provider mode;
2. если configured — использовать текущую логику;
3. если live — вызвать provider client;
4. нормализовать payload;
5. создать snapshots;
6. записать refresh run;
7. обновить provider health state.

Псевдокод:

```python
if config.fetch_mode == "configured":
    payloads = _payloads_from_config(...)
else:
    client = registry.get(config.provider_key)
    payloads = await client.fetch_rates(
        pairs=requested_pairs,
        timeout_seconds=config.timeout_seconds,
    )
```

## 8.6. Stale-rate policy

Snapshot считается stale, если:

```text
valid_until < now
```

Provider считается stale, если:

```text
last_success_at is null
or now - last_success_at > provider.stale_after_seconds
```

Checkout conversion должен использовать только:

```text
status = active
approval_state = approved
valid_until >= now
```

Если подходящего rate snapshot нет:

```text
FX_RATE_UNAVAILABLE
```

## 8.7. Admin API

Файл:

```text
backend/src/presentation/api/v3/admin_growth_fx.py
```

Добавить/проверить endpoints:

```text
POST /api/v3/admin/growth/fx/providers/{provider_key}/refresh
POST /api/v3/admin/growth/fx/rates/{rate_snapshot_id}/approve
POST /api/v3/admin/growth/fx/rates/{rate_snapshot_id}/reject
POST /api/v3/admin/growth/fx/providers/{provider_key}/enable
POST /api/v3/admin/growth/fx/providers/{provider_key}/disable
GET  /api/v3/admin/growth/fx/status
GET  /api/v3/admin/growth/fx/rates
GET  /api/v3/admin/growth/fx/refresh-runs
```

Для refresh endpoint request:

```json
{
  "base_currency": "USD",
  "quote_currency": "RUB",
  "reason": "daily scheduled refresh",
  "idempotency_key": "..."
}
```

Для reject:

```json
{
  "reason": "Provider outlier vs secondary source"
}
```

## 8.8. Task-worker scheduled job

Файлы:

```text
services/task-worker/src/tasks/analytics/refresh_growth_fx.py
services/task-worker/src/schedules/definitions.py
services/task-worker/src/services/backend_api_client.py
```

Добавить scheduled job:

```text
growth_fx_refresh
```

Default cadence:

```text
every 15 minutes for production
every 60 minutes for staging
disabled by default in local
```

Job должен:

- вызвать backend admin/internal refresh endpoint;
- передать internal secret;
- логировать only provider_key/status/counts;
- не логировать raw provider payload;
- метрики success/partial/fail.

## 8.9. Admin UI

Файлы:

```text
admin/src/features/growth/components/growth-v6-operations-console.tsx
или отдельный FX console component
```

UI должен показывать:

- provider state;
- last success;
- last failure;
- consecutive failures;
- active approved snapshots;
- pending approval snapshots;
- stale snapshots;
- refresh runs;
- кнопки approve/reject/refresh/enable/disable;
- read-only state для ролей без permissions.

## 8.10. Metrics / Alerts

Добавить метрики:

```text
growth_fx_refresh_runs_total{provider,status}
growth_fx_snapshots_created_total{provider,base,quote,status}
growth_fx_provider_stale_total{provider}
growth_fx_provider_consecutive_failures{provider}
growth_fx_rate_snapshot_stale_total{base,quote}
```

Alert examples:

```text
provider stale > 30 minutes
no approved active USD/RUB rate
refresh failure ratio > 50% for 30 minutes
pending approvals older than 2 hours
```

## 8.11. Тесты

Backend:

```text
backend/tests/unit/application/use_cases/test_growth_fx_refresh.py
backend/tests/unit/presentation/api/v3/test_admin_growth_fx_private.py
backend/tests/integration/test_growth_v62_db_hardening_migration_postgres.py
```

Новые сценарии:

1. live provider success creates snapshots.
2. provider timeout records failed run.
3. duplicate idempotency key returns existing run.
4. approval required → pending snapshot not used in checkout.
5. approved active snapshot used in fixed discount conversion.
6. expired snapshot not used.
7. stale provider appears in status.
8. secret-like change reason redacted.
9. reject snapshot prevents checkout usage.
10. fallback provider priority chooses lower priority number.

Task-worker:

```text
services/task-worker/tests/unit/tasks/test_growth_fx_refresh.py
```

Сценарии:

1. scheduled job calls backend.
2. backend partial response logs safe summary.
3. backend 5xx retries.
4. disabled config skips.

Admin:

```text
admin/src/features/growth/components/__tests__/growth-v6-operations-console.test.tsx
```

Сценарии:

1. provider status shown.
2. stale warning shown.
3. approve/reject disabled for read-only role.
4. refresh action requires reason.

## 8.12. Acceptance Criteria

- FX rates can be refreshed from at least one live provider.
- Config-backed provider remains available for staging/manual mode.
- Checkout never uses unapproved or stale live rate.
- Admin can approve/reject snapshots.
- Stale provider/snapshot visible in admin and metrics.
- Task-worker can refresh rates on schedule.
- Secrets/raw payloads are never exposed in logs/API.

---

# 9. Миграции

Если для разделов 5 и 8 требуются новые поля, создать новую migration:

```text
backend/alembic/versions/20260628_growth_v63_hardening.py
```

Возможные изменения:

```text
fx_provider_configs.provider_type
fx_provider_configs.endpoint_url
fx_provider_configs.timeout_seconds
fx_provider_configs.retry_count
fx_provider_configs.stale_after_seconds
fx_provider_configs.last_success_at
fx_provider_configs.last_failure_at
fx_provider_configs.consecutive_failures

system_config customer_onboarding.runtime default keys:
  telegram_bot_code_apply_enabled
  connection_bootstrap_enabled
```

Migration должна быть безопасной:

- nullable или defaults;
- backfill existing rows;
- no destructive changes;
- indexes for provider status queries if needed.

---

# 10. Документация

Обновить:

```text
docs/plans/CyberVPN_Growth_Codes_v6_2_Hardening_TZ_RU.md
docs/...
```

Добавить новый документ:

```text
docs/plans/CyberVPN_Growth_Codes_v6_3_Hardening_TZ_RU.md
```

Документировать:

- difference between prompt and connection bootstrap;
- Telegram Bot `/code` state auto-create;
- allowed code type enforcement;
- code basket 1-based positions;
- FX live provider lifecycle;
- production rollout checklist.

---

# 11. Rollout plan

## 11.1. Stage 1 — Backend safety

1. Add runtime config fields.
2. Add apply allowed-code enforcement.
3. Add Telegram Bot ensure state.
4. Add code basket position fix.
5. Add tests.
6. Deploy to staging.

## 11.2. Stage 2 — Bot / frontend

1. Update Bot idempotency key.
2. Confirm `/code` without state.
3. Confirm `/connect` with prompt disabled.
4. Confirm Web/Mini App connection UX unchanged.
5. Deploy Bot staging.

## 11.3. Stage 3 — FX live provider

1. Configure provider in staging.
2. Run manual refresh.
3. Approve snapshot.
4. Run checkout fixed discount conversion.
5. Enable scheduled task-worker job.
6. Add alerts.

## 11.4. Stage 4 — Production canary

1. Enable `connection_bootstrap_enabled=true`.
2. Keep `telegram_bot_code_apply_enabled=false`.
3. Test `/connect` for internal users.
4. Enable `telegram_bot_code_apply_enabled=true` for staging/canary users if config supports cohort.
5. Monitor metrics.
6. Enable globally.

---

# 12. Definition of Done

Задача считается выполненной, если:

- Telegram Bot `/code <код>` успешно работает без заранее созданного onboarding state.
- Telegram Bot `/connect` работает даже при выключенном post-registration prompt.
- Backend apply path блокирует code types, запрещённые runtime config.
- Preview и apply не расходятся по allowed code types.
- Bot idempotency key стал per-attempt.
- Multi-code public contract использует 1-based `position_entered`.
- Structured `CODE_SET_REJECTED` корректно отображается в frontend fallback без `client_slot_id`.
- FX refresh поддерживает live provider adapter или явно реализованный provider abstraction с рабочим первым provider.
- Checkout использует только approved active non-stale FX snapshots.
- Admin видит stale-rate/provider status.
- Task-worker умеет scheduled FX refresh.
- Все новые unit/integration/security tests проходят.
- Raw codes и VPN subscription URLs не попадают в logs, DB safe ledgers и public API responses сверх разрешённого connection bootstrap.


---

# 19. Production incident addendum: OTP onboarding, cabinet-only redirects, locale persistence

**Версия дополнения:** v6.3.1 production fixes  
**Дата:** 2026-06-28  
**Основание:** production-инцидент после деплоя на `cyber-vpn.net` / `my.cyber-vpn.net`.

## 19.1. Наблюдаемые симптомы

### 19.1.1. После регистрации и OTP пользователь остаётся на OTP форме

Фактическое поведение:

1. Пользователь регистрируется.
2. Пользователь вводит OTP.
3. Сессия фактически создаётся.
4. Пользователь остаётся на форме OTP.
5. После `F5` пользователь попадает в личный кабинет.

Ожидаемое поведение:

```text
registration -> OTP success -> post-registration code prompt
```

Если post-registration prompt выключен:

```text
registration -> OTP success -> dashboard
```

Но пользователь не должен оставаться на OTP форме после успешной верификации.

### 19.1.2. В личном кабинете не работают разделы `/rewards/*` и `/messages`

В консоли production наблюдаются ошибки вида:

```text
Access to fetch at 'https://cyber-vpn.net/en-EN'
redirected from 'https://my.cyber-vpn.net/en-EN/rewards/invites?_rsc=...'
from origin 'https://my.cyber-vpn.net' has been blocked by CORS policy:
Redirect is not allowed for a preflight request.
```

Аналогично ломаются:

```text
/rewards
/rewards/referral
/rewards/gifts
/rewards/invites
/rewards/codes
/rewards/notifications
/messages
```

Ожидаемое поведение:

- все private cabinet routes должны обслуживаться на `my.cyber-vpn.net`;
- RSC-запросы Next.js не должны получать cross-origin redirect на `cyber-vpn.net`;
- public marketing redirect допустим только для настоящих marketing pages, но не для cabinet pages.

### 19.1.3. Выбор русского языка сбрасывается обратно на английский

Фактическое поведение:

1. Пользователь выбирает `ru-RU`.
2. Через переходы/редиректы язык возвращается в `en-EN`.

Вероятная связь:

- часть cabinet route не входит в `cabinet_allowed_prefixes`;
- proxy классифицирует такой путь как marketing route;
- в `cabinet_only` режиме redirect уводит пользователя на public origin;
- дальнейшая нормализация/redirect может возвращать default locale `en-EN`.

---

## 19.2. Root cause analysis

### 19.2.1. Cabinet-only allowlist не синхронизирован с реальной навигацией

В `frontend/src/proxy.ts` default `cabinetAllowedPrefixes` содержит:

```ts
'/dashboard',
'/subscriptions',
'/payment-history',
'/referral',
'/wallet',
'/settings',
'/support',
'/servers',
'/monitoring',
'/analytics',
'/users',
'/partner',
'/login',
'/register',
'/verify',
'/verify-email',
'/forgot-password',
'/reset-password',
'/magic-link',
'/oauth',
'/telegram-link',
'/onboarding',
```

Но в реальной cabinet-навигации есть routes:

```ts
'/rewards',
'/rewards/referral',
'/rewards/gifts',
'/rewards/invites',
'/rewards/codes',
'/rewards/notifications',
'/messages',
```

Эти routes объявлены в `WEB_CABINET_SECTION_DEFINITIONS`, но отсутствуют в `cabinetAllowedPrefixes`.

Из-за этого `buildCabinetOnlyRedirect()` на cabinet host (`my.cyber-vpn.net`) делает:

```text
if path not in cabinetAllowedPrefixes
    and cabinetMarketingRouteAction == redirect_public
        -> redirect to public host
```

Для обычной browser navigation это уже плохо. Для Next.js RSC-запросов (`?_rsc=...`, `RSC: 1`, `Next-Router-State-Tree`) это критично: браузер блокирует cross-origin redirect, и SPA-навигация ломается.

### 19.2.2. OTP success flow не имеет гарантированного fallback navigation

`OtpVerificationForm` после успешной верификации вызывает:

```ts
router.push(getPostAuthDestination({
  onboarding: result.onboarding,
  surface: 'web',
}));
```

Риски:

1. Если backend не вернул `onboarding.required=true`, frontend пойдёт в `/dashboard`.
2. Если production runtime config для onboarding выключен или неполный, backend вернёт `onboarding=null`.
3. Если SPA navigation/RSC fetch ломается, пользователь остаётся на OTP форме.
4. Нет контрольной проверки: действительно ли pathname изменился после успешного OTP.
5. Нет fallback на `window.location.assign(...)`.

Backend создаёт onboarding state только если одновременно выполнено:

```text
customer_onboarding.runtime.post_registration_code_prompt_enabled = true
customer_onboarding.runtime.web_otp_enabled = true
customer_onboarding.runtime.state_store_ready = true
```

Если любой флаг выключен, `_resolve_post_registration_onboarding()` вернёт `None` или unavailable-state, и post-registration prompt не будет показан.

### 19.2.3. Locale сбрасывается из-за redirect path/default locale behavior

`LanguageSelector` делает правильный базовый вызов:

```ts
router.replace(pathname, { locale: newLocale });
```

Но после этого path всё равно проходит через `proxy.ts`.

Если selected locale route относится к cabinet page, но route не входит в allowlist, proxy может отправить пользователя на public origin. Плюс отдельная проблема: root redirect на cabinet host сейчас использует `defaultLocale`, а не preferred locale пользователя.

Требуется единый helper:

```ts
resolvePreferredLocale(request)
```

Приоритет:

1. locale из текущего pathname;
2. `NEXT_LOCALE` cookie;
3. `Accept-Language`;
4. `defaultLocale`.

---

# 20. Production hotfix scope

## 20.1. Immediate config hotfix без ожидания deploy

Если runtime config доступен через admin/system config, нужно немедленно обновить `customer_site.runtime`.

Минимальный production patch:

```json
{
  "mode": "cabinet_only",
  "version": 2,
  "public_hosts": ["cyber-vpn.net", "www.cyber-vpn.net"],
  "cabinet_hosts": ["my.cyber-vpn.net"],
  "cabinet_destination_path": "/dashboard",
  "public_marketing_destination_path": "/",
  "cabinet_marketing_route_action": "not_found",
  "cabinet_allowed_prefixes": [
    "/dashboard",
    "/subscriptions",
    "/payment-history",
    "/rewards",
    "/messages",
    "/referral",
    "/wallet",
    "/settings",
    "/support",
    "/servers",
    "/monitoring",
    "/analytics",
    "/users",
    "/partner",
    "/onboarding",
    "/login",
    "/register",
    "/verify",
    "/verify-email",
    "/forgot-password",
    "/reset-password",
    "/magic-link",
    "/oauth",
    "/telegram-link"
  ],
  "allowed_path_prefixes": [
    "/login",
    "/register",
    "/verify",
    "/verify-email",
    "/forgot-password",
    "/reset-password",
    "/magic-link",
    "/oauth",
    "/telegram-link",
    "/legal",
    "/r/",
    "/p/",
    "/.well-known/"
  ],
  "legal_path_prefixes": [
    "/acceptable-use",
    "/cookie-policy",
    "/privacy",
    "/privacy-policy",
    "/refund-policy",
    "/terms"
  ],
  "operational_path_prefixes": [
    "/status",
    "/telegram-widget",
    "/.well-known"
  ],
  "preserve_query_keys": [
    "ref",
    "referral",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_content",
    "utm_term"
  ]
}
```

Почему временно лучше `cabinet_marketing_route_action = "not_found"`:

- пока allowlist не покрыт на 100%, неизвестный cabinet path не должен давать cross-origin redirect;
- 404 лучше, чем CORS-failure для RSC;
- после full allowlist sync можно вернуть `redirect_public`, если это действительно нужно продуктово.

Также нужно проверить `customer_onboarding.runtime`:

```json
{
  "post_registration_code_prompt_enabled": true,
  "web_otp_enabled": true,
  "telegram_miniapp_enabled": true,
  "state_store_ready": true,
  "flow_key": "post_registration_growth_code_v1",
  "version": 1,
  "allowed_code_types": ["promo", "invite", "gift"],
  "allow_referral_input": false,
  "allow_partner_input": false,
  "connection_bootstrap_enabled": true
}
```

Если `connection_bootstrap_enabled` ещё не реализован в v6.3, временно не добавлять ключ в production config либо backend должен игнорировать unknown keys.

---

# 21. Code changes required

## 21.1. Single source of truth для cabinet route allowlist

### Проблема

Сейчас существуют минимум два источника истины:

1. `frontend/src/shared/cabinet-navigation/index.ts`;
2. hardcoded `cabinetAllowedPrefixes` в `frontend/src/proxy.ts`;
3. hardcoded defaults в backend `CustomerSiteRuntimeConfig`.

Они рассинхронизировались.

### Требование

Создать общий список private cabinet route prefixes:

```ts
export const WEB_CABINET_ROUTE_PREFIXES = [
  '/dashboard',
  '/subscriptions',
  '/payment-history',
  '/rewards',
  '/messages',
  '/wallet',
  '/settings',
  '/support',
  '/servers',
  '/monitoring',
  '/analytics',
  '/users',
  '/partner',
  '/onboarding',
] as const;
```

И использовать его в:

- `frontend/src/shared/cabinet-navigation/index.ts`;
- `frontend/src/proxy.ts`;
- тестах proxy;
- generated runtime config defaults;
- backend default `CustomerSiteRuntimeConfig`;
- backend tests for `CustomerSiteRuntimePolicy`.

Для backend можно продублировать список, но обязательно добавить test, который сравнивает backend default prefixes с frontend route contract artifact.

### Acceptance criteria

- `/en-EN/rewards` на `my.cyber-vpn.net` не редиректит на `cyber-vpn.net`;
- `/en-EN/rewards/invites` на `my.cyber-vpn.net` не редиректит на `cyber-vpn.net`;
- `/en-EN/rewards/gifts` на `my.cyber-vpn.net` не редиректит на `cyber-vpn.net`;
- `/en-EN/rewards/codes` на `my.cyber-vpn.net` не редиректит на `cyber-vpn.net`;
- `/en-EN/rewards/notifications` на `my.cyber-vpn.net` не редиректит на `cyber-vpn.net`;
- `/en-EN/rewards/referral` на `my.cyber-vpn.net` не редиректит на `cyber-vpn.net`;
- `/en-EN/messages` на `my.cyber-vpn.net` не редиректит на `cyber-vpn.net`;
- `/en-EN/pricing` на `my.cyber-vpn.net` в `cabinet_only` режиме ведёт себя по `cabinet_marketing_route_action`.

---

## 21.2. Запрет cross-origin redirects для RSC / Next data requests

### Проблема

Next.js App Router делает internal fetch/RSC-запросы с query `_rsc` и служебными headers. Cross-origin redirect для таких запросов приводит к CORS-failure.

### Требование

В `frontend/src/proxy.ts` добавить detector:

```ts
function isNextInternalNavigationRequest(request: NextRequest): boolean {
  return (
    request.nextUrl.searchParams.has('_rsc') ||
    request.headers.get('RSC') === '1' ||
    request.headers.has('Next-Router-State-Tree') ||
    request.headers.has('Next-Router-Prefetch') ||
    request.headers.get('Accept')?.includes('text/x-component') === true
  );
}
```

Если request является RSC/internal и policy хочет сделать cross-origin redirect:

- не делать redirect;
- вернуть `404` или `409` с коротким текстом;
- либо redirect только same-origin на safe cabinet destination.

Рекомендуемое поведение:

```text
cabinet host + internal RSC + path not allowed:
    return 404
public host + internal RSC + cabinet route:
    return 404
```

Для обычной browser navigation redirect остаётся разрешённым.

### Acceptance criteria

- RSC-запрос `GET https://my.cyber-vpn.net/en-EN/rewards/invites?_rsc=...` не получает redirect на `https://cyber-vpn.net`;
- DevTools больше не показывает `Redirect is not allowed for a preflight request`;
- при unknown cabinet route RSC получает controlled `404`, а не CORS-failure.

---

## 21.3. Resilient OTP success navigation

### Проблема

После успешного OTP пользователь может остаться на форме, хотя сессия уже создана.

### Требование

В `OtpVerificationForm` заменить мягкий single `router.push(...)` на resilient flow.

Псевдокод:

```ts
const result = await verifyOtpAndLogin(email, normalizedCode);

let onboarding = result.onboarding ?? null;

if (!onboarding) {
  onboarding = await tryFetchCurrentOnboardingAfterOtp();
}

const destination = getPostAuthDestination({
  onboarding,
  surface: 'web',
});

setSuccess(true);

router.replace(destination);
router.refresh();

window.setTimeout(() => {
  const expected = localizePathname(destination, locale);
  if (window.location.pathname !== expected) {
    window.location.assign(expected);
  }
}, 800);
```

`tryFetchCurrentOnboardingAfterOtp()`:

- вызывает `/customer/onboarding/current`;
- делает это только если `/client/capabilities.onboarding.available === true` или если backend `VerifyOtpResponse.onboarding` отсутствует;
- graceful fallback на `/dashboard`.

### Дополнительные требования

- После OTP success форма должна показать статус:
  - `VERIFY_OK_REDIRECTING`;
  - destination path;
  - fallback button `Продолжить`;
- кнопку submit нужно блокировать после success, чтобы пользователь не отправлял OTP повторно;
- если `router.replace` не сработал за 800–1200ms, делать hard navigation.

### Acceptance criteria

- После OTP success пользователь всегда покидает OTP форму без `F5`;
- если onboarding enabled и state pending — попадает на `/onboarding/code`;
- если onboarding disabled — попадает на `/dashboard`;
- если SPA navigation сломана — hard redirect срабатывает автоматически;
- при network failure `/customer/onboarding/current` пользователь всё равно попадает в `/dashboard`.

---

## 21.4. Production readiness check для onboarding config

### Проблема

Onboarding prompt зависит от runtime config. Если production config выключен или неполный, prompt не появится.

### Требование

Добавить health/readiness check:

```text
GET /api/v1/client/capabilities
```

должен в production отдавать:

```json
{
  "onboarding": {
    "post_registration_code_prompt": true,
    "web_otp": true,
    "state_store": true,
    "available": true
  }
}
```

Добавить admin warning в Growth Onboarding console:

```text
Post-registration prompt is configured but unavailable:
- state_store_ready=false
- web_otp_enabled=false
- post_registration_code_prompt_enabled=false
```

Добавить backend log на OTP success:

```text
auth_email_verification_onboarding_decision
user_id
mobile_user_id
realm_type
runtime_prompt_enabled
runtime_web_otp_enabled
runtime_state_store_ready
onboarding_returned
onboarding_status
onboarding_required
```

### Acceptance criteria

- Если production config не готов, admin видит warning до деплоя;
- OTP logs позволяют понять, почему `onboarding=null`;
- smoke-test регистрации валится, если ожидался prompt, но backend вернул `onboarding=null`.

---

## 21.5. Locale persistence and cross-domain redirect consistency

### Проблема

Выбор `ru-RU` сбрасывается в `en-EN` после redirect/fallback navigation.

### Требование

Добавить helper в `frontend/src/proxy.ts`:

```ts
function resolvePreferredLocale(request: NextRequest): string {
  const pathnameLocale = getRequestLocaleFromPathname(request.nextUrl.pathname);
  if (pathnameLocale) return pathnameLocale;

  const cookieLocale = request.cookies.get('NEXT_LOCALE')?.value;
  if (isSupportedLocale(cookieLocale)) return cookieLocale;

  const acceptLanguageLocale = resolveLocaleFromAcceptLanguage(
    request.headers.get('accept-language')
  );
  if (acceptLanguageLocale) return acceptLanguageLocale;

  return defaultLocale;
}
```

Использовать его в:

- root redirect на cabinet host;
- cabinet-only redirect to cabinet destination;
- cabinet marketing redirect to public destination;
- maintenance redirect;
- auth redirect public -> cabinet.

`LanguageSelector` должен:

- выставлять `NEXT_LOCALE` cookie перед navigation;
- использовать `router.replace(pathname, { locale: newLocale })`;
- при failure делать hard navigation на localized href.

Пример:

```ts
document.cookie = `NEXT_LOCALE=${newLocale}; path=/; max-age=31536000; SameSite=Lax; Secure`;
router.replace(pathname, { locale: newLocale });
```

Если нужен cookie на оба поддомена:

```text
Domain=.cyber-vpn.net
```

Но это должно быть включено только для production hostnames, чтобы не ломать localhost.

### Acceptance criteria

- На `my.cyber-vpn.net/en-EN/dashboard` выбор `ru-RU` переводит на `/ru-RU/dashboard`;
- после перехода в `/ru-RU/rewards/invites` язык остаётся `ru-RU`;
- `F5` не сбрасывает язык;
- переход на `/` cabinet host ведёт в `/ru-RU/dashboard`, если `NEXT_LOCALE=ru-RU`;
- public/cabinet redirects сохраняют locale.

---

## 21.6. Tests to add

### Proxy tests

Добавить тесты:

```text
cabinet host allows /en-EN/rewards
cabinet host allows /en-EN/rewards/invites
cabinet host allows /en-EN/rewards/gifts
cabinet host allows /en-EN/rewards/codes
cabinet host allows /en-EN/rewards/notifications
cabinet host allows /en-EN/rewards/referral
cabinet host allows /en-EN/messages
cabinet host blocks unknown marketing RSC without cross-origin redirect
cabinet root uses NEXT_LOCALE cookie
language redirect preserves ru-RU
```

### Backend policy tests

Добавить тесты:

```text
CustomerSiteRuntimePolicy allows /rewards on cabinet host
CustomerSiteRuntimePolicy allows /messages on cabinet host
CustomerSiteRuntimePolicy redirects marketing route according to action
CustomerSiteRuntimePolicy returns not_found when cabinet_marketing_route_action=not_found
```

### OTP tests

Frontend:

```text
OTP success with onboarding.required=true -> navigates to /onboarding/code
OTP success with onboarding=null but current endpoint pending -> navigates to /onboarding/code
OTP success with onboarding=null and current unavailable -> navigates to /dashboard
OTP success router.replace no-op -> hard navigation fallback
```

Backend:

```text
verify_otp logs onboarding decision
verify_otp returns onboarding pending when runtime enabled
verify_otp returns onboarding null when runtime disabled
```

### Production smoke test

Добавить Playwright smoke:

```text
register random user
read OTP from test channel or test bypass
submit OTP
expect page URL to match /onboarding/code OR /dashboard according to runtime
navigate to rewards/invites
expect no CORS redirect
switch language to ru-RU
navigate rewards/gifts
expect URL starts with /ru-RU/
```

---

## 21.7. Rollback plan

Если после фикса что-то пошло не так:

1. Поставить `customer_site.runtime.mode = "full_site"`.
2. Или оставить `cabinet_only`, но поставить:

```json
{
  "cabinet_marketing_route_action": "not_found"
}
```

3. Отключить post-registration prompt:

```json
{
  "post_registration_code_prompt_enabled": false
}
```

4. Убедиться, что `/dashboard`, `/subscriptions`, `/servers`, `/settings`, `/support` остаются доступны.
5. Очистить edge/runtime cache или увеличить `customer_site.runtime.version`.

---

## 21.8. Definition of Done для production incident

Задача считается закрытой, если выполнены все условия:

- после OTP пользователь не остаётся на OTP форме;
- при включённом onboarding prompt пользователь попадает на `/onboarding/code`;
- при выключенном onboarding prompt пользователь попадает на `/dashboard`;
- `F5` больше не требуется;
- все routes из `WEB_CABINET_SECTION_DEFINITIONS` доступны на `my.cyber-vpn.net`;
- Next RSC requests не получают cross-origin redirect;
- DevTools больше не содержит `Redirect is not allowed for a preflight request`;
- русский язык не сбрасывается на английский при навигации и refresh;
- production `/client/capabilities` показывает корректный runtime snapshot;
- добавлены tests из раздела 21.6;
- добавлен temporary admin/runbook по production config hotfix.

