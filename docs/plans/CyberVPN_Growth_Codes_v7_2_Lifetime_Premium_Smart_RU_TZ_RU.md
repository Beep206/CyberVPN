# Техническое задание v7.2
# Бессрочные Premium Smart RU Invite Campaigns с настраиваемыми устройствами и каскадной выдачей инвайтов

**Проект:** CyberVPN
**Версия ТЗ:** v7.2
**Цель:** доработать flexible invite system так, чтобы администратор мог создавать бессрочные invite campaigns для тарифа `premium_smart_ru`, задавать количество устройств, количество дочерних инвайтов, тариф дочерних инвайтов и наследование этих параметров на всю invite-цепочку.

---

## 1. Контекст

В текущей реализации v7/v7.1 уже есть гибкая invite-система:

- invite campaigns;
- campaign versions;
- root invite batches;
- plan-backed invite redemption;
- child invites после успешного redemption;
- invite tree;
- admin inventory;
- admin redemptions;
- admin tree view;
- admin batch export/revoke/extend;
- Mini App session-first auth hardening;
- RSC/CORS hardening;
- paginated invite inventory;
- allowed surfaces UI.

Но текущая модель не закрывает сценарий:

> Создать инвайт с тарифом Premium Smart RU без ограничения по времени, с 5 устройствами, чтобы после применения пользователь получил 12 бессрочных инвайтов для друзей, каждый из которых также выдаёт Premium Smart RU без ограничения по времени, 5 устройств и 12 следующих инвайтов.

Сейчас это невозможно сделать как настоящий бессрочный режим, потому что:

- `grant_duration_days` обязателен и ограничен числом дней;
- `child_grant_duration_days` обязателен или наследуется как число дней;
- `child_invite_free_days` также числовой;
- root batch expiry задаётся через `expiry_days` или `expires_at`;
- child batch expiry создаётся как `now + expiry_days`;
- entitlement grant при invite redemption получает `expires_at = now + access_days`;
- нет явного режима `lifetime` / `no_expiry`;
- устройство берётся из плана, но нельзя явно override-ить device limit на уровне invite campaign.

---

## 2. Целевой бизнес-сценарий

Администратор создаёт campaign:

```text
Campaign: premium_smart_ru_lifetime_wave_1

Root invite:
- grant plan: Premium Smart RU
- grant duration: lifetime / no expiry
- device limit: 5
- root invite code expiry: no expiry или configurable
- root owner mode: selected_user / system / uploaded_user_list

After redemption:
- пользователь получает Premium Smart RU lifetime access
- пользователь получает 12 дочерних invite codes

Child invites:
- grant plan: Premium Smart RU
- grant duration: lifetime / no expiry
- device limit: 5
- child invite code expiry: no expiry или configurable
- child invite count after redemption: 12
- max generation depth: configurable
```

---

## 3. Термины

### Access duration

Добавить enum:

```python
class InviteAccessDurationMode(StrEnum):
    FIXED_DAYS = "fixed_days"
    LIFETIME = "lifetime"
```

### Invite code expiry

Добавить enum:

```python
class InviteCodeExpiryMode(StrEnum):
    RELATIVE = "relative"
    ABSOLUTE = "absolute"
    NONE = "none"
```

### Device entitlement override

Добавить структуру:

```json
{
  "device_limit_override": 5
}
```

Override должен применяться только к entitlement snapshot, не меняя сам тариф в каталоге.

---

## 4. Backend. Изменения в моделях

### 4.1. `invite_campaign_versions`

Добавить поля:

```python
grant_duration_mode: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="fixed_days",
    server_default="fixed_days",
)

child_grant_duration_mode: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="fixed_days",
    server_default="fixed_days",
)

grant_device_limit_override: Mapped[int | None] = mapped_column(Integer, nullable=True)

child_grant_device_limit_override: Mapped[int | None] = mapped_column(Integer, nullable=True)

root_invite_expiry_mode: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="relative",
    server_default="relative",
)

child_invite_expiry_mode: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="relative",
    server_default="relative",
)
```

Constraints:

```sql
grant_duration_mode IN ('fixed_days', 'lifetime')
child_grant_duration_mode IN ('fixed_days', 'lifetime')
root_invite_expiry_mode IN ('relative', 'absolute', 'none')
child_invite_expiry_mode IN ('relative', 'absolute', 'none')
grant_device_limit_override IS NULL OR grant_device_limit_override > 0
child_grant_device_limit_override IS NULL OR child_grant_device_limit_override > 0
```

### 4.2. `invite_batches`

Поля уже частично поддерживают `expiry_mode='none'`. Нужно убедиться, что root и child batches реально могут сохранять:

```python
expiry_mode = "none"
expiry_days = None
expires_at = None
```

### 4.3. `invite_codes`

Нужно хранить duration mode и device override на коде, чтобы snapshot оставался стабильным даже после изменения campaign version:

```python
grant_duration_mode: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="fixed_days",
    server_default="fixed_days",
)

child_grant_duration_mode: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="fixed_days",
    server_default="fixed_days",
)

grant_device_limit_override: Mapped[int | None] = mapped_column(Integer, nullable=True)

child_grant_device_limit_override: Mapped[int | None] = mapped_column(Integer, nullable=True)

child_invite_expiry_mode: Mapped[str] = mapped_column(
    String(20),
    nullable=False,
    default="relative",
    server_default="relative",
)
```

---

## 5. Backend. Pydantic schemas

### 5.1. `AdminInviteCampaignCreateRequest`

Добавить:

```python
grant_duration_mode: Literal["fixed_days", "lifetime"] = "fixed_days"
grant_duration_days: int | None = Field(365, ge=1, le=3_660)

grant_device_limit_override: int | None = Field(None, ge=1, le=200)

root_invite_expiry_mode: Literal["relative", "absolute", "none"] = "relative"
root_invite_expiry_days: int | None = Field(30, ge=1, le=3_660)
root_invite_expires_at: datetime | None = None

child_grant_duration_mode: Literal["fixed_days", "lifetime"] = "fixed_days"
child_grant_duration_days: int | None = Field(365, ge=1, le=3_660)

child_grant_device_limit_override: int | None = Field(None, ge=1, le=200)

child_invite_expiry_mode: Literal["relative", "absolute", "none"] = "relative"
child_invite_expiry_days: int | None = Field(30, ge=1, le=3_660)
child_invite_expires_at: datetime | None = None
```

Validation:

```python
@model_validator(mode="after")
def validate_duration_and_expiry(self):
    if self.grant_duration_mode == "fixed_days" and self.grant_duration_days is None:
        raise ValueError("grant_duration_days is required for fixed_days mode")

    if self.grant_duration_mode == "lifetime":
        self.grant_duration_days = None

    if self.child_grant_duration_mode == "fixed_days" and self.child_grant_duration_days is None:
        raise ValueError("child_grant_duration_days is required for fixed_days mode")

    if self.child_grant_duration_mode == "lifetime":
        self.child_grant_duration_days = None

    if self.root_invite_expiry_mode == "relative" and self.root_invite_expiry_days is None:
        raise ValueError("root_invite_expiry_days is required for relative expiry mode")

    if self.root_invite_expiry_mode == "absolute" and self.root_invite_expires_at is None:
        raise ValueError("root_invite_expires_at is required for absolute expiry mode")

    if self.root_invite_expiry_mode == "none":
        self.root_invite_expiry_days = None
        self.root_invite_expires_at = None

    if self.child_invite_expiry_mode == "relative" and self.child_invite_expiry_days is None:
        raise ValueError("child_invite_expiry_days is required for relative expiry mode")

    if self.child_invite_expiry_mode == "absolute" and self.child_invite_expires_at is None:
        raise ValueError("child_invite_expires_at is required for absolute expiry mode")

    if self.child_invite_expiry_mode == "none":
        self.child_invite_expiry_days = None
        self.child_invite_expires_at = None

    return self
```

### 5.2. `AdminInviteCampaignVersionCreateRequest`

Добавить те же поля, что и для create request.

### 5.3. `AdminInviteCampaignBatchCreateRequest`

Заменить:

```python
expires_at: datetime | None = None
expiry_days: int | None = Field(30, ge=1, le=3_660)
```

на:

```python
expiry_mode: Literal["campaign_default", "relative", "absolute", "none"] = "campaign_default"
expiry_days: int | None = Field(None, ge=1, le=3_660)
expires_at: datetime | None = None
```

Правила:

- `campaign_default` — брать root expiry из campaign version.
- `relative` — требовать `expiry_days`.
- `absolute` — требовать `expires_at`.
- `none` — `expiry_days=None`, `expires_at=None`.

---

## 6. Backend. Entitlement snapshot builder

Добавить helper:

```python
def apply_invite_entitlement_overrides(
    *,
    snapshot: dict,
    duration_mode: str,
    duration_days: int | None,
    expires_at: datetime | None,
    device_limit_override: int | None,
) -> dict:
    snapshot = copy.deepcopy(snapshot)

    if duration_mode == "lifetime":
        snapshot["period_days"] = None
        snapshot["expires_at"] = None
        snapshot["lifetime"] = True
        snapshot["duration_mode"] = "lifetime"
    else:
        snapshot["period_days"] = duration_days
        snapshot["expires_at"] = expires_at.isoformat() if expires_at else None
        snapshot["lifetime"] = False
        snapshot["duration_mode"] = "fixed_days"

    if device_limit_override is not None:
        effective = dict(snapshot.get("effective_entitlements") or {})
        effective["device_limit"] = int(device_limit_override)
        snapshot["effective_entitlements"] = effective
        snapshot["device_limit_override"] = int(device_limit_override)

    return snapshot
```

Применять:

- при создании campaign version;
- при создании root batch;
- при создании child invites;
- при redeem invite.

---

## 7. Backend. Invite redemption

### 7.1. `_build_grant_snapshot`

Текущая логика:

```python
access_expires_at = now + timedelta(days=access_days)
grant_snapshot, access_days = await self._build_grant_snapshot(invite)
```

Нужно заменить на:

```python
grant_snapshot, access_expires_at = await self._build_grant_snapshot(invite)
```

Новый контракт:

```python
async def _build_grant_snapshot(
    self,
    invite: InviteCodeModel,
) -> tuple[dict, datetime | None]:
```

Для `duration_mode == "lifetime"`:

```python
expires_at = None
```

Для `fixed_days`:

```python
expires_at = now + timedelta(days=duration_days)
```

При создании entitlement grant:

```python
grant = await self._entitlements.execute(
    service_identity_id=service_identity.service_identity.id,
    manual_source_key=f"invite:{invite.id}:redeemer:{user_id}",
    grant_snapshot=grant_snapshot,
    expires_at=access_expires_at,
)
```

### 7.2. `_ensure_child_invites_after_redemption`

Поддержать child invite expiry mode:

```python
if expiry_mode == "none":
    expires_at = None
    expiry_days = None
elif expiry_mode == "absolute":
    expires_at = configured_absolute_expiry
    expiry_days = None
else:
    expires_at = now + timedelta(days=expiry_days)
```

Child grant duration mode:

```python
if child_grant_duration_mode == "lifetime":
    child_access_expires_at = None
    access_days = None
else:
    child_access_expires_at = now + timedelta(days=child_grant_duration_days)
```

---

## 8. Remnawave provisioning для lifetime

Нужно определить upstream-поведение.

### Вариант A — Remnawave поддерживает no-expire

Если Remnawave допускает отсутствие `expire_at`:

```python
payload["expire_at"] = None
```

или не передавать поле.

### Вариант B — Remnawave требует дату

Использовать configurable sentinel:

```env
REMNAWAVE_LIFETIME_EXPIRE_AT=2099-12-31T23:59:59Z
```

При этом внутри CyberVPN entitlement должен оставаться настоящим lifetime:

```python
entitlement_grant.expires_at = None
grant_snapshot["expires_at"] = None
grant_snapshot["lifetime"] = True
```

А в service/provisioning metadata записать:

```json
{
  "upstream_expiry_mode": "sentinel",
  "upstream_expires_at": "2099-12-31T23:59:59Z"
}
```

---

## 9. Admin UI

### 9.1. Campaign form

Добавить секции.

#### Grant access

```text
Тариф доступа:
  [Premium Smart RU 365 / Premium Smart RU 30 / ...]
  или Plan Code fallback: premium_smart_ru

Срок доступа:
  ○ Fixed days
      Days: [365]
  ● Lifetime / no expiry

Device limit:
  ○ Use plan default
  ● Override: [5]
```

#### Child invite grant

```text
Количество дочерних инвайтов после применения:
  [12]

Тариф дочернего инвайта:
  [Premium Smart RU]
  или Plan Code fallback: premium_smart_ru

Срок доступа дочернего инвайта:
  ○ Fixed days
      Days: [365]
  ● Lifetime / no expiry

Device limit для дочернего инвайта:
  ○ Use parent / plan default
  ● Override: [5]
```

#### Invite code expiry

```text
Root invite code expiry:
  ○ Relative days
  ○ Absolute date
  ● No expiry

Child invite code expiry:
  ○ Relative days
  ○ Absolute date
  ● No expiry
```

### 9.2. UX warnings

Если выбран lifetime:

```text
Внимание: бессрочный доступ создаёт entitlement без expires_at. Отзыв доступа возможен только вручную через revoke/reversal.
```

Если выбран max generation depth > 3 и child_invite_count >= 10:

```text
Внимание: кампания может расти экспоненциально. Проверьте risk policy и caps.
```

Пример:

```text
12 инвайтов на глубине 5 потенциально создают 248 832+ кодов.
```

### 9.3. Preset

Добавить быстрый preset:

```text
Preset: Premium Smart RU Lifetime Viral
```

Он заполняет:

```json
{
  "grant_plan_code": "premium_smart_ru",
  "grant_duration_mode": "lifetime",
  "grant_duration_days": null,
  "grant_device_limit_override": 5,
  "child_invite_count": 12,
  "child_grant_plan_code": "premium_smart_ru",
  "child_grant_duration_mode": "lifetime",
  "child_grant_duration_days": null,
  "child_grant_device_limit_override": 5,
  "child_invite_expiry_mode": "none",
  "root_invite_expiry_mode": "none",
  "max_generation_depth": 5,
  "require_no_active_access": true,
  "block_self_redemption": true
}
```

---

## 10. API payload examples

### 10.1. Create campaign

```json
{
  "campaign_key": "premium_smart_ru_lifetime_wave_1",
  "name": "Premium Smart RU Lifetime Invite Wave 1",
  "description": "Root invites grant lifetime Premium Smart RU and issue 12 lifetime child invites.",
  "owner_mode": "selected_user",
  "allowed_surfaces": ["web", "miniapp", "telegram_bot"],

  "grant_plan_code": "premium_smart_ru",
  "grant_duration_mode": "lifetime",
  "grant_duration_days": null,
  "grant_device_limit_override": 5,

  "root_invite_expiry_mode": "none",
  "root_invite_expiry_days": null,
  "root_invite_expires_at": null,

  "child_invite_count": 12,

  "child_grant_plan_code": "premium_smart_ru",
  "child_grant_duration_mode": "lifetime",
  "child_grant_duration_days": null,
  "child_grant_device_limit_override": 5,

  "child_invite_expiry_mode": "none",
  "child_invite_expiry_days": null,
  "child_invite_expires_at": null,

  "max_generation_depth": 5,
  "require_no_active_access": true,
  "block_self_redemption": true,

  "risk_policy": {
    "per_user_redeem_cap": 1,
    "high_risk_context": true,
    "velocity_window_hours": 24,
    "max_redemptions_per_device": 1
  },

  "caps": {
    "global_issue_cap": 100000,
    "max_per_batch": 1000,
    "max_per_owner": 12,
    "max_daily_issued": 10000
  },

  "export_policy": {
    "raw_export_enabled": true
  },

  "publish": true,
  "reason": "premium_smart_ru_lifetime_wave_1_launch"
}
```

### 10.2. Create root batch

```json
{
  "owner_user_id": "00000000-0000-0000-0000-000000000000",
  "count": 1,
  "expiry_mode": "campaign_default",
  "reason": "issue root invite for selected seed user"
}
```

Для system pool:

```json
{
  "owner_user_id": null,
  "count": 100,
  "expiry_mode": "campaign_default",
  "reason": "issue root system pool batch"
}
```

---

## 11. Admin inventory

В inventory table добавить колонки:

- duration mode;
- lifetime badge;
- device limit override;
- root invite expiry mode;
- child invite expiry mode;
- child invite count;
- child grant duration mode.

Пример строки:

```text
PREM...ABCD
Plan: Premium Smart RU
Access: Lifetime
Devices: 5
Child invites: 12
Child plan: Premium Smart RU / Lifetime / 5 devices
Depth: 0
Status: issued
Expiry: no expiry
```

---

## 12. Invite tree

Tree view должен показывать lifetime metadata:

```text
Root Invite
├─ User A — Premium Smart RU Lifetime · 5 devices · issued 12 child invites
│  ├─ User B — Premium Smart RU Lifetime · 5 devices · issued 12 child invites
│  └─ User C — Premium Smart RU Lifetime · 5 devices · issued 12 child invites
```

Stats:

```json
{
  "total_nodes": 100,
  "total_redeemed": 44,
  "lifetime_grants": 44,
  "premium_smart_ru_grants": 44,
  "child_invites_issued_total": 528,
  "max_depth_reached": 3
}
```

---

## 13. Risk / abuse controls

Lifetime invite campaigns are high-risk by default.

Required controls:

```json
{
  "per_user_redeem_cap": 1,
  "block_self_redemption": true,
  "require_no_active_access": true,
  "max_redemptions_per_device": 1,
  "max_redemptions_per_ip_window": 3,
  "velocity_window_hours": 24,
  "deny_disposable_email": true,
  "deny_known_abuse_subject": true
}
```

Hard validation:

- if `grant_duration_mode=lifetime` and `child_invite_count > 0`, require `max_generation_depth <= 5` unless explicit admin override;
- if `child_invite_count >= 10`, require `global_issue_cap`;
- if `root_invite_expiry_mode=none`, require campaign `expires_at` or explicit lifetime campaign acknowledgement;
- if campaign has lifetime + no invite expiry + depth > 3, require `risk_policy.high_risk_context=true`.

---

## 14. Reversal behavior

When admin reverses redemption:

1. revoke entitlement grant;
2. revoke unused child invites;
3. mark invite tree edge as reversed;
4. mark closure paths affected by reversal as inactive or keep immutable with status metadata;
5. keep already redeemed descendants active by default unless admin selects cascade reversal.

Add request:

```python
class AdminInviteRedemptionReverseRequest(BaseModel):
    reason: str
    cascade_mode: Literal["none", "unused_child_invites", "all_descendants"] = "unused_child_invites"
```

For `all_descendants`, require second confirmation:

```json
{
  "confirm_descendant_reversal": true
}
```

---

## 15. Tests

### 15.1. Unit tests

- create lifetime campaign version;
- reject fixed_days without days;
- reject lifetime with non-null days if strict mode enabled;
- create lifetime grant snapshot with `expires_at=None`;
- apply device override;
- create root invite with no expiry;
- create child invites with no expiry;
- max generation depth enforcement;
- risk high-risk validation.

### 15.2. Integration tests

Scenario:

```text
Admin creates Premium Smart RU Lifetime campaign
Admin publishes campaign
Admin creates root batch count=1
User A registers
User A redeems root invite during onboarding
User A receives active entitlement:
  plan_code=premium_smart_ru
  expires_at=None
  device_limit=5
User A receives 12 child invites
Child invites:
  expires_at=None
  grant_duration_mode=lifetime
  child_invite_count=12
User B redeems User A child invite
User B receives same lifetime entitlement
User B receives 12 child invites
Invite tree shows root -> A -> B
```

### 15.3. Remnawave tests

- if no-expire supported: payload omits `expire_at`;
- if sentinel mode: payload contains configured sentinel date;
- CyberVPN entitlement still stores `expires_at=None`;
- Smart RU external/internal squads are present.

### 15.4. Admin UI tests

- preset fills all fields;
- lifetime disables days input;
- no-expiry disables expiry date/days input;
- child count accepts 12;
- device override accepts 5;
- save payload matches backend contract.

---

## 16. Migration/backfill

Migration must:

1. add new fields with defaults;
2. backfill existing campaigns as `fixed_days`;
3. backfill existing invite codes as `fixed_days`;
4. backfill expiry mode:
   - if `expires_at IS NULL` -> `none`;
   - else if `expiry_days IS NULL` -> `absolute`;
   - else -> `relative`;
5. not modify already redeemed grants.

---

## 17. Observability

Add metrics:

```text
invite_campaign_lifetime_created_total
invite_lifetime_redemption_total
invite_lifetime_child_issued_total
invite_device_override_used_total
invite_lifetime_reversal_total
invite_lifetime_remnawave_sentinel_total
```

Logs must not contain raw invite codes.

---

## 18. Acceptance criteria

The implementation is accepted only if:

- admin can create `premium_smart_ru` campaign with `grant_duration_mode=lifetime`;
- admin can set `grant_device_limit_override=5`;
- admin can set `child_invite_count=12`;
- admin can set `child_grant_duration_mode=lifetime`;
- admin can set `child_grant_device_limit_override=5`;
- root invite codes can be `expires_at=None`;
- child invite codes can be `expires_at=None`;
- redeemed entitlement grant has `expires_at=None`;
- entitlement snapshot has:
  - `plan_code=premium_smart_ru`;
  - `duration_mode=lifetime`;
  - `lifetime=true`;
  - `device_limit=5`;
- after redemption user receives exactly 12 child invite codes;
- each child invite has same lifetime Premium Smart RU policy;
- invite tree shows root and descendant relationships;
- connection bootstrap returns VPN config/QR after redemption;
- reversal revokes entitlement and unused child invites;
- all tests pass.

---

## 19. Temporary workaround before this TЗ is implemented

A true lifetime campaign is not currently supported.

Temporary workaround:

```text
grant_duration_days = 3660
child_grant_duration_days = 3660
child_invite_count = 12
child_invite_expiry_days = 3660
grant_plan_code = premium_smart_ru
child_grant_plan_code = premium_smart_ru
```

This gives approximately 10 years, not real lifetime. It should not be presented to users as “бессрочно”.
