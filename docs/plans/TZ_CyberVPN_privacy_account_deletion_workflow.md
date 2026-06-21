# Техническое задание

## Реализация ручной проверки запросов на удаление аккаунта

| Параметр | Значение |
|---|---|
| Проект | CyberVPN |
| Репозиторий | `Beep206/CyberVPN` |
| Базовая ветка | `main` |
| Дата | 2026-06-19 |
| Статус | Готово к реализации |
| Приоритет | Release blocker / High |
| Контуры | Backend, Customer Frontend, Admin, PostgreSQL, Redis, Remnawave, Messaging/Outbox |

---

## 1. Назначение

Нужно реализовать полный и проверяемый процесс:

```text
Пользователь отправил запрос
→ запрос сохранён в БД
→ запрос появился в админской очереди
→ сотрудник начал проверку
→ личность пользователя подтверждена
→ принято решение
→ удаление запланировано
→ удаление фактически выполнено
→ результат зафиксирован в аудите
→ пользователь получил уведомление
```

Главный критерий: успешное сообщение пользователю всегда должно соответствовать реально сохранённому запросу, доступному в административной части.

## 2. Обнаруженная причина дефекта

Текущий frontend вызывает:

```http
POST /api/v1/auth/me/privacy-requests
```

Backend-функция `create_privacy_request()`:

1. Создаёт `Stage1PrivacyRequestDecision` только в памяти.
2. Генерирует synthetic reference вида `s1sup-web-p1-...`.
3. Записывает `logger.info(...)`.
4. Возвращает `202 Accepted`.

Она не:

- получает `AsyncSession`;
- не создаёт запись в PostgreSQL;
- не создаёт `SupportTicketModel`;
- не создаёт privacy request;
- не создаёт audit event;
- не отправляет outbox event;
- не связывает reference с admin API.

Админская часть читает реальные тикеты из:

```text
support_tickets
support_ticket_messages
support_ticket_events
```

Поэтому запрос пользователя физически отсутствует в очереди.

Дополнительные проблемы:

- `ticket_reference` не является ID реального тикета;
- одинаковые запросы могут иметь одинаковый hash reference;
- нет статусов проверки;
- нет approve/deny;
- нет безопасного admin fulfillment;
- `DELETE /api/v1/auth/me` удаляет текущего авторизованного пользователя и не подходит для удаления целевого customer;
- тесты проверяют policy builder, но не persistence и admin visibility.

## 3. Цели

Обязательные результаты:

1. Каждый принятый запрос сохраняется в PostgreSQL.
2. Запрос связан с реальным support ticket.
3. Пользователь получает реальные публичные references.
4. Запрос отображается в admin queue.
5. Работает state machine ручной проверки.
6. Подтверждение личности обязательно до approve.
7. Удаление выполняется только уполномоченной ролью.
8. `fulfilled` устанавливается только после фактического выполнения.
9. Все действия записываются в audit trail.
10. Повторные клики и сетевые ретраи не создают дубликаты.
11. Пользователь видит актуальный статус.
12. Секреты, токены и VPN-конфигурации не попадают в логи и admin API.

## 4. Scope

Входит:

- `account_deletion`;
- совместимое сохранение `data_export`;
- таблицы privacy request и audit events;
- связанный support ticket;
- user list/detail/cancel API;
- admin list/detail/actions API;
- admin queue и review UI;
- fulfillment удаления;
- RBAC, idempotency, rate limiting;
- уведомления через outbox;
- backend/frontend/admin тесты;
- миграции, rollout и observability.

Не входит:

- автоматическая генерация архива data export;
- удаление финансовых/legal/security записей, подлежащих хранению;
- автоматическое одобрение;
- замена всей support-системы внешним SaaS.

## 5. Целевая архитектура

Создать отдельную доменную сущность `PrivacyRequest`, связанную один-к-одному с существующим `SupportTicket`.

```text
privacy_requests
        │
        │ 1:1
        ▼
support_tickets
        ├── support_ticket_messages
        └── support_ticket_events

privacy_requests
        └── privacy_request_events
```

### Ответственность сущностей

`privacy_requests` хранит:

- тип запроса;
- доменный статус;
- auth realm и principal;
- назначенного reviewer;
- подтверждение личности;
- approve/deny;
- плановую дату выполнения;
- результат fulfillment;
- безопасный policy snapshot;
- техническую ошибку;
- optimistic-lock version.

`support_tickets` хранит:

- общение с пользователем;
- public replies;
- internal notes;
- support status;
- назначение сотрудника;
- существующую интеграцию с support console.

`privacy_request_events` хранит неизменяемую историю:

- создание;
- назначение;
- запрос и завершение identity verification;
- изменение статуса;
- approve/deny;
- schedule;
- fulfillment success/failure;
- отмену;
- notification events.

Обычный support ticket не должен быть единственным источником истины, потому что у него нет обязательных privacy-инвариантов, identity verification и состояния фактического выполнения.

### Использование существующего Stage1 builder

Сохранить `build_stage1_privacy_request()` как policy/routing builder для:

- priority;
- required actions;
- forbidden actions;
- target queue;
- redaction;
- policy snapshot.

Synthetic reference `decision.ticket.reference` больше не является основным публичным ID. Его разрешено сохранить только в metadata:

```json
{
  "legacy_routing_reference": "s1sup-web-p1-..."
}
```

## 6. Доменная модель

### Типы запросов

```python
class PrivacyRequestType(StrEnum):
    ACCOUNT_DELETION = "account_deletion"
    DATA_EXPORT = "data_export"
```

### Статусы

```python
class PrivacyRequestStatus(StrEnum):
    SUBMITTED = "submitted"
    IDENTITY_VERIFICATION = "identity_verification"
    PENDING_DECISION = "pending_decision"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    FULFILLED = "fulfilled"
    DENIED = "denied"
    CANCELED = "canceled"
    FAILED = "failed"
```

Активные статусы:

```text
submitted
identity_verification
pending_decision
approved
scheduled
failed
```

Терминальные статусы:

```text
fulfilled
denied
canceled
```

### Разрешённые переходы

| Текущий статус | Следующий статус |
|---|---|
| `submitted` | `identity_verification`, `canceled` |
| `identity_verification` | `pending_decision`, `denied`, `canceled` |
| `pending_decision` | `approved`, `denied`, `canceled` |
| `approved` | `scheduled` |
| `scheduled` | `fulfilled`, `failed` |
| `failed` | `scheduled`, `denied` |
| `fulfilled` | нет |
| `denied` | нет |
| `canceled` | нет |

### Бизнес-инварианты

1. `approved` невозможен без `identity_verified_at`.
2. `scheduled` невозможен без approve.
3. `fulfilled` невозможен без успешного fulfillment use case.
4. `denied` требует непустой безопасной причины.
5. Пользователь может отменить запрос только до approve.
6. У principal может быть только один активный запрос одного типа.
7. Privacy request связан ровно с одним support ticket.
8. Support ticket связан не более чем с одним privacy request.
9. Любой transition создаёт audit event в той же транзакции.
10. Terminal request нельзя повторно изменять.
11. Support operator без отдельного permission не может выполнять удаление.
12. Raw password, TOTP, JWT, VPN URL и provider payload не сохраняются.

## 7. Модель данных

### Таблица `privacy_requests`

| Поле | Тип | Null | Назначение |
|---|---:|:---:|---|
| `id` | UUID | нет | Primary key |
| `public_id` | VARCHAR(40) | нет | Публичный ID `PRV-...` |
| `auth_realm_id` | UUID | нет | FK `auth_realms.id` |
| `principal_type` | VARCHAR(40) | нет | Например `customer` |
| `principal_subject` | UUID | нет | Стабильный subject |
| `customer_account_id` | UUID | да | FK `mobile_users.id`, `ON DELETE SET NULL` |
| `support_ticket_id` | UUID | нет | Unique FK `support_tickets.id`, `ON DELETE RESTRICT` |
| `request_type` | VARCHAR(32) | нет | Тип запроса |
| `status` | VARCHAR(32) | нет | Privacy status |
| `reason_code` | VARCHAR(64) | да | Нормализованная причина |
| `notes_redacted` | TEXT | да | Только очищенный текст, max 700 |
| `locale` | VARCHAR(10) | да | Локаль |
| `idempotency_key_hash` | CHAR(64) | да | SHA-256 ключа |
| `policy_snapshot` | JSONB | нет | Policy и guardrails |
| `assigned_admin_id` | UUID | да | Reviewer |
| `submitted_at` | TIMESTAMPTZ | нет | Отправка |
| `review_started_at` | TIMESTAMPTZ | да | Начало review |
| `identity_verified_at` | TIMESTAMPTZ | да | Проверка личности |
| `identity_verified_by` | UUID | да | Кто подтвердил |
| `decision_at` | TIMESTAMPTZ | да | Время решения |
| `decision_by` | UUID | да | Кто решил |
| `decision_reason` | VARCHAR(500) | да | Safe reason |
| `scheduled_for` | TIMESTAMPTZ | да | Плановая дата |
| `fulfilled_at` | TIMESTAMPTZ | да | Выполнение |
| `fulfilled_by` | UUID | да | Fulfiller |
| `canceled_at` | TIMESTAMPTZ | да | Отмена |
| `canceled_by` | UUID | да | Actor отмены |
| `last_error_code` | VARCHAR(80) | да | Safe code |
| `last_error_redacted` | VARCHAR(500) | да | Safe error |
| `version` | INTEGER | нет | Optimistic locking |
| `created_at` | TIMESTAMPTZ | нет | Создание |
| `updated_at` | TIMESTAMPTZ | нет | Обновление |

Публичный ID должен быть случайным, непоследовательным и не содержать UUID/email пользователя. Пример:

```text
PRV-01JY8D4ZKJ7Q9A2M6V
```

### Таблица `privacy_request_events`

| Поле | Тип | Назначение |
|---|---:|---|
| `id` | UUID | Primary key |
| `privacy_request_id` | UUID | FK, `ON DELETE RESTRICT` |
| `event_type` | VARCHAR(50) | Тип события |
| `actor_type` | VARCHAR(20) | `customer`, `admin`, `system` |
| `actor_id` | UUID nullable | Actor |
| `from_status` | VARCHAR(32) nullable | Старый статус |
| `to_status` | VARCHAR(32) nullable | Новый статус |
| `safe_summary` | VARCHAR(500) | Описание без PII |
| `metadata` | JSONB | Безопасная metadata |
| `created_at` | TIMESTAMPTZ | Время |

Типы событий:

```text
request_created
support_ticket_linked
review_started
assigned
identity_verification_requested
identity_verified
approved
denied
scheduled
fulfillment_started
fulfillment_succeeded
fulfillment_failed
canceled
notification_queued
notification_failed
```

### Индексы и ограничения

```text
UNIQUE privacy_requests.public_id
UNIQUE privacy_requests.support_ticket_id
UNIQUE privacy_requests.idempotency_key_hash
    WHERE idempotency_key_hash IS NOT NULL
```

Partial unique index:

```sql
CREATE UNIQUE INDEX uq_privacy_request_active_principal_type
ON privacy_requests (
    auth_realm_id,
    principal_type,
    principal_subject,
    request_type
)
WHERE status IN (
    'submitted',
    'identity_verification',
    'pending_decision',
    'approved',
    'scheduled',
    'failed'
);
```

Индексы:

```text
(status, submitted_at DESC)
(request_type, status, submitted_at DESC)
(assigned_admin_id, status, updated_at DESC)
(scheduled_for) WHERE status IN ('approved', 'scheduled', 'failed')
(principal_subject, submitted_at DESC)
```

### Сохранение аудита support tickets

Текущий FK `support_tickets.customer_account_id` использует `ON DELETE CASCADE`. Для сохранения privacy/support аудита при будущем hard delete рекомендуется заменить его на `ON DELETE SET NULL` и покрыть миграционным тестом.

## 8. Создание связанного support ticket

Для каждого privacy request создавать реальный support ticket:

| Поле | Значение |
|---|---|
| `owner_type` | `customer` |
| `source` | `customer_web` |
| `status` | `pending_support` |
| `category` | `privacy` |
| `priority` | `high` |
| `subject` | `Account deletion request` / `Data export request` |
| `customer_account_id` | Customer shadow, если существует |
| `created_by_actor_type` | `customer` |
| `created_by_actor_id` | Principal subject |
| `metadata.privacy_request_id` | Внутренний UUID |
| `metadata.privacy_request_public_id` | `PRV-...` |
| `metadata.request_type` | Тип запроса |
| `metadata.legacy_routing_reference` | Stage1 synthetic reference |

В `SupportTicketService` добавить специализированный метод:

```python
async def create_privacy_ticket(
    self,
    *,
    customer_account_id: UUID | None,
    actor_id: UUID,
    subject: str,
    message: str,
    metadata: dict[str, object],
) -> SupportTicket:
    ...
```

Метод принудительно использует:

```python
status=SupportTicketStatus.PENDING_SUPPORT
category=SupportTicketCategory.PRIVACY
priority=SupportTicketPriority.HIGH
source=SupportTicketSource.CUSTOMER_WEB
```

Создание privacy request, ticket, initial message, support event, privacy event и outbox event выполняется в одной DB-транзакции. Нельзя возвращать `202`, если хотя бы одна обязательная запись не сохранена.

## 9. Customer realm и mobile shadow

Customer web auth использует `AdminUserModel` в customer realm, а B2C resource APIs и support tickets используют `MobileUserModel`.

Перед созданием support ticket backend обязан:

1. Найти `MobileUserModel` по principal subject/current user ID.
2. При отсутствии безопасно создать или восстановить shadow.
3. Не создавать duplicate по email/username.
4. Не использовать email как основной идентификатор.
5. При конфликте не возвращать ложный success.
6. Сохранить generic principal reference независимо от наличия shadow.

Вынести `_ensure_customer_web_mobile_shadow()` из auth routes в:

```text
backend/src/application/services/customer_shadow_service.py
```

и переиспользовать в login и privacy flows.

## 10. Пользовательский API

### 10.1. Создание запроса

Сохранить URL:

```http
POST /api/v1/auth/me/privacy-requests
```

Headers:

```http
Content-Type: application/json
Idempotency-Key: <UUID>
```

Request:

```json
{
  "request_type": "account_deletion",
  "reason_code": "privacy_concerns",
  "notes": "Дополнительный комментарий"
}
```

`reason_code` должен стать отдельным полем. Для временной обратной совместимости backend может разбирать старый формат `reason=...
feedback=...`.

Response нового запроса:

```http
202 Accepted
```

```json
{
  "privacy_request_reference": "PRV-01JY8D4ZKJ7Q9A2M6V",
  "ticket_reference": "SUP-01JY8D5AG2S4MV82TQ",
  "request_type": "account_deletion",
  "status": "submitted",
  "message": "Account deletion request accepted for manual privacy review.",
  "submitted_at": "2026-06-19T12:30:00Z",
  "manual_fulfillment_target_days": 30,
  "existing": false
}
```

Повтор с тем же `Idempotency-Key` возвращает те же references и:

```json
{
  "existing": true
}
```

Если существует другой активный request того же типа, backend должен вернуть существующую заявку. Предпочтительно:

```http
200 OK
```

или `409 Conflict` с телом:

```json
{
  "code": "ACTIVE_PRIVACY_REQUEST_EXISTS",
  "privacy_request_reference": "PRV-...",
  "ticket_reference": "SUP-...",
  "request_type": "account_deletion",
  "status": "identity_verification",
  "existing": true
}
```

Ошибки:

| HTTP | Code | Условие |
|---:|---|---|
| 401 | `NOT_AUTHENTICATED` | Нет валидной сессии |
| 403 | `ACCOUNT_INACTIVE` | Аккаунт неактивен |
| 409 | `ACTIVE_PRIVACY_REQUEST_EXISTS` | Уже есть активный request |
| 422 | `VALIDATION_ERROR` | Ошибка данных |
| 429 | `PRIVACY_REQUEST_RATE_LIMITED` | Rate limit |
| 500 | `PRIVACY_REQUEST_PERSISTENCE_FAILED` | Не удалось сохранить |
| 503 | `PRIVACY_WORKFLOW_UNAVAILABLE` | Критическая зависимость недоступна |

### 10.2. Список запросов пользователя

```http
GET /api/v1/auth/me/privacy-requests
```

Фильтры:

```text
request_type
status
limit
cursor
```

Response:

```json
{
  "requests": [
    {
      "privacy_request_reference": "PRV-...",
      "ticket_reference": "SUP-...",
      "request_type": "account_deletion",
      "status": "identity_verification",
      "submitted_at": "2026-06-19T12:30:00Z",
      "updated_at": "2026-06-19T13:00:00Z"
    }
  ],
  "next_cursor": null
}
```

### 10.3. Detail

```http
GET /api/v1/auth/me/privacy-requests/{privacy_request_reference}
```

Request должен принадлежать текущему principal. Чужой ID возвращает `404`, а не `403`.

### 10.4. Отмена

```http
POST /api/v1/auth/me/privacy-requests/{privacy_request_reference}/cancel
```

Разрешено для:

```text
submitted
identity_verification
pending_decision
```

После approve user cancellation запрещён.

## 11. Административный API

### 11.1. Список

```http
GET /api/v1/admin/privacy-requests
```

Фильтры:

```text
status
request_type
assigned_admin_id
overdue
submitted_from
submitted_to
query
cursor
limit
```

`query` ищет только по безопасным значениям:

- `PRV-...`;
- `SUP-...`;
- principal UUID;
- customer public UID.

Response:

```json
{
  "requests": [
    {
      "privacy_request_reference": "PRV-...",
      "ticket_reference": "SUP-...",
      "request_type": "account_deletion",
      "status": "submitted",
      "principal_reference": "customer:8f4d...",
      "customer_public_uid": 1234567890,
      "assigned_admin_id": null,
      "submitted_at": "2026-06-19T12:30:00Z",
      "updated_at": "2026-06-19T12:30:00Z",
      "scheduled_for": null,
      "is_overdue": false
    }
  ],
  "next_cursor": null
}
```

### 11.2. Detail

```http
GET /api/v1/admin/privacy-requests/{reference}
```

Возвращает:

- request;
- ticket reference;
- safe user reference;
- status;
- policy snapshot;
- timestamps;
- reviewer/fulfiller;
- audit events;
- разрешённые действия;
- ссылки на user и support ticket.

Не возвращает password/TOTP/JWT/VPN URL/provider payload/raw notes.

### 11.3. Start review

```http
POST /api/v1/admin/privacy-requests/{reference}/start-review
```

```json
{
  "assign_to_self": true
}
```

Переход:

```text
submitted → identity_verification
```

### 11.4. Запрос подтверждения личности

```http
POST /api/v1/admin/privacy-requests/{reference}/request-identity-verification
```

```json
{
  "message": "Безопасный локализованный текст"
}
```

Действие:

- добавляет public reply в support ticket;
- создаёт audit event;
- support status становится `pending_customer`;
- privacy status остаётся `identity_verification`.

### 11.5. Подтверждение личности

```http
POST /api/v1/admin/privacy-requests/{reference}/verify-identity
```

```json
{
  "verification_method": "authenticated_session_and_support_challenge",
  "safe_note": "Verification completed"
}
```

Переход:

```text
identity_verification → pending_decision
```

Обязательно установить `identity_verified_at` и `identity_verified_by`.

### 11.6. Approve

```http
POST /api/v1/admin/privacy-requests/{reference}/approve
```

```json
{
  "decision_reason": "Identity verified; request approved."
}
```

Условия:

- request в `pending_decision`;
- identity verification завершена;
- actor имеет `privacy_request_review`;
- создаётся audit event;
- status становится `approved`.

### 11.7. Deny

```http
POST /api/v1/admin/privacy-requests/{reference}/deny
```

```json
{
  "decision_reason": "Unable to verify account ownership."
}
```

Причина обязательна, очищается и ограничивается 500 символами.

### 11.8. Schedule

```http
POST /api/v1/admin/privacy-requests/{reference}/schedule
```

```json
{
  "scheduled_for": "2026-06-20T09:00:00Z"
}
```

Переход:

```text
approved → scheduled
```

### 11.9. Execute

```http
POST /api/v1/admin/privacy-requests/{reference}/execute
```

Endpoint:

1. Проверяет permission.
2. Проверяет step-up/MFA.
3. Создаёт idempotent fulfillment job/outbox event.
4. Возвращает `202 Accepted`.
5. Worker выполняет удаление.
6. Только после успеха status становится `fulfilled`.

### 11.10. Retry

```http
POST /api/v1/admin/privacy-requests/{reference}/retry
```

Разрешено только из `failed`.

## 12. RBAC

Добавить permissions:

```text
privacy_request_read
privacy_request_review
privacy_request_fulfill
privacy_request_audit_read
```

| Действие | Permission |
|---|---|
| Список/detail | `privacy_request_read` |
| Review, verify, approve, deny | `privacy_request_review` |
| Запуск удаления | `privacy_request_fulfill` |
| Полный audit | `privacy_request_audit_read` |

Запрещено использовать общий `USER_UPDATE` как единственное разрешение. Support operator может общаться и проверять, но destructive fulfillment должен быть отделён.

## 13. Backend: структура реализации

Рекомендуемые новые файлы:

```text
backend/src/domain/entities/privacy_request.py
backend/src/domain/repositories/privacy_request_repository.py

backend/src/infrastructure/database/models/privacy_request_model.py
backend/src/infrastructure/database/repositories/privacy_request_repo.py

backend/src/application/services/privacy_request_service.py
backend/src/application/services/customer_shadow_service.py

backend/src/application/use_cases/privacy_requests/create_privacy_request.py
backend/src/application/use_cases/privacy_requests/list_user_privacy_requests.py
backend/src/application/use_cases/privacy_requests/cancel_privacy_request.py
backend/src/application/use_cases/privacy_requests/start_privacy_review.py
backend/src/application/use_cases/privacy_requests/verify_privacy_identity.py
backend/src/application/use_cases/privacy_requests/approve_privacy_request.py
backend/src/application/use_cases/privacy_requests/deny_privacy_request.py
backend/src/application/use_cases/privacy_requests/schedule_privacy_request.py
backend/src/application/use_cases/privacy_requests/execute_account_deletion.py

backend/src/presentation/api/v1/privacy_requests/schemas.py
backend/src/presentation/api/v1/privacy_requests/routes.py
backend/src/presentation/api/v1/admin_privacy_requests/routes.py
```

Существующий compatibility URL в `auth/routes.py` должен вызывать новый use case либо быть перенесён с полным сохранением API path.

### Repository interface

Минимальные методы:

```python
class PrivacyRequestRepository(Protocol):
    async def create(...) -> PrivacyRequest: ...
    async def get_by_public_id(...) -> PrivacyRequest | None: ...
    async def get_for_update(...) -> PrivacyRequest | None: ...
    async def get_by_idempotency_hash(...) -> PrivacyRequest | None: ...
    async def get_active_for_principal(...) -> PrivacyRequest | None: ...
    async def list_for_principal(...) -> PrivacyRequestListResult: ...
    async def list_for_admin(...) -> PrivacyRequestListResult: ...
    async def update(...) -> PrivacyRequest: ...
    async def add_event(...) -> PrivacyRequestEvent: ...
```

### Алгоритм создания

```python
async def execute(command: CreatePrivacyRequestCommand) -> PrivacyRequestResult:
    # 1. Проверить request_type.
    # 2. Нормализовать reason и notes.
    # 3. Рассчитать hash Idempotency-Key.
    # 4. Вернуть запись по тому же idempotency hash, если она существует.
    # 5. Найти активный request этого principal и типа.
    # 6. Построить Stage1 policy/routing decision.
    # 7. Очистить notes существующим redactor.
    # 8. Обеспечить customer mobile shadow.
    # 9. Создать support ticket со status=pending_support.
    # 10. Создать privacy request и связать с ticket.
    # 11. Создать request_created event.
    # 12. Создать acknowledgement в outbox.
    # 13. Flush.
    # 14. Вернуть реальные PRV/SUP references.
```

### Race condition и idempotency

Проверки на уровне Python недостаточно. Partial unique index обязателен.

При двух одновременных POST:

1. Первая транзакция создаёт request.
2. Вторая получает unique violation.
3. Backend перехватывает конкретное нарушение.
4. Выполняет select активного request.
5. Возвращает его с `existing=true`.

`Idempotency-Key`:

- frontend создаёт через `crypto.randomUUID()`;
- backend хранит SHA-256, а не исходное значение;
- повтор с тем же ключом возвращает прежний response;
- duplicate не создаёт новый ticket/outbox event.

### Locking transitions

Каждый admin transition:

1. Загружает request через `SELECT ... FOR UPDATE`.
2. Проверяет текущий status.
3. Проверяет permission и бизнес-инварианты.
4. Меняет поля.
5. Увеличивает `version`.
6. Создаёт audit event.
7. Синхронизирует support status.
8. Commit.

При конфликте возвращать:

```http
409 Conflict
```

```json
{
  "code": "PRIVACY_REQUEST_STATE_CONFLICT",
  "current_status": "approved",
  "current_version": 5
}
```

## 14. Оркестрация фактического удаления

### Текущие операции проекта

`DeleteAccountUseCase`:

- soft-delete `AdminUserModel`;
- ставит `is_active=False`;
- ставит `deleted_at`;
- отзывает refresh tokens;
- отзывает Redis JWT sessions.

`MobileDeleteAccountUseCase`:

- удаляет VPN access в Remnawave;
- анонимизирует `MobileUserModel`;
- очищает Telegram, TOTP, subscription и referral данные;
- ставит `status=deleted`;
- отзывает JWT sessions.

### Новый use case

Создать:

```text
ExecuteApprovedAccountDeletionUseCase
```

Вход:

```python
privacy_request_id: UUID
actor_id: UUID | None
actor_type: Literal["admin", "system"]
```

Алгоритм:

1. Загрузить request `FOR UPDATE`.
2. Проверить:
   - type = `account_deletion`;
   - status = `scheduled`;
   - identity verification завершена;
   - approve зафиксирован;
   - `scheduled_for` наступил;
   - fulfillment ранее не завершён.
3. Создать `fulfillment_started`.
4. Зафиксировать idempotent execution key.
5. Найти web и mobile customer по principal subject.
6. Выполнить pre-deletion checks:
   - активные подписки;
   - незавершённые payment/refund операции;
   - security/legal hold;
   - записи, подлежащие сохранению.
7. Сохранить только безопасный результат policy checks.
8. Удалить/revoke VPN access.
9. Анонимизировать mobile account.
10. Soft-delete web account.
11. Отозвать все principal sessions.
12. Поставить финальное уведомление в outbox до потери контактных данных.
13. Установить:
    - `status=fulfilled`;
    - `fulfilled_at`;
    - `fulfilled_by`.
14. Создать `fulfillment_succeeded`.
15. Перевести support ticket в `resolved`.
16. Commit.

Нельзя вызывать из admin UI:

```http
DELETE /api/v1/auth/me
```

Этот endpoint относится к текущему авторизованному субъекту и создаёт риск удаления администратора.

### Remnawave и внешние ошибки

Внешняя операция не входит в атомарную PostgreSQL-транзакцию.

Требования:

- операция idempotent;
- `404` означает «уже удалено» и считается успешным результатом;
- другие ошибки не приводят к `fulfilled`;
- request переходит в `failed`;
- сохраняется safe error code;
- raw provider response не сохраняется;
- admin видит retry;
- создаются metric и alert.

### Worker/outbox

Предпочтительный поток:

```text
Admin execute
→ DB: scheduled/outbox event
→ worker получает событие
→ выполняет external и local actions
→ status=fulfilled или failed
```

Синхронный MVP допускается только при выполнении всех условий:

- endpoint idempotent;
- повторный запуск безопасен;
- timeout контролируется;
- `fulfilled` не устанавливается заранее;
- external failure сохраняется как `failed`.

## 15. Синхронизация privacy и support статусов

| Privacy status | Support status |
|---|---|
| `submitted` | `pending_support` |
| `identity_verification`, ожидается пользователь | `pending_customer` |
| `identity_verification`, получен ответ | `pending_support` |
| `pending_decision` | `pending_support` |
| `approved` | `pending_support` |
| `scheduled` | `pending_support` |
| `failed` | `pending_support` |
| `fulfilled` | `resolved` |
| `denied` | `resolved` |
| `canceled` | `closed` |

Privacy request является источником истины для privacy state. Support status отвечает за коммуникационную очередь.

## 16. Уведомления

Обязательные события:

1. Request accepted.
2. Identity verification requested.
3. Request approved.
4. Request denied.
5. Deletion scheduled.
6. Deletion fulfilled.
7. Fulfillment failed — internal alert.

Каналы:

- in-app messaging;
- email dispatcher;
- Telegram при linked account;
- internal admin alert.

Уведомления создаются через transactional outbox.

Нельзя:

- отправлять email до DB commit;
- считать request созданным только по факту отправки email;
- откатывать сохранённый request из-за временной ошибки канала.

Notification failure создаёт event, повторяется worker и не меняет успешный fulfillment обратно.

## 17. Пользовательский frontend

Затрагиваемые файлы:

```text
frontend/src/widgets/delete-account/delete-account-client.tsx
frontend/src/lib/api/auth.ts
frontend/src/lib/api/privacy-requests.ts
frontend/src/widgets/settings-cabinet/settings-cabinet-dashboard.tsx
frontend/messages/*/delete-account.json
frontend/messages/*/settings.json
```

### API module

Создать:

```text
frontend/src/lib/api/privacy-requests.ts
```

Существующий `authApi.requestPrivacyAction()` временно оставить как wrapper для обратной совместимости.

### Idempotency-Key

При первой попытке submit:

```ts
const idempotencyKey = crypto.randomUUID();
```

Ключ:

- создаётся один раз на попытку;
- повторно используется при network retry;
- сбрасывается после успешного ответа;
- не содержит пользовательских данных.

### Форма

Сохранить:

- выбор причины;
- дополнительный комментарий;
- ввод `DELETE`;
- checkbox подтверждения.

Не вызывать `DELETE /auth/me`.

После успешной отправки показать:

- `privacy_request_reference`;
- `ticket_reference`;
- статус;
- дату отправки;
- целевой срок;
- ссылку «Посмотреть статус»;
- возврат в настройки.

### Активный request

При открытии страницы сначала загрузить активные requests.

Если найден активный `account_deletion`:

- показать status card вместо новой формы;
- показать references;
- показать доступную отмену;
- запретить создание второго request;
- дать ссылку на поддержку.

### Обработка ошибок

Различать:

```text
401 — сессия истекла
409 — существует активный запрос
422 — ошибка данных
429 — rate limit
5xx — backend failure
network — ошибка сети
```

Development logging:

```ts
console.log('[privacy-request] submission started', {
  requestType: 'account_deletion',
});

console.log('[privacy-request] submission completed', {
  status: response.data.status,
  existing: response.data.existing,
});

console.trace('[privacy-request] submission failed', {
  status: axiosError.response?.status,
  code: axiosError.response?.data?.code,
});
```

Не логировать notes, email, токены, cookies или полный body.

UI states:

```text
idle
validating
loadingExisting
existingRequest
submitting
submitted
canceling
error
```

Submit должен быть disabled при `submitting`.

## 18. Административный frontend

Рекомендуемые файлы:

```text
admin/src/lib/api/privacy-requests.ts

admin/src/features/privacy-requests/components/privacy-request-console.tsx
admin/src/features/privacy-requests/components/privacy-request-list.tsx
admin/src/features/privacy-requests/components/privacy-request-detail.tsx
admin/src/features/privacy-requests/components/privacy-request-status-chip.tsx
admin/src/features/privacy-requests/components/privacy-request-actions.tsx
admin/src/features/privacy-requests/lib/formatting.ts

admin/src/app/[locale]/privacy-requests/page.tsx
admin/src/app/[locale]/privacy-requests/[reference]/page.tsx
```

### Навигация и badge

Добавить route:

```text
/privacy-requests
```

Badge считает action-required статусы:

```text
submitted
identity_verification
pending_decision
approved
scheduled
failed
```

Он не должен зависеть только от support status `pending_support`.

### Список

Desktop columns:

| Колонка | Значение |
|---|---|
| Request | `PRV-...`, тип |
| Customer | public UID / safe principal |
| State | Privacy status |
| Support | `SUP-...` |
| Assigned | Reviewer |
| Submitted | Дата |
| SLA | Due/overdue |
| Actions | Открыть |

Mobile layout — карточки без горизонтального overflow.

Фильтры:

```text
status
request_type
assignment: all / mine / unassigned
overdue
date range
query
```

Фильтры синхронизировать с URL.

### Detail page

Блоки:

1. Summary.
2. Safe account reference.
3. Privacy status.
4. Support ticket link.
5. Policy checklist.
6. Identity verification.
7. Decision.
8. Fulfillment.
9. Audit timeline.
10. Internal notes.
11. Public communication.
12. Allowed actions.

### Action controls

Кнопка доступна только если:

- transition разрешён;
- permission присутствует;
- request version актуальна.

Для approve/deny/execute нужны confirmation dialogs.

Для execute:

- показать PRV reference;
- показать safe target customer;
- потребовать ввод `DELETE`;
- потребовать step-up auth;
- явно указать, что удаляется целевой customer, а не admin.

### React Query

Keys:

```ts
['admin', 'privacy-requests', 'list', filters]
['admin', 'privacy-requests', 'detail', reference]
['admin', 'privacy-requests', 'queue-count']
```

После mutation инвалидировать:

```text
privacy list
privacy detail
queue count
support ticket detail
support queue
```

В privacy detail добавить ссылку `/support/{ticket_reference}`. В support ticket category `privacy` добавить обратную ссылку `/privacy-requests/{privacy_reference}`.

## 19. Безопасность

### Redaction

Перед сохранением notes использовать существующую redaction-логику.

Удалять/заменять:

```text
vless/vmess/trojan/ss/wireguard URLs
HTTP URLs
email
Telegram bot tokens
длинные secret-like строки
access/refresh tokens
```

### Логи

Разрешено:

```text
privacy_request_id
privacy_request_reference
ticket_reference
request_type
status
actor_type
actor_id
error_code
duration
```

Запрещено:

```text
raw notes
email
password
password hash
TOTP secret
subscription URL
VPN config
provider payload
JWT
cookie
```

### Rate limiting

Минимум:

```text
3 create requests в сутки на principal
```

Та же idempotency key не должна повторно расходовать лимит.

Использовать комбинацию:

```text
principal + auth_realm
principal + IP
```

### CSRF/auth

- Mutating cookie-auth endpoints защищаются существующим same-origin/CSRF механизмом.
- CORS не разрешает произвольные origin.
- Admin actions не принимают customer token.
- Customer routes не принимают admin session как замену ownership.

### Step-up authentication

Перед `execute` проверить недавнюю MFA либо short-lived step-up token. Максимальный возраст подтверждения задаётся конфигурацией.

### Object authorization

- Customer видит только свои requests.
- Admin имеет отдельные permissions.
- Чужой customer request возвращает `404`.
- Случайный public ID не заменяет authorization.

### Audit

Audit events недоступны для изменения через обычный API. Обязательно фиксировать actor, event, from/to status, timestamp, safe summary и version.

## 20. Observability

Метрики:

```text
privacy_requests_created_total{request_type}
privacy_requests_existing_returned_total{request_type}
privacy_requests_active{request_type,status}
privacy_request_transition_total{from_status,to_status,result}
privacy_request_transition_conflict_total
privacy_request_fulfillment_total{result}
privacy_request_fulfillment_duration_seconds
privacy_request_overdue_total{request_type,status}
privacy_request_support_link_failure_total
privacy_request_notification_failure_total{channel}
```

Structured events:

```text
privacy_request.created
privacy_request.existing_returned
privacy_request.review_started
privacy_request.identity_verified
privacy_request.approved
privacy_request.denied
privacy_request.scheduled
privacy_request.fulfillment_started
privacy_request.fulfillment_succeeded
privacy_request.fulfillment_failed
privacy_request.canceled
```

Alerts:

- persistence failure;
- support linkage failure;
- fulfillment failure;
- requests в `failed`;
- requests сверх SLA;
- рост overdue;
- outbox notification failures.

## 21. Backend-тестирование

### Unit tests

Проверить state machine:

```text
submitted -> identity_verification: PASS
submitted -> approved: FAIL
identity_verification -> approved без verification: FAIL
pending_decision -> approved после verification: PASS
scheduled -> fulfilled напрямую через repository: FAIL
terminal -> любой status: FAIL
```

Redaction:

- `vless://`;
- `https://`;
- email;
- Telegram token;
- long secret.

Public ID:

- формат;
- уникальность;
- отсутствие user UUID;
- отсутствие email.

Idempotency:

- одинаковый key возвращает один request;
- разные keys при активном request возвращают существующий request;
- после terminal status можно создать новый request.

### Repository tests

Проверить:

- create/get/list;
- partial unique index;
- unique support link;
- cursor pagination;
- `FOR UPDATE`;
- version increment;
- audit events;
- admin filters;
- `ON DELETE SET NULL`.

### Integration API test полного потока

```text
1. Создать и авторизовать customer.
2. POST /auth/me/privacy-requests.
3. Получить 202.
4. Проверить privacy_requests row.
5. Проверить support_tickets row.
6. Проверить initial message/event.
7. Проверить privacy_request_events.
8. Авторизовать admin.
9. GET /admin/privacy-requests?status=submitted.
10. Найти тот же PRV reference.
11. Открыть detail.
12. Выполнить start-review.
13. Запросить/подтвердить identity verification.
14. Выполнить approve.
15. Выполнить schedule.
16. Выполнить execute.
17. Проверить fulfilled.
18. Проверить web soft-delete.
19. Проверить mobile anonymization.
20. Проверить Remnawave deletion.
21. Проверить отзыв sessions.
22. Проверить audit sequence.
```

Дополнительные cases:

- unauthenticated create;
- inactive customer;
- invalid type;
- notes > 700;
- concurrent duplicate;
- admin без permission;
- approve без identity verification;
- deny без reason;
- cancel после approve;
- execute до scheduled time;
- execute дважды;
- Remnawave 404;
- Remnawave 500;
- missing mobile shadow;
- support ticket failure;
- outbox failure;
- чужой customer detail;
- mutation terminal request.

### Contract tests

Проверить OpenAPI paths:

```text
POST /api/v1/auth/me/privacy-requests
GET /api/v1/auth/me/privacy-requests
GET /api/v1/auth/me/privacy-requests/{reference}
POST /api/v1/auth/me/privacy-requests/{reference}/cancel

GET /api/v1/admin/privacy-requests
GET /api/v1/admin/privacy-requests/{reference}
POST /api/v1/admin/privacy-requests/{reference}/start-review
POST /api/v1/admin/privacy-requests/{reference}/request-identity-verification
POST /api/v1/admin/privacy-requests/{reference}/verify-identity
POST /api/v1/admin/privacy-requests/{reference}/approve
POST /api/v1/admin/privacy-requests/{reference}/deny
POST /api/v1/admin/privacy-requests/{reference}/schedule
POST /api/v1/admin/privacy-requests/{reference}/execute
POST /api/v1/admin/privacy-requests/{reference}/retry
```

После OpenAPI export пересоздать frontend/admin generated types.

## 22. Frontend и admin тестирование

Customer frontend:

- submit с реальным response;
- наличие `Idempotency-Key`;
- active request card;
- duplicate response;
- отображение PRV/SUP references;
- cancel;
- 401/409/422/429/500;
- network error;
- disabled submit;
- сохранение `DELETE` confirmation;
- отсутствие notes в console;
- accessibility;
- mobile layout.

Admin:

- permission denied;
- loading/error/empty;
- filters и URL sync;
- queue count;
- list/detail;
- allowed action buttons;
- invalid transitions disabled;
- confirmation dialogs;
- step-up required;
- query invalidation;
- support backlink;
- audit timeline;
- responsive layout.

MSW handlers должны моделировать реальные transitions и ошибки, а не всегда возвращать success.

## 23. E2E-сценарии

### Успешное удаление

```gherkin
Given активный customer вошёл в кабинет
When он отправляет account deletion request
Then запрос сохраняется
And отображается PRV reference
And создаётся support ticket
And admin видит request в очереди
When admin начинает проверку
And подтверждает личность
And одобряет запрос
And планирует выполнение
And запускает fulfillment
Then customer деактивирован и анонимизирован
And VPN access удалён
And sessions отозваны
And request имеет status fulfilled
And audit содержит все переходы
```

### Повторный клик

```gherkin
Given первый POST принят
When browser повторяет POST с тем же Idempotency-Key
Then новая строка не создаётся
And возвращаются те же references
```

### Параллельные запросы

```gherkin
When два запроса отправлены одновременно
Then существует один active privacy request
And один support ticket
```

### Remnawave failure

```gherkin
Given request scheduled
When Remnawave возвращает 500
Then request не становится fulfilled
And получает failed
And audit содержит safe error
And admin может выполнить retry
```

### Отказ

```gherkin
Given ownership не подтверждён
When reviewer указывает reason и выполняет deny
Then status становится denied
And удаление не запускается
And пользователь получает уведомление
```

## 24. Критерии приёмки

| ID | Критерий |
|---|---|
| AC-01 | После успешного POST существует строка `privacy_requests` |
| AC-02 | Создан связанный реальный `support_tickets` |
| AC-03 | References из ответа существуют в БД |
| AC-04 | Request появляется в admin queue |
| AC-05 | Request учитывается в queue badge |
| AC-06 | Повтор с тем же idempotency key не создаёт дубль |
| AC-07 | Параллельные запросы не обходят active unique constraint |
| AC-08 | Approve невозможен без identity verification |
| AC-09 | RBAC запрещает неавторизованный доступ |
| AC-10 | Execute удаляет target customer, а не admin |
| AC-11 | `fulfilled` ставится только после реального успеха |
| AC-12 | External failure приводит к `failed` |
| AC-13 | Каждый transition создаёт audit event |
| AC-14 | Customer видит активный request и status |
| AC-15 | Customer может отменить только до approve |
| AC-16 | Логи не содержат PII, tokens и VPN URLs |
| AC-17 | Admin общается через связанный support ticket |
| AC-18 | Account deletion не уничтожает privacy audit |
| AC-19 | Login/support/device/mobile delete regression проходит |
| AC-20 | OpenAPI, types, docs и runbook обновлены |

## 25. Порядок реализации

### PRIV-001. Baseline regression

- Добавить failing integration test текущего дефекта.
- Проверить, что POST сейчас не создаёт DB row.
- Добавить ожидание admin visibility.
- Зафиксировать текущий OpenAPI contract.
- Не менять customer success UI до persistence.

**Результат:** дефект воспроизводится тестом.

### PRIV-002. DB и domain

- Создать enums/entities.
- Создать ORM models.
- Создать Alembic migration.
- Создать repository interface/implementation.
- Добавить partial unique index.
- Добавить event table.
- Обновить FK support ticket при принятом решении.

**Результат:** готова доменная модель.

### PRIV-003. Transactional create

- Добавить create use case.
- Интегрировать Stage1 policy builder.
- Создать support ticket.
- Вернуть реальные references.
- Добавить idempotency.
- Добавить duplicate handling.
- Добавить acknowledgement outbox event.

**Результат:** POST создаёт долговечную заявку.

### PRIV-004. User read/cancel API

- List.
- Detail.
- Active request query.
- Cancel.
- Ownership tests.

**Результат:** customer отслеживает запрос.

### PRIV-005. Admin read queue

- Admin list/detail.
- Filters.
- Permissions.
- Queue count.
- Support/privacy links.

**Результат:** request виден в админке.

### PRIV-006. Review workflow

- Start review.
- Identity verification request.
- Verify identity.
- Approve.
- Deny.
- Schedule.
- Audit.
- Support status sync.

**Результат:** работает ручная проверка.

### PRIV-007. Fulfillment

- Target-account deletion orchestrator.
- Web/mobile account handling.
- Remnawave.
- Session revocation.
- Worker/outbox.
- Failed/retry.
- Step-up auth.

**Результат:** одобренный request безопасно выполняется.

### PRIV-008. Customer UI

- Новый API module.
- Idempotency-Key.
- Active request card.
- Status/detail.
- Cancel.
- Error mapping.
- Переводы.

**Результат:** UI отражает реальное состояние.

### PRIV-009. Admin UI

- Queue/list/detail.
- Filters.
- Actions.
- Confirmation dialogs.
- Audit timeline.
- Responsive layout.
- React Query invalidation.
- Переводы.

**Результат:** готово рабочее место reviewer.

### PRIV-010. Observability и rollout

- Metrics.
- Alerts.
- Runbook.
- Feature flags.
- Production verification.
- Cleanup synthetic-only flow.

**Результат:** feature готова к эксплуатации.

## 26. Feature flags

```text
privacy_requests_persistence_enabled
privacy_requests_admin_queue_enabled
privacy_requests_fulfillment_enabled
```

Порядок включения:

1. Persistence backend.
2. Admin read queue.
3. Review actions.
4. Customer status UI.
5. Fulfillment.
6. Notifications и alerts.

Нельзя включать новый customer success UI до persistence.

## 27. Миграция и rollout

Deploy sequence:

1. Применить additive migration.
2. Развернуть backend persistence.
3. Проверить создание через API/SQL.
4. Развернуть admin read UI.
5. Проверить очередь.
6. Развернуть admin transitions.
7. Развернуть customer status UI.
8. Включить fulfillment flag.
9. Выполнить production smoke test.
10. Сохранить evidence.

### Исторические synthetic requests

Старые requests не существуют в БД. Возможный источник — structured logs:

```text
S1 privacy request accepted
```

Автоматический destructive backfill запрещён, потому что:

- логи могут быть неполными;
- synthetic reference детерминирован;
- повторы не всегда различимы;
- отсутствует полноценный request state;
- пользователь мог обратиться повторно.

Рекомендуется:

1. Экспортировать log events.
2. Дедуплицировать по user ID, type и времени.
3. Сформировать ручной review list.
4. Не создавать автоматические approved requests.
5. Зафиксировать дату перехода на durable flow.

### Rollback

- Не удалять новые таблицы.
- Не удалять сохранённые requests.
- Отключить fulfillment flag.
- Оставить admin read-only.
- Сохранить audit/outbox.
- Не возвращаться молча к synthetic-only success.

## 28. Definition of Done

Задача завершена, когда:

- миграции применяются и откатываются на тестовой БД;
- backend unit/integration/contract tests проходят;
- customer frontend tests проходят;
- admin tests проходят;
- OpenAPI обновлён;
- generated types обновлены;
- один POST создаёт один privacy request и один support ticket;
- request виден admin пользователю;
- review workflow работает;
- execute удаляет target customer;
- failure корректно отображается;
- customer видит status;
- metrics и alerts добавлены;
- runbook создан;
- production smoke evidence сохранён;
- в логах отсутствуют чувствительные данные.

## 29. Smoke-check после реализации

PostgreSQL:

```sql
SELECT
    public_id,
    request_type,
    status,
    support_ticket_id,
    submitted_at
FROM privacy_requests
ORDER BY submitted_at DESC
LIMIT 10;
```

```sql
SELECT
    public_id,
    status,
    category,
    priority,
    customer_account_id,
    created_at
FROM support_tickets
WHERE category = 'privacy'
ORDER BY created_at DESC
LIMIT 10;
```

Проверка связи:

```sql
SELECT
    pr.public_id AS privacy_reference,
    st.public_id AS ticket_reference,
    pr.status AS privacy_status,
    st.status AS support_status
FROM privacy_requests pr
JOIN support_tickets st ON st.id = pr.support_ticket_id
ORDER BY pr.created_at DESC
LIMIT 10;
```

Audit:

```sql
SELECT
    event_type,
    actor_type,
    from_status,
    to_status,
    safe_summary,
    created_at
FROM privacy_request_events
WHERE privacy_request_id = :request_id
ORDER BY created_at;
```

Windows logs:

```powershell
docker compose logs backend |
    Select-String "privacy_request."
```

В логах допускаются references/status/error code, но не notes/email/token/config.

## 30. Исходные точки кода

Customer frontend:

```text
frontend/src/widgets/delete-account/delete-account-client.tsx
frontend/src/lib/api/auth.ts
frontend/messages/ru-RU/delete-account.json
```

Текущий endpoint и Stage1 policy:

```text
backend/src/presentation/api/v1/auth/routes.py
backend/src/presentation/api/v1/auth/schemas.py
backend/src/presentation/api/shared/stage1_privacy_request_path.py
backend/src/presentation/api/shared/stage1_support_ticket_path.py
backend/src/presentation/api/shared/stage1_support_escalation.py
```

Support tickets:

```text
backend/src/domain/entities/support_ticket.py
backend/src/application/services/support_ticket_service.py
backend/src/infrastructure/database/models/support_ticket_model.py
backend/src/infrastructure/database/repositories/support_ticket_repo.py
backend/src/presentation/api/v1/support_tickets/routes.py
```

Удаление аккаунтов:

```text
backend/src/application/use_cases/auth/delete_account.py
backend/src/application/use_cases/mobile_auth/delete_account.py
backend/src/presentation/api/v1/mobile_auth/routes.py
```

Admin:

```text
admin/src/lib/api/support.ts
admin/src/features/support/components/support-console.tsx
admin/src/features/admin-shell/hooks/use-admin-action-queues.ts
```

Тесты для расширения:

```text
backend/tests/security/test_stage1_privacy_request_path.py
backend/tests/integration/test_support_tickets.py
frontend/src/lib/api/__tests__/auth.test.ts
frontend/src/test/mocks/handlers.ts
admin/src/features/support/components/__tests__/support-console.test.tsx
admin/src/lib/api/__tests__/support.test.ts
```

## 31. Запреты реализации

Нельзя:

1. Исправлять проблему вызовом `DELETE /auth/me` из формы.
2. Считать `logger.info` созданием заявки.
3. Использовать synthetic hash как источник истины.
4. Возвращать success до persistence.
5. Хранить raw VPN URL или tokens.
6. Approve без identity verification.
7. Выполнять deletion без отдельного permission.
8. Выставлять `fulfilled` до реального результата.
9. Удалять privacy audit вместе с customer.
10. Скрывать external failure под success.
11. Создавать несвязанные privacy и support записи.
12. Полагаться только на frontend disable от дублей.
13. Использовать email как единственный principal key.
14. Логировать request body целиком.
15. Выполнять destructive action без step-up auth.

## 32. Итоговый ожидаемый результат

```text
Customer:
POST
→ получает PRV и SUP references
→ видит status
→ может открыть поддержку
→ может отменить до approve

Backend:
сохраняет request + ticket + events
→ обеспечивает idempotency
→ контролирует state machine
→ выполняет target-account deletion
→ ведёт audit

Admin:
видит queue badge
→ открывает request
→ проверяет личность
→ approve/deny
→ schedule
→ execute
→ видит success/failure и audit
```

**Главный критерий корректности: успешное подтверждение пользователю всегда соответствует реально сохранённому и доступному для административной обработки запросу.**
