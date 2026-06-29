# Техническое задание v7.5
# Многоразовые и одноразовые invite-коды для CyberVPN Growth System

**Проект:** CyberVPN
**Версия ТЗ:** v7.5
**Формат:** backend + admin + frontend/customer + Telegram Mini App + Telegram Bot + миграции + тесты
**Цель:** добавить поддержку многоразовых invite-кодов, сохранив существующие одноразовые invite-коды и текущую flexible invite campaign систему.

---

## 1. Контекст

Сейчас invite-код фактически является одноразовым: у `invite_codes` есть поля `is_used`, `used_by_user_id`, `used_at`, после успешного redeem код помечается использованным. Это подходит для персональных/уникальных кодов, но не подходит для сценариев, где один и тот же invite-code нужно дать нескольким людям.

Нужно добавить второй режим:

```text
single_use — текущий режим, один код активируется один раз;
multi_use  — один и тот же код можно активировать много раз, но каждый пользователь может активировать его только один раз.
```

При этом текущая логика lifetime Premium Smart RU, child invites, tree lineage, onboarding prompt, Mini App и Telegram Bot должна продолжить работать.

---

## 2. Целевой пользовательский сценарий

Администратор создаёт invite campaign:

```text
Campaign: premium_smart_ru_lifetime_multi_use

Root invite-code:
- usage mode: multi_use
- code: например SMART-RU-VIP
- max total redemptions: без лимита или большой лимит, например 100000
- per user redemption cap: 1
- plan: Premium Smart RU
- access duration: lifetime
- device limit: 5
- traffic: Unlimited / fair_use
- after redemption: выдать пользователю 12 child invite-кодов

Child invite-codes:
- usage mode: single_use или multi_use — настраивается отдельно
- plan: Premium Smart RU
- access duration: lifetime
- device limit: 5
- each redeemer gets 12 child invite-codes
```

Новый пользователь регистрируется, вводит один и тот же root invite-code в onboarding, Mini App или Bot. Каждый уникальный пользователь получает доступ один раз. Следующая попытка тем же пользователем должна возвращать понятную ошибку:

```text
Вы уже активировали этот invite-code.
```

---

## 3. Цели

### 3.1. Функциональные цели

1. Добавить поддержку одноразовых и многоразовых invite-кодов.
2. Сохранить обратную совместимость текущих одноразовых invite-кодов.
3. Позволить администратору выбирать режим кода:
   - `Одноразовый`;
   - `Многоразовый`.
4. Для многоразового кода дать настройки:
   - общий лимит активаций;
   - лимит активаций на пользователя;
   - лимит на устройство;
   - лимит на IP-окно;
   - период velocity;
   - срок действия самого кода;
   - surfaces: Web / Mini App / Telegram Bot.
5. После каждой успешной активации многоразового invite-code создавать отдельный redemption record.
6. После каждой успешной активации выдавать пользователю тариф и дочерние invite-коды по policy.
7. Правильно строить дерево приглашений даже если один root code активировали много пользователей.
8. В админке показывать inventory и аналитику многоразового кода:
   - сколько активаций;
   - кто активировал;
   - сколько осталось;
   - какие child invites выданы;
   - дерево пользователей.
9. Web onboarding, Mini App и Telegram Bot должны поддерживать multi-use без отдельных полей.

### 3.2. Нефункциональные цели

1. Исключить race condition при одновременных активациях одного multi-use code.
2. Не логировать raw invite code.
3. Не ломать legacy invite flow.
4. Все операции должны быть idempotent.
5. Все важные изменения должны иметь audit trail.
6. Все новые лимиты должны быть backend-authoritative, frontend только UI.

---

## 4. Термины

### 4.1. Usage mode

Добавить enum:

```python
class InviteCodeUsageMode(StrEnum):
    SINGLE_USE = "single_use"
    MULTI_USE = "multi_use"
```

### 4.2. Redemption cap mode

```python
class InviteRedemptionCapMode(StrEnum):
    LIMITED = "limited"
    UNLIMITED = "unlimited"
```

Рекомендуется не делать реально бесконечную выдачу без технического лимита. Для UI можно показывать “без лимита”, но backend должен хранить безопасный hard cap или требовать explicit high-risk acknowledgement.

---

## 5. Backend. Модель данных

## 5.1. Таблица `invite_codes`

Добавить поля:

```python
usage_mode: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="single_use",
    server_default="single_use",
    index=True,
)

max_redemptions: Mapped[int | None] = mapped_column(Integer, nullable=True)

redeemed_count: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=0,
    server_default="0",
)

active_redemptions_count: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=0,
    server_default="0",
)

reversed_redemptions_count: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=0,
    server_default="0",
)

first_redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

last_redeemed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

exhausted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

per_user_redemption_cap: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=1,
    server_default="1",
)

multi_use_policy: Mapped[dict[str, Any]] = mapped_column(
    JSON,
    nullable=False,
    default=dict,
)
```

Constraints:

```sql
usage_mode IN ('single_use', 'multi_use')
max_redemptions IS NULL OR max_redemptions > 0
redeemed_count >= 0
active_redemptions_count >= 0
reversed_redemptions_count >= 0
per_user_redemption_cap >= 1
```

### 5.1.1. Семантика legacy `is_used`

Поле `is_used` оставить для обратной совместимости.

Правила:

```text
single_use:
  is_used=false до первой успешной активации
  is_used=true после первой успешной активации

multi_use:
  is_used=false пока код ещё можно активировать
  is_used=true только когда код exhausted/revoked/expired
```

Добавить helper:

```python
def invite_code_is_redeemable(invite: InviteCodeModel, now: datetime) -> bool:
    if invite.status in {"revoked", "expired", "exhausted"}:
        return False
    if invite.expires_at is not None and invite.expires_at <= now:
        return False
    if invite.usage_mode == "single_use":
        return not invite.is_used
    if invite.usage_mode == "multi_use":
        if invite.max_redemptions is None:
            return True
        return invite.active_redemptions_count < invite.max_redemptions
    return False
```

---

## 5.2. Таблица `invite_campaign_versions`

Добавить поля:

```python
root_usage_mode: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="single_use",
    server_default="single_use",
)

root_max_redemptions: Mapped[int | None] = mapped_column(Integer, nullable=True)

root_per_user_redemption_cap: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=1,
    server_default="1",
)

child_usage_mode: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="single_use",
    server_default="single_use",
)

child_max_redemptions: Mapped[int | None] = mapped_column(Integer, nullable=True)

child_per_user_redemption_cap: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=1,
    server_default="1",
)

multi_use_policy: Mapped[dict[str, Any]] = mapped_column(
    JSONB,
    nullable=False,
    default=dict,
)
```

Назначение:

```text
root_usage_mode — режим root-кодов, которые создаёт admin batch;
child_usage_mode — режим дочерних кодов, которые выдаются после redemption.
```

---

## 5.3. Таблица `invite_batches`

Добавить snapshot-поля:

```python
usage_mode: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="single_use",
    server_default="single_use",
)

max_redemptions_per_code: Mapped[int | None] = mapped_column(Integer, nullable=True)

per_user_redemption_cap: Mapped[int] = mapped_column(
    Integer,
    nullable=False,
    default=1,
    server_default="1",
)

multi_use_policy: Mapped[dict[str, Any]] = mapped_column(
    JSON,
    nullable=False,
    default=dict,
)
```

---

## 5.4. Таблица `invite_redemptions`

Если уже есть `InviteRedemptionModel`, расширить:

```python
usage_mode_snapshot: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="single_use",
    server_default="single_use",
)

redemption_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)

code_redemptions_count_after: Mapped[int | None] = mapped_column(Integer, nullable=True)

device_key_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

client_ip_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

user_agent_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
```

Уникальные constraints / indexes:

```sql
-- Один пользователь может успешно активировать один и тот же invite-code только один раз,
-- если per_user_redemption_cap = 1.
CREATE UNIQUE INDEX uq_invite_redemptions_code_user_active
ON invite_redemptions(invite_code_id, invitee_user_id)
WHERE status = 'redeemed';
```

Если нужен режим `per_user_redemption_cap > 1`, уникальный индекс нужно заменить на runtime validation, а не DB constraint. Для текущего требования оставить `per_user_redemption_cap=1`.

---

## 6. Backend. Миграции

Создать Alembic migration:

```text
202607xx_invite_multi_use_codes.py
```

Migration steps:

1. Добавить поля в `invite_codes`.
2. Добавить поля в `invite_campaign_versions`.
3. Добавить поля в `invite_batches`.
4. Добавить поля в `invite_redemptions`.
5. Backfill:
   ```sql
   invite_codes.usage_mode = 'single_use'
   invite_codes.max_redemptions = 1
   invite_codes.redeemed_count = CASE WHEN is_used THEN 1 ELSE 0 END
   invite_codes.active_redemptions_count = CASE WHEN is_used THEN 1 ELSE 0 END
   invite_codes.first_redeemed_at = used_at
   invite_codes.last_redeemed_at = used_at
   invite_codes.exhausted_at = used_at WHERE is_used = TRUE
   invite_codes.per_user_redemption_cap = 1
   ```
6. Для существующих campaign versions:
   ```sql
   root_usage_mode = 'single_use'
   root_max_redemptions = 1
   child_usage_mode = 'single_use'
   child_max_redemptions = 1
   ```
7. Добавить indexes.
8. Downgrade должен удалять новые поля без изменения старых `is_used`.

---

## 7. Backend. Redemption logic

## 7.1. Проблема текущего flow

Сейчас redemption flow для invite-code делает:

```text
find invite by code
check is_used / expired / revoked
grant entitlement
mark_used(invite.id, user_id)
ensure InviteRedemption
issue child invites
ensure tree state
```

Для multi-use нельзя глобально `mark_used` после первой активации. Нужно разделить:

```text
single_use redemption
multi_use redemption
```

---

## 7.2. Новый atomic redemption flow

В `RedeemInviteUseCase` сделать:

```python
async def execute(...):
    invite = await invite_repo.get_by_code_for_update(code)

    await validate_invite_redeemable(invite, user_id, runtime_context)

    redemption = await reserve_invite_redemption(
        invite=invite,
        user_id=user_id,
        runtime_context=runtime_context,
        idempotency_key=...
    )

    grant = await grant_entitlement(...)

    child_batch = await issue_child_invites(...)

    await finalize_invite_redemption(
        invite=invite,
        redemption=redemption,
        grant=grant,
        child_batch=child_batch,
    )
```

### 7.2.1. Locking

Обязательно использовать row lock:

```sql
SELECT * FROM invite_codes WHERE code_hash = :hash FOR UPDATE
```

или repository method:

```python
get_by_code_hash_for_update(...)
```

Для multi-use это нужно, чтобы одновременно 100 пользователей не превысили `max_redemptions`.

---

## 7.3. Валидация redeemable

```python
def validate_invite_redeemable(invite, user_id, now):
    if invite.status in {"revoked", "expired", "exhausted"}:
        raise InviteCodeNotAvailable

    if invite.expires_at and invite.expires_at <= now:
        raise InviteCodeExpired

    if invite.usage_mode == "single_use" and invite.is_used:
        raise InviteCodeAlreadyUsed

    if invite.usage_mode == "multi_use":
        if invite.max_redemptions is not None:
            if invite.active_redemptions_count >= invite.max_redemptions:
                raise InviteCodeExhausted
```

Пользовательский лимит:

```python
existing_user_redemptions = count invite_redemptions
WHERE invite_code_id = invite.id
AND invitee_user_id = user_id
AND status = 'redeemed'

if existing_user_redemptions >= invite.per_user_redemption_cap:
    raise InviteCodeAlreadyRedeemedByUser
```

---

## 7.4. Finalize counters

Для `single_use`:

```python
invite.is_used = True
invite.used_by_user_id = user_id
invite.used_at = now
invite.redeemed_count = 1
invite.active_redemptions_count = 1
invite.first_redeemed_at = now
invite.last_redeemed_at = now
invite.exhausted_at = now
invite.status = "redeemed"
```

Для `multi_use`:

```python
invite.redeemed_count += 1
invite.active_redemptions_count += 1
invite.first_redeemed_at = invite.first_redeemed_at or now
invite.last_redeemed_at = now

if invite.max_redemptions is not None and invite.active_redemptions_count >= invite.max_redemptions:
    invite.is_used = True
    invite.exhausted_at = now
    invite.status = "exhausted"
else:
    invite.is_used = False
    invite.status = "issued" or "active"
```

Рекомендуемый статус:

```text
issued    — создан, ещё не активирован
active    — multi_use код уже активировали хотя бы 1 раз, но он ещё доступен
exhausted — достигнут лимит активаций
redeemed  — single_use код активирован
revoked   — отозван
expired   — истёк
```

---

## 7.5. Idempotency

Для multi-use idempotency key:

```python
idempotency_key = f"invite:{invite.id}:redeemer:{user_id}"
```

Если повторить запрос тем же пользователем:

```text
если redemption уже successful — вернуть идемпотентный success или понятное "already_redeemed_by_user"
```

Для UX лучше:

```json
{
  "status": "already_redeemed",
  "message_key": "growth.invite.alreadyRedeemedByUser",
  "existing_redemption_id": "..."
}
```

Но если flow уже выдал entitlement и child invites, повторный запрос не должен выдавать второй entitlement и вторые 12 child invites.

---

## 8. Child invites при multi-use redemption

При каждом успешном redemption multi-use root code:

```text
User A активировал SMART-RU-VIP → User A получил 12 child invites
User B активировал SMART-RU-VIP → User B получил 12 child invites
User C активировал SMART-RU-VIP → User C получил 12 child invites
```

Каждый child batch должен иметь:

```python
source_redemption_id = redemption.id
parent_invite_code_id = root_invite.id
root_invite_code_id = root_invite.root_invite_code_id or root_invite.id
owner_user_id = redeemer_user_id
generation_depth = parent_depth + 1
```

Для child codes usage mode брать из campaign version:

```text
child_usage_mode
child_max_redemptions
child_per_user_redemption_cap
```

Если админ выбрал child codes `single_use`, каждый child code можно активировать 1 раз.

Если админ выбрал child codes `multi_use`, каждый child code можно активировать N раз.

---

## 9. Invite tree semantics

Для multi-use root code дерево должно строиться так:

```text
Root multi-use invite SMART-RU-VIP
├── Redemption #1: User A
│   ├── Child batch A, 12 codes
│   └── descendants...
├── Redemption #2: User B
│   ├── Child batch B, 12 codes
│   └── descendants...
└── Redemption #3: User C
    ├── Child batch C, 12 codes
    └── descendants...
```

`InviteTreeEdgeModel` должен хранить:

```python
redeemed_invite_code_id = invite.id
redemption_id = redemption.id
invitee_user_id = redeemer_user_id
child_batch_id = child_batch.id
generation_depth = invite.generation_depth
```

Для multi-use root будет несколько tree edges с одним `redeemed_invite_code_id`, но разными `redemption_id` и `invitee_user_id`.

---

## 10. Admin API

## 10.1. Campaign create/update request

Добавить поля:

```python
root_usage_mode: Literal["single_use", "multi_use"] = "single_use"
root_max_redemptions: int | None = Field(1, ge=1, le=1_000_000)
root_per_user_redemption_cap: int = Field(1, ge=1, le=10)

child_usage_mode: Literal["single_use", "multi_use"] = "single_use"
child_max_redemptions: int | None = Field(1, ge=1, le=1_000_000)
child_per_user_redemption_cap: int = Field(1, ge=1, le=10)
```

Validation:

```python
if root_usage_mode == "single_use":
    root_max_redemptions = 1

if child_usage_mode == "single_use":
    child_max_redemptions = 1

if root_usage_mode == "multi_use" and root_max_redemptions is None:
    require high_risk_context and multi_use_unlimited_acknowledgement

if root_per_user_redemption_cap != 1:
    require explicit admin override
```

Для текущего требования:

```text
root_usage_mode = multi_use
root_max_redemptions = null или большой лимит
root_per_user_redemption_cap = 1
child_usage_mode = single_use или multi_use — выбирается админом
child_per_user_redemption_cap = 1
```

---

## 10.2. Batch create request

Добавить override поля:

```python
usage_mode: Literal["campaign_default", "single_use", "multi_use"] = "campaign_default"
max_redemptions_per_code: int | None = None
per_user_redemption_cap: int | None = None
```

Правила:

```text
campaign_default — взять root_usage_mode из campaign version;
single_use — force single-use for this batch;
multi_use — force multi-use for this batch, если policy разрешает.
```

---

## 10.3. Inventory response

Расширить `AdminInviteCodeSummaryResponse`:

```python
usage_mode: str
max_redemptions: int | None
redeemed_count: int
active_redemptions_count: int
remaining_redemptions: int | None
per_user_redemption_cap: int
first_redeemed_at: datetime | None
last_redeemed_at: datetime | None
exhausted_at: datetime | None
```

Для `remaining_redemptions`:

```python
if usage_mode == "single_use":
    remaining = 0 if is_used else 1

if usage_mode == "multi_use":
    remaining = None if max_redemptions is None else max_redemptions - active_redemptions_count
```

---

## 10.4. Redemptions API

Добавить фильтры:

```text
invite_code_id
usage_mode
root_invite_code_id
campaign_id
redeemer_user_id
status
created_from
created_to
```

Для многоразового кода на detail странице нужно видеть список всех пользователей, которые его активировали.

---

## 11. Admin UI

## 11.1. Campaign form

Добавить секцию:

```text
Режим использования root invite-кода
```

Поля:

```text
Root code usage mode:
  ○ Одноразовый
  ● Многоразовый

Максимум активаций root-кода:
  [100000] или [Без лимита] checkbox

Лимит активаций на пользователя:
  [1]
```

Добавить секцию:

```text
Режим использования дочерних invite-кодов
```

Поля:

```text
Child code usage mode:
  ● Одноразовый
  ○ Многоразовый

Максимум активаций каждого дочернего кода:
  [1] для одноразового
  [N] для многоразового

Лимит активаций на пользователя:
  [1]
```

---

## 11.2. Lifetime Premium Smart RU preset

Обновить preset:

```typescript
function premiumSmartRuLifetimePreset(displayName: string) {
  return {
    ...
    rootUsageMode: 'multi_use',
    rootMaxRedemptions: '100000',
    rootPerUserRedemptionCap: '1',

    childUsageMode: 'single_use',
    childMaxRedemptions: '1',
    childPerUserRedemptionCap: '1',
    ...
  }
}
```

Также добавить второй preset:

```text
Premium Smart RU Lifetime Multi-use Root
```

и, если нужно:

```text
Premium Smart RU Lifetime Multi-use Chain
```

Различие:

```text
Multi-use Root:
  root_usage_mode = multi_use
  child_usage_mode = single_use

Multi-use Chain:
  root_usage_mode = multi_use
  child_usage_mode = multi_use
```

---

## 11.3. Inventory UI

В таблицу invite inventory добавить колонки:

```text
Usage
Redemptions
Remaining
Per-user cap
First redeemed
Last redeemed
Exhausted
```

Пример строки:

```text
SMART-RU-VIP
Usage: Multi-use
Redemptions: 348 / 100000
Remaining: 99652
Per-user cap: 1
Plan: Premium Smart RU
Duration: Lifetime
Devices: 5
Child invites: 12
Status: Active
```

Для single-use:

```text
ABCD-1234
Usage: Single-use
Redemptions: 0 / 1
Remaining: 1
```

---

## 11.4. Code detail page / drawer

Добавить drawer/detail для конкретного invite-code:

```text
Code summary
Redemption policy
Grant policy
Child policy
Redemption list
Tree preview
Audit events
```

Для multi-use обязательно показывать:

```text
Последние 50 активаций
Всего активаций
Лимит
Остаток
Кнопка: Export redemptions CSV
Кнопка: Revoke code
Кнопка: Exhaust code
```

---

## 12. Customer UX

## 12.1. Web onboarding

Поле остаётся одно:

```text
Введите invite / promo / gift code
```

Если код multi-use, пользователь не должен видеть отличий, кроме успешного результата.

Ошибки:

```text
Invite code exhausted — лимит активаций исчерпан
Invite code already redeemed by you — вы уже активировали этот код
Invite code expired — срок действия истёк
Invite code revoked — код отозван
```

---

## 12.2. Telegram Mini App

Тот же endpoint apply должен поддерживать multi-use.

Если пользователь уже активировал код:

```text
Вы уже активировали этот invite-код. Перейдите к подключению VPN или в личный кабинет.
```

Если код исчерпан:

```text
Лимит активаций invite-кода исчерпан.
```

---

## 12.3. Telegram Bot

Команда:

```text
/code SMART-RU-VIP
```

должна работать с multi-use.

Если пользователь новый:

1. Создать pending onboarding user.
2. Активировать code.
3. Выдать Premium Smart RU.
4. Показать connection UX.
5. Сообщить, что пользователю выданы 12 invite-кодов.

---

## 13. Security / anti-abuse

Multi-use invite-code — высокорисковая сущность.

Обязательные защиты для `multi_use`:

```text
per_user_redemption_cap = 1
device cap = 1
IP window cap <= 3
velocity window <= 24h
deny_disposable_email = true
deny_known_abuse_subject = true
high_risk_context = true
```

Для `max_redemptions = null` требовать:

```text
multi_use_unlimited_acknowledgement = true
global_issue_cap exists
max_generation_depth <= 5
```

Рекомендуется не разрешать настоящий unlimited без technical cap. В UI можно дать "Без лимита", но backend должен сохранять:

```text
max_redemptions = 1000000
cap_mode = practically_unlimited
```

или требовать super-admin permission.

---

## 14. Reversal / revoke

### 14.1. Revoke multi-use code

Если админ отзывает multi-use code:

```text
код больше нельзя активировать новым пользователям;
существующие redemptions остаются активными;
unused child invites остаются или отзываются по cascade policy.
```

Request:

```json
{
  "reason": "campaign_abuse_detected",
  "cascade_mode": "none | unused_child_invites | all_descendants"
}
```

### 14.2. Reverse one redemption

Если нужно откатить одну конкретную активацию multi-use кода:

```text
отозвать entitlement этого пользователя;
отозвать unused child invites, выданные именно этой redemption;
уменьшить active_redemptions_count;
увеличить reversed_redemptions_count;
не делать код снова доступным этому же пользователю, если policy запрещает повторную активацию.
```

---

## 15. Observability

Добавить метрики:

```text
invite_multi_use_created_total
invite_multi_use_redeemed_total
invite_multi_use_exhausted_total
invite_multi_use_redeem_blocked_total
invite_multi_use_remaining_redemptions
invite_multi_use_child_issued_total
invite_multi_use_reversal_total
```

Логи:

```python
logger.info(
    "invite_multi_use_redeemed",
    invite_code_id=str(invite.id),
    code_prefix=invite.code_prefix,
    campaign_id=str(invite.campaign_id) if invite.campaign_id else None,
    redemption_id=str(redemption.id),
    redemptions_count_after=invite.active_redemptions_count,
)
```

Не логировать raw code.

---

## 16. Tests

## 16.1. Unit tests

1. `single_use` code can be redeemed once.
2. `single_use` second redemption returns already used.
3. `multi_use` code can be redeemed by User A and User B.
4. `multi_use` same user second redemption is blocked.
5. `multi_use` respects `max_redemptions`.
6. `multi_use` changes status to `exhausted`.
7. `multi_use` with `max_redemptions=null` requires acknowledgement.
8. `multi_use` redemption increments counters atomically.
9. `multi_use` reverse one redemption updates counters correctly.
10. `single_use` legacy `is_used` behavior unchanged.

## 16.2. Integration tests

Scenario:

```text
Admin creates campaign:
  root_usage_mode=multi_use
  root_max_redemptions=100
  grant_plan_code=premium_smart_ru
  grant_duration_mode=lifetime
  grant_device_limit_override=5
  child_invite_count=12
  child_usage_mode=single_use
  child_grant_plan_code=premium_smart_ru
  child_grant_duration_mode=lifetime
  child_grant_device_limit_override=5

Admin creates root batch count=1.

User A redeems same root code.
User B redeems same root code.
User A tries again and gets already_redeemed_by_user.

A and B each get:
  Premium Smart RU lifetime
  12 child invites
```

## 16.3. Concurrency tests

Simulate 100 parallel redemptions of one code with `max_redemptions=50`.

Expected:

```text
50 successful
50 blocked as exhausted
redeemed_count=50
active_redemptions_count=50
no duplicate user redemption
no count > 50
```

## 16.4. Admin UI tests

1. Usage mode selector renders.
2. Switching `single_use` disables max redemptions or sets it to 1.
3. Switching `multi_use` enables max redemptions.
4. Lifetime preset sets root multi-use and child single-use.
5. Inventory shows redemptions and remaining.
6. Export redemptions works.

## 16.5. Bot / Mini App tests

1. `/code MULTI` works for new Telegram user.
2. `/code MULTI` repeated by same user returns already redeemed.
3. Mini App apply supports multi-use.
4. Web onboarding apply supports multi-use.

---

## 17. API examples

## 17.1. Create campaign with multi-use root and single-use children

```json
{
  "campaign_key": "premium_smart_ru_lifetime_multi_use_2026_07",
  "name": "Premium Smart RU Lifetime Multi-use Root",
  "owner_mode": "system",
  "allowed_surfaces": ["web", "miniapp", "telegram_bot"],

  "grant_plan_code": "premium_smart_ru",
  "grant_duration_mode": "lifetime",
  "grant_duration_days": null,
  "grant_device_limit_override": 5,

  "root_invite_expiry_mode": "none",
  "root_invite_expiry_days": null,

  "root_usage_mode": "multi_use",
  "root_max_redemptions": 100000,
  "root_per_user_redemption_cap": 1,

  "child_invite_count": 12,
  "child_usage_mode": "single_use",
  "child_max_redemptions": 1,
  "child_per_user_redemption_cap": 1,

  "child_grant_plan_code": "premium_smart_ru",
  "child_grant_duration_mode": "lifetime",
  "child_grant_duration_days": null,
  "child_grant_device_limit_override": 5,

  "child_invite_expiry_mode": "none",
  "child_invite_expiry_days": null,

  "max_generation_depth": 5,
  "require_no_active_access": true,
  "block_self_redemption": true,

  "risk_policy": {
    "per_user_redeem_cap": 1,
    "high_risk_context": true,
    "max_redemptions_per_device": 1,
    "max_redemptions_per_ip_window": 3,
    "velocity_window_hours": 24,
    "deny_disposable_email": true,
    "deny_known_abuse_subject": true
  },

  "caps": {
    "global_issue_cap": 1000000,
    "max_per_batch": 1000,
    "max_per_owner": 12,
    "max_daily_issued": 10000
  },

  "lifetime_campaign_acknowledgement": true,
  "multi_use_acknowledgement": true,
  "publish": false,
  "reason": "create premium smart ru lifetime multi-use root campaign"
}
```

---

## 17.2. Create root batch

```json
{
  "count": 1,
  "owner_user_id": null,
  "usage_mode": "campaign_default",
  "expiry_mode": "campaign_default",
  "reason": "issue one multi-use root invite code"
}
```

---

## 18. Acceptance criteria

Функционал считается готовым только если:

1. Админ может создать `single_use` invite-code.
2. Админ может создать `multi_use` invite-code.
3. Старые одноразовые invite-коды продолжают работать.
4. Multi-use code может активироваться разными пользователями.
5. Один пользователь не может активировать один и тот же multi-use code второй раз.
6. Multi-use code соблюдает общий лимит активаций.
7. Multi-use code корректно становится `exhausted`.
8. Каждая активация создаёт отдельный redemption record.
9. Каждая активация выдаёт entitlement grant.
10. Каждая активация выдаёт дочерние invite-коды по policy.
11. Tree показывает всех пользователей, активировавших один root multi-use code.
12. Admin inventory показывает usage mode, redemption count и remaining.
13. Web onboarding поддерживает multi-use.
14. Mini App поддерживает multi-use.
15. Telegram Bot `/code` поддерживает multi-use.
16. Race condition не может превысить лимит.
17. Raw codes не попадают в логи.
18. Все тесты проходят.

---

## 19. Рекомендованный UX для твоего сценария

Для кампании:

```text
Root usage mode: Многоразовый
Root max redemptions: 100000 или practically unlimited
Root per user cap: 1

Plan: premium_smart_ru
Duration: Бессрочно
Device limit: 5
Traffic: Unlimited из плана

Child invite count: 12
Child usage mode: Одноразовый
Child max redemptions: 1
Child per user cap: 1

Child plan: premium_smart_ru
Child duration: Бессрочно
Child device limit: 5

Max generation depth: 5
Global issue cap: 1000000
High-risk context: enabled
```

Если хочешь, чтобы дочерние invite-коды тоже были многоразовыми:

```text
Child usage mode: Многоразовый
Child max redemptions: например 100
Child per user cap: 1
```

Но это сильно увеличивает viral growth, поэтому требует более строгих caps и мониторинга.
