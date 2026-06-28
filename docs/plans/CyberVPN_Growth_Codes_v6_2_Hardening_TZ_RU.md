# Техническое задание: CyberVPN Growth Codes v6.2 Hardening & Multichannel VPN Connection UX

**Проект:** CyberVPN
**Документ:** новое ТЗ на доработки после аудита реализации Growth Codes v6
**Формат:** Markdown
**Версия ТЗ:** v6.2 Hardening
**Дата:** 2026-06-27
**Язык реализации:** backend — Python/FastAPI/SQLAlchemy/Alembic, frontend/admin — Next.js/TypeScript/React
**PostHog/A/B testing:** не входит в это ТЗ

## Изменения v6.2 относительно v6.1

- Connection UX после успешного onboarding-кода обязателен не только для Web frontend, но и для Telegram Mini App и Telegram Bot.
- Добавлен единый backend connection bootstrap contract с `surface=web|miniapp|telegram_bot`.
- Добавлены требования к Telegram Bot: private chat only, inline callbacks, QR delivery, platform instructions, mark-connected, shared state между Web/Mini App/Bot.
- Добавлены Bot/Mini App-specific tests, metrics, i18n и Definition of Done.

---

## 1. Цель документа

Цель этого ТЗ — закрыть обнаруженные после реализации Growth Codes v6 архитектурные и UX-пробелы, довести систему промокодов, инвайтов, подарочных кодов, приватных тарифов, zero-payment и post-registration onboarding до production-ready состояния.

Документ описывает доработки по следующим направлениям:

1. Единая backend/frontend политика `cabinet_only` режима.
2. Явная идемпотентность apply/skip в post-registration onboarding.
3. Preview введённого кода до фактического применения.
4. Отдельная семантика ошибки ambiguous namespace.
5. Проверка и унификация внешнего payment completion path через `FinalizeCompletedPaymentUseCase`.
6. Полноценное исполнение benefit-типов `bonus_days`, `issue_gift`, `grant_addon`.
7. Структурированный API/UX для multi-code checkout при частичных ошибках.
8. Полный lifecycle FX rates: provider refresh, snapshots, admin approval, stale-rate alerts.
9. Финальная приёмка rule-builder.
10. Новый UX после успешного onboarding-кода: окно подключения VPN с QR, ссылкой и инструкциями для iOS, Android, Windows, macOS, Linux во всех customer-каналах: Web frontend, Telegram Mini App и Telegram Bot.

---

## 2. Текущий контекст

В v6 уже реализованы ключевые части платформы Growth Codes:

- canonical growth code namespace;
- customer onboarding state machine;
- onboarding prompt после email OTP, Telegram Mini App registration/login и Telegram Bot onboarding;
- `internal_zero` settlement для 100% скидки без внешней оплаты;
- payment attempts;
- private catalog grants;
- checkout code basket;
- FX conversion helpers;
- growth benefits fulfillment для `issue_invites` и `wallet_credit`;
- runtime risk guard;
- admin rule-builder и growth v6 consoles;
- новые миграции и тесты.

Настоящее ТЗ не переписывает v6 с нуля, а задаёт hardening-pass поверх текущей архитектуры.

---

## 3. Термины

### Cabinet-only mode

Режим, при котором публичный сайт временно не используется как основной entrypoint, а пользовательские маршруты должны вести в личный кабинет. Нужен для приватного/публичного теста, пока маркетинговые страницы не заполнены актуальным контентом.

### Customer onboarding prompt

Окно после регистрации/верификации, где пользователь может ввести один код: промокод, инвайт-код или подарочный код. Окно можно пропустить.

### Code preview

Безопасная проверка введённого кода без мутаций: не погашает gift/invite, не резервирует checkout-discount, не создаёт entitlement. Показывает пользователю тип кода и ожидаемое действие.

### Code namespace ambiguity

Ситуация, когда один и тот же customer input совпадает сразу с несколькими типами кодов или с несколькими источниками: например invite + promo, promo + referral, gift + invite.

### Growth benefit

Post-settlement действие, связанное с growth code: выдача инвайтов, бонусных дней, wallet credit, gift code, add-on.

---

## 4. Обязательные принципы реализации

1. **Fail closed для платежей, бонусов и приватного каталога.** Если система не уверена, что действие разрешено, оно должно быть заблокировано или отправлено в review.
2. **Raw-коды не логировать.** В логах, Sentry, outbox, snapshots и API-ответах использовать `code_hash`, `code_prefix`, `masked_code`.
3. **Idempotency mandatory.** Любой apply, skip, payment finalization, benefit fulfillment и FX approval должен быть повторяемым безопасно.
4. **Backend authoritative.** Frontend может делать preview и улучшать UX, но backend принимает окончательное решение.
5. **Не ломать referral attribution.** Post-registration prompt не должен перезаписывать уже захваченную referral attribution без явной policy.
6. **Не использовать PostHog/A/B testing.** В рамках этого ТЗ PostHog не добавлять.
7. **Не удалять существующие закомментированные строки кода без отдельной причины.** При рефакторинге сохранять комментарии, если они не стали технически неверными.

---

# Часть A. Cabinet-only runtime policy hardening

## 5. Проблема

Сейчас backend `CustomerSiteRuntimePolicy` разрешает всё, если host является cabinet host. Frontend proxy дополнительно ограничивает public route segments и редиректит часть marketing pages обратно на public origin.

Это создаёт архитектурное расхождение:

```text
backend policy: cabinet host => allow everything
frontend proxy: cabinet host + marketing segment => redirect public
```

Если backend policy позже станет source-of-truth для SSR, API gateway, edge worker или мобильного webview, она окажется слишком permissive.

## 6. Цель доработки

Сделать единую backend-authoritative route policy, которую frontend proxy только исполняет. Backend должен различать:

```text
cabinet host + dashboard/auth/private routes => allow
cabinet host + marketing route => redirect_public или allow по explicit config
public host + marketing route in cabinet_only => redirect_cabinet
public host + legal/status/operational => allow
```

## 7. Backend changes

### 7.1. Расширить `CustomerSiteRuntimeConfig`

Файл:

```text
backend/src/application/services/config_service.py
```

Добавить поля:

```python
@dataclass(frozen=True)
class CustomerSiteRuntimeConfig:
    mode: CustomerSiteMode = "full_site"
    version: int = 1
    public_hosts: tuple[str, ...] = ("cyber-vpn.net", "www.cyber-vpn.net")
    cabinet_hosts: tuple[str, ...] = ("my.cyber-vpn.net",)
    cabinet_destination_path: str = "/dashboard"

    # Уже есть или должен остаться для public host allowlist в cabinet_only
    allowed_path_prefixes: tuple[str, ...] = (...)

    # Новое
    cabinet_allowed_prefixes: tuple[str, ...] = (
        "/dashboard",
        "/subscriptions",
        "/payment-history",
        "/referral",
        "/wallet",
        "/settings",
        "/support",
        "/servers",
        "/monitoring",
        "/analytics",
        "/users",
        "/partner",
        "/login",
        "/register",
        "/verify",
        "/verify-email",
        "/forgot-password",
        "/reset-password",
        "/magic-link",
        "/oauth",
        "/telegram-link",
        "/onboarding",
    )

    cabinet_marketing_route_action: Literal[
        "redirect_public",
        "allow",
        "not_found",
    ] = "redirect_public"

    public_marketing_destination_path: str = "/"

    legal_path_prefixes: tuple[str, ...] = (
        "/acceptable-use",
        "/cookie-policy",
        "/privacy",
        "/privacy-policy",
        "/refund-policy",
        "/terms",
    )

    operational_path_prefixes: tuple[str, ...] = (
        "/status",
        "/telegram-widget",
        "/.well-known",
    )

    preserve_query_keys: tuple[str, ...] = (...)
```

### 7.2. Обновить чтение system_config

Ключ:

```text
customer_site.runtime
```

Добавить поддержку новых полей:

```json
{
  "mode": "cabinet_only",
  "version": 2,
  "public_hosts": ["cyber-vpn.net", "www.cyber-vpn.net"],
  "cabinet_hosts": ["my.cyber-vpn.net"],
  "cabinet_destination_path": "/dashboard",
  "allowed_path_prefixes": ["/login", "/register", "/verify", "/r/", "/p/"],
  "cabinet_allowed_prefixes": ["/dashboard", "/subscriptions", "/onboarding", "/settings"],
  "cabinet_marketing_route_action": "redirect_public",
  "public_marketing_destination_path": "/",
  "legal_path_prefixes": ["/privacy", "/terms", "/refund-policy"],
  "operational_path_prefixes": ["/status", "/.well-known"],
  "preserve_query_keys": ["ref", "referral", "utm_source", "utm_medium", "utm_campaign"]
}
```

Валидация:

- все paths должны начинаться с `/`;
- `//evil.com` запрещён;
- пустые строки отбрасывать;
- количество prefixes ограничить, например `max_items=100`;
- `cabinet_marketing_route_action` нормализовать к default `redirect_public`.

### 7.3. Обновить `CustomerSiteRuntimePolicy`

Файл:

```text
backend/src/application/services/customer_site_policy.py
```

Расширить `CustomerSiteRouteDecision`:

```python
CustomerSiteRouteAction = Literal[
    "allow",
    "redirect",
    "maintenance",
    "not_found",
]

@dataclass(frozen=True, slots=True)
class CustomerSiteRouteDecision:
    action: CustomerSiteRouteAction
    mode: str
    reason: str
    target_host: str | None = None
    target_path: str | None = None
    preserve_query_keys: tuple[str, ...] = ()
    route_class: Literal[
        "cabinet",
        "auth",
        "marketing",
        "legal",
        "operational",
        "unknown",
    ] = "unknown"
```

Логика:

```text
mode == full_site:
  allow

mode == maintenance:
  allow legal/operational
  maintenance для public/cabinet scoped hosts

mode == cabinet_only:
  if public host:
    legal/operational => allow
    allowed_path_prefixes => allow или redirect cabinet для auth routes по policy
    marketing/unknown => redirect cabinet_destination

  if cabinet host:
    cabinet_allowed_prefixes => allow
    legal/operational => allow
    marketing/unknown:
      if cabinet_marketing_route_action == redirect_public:
        redirect public_marketing_destination_path на primary public host
      if allow:
        allow
      if not_found:
        not_found

  other host:
    allow или redirect canonical по отдельной host policy, если уже есть
```

### 7.4. Client capabilities schema

Файлы:

```text
backend/src/presentation/api/v1/client_capabilities/schemas.py
backend/src/presentation/api/v1/client_capabilities/routes.py
frontend/src/features/client-capabilities/useClientCapabilities.ts
```

Добавить в `ClientSiteCapabilities`:

```python
cabinet_allowed_prefixes: list[str]
cabinet_marketing_route_action: Literal["redirect_public", "allow", "not_found"]
public_marketing_destination_path: str
legal_path_prefixes: list[str]
operational_path_prefixes: list[str]
```

### 7.5. Frontend proxy должен использовать backend snapshot

Файл:

```text
frontend/src/proxy.ts
```

Требования:

- убрать или минимизировать дублирующую hardcoded route policy;
- hardcoded sets оставить только как fallback при недоступности backend capabilities;
- использовать `cabinet_allowed_prefixes`, `legal_path_prefixes`, `operational_path_prefixes` из runtime snapshot;
- поведение frontend proxy должно совпадать с unit-тестами backend policy.

### 7.6. Тесты

Добавить/обновить:

```text
backend/tests/unit/application/services/test_customer_site_policy.py
frontend/src/__tests__/proxy.test.ts
backend/tests/unit/api/v1/test_client_capabilities.py
```

Сценарии:

1. `cabinet_only + public host + /pricing` => redirect cabinet `/dashboard`.
2. `cabinet_only + public host + /privacy` => allow.
3. `cabinet_only + cabinet host + /dashboard` => allow.
4. `cabinet_only + cabinet host + /pricing + redirect_public` => redirect public `/`.
5. `cabinet_only + cabinet host + /pricing + allow` => allow.
6. `cabinet_only + cabinet host + /pricing + not_found` => not_found decision.
7. `maintenance + /status` => allow.
8. `maintenance + /dashboard` => maintenance decision.
9. Query whitelist сохраняет `ref`, `referral`, `utm_*`, но не сохраняет произвольные параметры.

---

# Часть B. Onboarding apply/skip idempotency и preview кода

## 8. Проблема

Frontend сейчас не передаёт явный `idempotency_key` при apply/skip. Backend fallback-ит на hash кода, что защищает повторную отправку того же кода, но хуже для трассировки попыток и корректного retry после transient error.

Также пользователь не видит preview: система уже умеет определить тип кода, но UI показывает результат только после применения.

## 9. Цель

1. Сделать явный frontend-generated idempotency key для каждой apply/skip попытки.
2. Добавить безопасный preview endpoint, который показывает тип кода до применения.
3. Добавить UX preview: `Промокод`, `Инвайт`, `Подарочный код`, `Код не найден`, `Код неоднозначен`, `Код нельзя применить здесь`.

## 10. Frontend idempotency

Файл:

```text
frontend/src/features/customer-onboarding/PostRegistrationGrowthCodePrompt.tsx
```

Реализовать helper:

```ts
function createIdempotencyKey(prefix: string): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `${prefix}:${crypto.randomUUID()}`;
  }
  return `${prefix}:${Date.now()}:${Math.random().toString(16).slice(2)}`;
}
```

Поведение:

- при первом submit apply создать `applyIdempotencyKeyRef.current`;
- пока mutation pending, использовать тот же ключ;
- при retry после network error использовать тот же ключ, если пользователь не менял code;
- если пользователь изменил code, сбросить apply key;
- для skip создать отдельный `skipIdempotencyKeyRef.current`;
- отправлять `idempotency_key` в API.

Пример:

```ts
const applyAttemptRef = useRef<{ code: string; key: string } | null>(null);

function getApplyIdempotencyKey(normalizedCode: string): string {
  if (applyAttemptRef.current?.code === normalizedCode) {
    return applyAttemptRef.current.key;
  }
  const key = createIdempotencyKey('onboarding-apply');
  applyAttemptRef.current = { code: normalizedCode, key };
  return key;
}
```

## 11. Backend preview endpoint

Добавить endpoint:

```text
POST /api/v1/customer/onboarding/growth-code/preview
```

Файл:

```text
backend/src/presentation/api/v1/customer_onboarding/routes.py
backend/src/presentation/api/v1/customer_onboarding/schemas.py
```

Request:

```python
class CustomerOnboardingPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., min_length=1, max_length=64)
    flow_token: str | None = Field(None, min_length=16, max_length=240)
```

Response:

```python
class CustomerOnboardingPreviewResponse(BaseModel):
    accepted: bool
    detected_code_type: Literal["promo", "invite", "gift", "referral", "partner"] | None
    status: Literal[
        "preview_available",
        "not_found",
        "ambiguous",
        "wrong_context",
        "not_eligible",
        "expired",
        "already_used",
        "blocked",
    ]
    message_key: str
    masked_code: str
    matched_code_types: list[str] = []
    next_action: Literal[
        "apply_now",
        "stage_for_checkout",
        "redeem_entitlement",
        "resolve_ambiguity",
        "none",
    ]
    safe_details: dict[str, object] = {}
```

### 11.1. Preview не должен мутировать состояние

Запрещено в preview:

- redemption invite/gift;
- reservation checkout promo;
- создание order/payment;
- создание entitlement;
- изменение onboarding state.

Preview может:

- вызвать namespace lookup;
- вызвать resolver в read-only режиме;
- вернуть wrong context для checkout-only promo;
- вернуть matched code types;
- залогировать resolution event только если это уже принято в текущей архитектуре и не содержит raw code.

Лучше добавить в `ResolveGrowthCodeUseCase.execute()` параметр:

```python
record_event: bool = True
```

Для preview:

```python
record_event=False
```

Если менять resolver рискованно, preview должен использовать только `GrowthCodeNamespaceService` и read-only policy lookup.

## 12. Frontend preview UX

Файл:

```text
frontend/src/features/customer-onboarding/PostRegistrationGrowthCodePrompt.tsx
frontend/src/features/customer-onboarding/api.ts
```

Поведение:

- debounce 350–500ms после изменения code;
- не вызывать preview для пустого input;
- отменять/игнорировать устаревшие preview responses;
- показывать компактный status block под input;
- при `ambiguous` заблокировать apply и показать сообщение;
- при `wrong_context` для promo показать, что код будет сохранён/использован на checkout, если такая логика разрешена;
- apply всё равно должен проверяться backend-ом повторно.

UI-сообщения:

```text
Похоже, это промокод. Он будет применён при покупке тарифа.
Похоже, это инвайт-код. После применения вы получите доступ к VPN.
Похоже, это подарочный код. После применения подписка будет активирована.
Код найден в нескольких системах. Обратитесь в поддержку или введите другой код.
Код не найден или больше недействителен.
```

## 13. Тесты

Добавить:

```text
backend/tests/unit/api/v1/test_customer_onboarding.py
frontend/src/features/customer-onboarding/__tests__/PostRegistrationGrowthCodePrompt.test.tsx
```

Сценарии:

1. Apply отправляет `idempotency_key`.
2. Skip отправляет `idempotency_key`.
3. Retry apply с тем же code использует тот же key.
4. Изменение code создаёт новый key.
5. Preview invite показывает `detected_code_type=invite`.
6. Preview gift показывает `detected_code_type=gift`.
7. Preview promo checkout-only показывает `next_action=stage_for_checkout`.
8. Preview ambiguous блокирует apply.
9. Preview не создаёт redemption/entitlement/reservation.

---

# Часть C. Отдельный reject reason для ambiguous namespace

## 14. Проблема

Сейчас ambiguous namespace возвращается через:

```python
reject_reason = CODE_CONFLICTS_WITH_PROMO
conflict_code = CODE_NAMESPACE_AMBIGUOUS
```

Это семантически неверно: конфликт может быть invite/gift/referral/partner, а не promo.

## 15. Требование

Добавить отдельный enum:

```python
GrowthCodeRejectReason.CODE_NAMESPACE_AMBIGUOUS
```

Если имя enum уже зарезервировано, использовать:

```python
GrowthCodeRejectReason.CODE_AMBIGUOUS
```

Предпочтительное имя — `CODE_NAMESPACE_AMBIGUOUS`.

## 16. Backend changes

Файл enum:

```text
backend/src/domain/enums/enums.py
```

Добавить:

```python
class GrowthCodeRejectReason(StrEnum):
    ...
    CODE_NAMESPACE_AMBIGUOUS = "code_namespace_ambiguous"
```

Обновить:

```text
backend/src/application/use_cases/growth_codes/resolve_code.py
backend/src/presentation/api/v1/codes/schemas.py
backend/src/presentation/api/v1/customer_onboarding/routes.py
backend/src/presentation/api/shared/growth_customer_errors.py
frontend generated types/openapi
admin generated types/openapi
```

`_namespace_ambiguous()` должен возвращать:

```python
reject_reason=GrowthCodeRejectReason.CODE_NAMESPACE_AMBIGUOUS
conflict_code="CODE_NAMESPACE_AMBIGUOUS"
user_message_key="growth_codes.code.namespace_ambiguous"
```

## 17. Frontend/admin changes

- Добавить message key для customer frontend и admin.
- Отображать ambiguous как отдельное состояние.
- Не показывать это как promo conflict.

## 18. Тесты

Сценарии:

1. Код найден как invite и promo одновременно.
2. Resolver возвращает `result=conflicted`.
3. `reject_reason=code_namespace_ambiguous`.
4. `conflict_code=CODE_NAMESPACE_AMBIGUOUS`.
5. Response содержит `matched_code_types` в `policy_snapshot` или dedicated field.
6. Frontend показывает сообщение ambiguous и блокирует apply/checkout.

---

# Часть D. External payment completion path должен использовать FinalizeCompletedPaymentUseCase

## 19. Проблема

Zero-payment path явно вызывает `FinalizeCompletedPaymentUseCase`. Нужно подтвердить и при необходимости доработать внешний payment completion path:

```text
external invoice paid
-> payment completed
-> payment_attempt.succeeded
-> FinalizeCompletedPaymentUseCase
-> order paid
-> reservations consumed
-> growth benefits fulfilled
```

Старый `PostPaymentProcessingUseCase` всё ещё содержит legacy invite generation и order finalization. Он может остаться как legacy fallback, но order-based v6 flow должен быть через finalizer.

## 20. Требование

Все order-based payments, включая внешние CryptoBot/Telegram Stars/будущие providers, после подтверждения оплаты должны проходить через единую финализацию:

```python
FinalizeCompletedPaymentUseCase.execute(
    order=order,
    payment=payment,
    payment_attempt=payment_attempt,
    quote_snapshot=quote_snapshot,
    source="external_gateway_webhook" | "settlement_worker" | "telegram_stars_webhook"
)
```

## 21. Backend design

### 21.1. Добавить service/facade

Создать use-case:

```text
backend/src/application/use_cases/payment_attempts/settle_completed_attempt.py
```

Интерфейс:

```python
class SettleCompletedPaymentAttemptUseCase:
    async def execute(
        self,
        *,
        payment_id: UUID | None = None,
        payment_attempt_id: UUID | None = None,
        external_reference: str | None = None,
        provider: str | None = None,
        source: str,
    ) -> SettlementResult:
        ...
```

Responsibilities:

1. Найти `PaymentModel`.
2. Найти связанный `PaymentAttemptModel`.
3. Убедиться, что payment completed.
4. Если attempt ещё не `succeeded`, перевести в `succeeded` идемпотентно.
5. Загрузить order.
6. Извлечь quote snapshot из order/payment attempt/payment metadata.
7. Вызвать `FinalizeCompletedPaymentUseCase`.
8. Если order уже `paid`, вернуть idempotent result без повторной выдачи benefits.
9. Не выполнять legacy invite generation для order-based v6 payments.

### 21.2. Интеграция webhook/reconciliation

Найти все места, где payment переводится в `completed`:

- CryptoBot webhook/reconciliation;
- Telegram Stars completion;
- payment settlement worker;
- manual/admin completion, если есть;
- legacy direct payment completion.

Для order-based payment добавлять:

```python
await SettleCompletedPaymentAttemptUseCase(db).execute(
    payment_id=payment.id,
    source="cryptobot_webhook",
)
```

Legacy fallback оставить только если:

```text
payment_attempt отсутствует
order отсутствует
payment.metadata_.checkout_mode legacy
```

### 21.3. Idempotency

`FinalizeCompletedPaymentUseCase` уже возвращает `[]`, если order `settlement_status == paid`. Дополнительно settlement facade должен:

- не создавать второй succeeded attempt;
- не публиковать повторный event с другим key;
- не вызывать legacy `GenerateInvitesForPaymentUseCase` для order-based v6.

### 21.4. Ошибки

Если payment completed, но attempt/order не найдены:

- записать structured log;
- создать outbox event `payment.settlement.unlinked` или аналогичный;
- не выполнять benefits;
- не падать webhook 500, если provider webhook нельзя повторять бесконечно, но сохранить задачу reconciliation.

## 22. Тесты

Добавить:

```text
backend/tests/integration/test_external_payment_attempt_finalization.py
backend/tests/unit/application/use_cases/test_settle_completed_payment_attempt.py
backend/tests/unit/application/use_cases/test_payment_attempt_completed_publication.py
```

Главный acceptance test:

```text
Given order with growth benefits snapshot and external gateway_amount > 0
And payment attempt pending
And payment provider confirms invoice paid
When settlement use-case runs
Then payment_attempt.status == succeeded
And order.settlement_status == paid
And reservations consumed
And FulfillGrowthBenefitsUseCase created fulfillment
And invite batch/codes created if issue_invites exists
And second run creates no duplicates
```

---

# Часть E. Полноценное исполнение bonus_days, issue_gift, grant_addon

## 23. Проблема

Сейчас `issue_invites` и `wallet_credit` исполняются реально. `bonus_days`, `issue_gift`, `grant_addon` уходят в `side_effect_mode="queued_domain_worker"`. Для production-готовой benefit-platform нужно реализовать немедленное или worker-backed исполнение с фактическими side effects и идемпотентностью.

## 24. Решение

Сделать `FulfillGrowthBenefitsUseCase` центральным orchestrator-ом, а каждый тип benefit исполнять через dedicated handler.

Структура:

```text
backend/src/application/use_cases/growth_benefits/handlers/
  __init__.py
  issue_invites.py
  wallet_credit.py
  bonus_days.py
  issue_gift.py
  grant_addon.py
```

Или оставить в одном файле, но выделить private methods. Предпочтительно — отдельные handlers.

## 25. bonus_days

### 25.1. Config

Уже есть:

```python
BonusDaysBenefitConfig:
    days
    grant_mode
    entitlement_profile_key
    allow_zero_net_payment
    minimum_net_paid_amount
    reversal_mode
```

### 25.2. Поведение

Поддержать два режима:

```text
create_reward_allocation
extend_current_subscription
```

#### create_reward_allocation

Создать `growth_reward_allocation`:

```text
reward_type = bonus_days
quantity = days
unit = days
source_growth_code_id
source_order_id
source_payment_id
status = allocated/applied depending current reward model
```

Если уже есть allocation с idempotency key — вернуть existing.

#### extend_current_subscription

Если в проекте есть entitlement grant/service access model:

- найти active entitlement/subscription пользователя;
- продлить expires_at на `days`;
- создать audit/reward allocation;
- сохранить old/new expiration в result payload.

Если active entitlement нет:

- создать reward allocation в статусе `pending_application`;
- не терять бонус.

### 25.3. Result payload

```json
{
  "benefit_type": "bonus_days",
  "side_effect_mode": "entitlement_extension",
  "days": 14,
  "entitlement_grant_id": "...",
  "previous_expires_at": "...",
  "new_expires_at": "...",
  "reward_allocation_id": "...",
  "reversal_mode": "shorten_entitlement"
}
```

## 26. issue_gift

### 26.1. Поведение

Использовать существующий `IssueGiftCodeUseCase`, но вызвать его из benefit handler идемпотентно.

Config:

```text
count
friend_days или plan_id/duration profile
expiry_mode
entitlement_mode
recipient_hint optional
gift_message optional
```

Требование:

- если `count == 1`, создать один gift code;
- если `count > 1`, создать batch;
- source_payment_id/source_order_id/source_benefit_id должны сохраняться;
- raw gift code не должен попадать в logs/outbox, кроме защищённого выдаваемого владельцу канала.

### 26.2. Result payload

```json
{
  "benefit_type": "issue_gift",
  "side_effect_mode": "gift_code_issuance",
  "gift_batch_id": "...",
  "issued_count": 3,
  "gift_code_refs": [
    {
      "id": "...",
      "code_prefix": "GFT",
      "code_hash": "...",
      "status": "active"
    }
  ],
  "reversal_mode": "revoke_unredeemed"
}
```

## 27. grant_addon

### 27.1. Поведение

Для `GrantAddonBenefitConfig` реализовать:

- найти `PlanAddonModel` по `addon_code`;
- проверить active;
- проверить совместимость с текущим plan/order entitlement;
- создать `SubscriptionAddonModel` или equivalent grant;
- если active subscription нет, создать pending reward allocation;
- source fields: order_id, payment_id, benefit_id, growth_code_id.

### 27.2. Idempotency

Уникальный ключ:

```text
growth-addon-benefit:{benefit_id}:payment:{payment_id}:addon:{addon_code}
```

Если повторный webhook — возвращать existing addon grant.

### 27.3. Result payload

```json
{
  "benefit_type": "grant_addon",
  "side_effect_mode": "subscription_addon_grant",
  "addon_code": "dedicated_ip",
  "quantity": 1,
  "subscription_addon_id": "...",
  "expires_at": "...",
  "reversal_mode": "revoke_addon"
}
```

## 28. Reversal support

Для всех новых benefit handlers необходимо поддержать reversal metadata:

- `reversal_mode`;
- `reversal_policy`;
- IDs созданных side effects;
- возможность будущего refund/chargeback reversal.

Если actual reversal use-case уже есть — интегрировать. Если нет — result payload должен содержать достаточно данных для будущего reversal worker.

## 29. Тесты

Добавить:

```text
backend/tests/unit/application/use_cases/growth_benefits/test_bonus_days.py
backend/tests/unit/application/use_cases/growth_benefits/test_issue_gift.py
backend/tests/unit/application/use_cases/growth_benefits/test_grant_addon.py
backend/tests/integration/test_growth_benefits_full_fulfillment.py
```

Сценарии:

1. `bonus_days/create_reward_allocation` создаёт allocation.
2. `bonus_days/extend_current_subscription` продлевает active entitlement.
3. `issue_gift/count=1` создаёт gift code.
4. `issue_gift/count=3` создаёт batch.
5. `grant_addon` создаёт subscription addon.
6. Повторный run не создаёт дублей.
7. Zero-payment allowed только при `allow_zero_net_payment=true` или policy допускает это.
8. Minimum net paid amount блокирует benefit при недостаточной оплате.

---

# Часть F. Multi-code checkout: структурированные ошибки и UX

## 30. Проблема

Если в basket хотя бы один код отклонён, `_evaluate_code_basket` выбрасывает общий:

```python
ValueError("CODE_SET_REJECTED")
```

Frontend не получает подробности по каждому коду.

## 31. Цель

При частичной ошибке вернуть `422` с безопасным списком applications по каждому введённому коду.

## 32. Backend exception

Создать:

```text
backend/src/application/use_cases/growth_code_sets/exceptions.py
```

```python
class CodeSetRejectedError(ValueError):
    def __init__(self, *, applications: list[dict], message: str = "CODE_SET_REJECTED") -> None:
        super().__init__(message)
        self.code = "CODE_SET_REJECTED"
        self.applications = applications
```

В `_evaluate_code_basket` заменить:

```python
if rejected:
    raise ValueError("CODE_SET_REJECTED")
```

на:

```python
if rejected:
    raise CodeSetRejectedError(applications=applications)
```

## 33. API mapping

Файл:

```text
backend/src/presentation/api/v1/payments/routes.py
```

В `_raise_checkout_value_error()` или рядом добавить:

```python
except CodeSetRejectedError as exc:
    raise HTTPException(
        status_code=422,
        detail={
            "code": exc.code,
            "message_key": "growth_codes.code_set.rejected",
            "applications": exc.applications,
        },
    )
```

Response detail пример:

```json
{
  "code": "CODE_SET_REJECTED",
  "message_key": "growth_codes.code_set.rejected",
  "applications": [
    {
      "client_slot_id": "slot-1",
      "masked_code": "PRO...A1",
      "status": "accepted",
      "roles": ["discount"],
      "discount": {
        "applied_amount": "10.00",
        "target_currency": "USD"
      }
    },
    {
      "client_slot_id": "slot-2",
      "masked_code": "OLD...99",
      "status": "rejected",
      "reject_reason": "code_expired",
      "user_message_key": "growth_codes.promo.expired"
    }
  ]
}
```

## 34. Frontend UX

Файлы:

```text
frontend/src/features/customer-growth-code-basket/components/GrowthCodeBasket.tsx
frontend/src/features/customer-growth/lib/checkout-code-resolution.ts
frontend/src/app/[locale]/(dashboard)/subscriptions/components/PurchaseConfirmModal.tsx
frontend/src/app/[locale]/miniapp/plans/components/...
```

Требования:

1. Показывать список введённых кодов с индивидуальными статусами.
2. Не терять accepted-коды при ошибке одного rejected-кода.
3. Дать возможность удалить только rejected-код и повторить quote.
4. Для `not_selected` показать: «Код принят, но не выбран из-за правил совместимости/выгодности».
5. Для `ambiguous` показать отдельный warning.
6. Для `wrong_context` показать подсказку, куда применить код.

UI states:

```text
Принят
Применён
Принят, но не выбран
Истёк
Уже использован
Нельзя сочетать
Не подходит к тарифу
Неоднозначный код
```

## 35. Тесты

Добавить:

```text
backend/tests/unit/pricing/test_checkout_code_basket_errors.py
frontend/src/features/customer-growth-code-basket/components/__tests__/GrowthCodeBasket.test.tsx
```

Сценарии:

1. Один accepted, один expired => API 422 с обоими applications.
2. Frontend показывает accepted и rejected rows.
3. Удаление rejected-кода сохраняет accepted-код.
4. Duplicate code возвращается как rejected application, не общий crash.
5. Ambiguous code отображается отдельным статусом.

---

# Часть G. Полный lifecycle FX rates

## 36. Проблема

Ядро conversion snapshot уже есть. Нужно закрыть полный lifecycle:

```text
FX provider -> rate snapshots -> admin approval -> policy snapshot -> checkout
```

## 37. Цель

Сделать управляемую систему FX snapshots для fixed discounts:

- автоматическое обновление курсов;
- immutable snapshots;
- admin review/approval;
- stale-rate alerts;
- no-rerate checkout snapshot;
- безопасная работа с XTR managed rate.

## 38. Backend models

Если ещё нет production-ready таблиц, добавить:

```python
class FxProviderConfigModel(Base):
    __tablename__ = "fx_provider_configs"

    id: UUID
    provider_key: str
    priority: int
    enabled: bool
    supported_pairs: list[dict]
    stale_after_seconds: int
    requires_admin_approval: bool
    created_at: datetime
    updated_at: datetime
```

```python
class FxRateSnapshotModel(Base):
    __tablename__ = "fx_rate_snapshots"

    id: UUID
    provider_key: str
    source_currency: str
    target_currency: str
    rate: Decimal
    fetched_at: datetime
    expires_at: datetime
    source_type: str  # provider/configured/managed_xtr/manual_override
    provider_priority: int
    approval_state: str  # pending/approved/rejected/expired
    approved_by_admin_id: UUID | None
    approved_at: datetime | None
    rejection_reason: str | None
    checksum: str
    raw_provider_payload_hash: str | None
    created_at: datetime
```

## 39. Provider refresh job

Создать worker/use-case:

```text
backend/src/application/use_cases/growth_code_sets/fx_refresh.py
```

Responsibilities:

1. Получить enabled providers.
2. Запросить курсы для configured pairs.
3. Нормализовать currencies.
4. Создать immutable `FxRateSnapshotModel`.
5. Если provider trusted и `requires_admin_approval=false`, auto-approve.
6. Если manual/XTR/configured rate, требовать approval или explicit config.
7. Публиковать outbox/metric.

## 40. Admin API

Добавить/проверить endpoints:

```text
GET  /api/v3/admin/growth/fx/status
GET  /api/v3/admin/growth/fx/rates
POST /api/v3/admin/growth/fx/rates/refresh
POST /api/v3/admin/growth/fx/rates/{id}/approve
POST /api/v3/admin/growth/fx/rates/{id}/reject
POST /api/v3/admin/growth/fx/simulate
```

`simulate` должен использовать только approved snapshots, если не указан admin override.

## 41. Stale-rate alerts

Добавить метрики/события:

```text
growth_fx_rate_snapshot_freshness_seconds
growth_fx_rate_stale_total
growth_fx_conversion_failures_total{reason}
```

Alert condition:

```text
нет approved snapshot для pair > stale_after_seconds
```

## 42. Policy snapshot integration

При создании/публикации промокода с fixed discount:

- если discount currency != checkout supported currency;
- или promo доступен в нескольких валютах;
- policy version должен включить approved FX snapshot refs или strategy.

Snapshot example:

```json
{
  "fixed_discount_currency": "USD",
  "fx_rate_snapshots": [
    {
      "rate_id": "...",
      "provider": "ecb",
      "source_currency": "USD",
      "target_currency": "RUB",
      "rate": "92.15",
      "fetched_at": "...",
      "expires_at": "...",
      "provider_priority": 10,
      "source_type": "provider"
    }
  ]
}
```

## 43. Тесты

1. Refresh создаёт pending snapshot.
2. Approve переводит snapshot в approved.
3. Checkout использует approved snapshot.
4. Expired snapshot блокирует fixed conversion.
5. XTR требует managed rate.
6. Simulate не мутирует checkout.
7. Stale-rate status отображается в admin.

---

# Часть H. Финальная приёмка rule-builder

## 44. Цель

Проверить и довести rule-builder до production-ready workflow.

## 45. Обязательные возможности

### 45.1. AST validation на backend

Endpoint:

```text
POST /api/v3/admin/growth/rules/compile
```

Должен:

- валидировать AST schema;
- проверять allowed fields/operators/actions по catalog;
- возвращать normalized AST;
- возвращать checksum;
- возвращать warnings;
- не мутировать policy.

### 45.2. Import/export JSON policy

Frontend:

- export draft AST as JSON;
- import JSON file;
- validate client-side shape;
- обязательно compile на backend после import;
- показывать diff imported vs normalized.

### 45.3. Preview/simulation

Endpoint:

```text
POST /api/v3/admin/growth/rules/simulate
```

Должен:

- принимать AST или compiled checksum;
- принимать simulation context;
- возвращать matched actions;
- не создавать policy version;
- не выполнять side effects.

### 45.4. Publish workflow

Endpoints:

```text
POST /api/v3/admin/growth/policies
POST /api/v3/admin/growth/policies/{id}/submit-approval
POST /api/v3/admin/growth/policies/{id}/approve
POST /api/v3/admin/growth/policies/{id}/publish
```

Требования:

- optimistic concurrency через version/checksum;
- reason_code обязателен;
- admin audit обязателен;
- publish только approved policy version;
- active unique constraint для policy key.

### 45.5. Rollback policy version

Endpoint:

```text
POST /api/v3/admin/growth/policies/{id}/rollback
```

Должен:

- создать новую active version на основе выбранной предыдущей;
- не удалять историю;
- записать audit reason.

### 45.6. Diff between versions

Admin UI должен показывать:

- added/removed/changed nodes;
- changed actions;
- checksum old/new;
- effective_from/effective_to.

### 45.7. Read-only audit view

Admin UI:

- кто создал;
- кто отправил на approval;
- кто approve/publish/rollback;
- reason codes;
- timestamps;
- policy checksum.

## 46. Тесты

1. Compile валидного AST возвращает checksum.
2. Compile невалидного AST возвращает typed errors.
3. Import JSON не публикует policy.
4. Simulation не создаёт side effects.
5. Publish без approval запрещён.
6. Rollback создаёт новую version.
7. Diff отображает изменения.
8. Read-only audit view доступен без write permissions.

---

# Часть I. Новый UX: после успешного кода показать подключение VPN во всех customer-каналах

## 47. Цель

После регистрации пользователь проходит через один из supported customer-каналов:

```text
Web: регистрация -> ввод OTP -> окно ввода кода -> код успешно применён
Mini App: Telegram auth/register -> окно ввода кода -> код успешно применён
Telegram Bot: /start или onboarding deep-link -> ввод/отправка кода -> код успешно применён
```

Если код активировал доступ к VPN или выдал entitlement, пользователь должен сразу получить удобный канал подключения VPN. Для Web/Mini App это экран/панель, для Telegram Bot — серия bot-сообщений с inline-кнопками, QR-картинкой или ссылкой, не требующая перехода на сайт:

- ссылка на подключение VPN;
- QR-код;
- инструкции для iOS, Android, Windows, macOS, Linux;
- переключение инструкций внутри этого же окна;
- QR-код и ссылка не должны исчезать при переключении инструкции;
- кнопка `Я подключил` — зелёная;
- кнопка `Перейти в Личный кабинет`;
- в Telegram Bot: inline-кнопки `Открыть ссылку`, `Инструкция`, `Я подключил`, `Личный кабинет`;
- всё максимально удобно и без потери контекста.

## 48. Когда показывать окно подключения

Показывать connection modal/step только если после apply:

```text
result.status == completed
AND entitlement/access is active or pending activation can be resolved immediately
AND next_destination is not checkout-only staging
```

Не показывать, если:

- пользователь нажал skip;
- promo только staged for checkout и подписка ещё не активирована;
- код rejected;
- entitlement не создан;
- service identity/config недоступны.

Для promo-only staged flow:

```text
показывать сообщение: "Промокод сохранён. Выберите тариф, чтобы применить скидку."
кнопка: "Выбрать тариф"
```

## 49. Backend endpoint для connection bootstrap

Добавить endpoint:

```text
GET /api/v1/customer/onboarding/connection/bootstrap
```

Файлы:

```text
backend/src/presentation/api/v1/customer_onboarding/routes.py
backend/src/presentation/api/v1/customer_onboarding/schemas.py
backend/src/application/use_cases/customer_onboarding/connection_bootstrap.py
```

### 49.1. Response

```python
class CustomerOnboardingConnectionBootstrapResponse(BaseModel):
    available: bool
    status: Literal[
        "available",
        "no_active_entitlement",
        "service_identity_pending",
        "config_unavailable",
        "disabled",
    ]
    message_key: str
    subscription_url: str | None = None
    qr_payload: str | None = None
    config_profile_name: str | None = None
    expires_at: datetime | None = None
    device_limit: int | None = None
    traffic_limit_bytes: int | None = None
    instructions: list[ConnectionInstructionResponse]

class ConnectionInstructionResponse(BaseModel):
    platform: Literal["ios", "android", "windows", "macos", "linux"]
    title_key: str
    steps: list[ConnectionInstructionStepResponse]
    recommended_apps: list[ConnectionAppRecommendationResponse] = []

class ConnectionInstructionStepResponse(BaseModel):
    order: int
    title_key: str
    body_key: str
    action_url: str | None = None
    copy_value: str | None = None

class ConnectionAppRecommendationResponse(BaseModel):
    name: str
    url: str | None = None
    platform_store: str | None = None
```

### 49.2. Security

- Endpoint только для authenticated customer.
- Не логировать `subscription_url` и `qr_payload`.
- Sentry/request logs должны фильтровать эти поля.
- Response не кэшировать публично.
- Добавить headers:

```text
Cache-Control: no-store
```

### 49.3. Источник subscription URL

Использовать существующий источник VPN config/subscription URL, если он уже есть:

- active service identity;
- Remnawave subscription URL;
- existing customer config endpoint;
- current entitlement/service state.

Если existing endpoint уже отдаёт subscription URL, новый bootstrap endpoint может быть thin aggregator-ом, но должен вернуть инструкции и единый shape для onboarding UI.

### 49.4. Поведение при pending config

Если entitlement создан, но VPN config ещё не готов:

```json
{
  "available": false,
  "status": "service_identity_pending",
  "message_key": "onboarding.connection.pending"
}
```

Frontend должен показать retry button и авто-refresh каждые 3–5 секунд максимум 30 секунд.

### 49.5. Канально-независимый contract для Web, Mini App и Telegram Bot

Connection bootstrap endpoint должен быть **единым source-of-truth** для всех customer surfaces:

```text
web_frontend
telegram_miniapp
telegram_bot
```

Добавить query/header context:

```text
surface=web | miniapp | telegram_bot
platform_hint=ios | android | windows | macos | linux | unknown
```

Backend не должен отдавать разные entitlement/config данные по разным каналам. Различаться могут только:

- `preferred_layout`;
- `supported_actions`;
- `deep_link_actions`;
- инструкция по платформе;
- формат QR, если bot просит картинку.

Расширить response:

```python
class CustomerOnboardingConnectionBootstrapResponse(BaseModel):
    ...
    surface: Literal["web", "miniapp", "telegram_bot"] = "web"
    preferred_layout: Literal["desktop_panel", "mobile_panel", "bot_messages"]
    supported_actions: list[Literal[
        "copy_subscription_url",
        "open_subscription_url",
        "show_qr",
        "send_qr_image",
        "show_instructions",
        "mark_connected",
        "open_dashboard",
        "open_miniapp",
    ]]
    telegram_payload: TelegramConnectionPayloadResponse | None = None

class TelegramConnectionPayloadResponse(BaseModel):
    intro_message_key: str
    safe_profile_label: str | None = None
    subscription_url_button_text_key: str = "onboarding.connection.openLink"
    instructions_button_text_key: str = "onboarding.connection.instructions"
    mark_connected_button_text_key: str = "onboarding.connection.connected"
    dashboard_button_text_key: str = "onboarding.connection.goDashboard"
    qr_caption_key: str = "onboarding.connection.qrCaption"
```

Security:

- `telegram_payload` не должен содержать raw code;
- subscription URL можно отправлять пользователю только в private chat с authenticated/linked Telegram identity;
- в group chat отправлять только deep-link в bot private chat или Mini App, без URL/QR.


## 50. Backend endpoint: mark connected

Добавить:

```text
POST /api/v1/customer/onboarding/connection/mark-connected
```

Request:

```python
class MarkOnboardingConnectionConnectedRequest(BaseModel):
    flow_key: str | None = None
    version: int | None = None
    platform: Literal["ios", "android", "windows", "macos", "linux", "unknown"] | None = None
```

Response:

```python
class MarkOnboardingConnectionConnectedResponse(BaseModel):
    status: Literal["recorded", "already_recorded", "not_required"]
    next_destination: str = "/dashboard"
```

Persist:

- onboarding state `connection_acknowledged_at` или отдельная table event;
- selected platform;
- do not store raw subscription URL.

## 51. Frontend UX component

Создать компонент:

```text
frontend/src/features/customer-onboarding/ConnectionBootstrapPanel.tsx
```

Или интегрировать в `PostRegistrationGrowthCodePrompt.tsx` как второй step.

### 51.1. State machine

```text
code_entry
  -> applying
  -> applied_success
  -> loading_connection_bootstrap
  -> connection_available
  -> connection_pending
  -> connection_unavailable
  -> completed
```

### 51.2. UI layout

Рекомендуемый layout:

```text
┌──────────────────────────────────────────────┐
│ Ваш VPN-доступ активирован                    │
│ Подключитесь сейчас — это займёт меньше минуты │
├───────────────────────┬──────────────────────┤
│ QR-код                │ Инструкция            │
│ [QR]                  │ Tabs: iOS Android ... │
│ Ссылка подключения    │ Шаг 1                 │
│ [copy] [open]         │ Шаг 2                 │
│ Expires / device info │ Шаг 3                 │
├───────────────────────┴──────────────────────┤
│ [Я подключил] [Перейти в Личный кабинет]      │
└──────────────────────────────────────────────┘
```

### 51.3. QR code

Использовать existing QR component/library, если есть. Если нет:

- добавить лёгкую зависимость, согласованную с проектом;
- либо генерировать QR на backend как SVG/data URL;
- предпочтительно frontend QR из `qr_payload`, чтобы backend не генерировал изображения.

QR должен оставаться видимым при переключении инструкции.

### 51.4. Instructions tabs

Tabs:

```text
iOS
Android
Windows
macOS
Linux
```

Требования:

- выбранная вкладка хранится в local state;
- default platform определять по user agent, но пользователь может поменять;
- шаги используют i18n keys;
- copy buttons для URL и отдельных values;
- все external app links открывать в new tab с `noopener noreferrer`.

### 51.5. Buttons

`Я подключил`:

- зелёная primary button;
- вызывает `mark-connected`;
- инвалидирует subscription/config queries;
- redirect в dashboard или miniapp home.

`Перейти в Личный кабинет`:

- secondary/outline button;
- не требует mark-connected;
- redirect в dashboard/miniapp home;
- можно оставить onboarding state как completed, если код уже применён.

### 51.6. Mini App variant

Для Mini App:

- путь `/miniapp/onboarding/code`;
- connection panel должен быть mobile-first;
- QR можно оставить, но основной action — copy/open subscription link;
- bottom nav не должен перекрывать кнопки;
- кнопка `Я подключил` sticky внизу.

### 51.7. Telegram Bot variant

Новый UX должен быть реализован не только в Web frontend и Mini App, но и в Telegram Bot.

#### 51.7.1. Когда Bot показывает connection UX

Bot должен показать connection flow в следующих случаях:

1. Пользователь зарегистрировался/авторизовался через Telegram Bot или Mini App, и post-registration onboarding вернул `required=true`.
2. Пользователь отправил код текстом в bot private chat.
3. Пользователь нажал deep-link вида:

```text
/start code_<payload>
/start onboarding_<flow_token>
/start connect
```

4. Пользователь уже применил код в Web/Mini App, но открыл Bot и у него есть active entitlement/config.

Bot не должен показывать subscription URL/QR в group/supergroup/channel. В таких чатах он отвечает:

```text
Для подключения VPN откройте личный чат с ботом.
```

и даёт кнопку `Открыть бот`.

#### 51.7.2. Bot commands и callbacks

Добавить/обновить команды:

```text
/start
/code <promo_or_invite_or_gift_code>
/connect
/instructions
/help
```

Inline callbacks:

```text
onboarding:apply_code
onboarding:skip
connection:open_link
connection:show_qr
connection:instructions:ios
connection:instructions:android
connection:instructions:windows
connection:instructions:macos
connection:instructions:linux
connection:mark_connected
connection:dashboard
```

Callback payload не должен содержать raw subscription URL или raw code. Использовать короткий state key:

```text
bot_connection_session_id
```

State хранить в Redis/DB с TTL 10–30 минут.

#### 51.7.3. Bot message sequence после успешного кода

После успешного применения invite/gift/promo-with-entitlement bot отправляет:

```text
✅ VPN-доступ активирован

Вы можете подключиться прямо сейчас.

[Открыть ссылку подключения]
[Показать QR-код]
[Инструкция iOS] [Android]
[Windows] [macOS] [Linux]
[Я подключил]
[Личный кабинет]
```

Если Telegram client не позволяет открыть subscription URL корректно, пользователь всё равно должен иметь кнопку `Скопировать ссылку` или получить ссылку отдельным сообщением с предупреждением:

```text
Нажмите и удерживайте ссылку, чтобы скопировать её.
```

#### 51.7.4. QR в Telegram Bot

Bot должен уметь отправить QR как изображение:

```text
sendPhoto(qr_png_or_svg_rendered_as_png)
```

Требования:

- QR генерировать из `qr_payload`/`subscription_url` server-side в bot worker или через shared QR service;
- QR не сохранять публично;
- не логировать payload;
- caption брать из i18n key `onboarding.connection.qrCaption`;
- если QR generation failed, fallback — отправить subscription link и инструкции.

#### 51.7.5. Инструкции в Bot

Инструкции должны быть короткими и адаптированными под Telegram:

- одно сообщение на выбранную платформу;
- не больше 6 шагов;
- QR/link остаются доступными через inline-кнопки после инструкции;
- кнопка `Назад к подключению` возвращает базовый connection message.

Пример:

```text
📱 iOS
1. Установите рекомендованное приложение.
2. Вернитесь в этот чат и нажмите «Открыть ссылку подключения».
3. Разрешите импорт профиля.
4. Включите VPN.

[Открыть ссылку] [Показать QR]
[Я подключил] [Назад]
```

#### 51.7.6. `Я подключил` в Bot

Callback `connection:mark_connected` должен вызывать тот же backend endpoint:

```text
POST /api/v1/customer/onboarding/connection/mark-connected
```

Bot должен передать:

```json
{
  "platform": "ios|android|windows|macos|linux|unknown",
  "source_surface": "telegram_bot"
}
```

Если backend ответил `recorded` или `already_recorded`, bot показывает:

```text
✅ Отлично. Подключение отмечено.

[Личный кабинет] [Помощь]
```

#### 51.7.7. Bot authentication / account binding

Перед отправкой subscription URL/QR Bot обязан определить customer user:

1. По linked Telegram account / `telegram_id`.
2. По bot login token/deep-link session.
3. Если user не найден — предложить регистрацию или Mini App auth.

Запрещено:

- отправлять VPN config anonymous user без grant/session binding;
- отправлять чужой config при mismatch Telegram ID;
- показывать raw code в сообщениях/логах.

### 51.8. Shared connection session для Mini App и Telegram Bot

Mini App и Bot должны использовать общий backend state, чтобы пользователь мог начать в одном канале и продолжить в другом:

```text
Web apply code -> Bot /connect показывает тот же active config
Bot apply code -> Mini App показывает connection panel
Mini App apply code -> Bot /connect доступен без повторного apply
```

Добавить модель или Redis-backed session:

```python
class CustomerConnectionSessionModel(Base):
    id: UUID
    user_id: UUID
    onboarding_state_id: UUID | None
    source_surface: str
    status: str
    subscription_config_hash: str
    selected_platform: str | None
    acknowledged_at: datetime | None
    expires_at: datetime
    created_at: datetime
    updated_at: datetime
```

Если отдельная таблица избыточна, можно хранить минимальный state в `customer_onboarding_state.result_payload`, но Bot callback session лучше держать отдельно из-за TTL и callback security.

### 51.9. Telegram Bot/Mini App API layer

Добавить adapter/use-case, который не дублирует бизнес-логику Web:

```text
backend/src/application/use_cases/customer_onboarding/connection_bootstrap.py
backend/src/application/use_cases/telegram_bot/customer_connection.py
```

Bot handler должен вызывать application use-case, а не читать service identity/config напрямую.

Минимальный contract:

```python
class GetTelegramConnectionMessageUseCase:
    async def execute(
        self,
        *,
        telegram_id: int,
        platform_hint: str | None,
        locale: str,
    ) -> TelegramConnectionMessage:
        ...
```

`TelegramConnectionMessage` содержит:

- text message key + params;
- inline keyboard schema;
- optional QR image payload reference;
- no raw secrets in logs.


## 52. i18n для Web, Mini App и Telegram Bot

Добавить общие ключи:

```text
Auth.onboarding.connection.title
Auth.onboarding.connection.description
Auth.onboarding.connection.copyLink
Auth.onboarding.connection.openLink
Auth.onboarding.connection.connected
Auth.onboarding.connection.goDashboard
Auth.onboarding.connection.pending
Auth.onboarding.connection.unavailable
Auth.onboarding.connection.platforms.ios
Auth.onboarding.connection.platforms.android
Auth.onboarding.connection.platforms.windows
Auth.onboarding.connection.platforms.macos
Auth.onboarding.connection.platforms.linux
Auth.onboarding.connection.qrCaption
Auth.onboarding.connection.backToConnection
Auth.onboarding.connection.openBotPrivateChat
```

Для каждой платформы в Web/Mini App и Bot:

```text
Auth.onboarding.connection.instructions.ios.step1.title
Auth.onboarding.connection.instructions.ios.step1.body
...
```

Минимальные инструкции:

### iOS

1. Установите рекомендованное приложение.
2. Нажмите `Открыть ссылку` или отсканируйте QR.
3. Разрешите импорт профиля.
4. Включите VPN.

### Android

1. Установите рекомендованное приложение.
2. Откройте ссылку подписки или скопируйте её.
3. Импортируйте профиль.
4. Подключитесь.

### Windows

1. Установите клиент.
2. Скопируйте ссылку подписки.
3. Добавьте профиль по ссылке.
4. Подключитесь.

### macOS

1. Установите клиент.
2. Откройте или скопируйте ссылку.
3. Импортируйте профиль.
4. Подключитесь.

### Linux

1. Установите поддерживаемый клиент.
2. Скопируйте ссылку подписки.
3. Импортируйте профиль через GUI/CLI.
4. Подключитесь.

### Telegram Bot-specific keys

Добавить ключи в bot i18n/messages catalog:

```text
Bot.onboarding.connection.activatedTitle
Bot.onboarding.connection.activatedDescription
Bot.onboarding.connection.openLink
Bot.onboarding.connection.showQr
Bot.onboarding.connection.instructions
Bot.onboarding.connection.markConnected
Bot.onboarding.connection.dashboard
Bot.onboarding.connection.privateChatRequired
Bot.onboarding.connection.copyFallback
Bot.onboarding.connection.connectedRecorded
Bot.onboarding.connection.pendingConfig
Bot.onboarding.connection.configUnavailable
Bot.onboarding.connection.back
Bot.onboarding.connection.help
```

Bot text должен быть короче Web-текста и помещаться в Telegram message limits.

## 53. Frontend, Mini App и Telegram Bot tests

Добавить:

```text
frontend/src/features/customer-onboarding/__tests__/ConnectionBootstrapPanel.test.tsx
frontend/src/features/customer-onboarding/__tests__/PostRegistrationGrowthCodePrompt.test.tsx
frontend/src/app/[locale]/miniapp/onboarding/code/__tests__/connection-flow.test.tsx
backend/tests/unit/application/use_cases/telegram_bot/test_customer_connection.py
backend/tests/integration/test_telegram_bot_onboarding_connection.py
```

Сценарии:

1. После successful invite apply показывается connection panel.
2. QR и subscription link остаются видимыми при переключении tabs.
3. Copy link вызывает clipboard.
4. `Я подключил` вызывает mark-connected и redirect.
5. `Перейти в Личный кабинет` redirect без mark-connected.
6. Pending config показывает retry/autorefresh.
7. Promo staged for checkout не показывает connection panel.
8. Mini App surface использует `/miniapp/home` fallback.
9. Telegram Bot `/connect` показывает connection message при active entitlement.
10. Telegram Bot не отправляет subscription URL/QR в group chat.
11. Telegram Bot `connection:show_qr` отправляет QR image или fallback link.
12. Telegram Bot `connection:mark_connected` вызывает общий mark-connected endpoint.
13. Web -> Bot и Bot -> Mini App используют один active connection state без повторного apply.

## 54. Backend tests

Добавить:

```text
backend/tests/unit/api/v1/test_customer_onboarding_connection.py
backend/tests/integration/test_onboarding_connection_bootstrap.py
```

Сценарии:

1. Active entitlement => `available=true`, subscription_url returned.
2. No entitlement => `available=false`, status `no_active_entitlement`.
3. Pending service identity => pending status.
4. Response не содержит raw secrets в logs/safe snapshots.
5. mark-connected idempotent.
6. mark-connected stores platform.
7. connection bootstrap с `surface=telegram_bot` возвращает `preferred_layout=bot_messages`.
8. Bot callback session не содержит raw subscription URL.
9. Bot connection use-case проверяет Telegram account binding перед выдачей config.

---

# Часть J. Observability, audit, security

## 55. Logs

Запрещено логировать:

- raw promo/invite/gift code;
- subscription URL;
- QR payload;
- flow token;
- idempotency key целиком.

Разрешено:

```text
code_hash
code_prefix
masked_code
idempotency_key_hash
flow_key
flow_version
user_id
order_id
payment_id
benefit_id
```

## 56. Metrics

Добавить/проверить:

```text
customer_onboarding_preview_total{status,detected_code_type}
customer_onboarding_apply_total{status,code_type}
customer_onboarding_skip_total{status}
customer_onboarding_connection_bootstrap_total{status,surface}
customer_site_policy_decisions_total{mode,action,route_class,reason}
checkout_code_set_rejected_total{reason}
growth_benefit_fulfillment_total{benefit_type,status}
growth_fx_rate_stale_total{pair,provider}
telegram_bot_connection_flow_total{status,action}
telegram_bot_connection_private_chat_required_total
```

## 57. Audit

Admin mutations должны писать audit:

- customer site runtime config update;
- onboarding runtime config update;
- FX rate approval/rejection;
- policy publish/rollback;
- private access grant revoke;
- risk review decision.

Customer events можно писать в growth event/outbox, но не в admin audit, если это не принято архитектурой.

---

# Часть K. План внедрения

## 58. Этап 1 — безопасные API и enum fixes

1. Добавить `CODE_NAMESPACE_AMBIGUOUS`.
2. Добавить structured `CodeSetRejectedError`.
3. Добавить onboarding preview endpoint.
4. Добавить frontend idempotency_key для apply/skip.
5. Обновить OpenAPI/generated types.
6. Добавить unit tests.

## 59. Этап 2 — cabinet-only policy unification

1. Расширить `CustomerSiteRuntimeConfig`.
2. Обновить backend policy.
3. Обновить `/client/capabilities`.
4. Обновить frontend proxy на новые fields.
5. Добавить backend/frontend parity tests.

## 60. Этап 3 — payment finalization hardening

1. Создать `SettleCompletedPaymentAttemptUseCase`.
2. Интегрировать external webhook/reconciliation path.
3. Legacy `PostPaymentProcessingUseCase` оставить только для legacy payments.
4. Добавить integration test external invoice -> finalizer -> benefits.

## 61. Этап 4 — benefits full fulfillment

1. Реализовать `bonus_days`.
2. Реализовать `issue_gift`.
3. Реализовать `grant_addon`.
4. Добавить reversal payload и idempotency.
5. Добавить tests.

## 62. Этап 5 — FX lifecycle

1. Добавить models/migrations для provider config/snapshots, если их ещё нет.
2. Добавить refresh job.
3. Добавить admin approval endpoints.
4. Добавить stale metrics/alerts.
5. Интегрировать approved snapshots в policy publish.

## 63. Этап 6 — multichannel connection bootstrap UX

1. Backend bootstrap endpoint с `surface=web|miniapp|telegram_bot`.
2. Backend mark-connected endpoint с `source_surface` и `platform`.
3. Frontend `ConnectionBootstrapPanel`.
4. Mini App mobile-first connection panel.
5. Telegram Bot connection message flow, inline callbacks и QR delivery.
6. Интеграция после successful onboarding apply во всех каналах.
7. i18n для платформ и bot-specific messages.
8. Web/Mini App/Bot tests.

## 64. Этап 7 — rule-builder acceptance

1. Пройти checklist.
2. Добавить недостающие tests.
3. Проверить publish/rollback/audit.
4. Проверить import/export/simulation/diff.

---

# Часть L. Definition of Done

## 65. Backend DoD

- Все новые endpoints описаны в OpenAPI.
- Все request schemas используют `extra="forbid"` для write endpoints.
- Все мутации идемпотентны.
- Raw codes/subscription URL/QR не попадают в logs/outbox/snapshots.
- Alembic migrations upgrade/downgrade проходят.
- Unit/integration/security tests добавлены.
- External payment path через finalizer подтверждён тестом.

## 66. Frontend DoD

- Onboarding apply/skip отправляют idempotency_key.
- Preview работает с debounce и не мутирует состояние.
- Ambiguous namespace отображается отдельно.
- Multi-code basket показывает per-code statuses.
- Connection panel показывает QR/link/instructions без потери контекста.
- Mini App и Web имеют корректные destinations.
- Telegram Bot показывает тот же connection UX через private chat, inline buttons и QR/link delivery.
- Telegram Bot не отправляет VPN config в group/supergroup/channel.
- Все строки через i18n.
- Нет PostHog/A/B logic.

## 67. Admin DoD

- Customer site mode console управляет новыми fields.
- FX console показывает stale/approval state.
- Rule-builder проходит checklist.

## 67.1. Telegram Bot / Mini App DoD

- Bot `/connect` использует общий connection bootstrap use-case.
- Bot поддерживает `/code <код>` или безопасный deep-link для onboarding-кода.
- Bot показывает инструкции iOS/Android/Windows/macOS/Linux inline-кнопками.
- Bot умеет отправить QR как image или fallback-сообщение со ссылкой.
- Bot callback payload не содержит raw code, subscription URL или QR payload.
- Mini App connection panel использует тот же backend contract, что Web/Bot.
- Пользователь может начать flow в Web, продолжить в Bot или Mini App без повторного применения кода.
- Policy publish/rollback/audit доступны по ролям.
- Read-only пользователи не видят write actions или получают disabled state.

## 68. CI DoD

Обязательно прогнать:

```bash
# backend
cd backend
ruff check src tests
ruff format --check src tests
mypy src/ --ignore-missing-imports --no-strict-optional
pytest tests/ -v --tb=short

# frontend
cd frontend
npm run lint
npm run typecheck
npm test -- --runInBand

# admin
cd admin
npm run lint
npm run typecheck
npm test -- --runInBand
```

Если реальные команды отличаются от текущего package.json/pyproject — использовать актуальные команды проекта.

---

# Часть M. Приёмочные сценарии end-to-end

## 69. E2E 1: регистрация + invite + подключение VPN

```text
Given post_registration_code_prompt enabled
And invite code grants active entitlement
When user registers by email
And verifies OTP
Then user is redirected to /onboarding/code
When user enters invite code
Then invite is redeemed
And entitlement is active
And connection panel is shown
And QR/link are visible
When user selects Windows tab
Then QR/link remain visible
When user clicks Я подключил
Then mark-connected is recorded
And user is redirected to /dashboard
```

## 70. E2E 2: регистрация + promo staged for checkout

```text
Given promo code is checkout-only
When user enters promo in onboarding prompt
Then code is identified as promo
And user sees message that promo applies at checkout
And connection panel is not shown
And user can go to subscriptions
```

## 71. E2E 3: zero-payment promo + issue_invites

```text
Given promo gives 100% discount
And promo benefit issue_invites count=10 allow_zero_net_payment=true
When user quotes checkout
Then requires_external_payment=false
When payment attempt is created
Then internal_zero payment is completed
And order is paid
And benefit fulfillment creates one invite batch
And 10 invite codes are issued
Second run creates no duplicates
```

## 72. E2E 4: external payment + issue_invites

```text
Given promo benefit issue_invites count=10
And gateway_amount > 0
When external provider marks invoice paid
Then payment attempt becomes succeeded
And FinalizeCompletedPaymentUseCase runs
And order is paid
And benefit fulfillment creates one invite batch
And 10 invite codes are issued
```

## 73. E2E 5: multi-code partial error

```text
Given user enters 4 codes
And 2 are accepted
And 1 expired
And 1 conflicts with partner binding
When quote endpoint runs
Then API returns 422 CODE_SET_REJECTED
And applications contain all 4 codes
And frontend displays per-code statuses
And user can remove rejected codes and retry
```

## 74. E2E 6: cabinet-only parity

```text
Given customer_site.mode=cabinet_only
When public host /pricing is opened
Then redirect to cabinet /dashboard
When cabinet host /dashboard is opened
Then allow
When cabinet host /pricing is opened
Then backend policy and frontend proxy both redirect public or allow according to config
```

---

## 75. Итог

После выполнения этого ТЗ Growth Codes v6 станет production-hardening релизом:

- backend и frontend будут использовать единую cabinet-only политику;
- onboarding получит безопасный preview и явную идемпотентность;
- namespace ambiguity станет отдельным first-class состоянием;
- external и zero-payment settlement будут идти через единый finalizer;
- все основные benefit-типы будут исполняться реально или через явно контролируемый worker path;
- multi-code checkout станет понятным для пользователя;
- FX conversion будет иметь полный lifecycle от provider до checkout snapshot;
- rule-builder будет готов к финальной приёмке;
- пользователь после успешного кода сразу получит удобное подключение VPN с QR, ссылкой и инструкциями под свою платформу в Web, Mini App или Telegram Bot.
