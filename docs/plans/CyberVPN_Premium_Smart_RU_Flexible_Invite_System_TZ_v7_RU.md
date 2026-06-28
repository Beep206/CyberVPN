# CyberVPN — Техническое задание v7
## Полноценная система гибких plan-backed invite campaigns для `premium_smart_ru`, дерева приглашений и admin inventory

**Версия документа:** v7.0
**Дата:** 2026-06-28
**Статус:** Technical Specification / Implementation Ready
**Цель:** реализовать полноценную гибкую систему invite/gift/promo onboarding, где администратор может задавать, какие тарифы выдаются по инвайту, сколько инвайтов получает приглашённый пользователь, как строится дерево приглашений, как управлять inventory/batches/redemptions в админке и как безопасно поддерживать `premium_smart_ru`.

---

## 0. Executive Summary

Нужно реализовать не минимальный workaround, а полноценный production-ready контур:

1. **Plan-backed invite codes**
   Инвайт может выдавать конкретный тариф, например `premium_smart_ru_365`, а не только legacy `Invite Access`.

2. **Гибкие параметры кампании**
   Администратор должен настраивать:
   - какой тариф выдаётся приглашённому;
   - на сколько дней;
   - сколько инвайтов получает приглашённый после активации;
   - какой тариф/период будут выдавать дочерние инвайты;
   - срок действия кодов;
   - глубину дерева;
   - лимиты;
   - risk/anti-fraud правила;
   - каналы: Web / Mini App / Telegram Bot;
   - разрешённые страны/рынки/сегменты.

3. **Viral invite tree**
   Система должна отслеживать полную цепочку:

   ```text
   Root campaign
   └─ User A
      ├─ User B
      │  ├─ User D
      │  └─ User E
      └─ User C
         └─ User F
   ```

4. **Admin `/growth/invite-codes` должен стать полноценной консолью**
   Сейчас страница фактически create-only. Нужно добавить:
   - inventory;
   - batch management;
   - redemption analytics;
   - tree explorer;
   - экспорт;
   - revoke/extend/resend;
   - поиск по пользователям;
   - фильтры;
   - raw-code export с audit;
   - создание гибких plan-backed campaigns.

5. **Onboarding UX должен работать для Web, Telegram Mini App и Telegram Bot**
   Пользователь после OTP вводит один код. Если это invite/gift/promo, backend сам определяет тип, применяет код, выдаёт доступ, показывает VPN connection UX и сообщает, сколько инвайтов ему выдано.

6. **`premium_smart_ru` должен работать как hidden/admin-only plan**
   Но его можно выдавать через админские gift/invite/campaign flows. Provisioning должен использовать Remnawave Smart RU external/internal squads и Mihomo template.

---

## 1. Текущее состояние и выявленные ограничения

### 1.1. `premium_smart_ru`

В репозитории добавлен `PlanCode.PREMIUM_SMART_RU = "premium_smart_ru"`.

Тариф сидится как hidden/admin-only:

```text
catalog_visibility = hidden
sale_channels = admin-only
device_limit = 5
server_pool = ["premium_smart_ru"]
connection_modes = ["standard", "stealth", "smart_routing"]
support_sla = priority
features.smart_routing = true
features.adblock = true
features.tracker_block = true
features.remnawave_external_squad = CYBERVPN_PREMIUM_SMART_RU
features.remnawave_subscription_template = CyberVPN Premium Smart RU
```

В seed price для всех длительностей пока `0.00`, с пометкой owner approval pending.

### 1.2. Проблема текущих legacy invite codes

Сейчас legacy invite code имеет поля:

```text
plan_id
free_days
entitlement_mode
entitlement_profile_key
entitlement_snapshot
owner_user_id
used_by_user_id
batch_id
source_growth_code_id
source_benefit_id
```

Но redemption flow фактически игнорирует `plan_id` и строит hardcoded snapshot:

```text
plan_code = "invite"
display_name = "Invite Access"
device_limit = 1
server_pool = ["shared"]
invite_bundle = 0
```

Следовательно, если в текущей админке создать invite с `plan_id = premium_smart_ru_365`, пользователь всё равно не получит Premium Smart RU.

### 1.3. Проблема post-redeem child invites

Сейчас автоматическая выдача invite bundle есть только в payment flow:

```text
successful payment
→ plan.invite_bundle
→ GenerateInvitesForPaymentUseCase
```

Но onboarding invite redemption — это не payment. Поэтому после применения invite code пользователю сейчас не выдаются 10 дочерних инвайтов.

### 1.4. Проблема admin `/growth/invite-codes`

Admin UI сейчас:
- создаёт legacy invite batch через `/admin/invite-codes`;
- показывает только последний созданный batch в локальном state;
- не показывает inventory;
- не показывает redemption analytics;
- не показывает tree;
- не использует уже существующие backend batch routes;
- загружает планы через public `/plans`, поэтому hidden `premium_smart_ru` может не отображаться.

Backend уже имеет часть batch routes:

```text
GET  /admin/invite-batches
GET  /admin/invite-batches/{batch_id}
POST /admin/invite-batches/{batch_id}/revoke
POST /admin/invite-batches/{batch_id}/extend
POST /admin/invite-batches/{batch_id}/resend
GET  /admin/invite-batches/{batch_id}/export
```

Но admin frontend ими не пользуется.

### 1.5. Production RSC/CORS проблема

В production был лог:

```text
my.cyber-vpn.net/.../rewards/invites?_rsc=...
→ redirected to cyber-vpn.net/en-EN
→ blocked by CORS
```

Эта проблема относится к cabinet-only route allowlist/runtime config. В рамках данного ТЗ нужно закрепить защиту, чтобы admin/growth/rewards/messages routes не ломались в личном кабинете.

---

## 2. Целевое продуктовое поведение

### 2.1. Root invite campaign для `premium_smart_ru`

Администратор создаёт кампанию:

```text
Campaign: Premium Smart RU invite wave
Root codes: 100
Root invite grants: premium_smart_ru_365
After redeem: give new user 10 child invite codes
Child invite grants: premium_smart_ru_365
Child expiry: 30 days
Max generation depth: configurable, e.g. 5
Self redemption: blocked
Existing active subscription redemption: blocked by default
```

### 2.2. Пользовательский flow Web

```text
User registers
→ enters OTP
→ sees onboarding code prompt
→ enters invite code
→ backend detects invite
→ invite grants premium_smart_ru
→ backend creates Remnawave Smart RU access
→ backend issues 10 child invite codes
→ user sees VPN connection modal:
     subscription link
     QR
     platform instructions
     "I connected"
     "Go to dashboard"
→ user sees "You also received 10 invites for friends"
```

### 2.3. Пользовательский flow Telegram Mini App

```text
Telegram Mini App registration/login
→ onboarding code prompt
→ enter invite
→ get premium_smart_ru
→ connection bootstrap inside miniapp
→ 10 child invites appear in rewards/invites
```

### 2.4. Пользовательский flow Telegram Bot

```text
/private chat
/code INVITE123
→ bot applies code through backend
→ bot sends:
   - subscription link
   - QR image
   - buttons: iOS / Android / Windows / macOS / Linux
   - button: I connected
   - button: My cabinet / Mini App
→ bot tells: "You received 10 invites for friends"
```

Bot must never send raw VPN config in group/supergroup/channel.

---

## 3. Core requirements

### 3.1. Invite campaign must be fully configurable

Admin must be able to configure:

| Parameter | Required | Description |
|---|---:|---|
| `campaign_key` | yes | Stable unique key |
| `display_name` | yes | Admin/customer readable title |
| `status` | yes | draft / scheduled / active / paused / archived |
| `root_code_count` | yes | How many root invites to create |
| `root_owner_mode` | yes | system / selected_user / uploaded_user_list |
| `root_owner_user_id` | conditional | Owner for root codes |
| `redeem_grant_plan_id` | yes | Plan granted when invite is redeemed |
| `redeem_grant_duration_days` | yes | Days of access |
| `redeem_entitlement_mode` | yes | plan_snapshot / custom_snapshot |
| `code_expires_at` | optional | Absolute expiry |
| `code_expiry_days` | optional | Relative expiry |
| `child_invites_enabled` | yes | Whether redeemer receives child invites |
| `child_invite_count` | conditional | How many child invites to issue |
| `child_grant_plan_id` | conditional | Plan granted by child invites |
| `child_grant_duration_days` | conditional | Days child invite grants |
| `child_code_expiry_days` | conditional | Expiry of child invite codes |
| `max_generation_depth` | yes | Tree depth cap |
| `per_user_redeem_cap` | yes | Usually 1 |
| `global_redeem_cap` | optional | Campaign global cap |
| `require_no_active_access` | yes | Default true |
| `self_redemption_block` | yes | Default true |
| `allowed_surfaces` | yes | web / miniapp / telegram_bot |
| `allowed_geos` | optional | Geo filter |
| `risk_policy_key` | optional | Anti-fraud rules |
| `notification_policy` | optional | Whether to notify new owner about child invites |
| `raw_code_export_policy` | yes | who can export raw codes |

### 3.2. Invite must be plan-backed

Invite redemption must support:

```text
legacy_mode:
  grants legacy Invite Access

plan_backed_mode:
  grants specific SubscriptionPlan entitlement snapshot

custom_snapshot_mode:
  grants admin-defined entitlement snapshot
```

For `premium_smart_ru`, use `plan_backed_mode`.

### 3.3. Child invite issuance must be triggered after successful redemption

After invite redemption succeeds:

```text
if child_invites_enabled:
  create InviteBatch
  create N InviteCode records
  link them to root/parent/redemption lineage
```

Child batch creation must be idempotent:

```text
idempotency_key = invite-child-batch:{parent_invite_code_id}:redeemer:{user_id}:campaign:{campaign_id}:depth:{depth}
```

### 3.4. Tree tracking must be first-class

Every invite redemption and child invite creation must create durable lineage records.

Admin must be able to answer:

- who invited this user;
- who this user invited;
- what root campaign started the chain;
- how deep this user is in the tree;
- how many users came from each branch;
- which invites are unused/expired/revoked;
- who got VPN access;
- who was blocked by risk;
- how many child invites were issued per generation;
- what plan each person received.

### 3.5. Admin UI must become full operational console

The page `/growth/invite-codes` must no longer say that coverage is narrow. It must include complete management functionality.

---

## 4. Data model

### 4.1. New table: `invite_campaigns`

```python
class InviteCampaignModel(Base):
    __tablename__ = "invite_campaigns"

    id: UUID
    campaign_key: str
    display_name: str
    description: str | None

    status: str  # draft/scheduled/active/paused/archived

    starts_at: datetime | None
    ends_at: datetime | None

    root_owner_mode: str  # system/selected_user/uploaded_user_list
    root_owner_user_id: UUID | None

    allowed_surfaces: list[str]
    allowed_geos: list[str]
    risk_policy_key: str | None

    max_generation_depth: int
    per_user_redeem_cap: int
    global_redeem_cap: int | None
    global_redeem_count: int

    require_no_active_access: bool
    self_redemption_block: bool

    raw_code_export_policy: dict
    notification_policy: dict

    created_by_admin_id: UUID
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None
    archived_at: datetime | None
```

Constraints:

```sql
UNIQUE(campaign_key)
CHECK(max_generation_depth >= 0)
CHECK(per_user_redeem_cap >= 1)
CHECK(global_redeem_cap IS NULL OR global_redeem_cap >= 1)
```

### 4.2. New table: `invite_campaign_versions`

All mutable rules must be versioned.

```python
class InviteCampaignVersionModel(Base):
    __tablename__ = "invite_campaign_versions"

    id: UUID
    campaign_id: UUID
    version: int

    status: str  # draft/submitted/approved/published/rolled_back

    root_invite_policy: dict
    redemption_policy: dict
    child_invite_policy: dict
    tree_policy: dict
    risk_policy: dict
    notification_policy: dict

    checksum: str

    submitted_by_admin_id: UUID | None
    approved_by_admin_id: UUID | None
    published_by_admin_id: UUID | None

    created_at: datetime
    submitted_at: datetime | None
    approved_at: datetime | None
    published_at: datetime | None
```

Example version snapshot:

```json
{
  "root_invite_policy": {
    "root_code_count": 100,
    "code_length": 12,
    "expiry_mode": "relative",
    "expiry_days": 30
  },
  "redemption_policy": {
    "grant_mode": "plan_snapshot",
    "grant_plan_id": "premium_smart_ru_365_uuid",
    "grant_duration_days": 365,
    "require_no_active_access": true,
    "self_redemption_block": true
  },
  "child_invite_policy": {
    "enabled": true,
    "count": 10,
    "grant_plan_id": "premium_smart_ru_365_uuid",
    "grant_duration_days": 365,
    "expiry_mode": "relative",
    "expiry_days": 30
  },
  "tree_policy": {
    "max_generation_depth": 5,
    "store_closure": true,
    "stop_child_issuance_at_depth": 5
  }
}
```

### 4.3. Extend `invite_codes`

Add:

```python
campaign_id: UUID | None
campaign_version_id: UUID | None

parent_invite_code_id: UUID | None
root_invite_code_id: UUID | None
source_redemption_id: UUID | None

generation_depth: int
lineage_path: list[str]

grant_mode: str  # legacy_invite_access / plan_snapshot / custom_snapshot
grant_plan_id: UUID | None
grant_duration_days: int | None

child_invites_enabled: bool
child_invite_count: int
child_grant_plan_id: UUID | None
child_grant_duration_days: int | None
child_expiry_days: int | None

redeem_policy_snapshot: dict
child_policy_snapshot: dict
risk_policy_snapshot: dict

issued_by_campaign_batch_id: UUID | None
```

Indexes:

```sql
CREATE INDEX ix_invite_codes_campaign_id ON invite_codes(campaign_id);
CREATE INDEX ix_invite_codes_root_invite_code_id ON invite_codes(root_invite_code_id);
CREATE INDEX ix_invite_codes_parent_invite_code_id ON invite_codes(parent_invite_code_id);
CREATE INDEX ix_invite_codes_used_by_user_id ON invite_codes(used_by_user_id);
CREATE INDEX ix_invite_codes_generation_depth ON invite_codes(generation_depth);
```

### 4.4. Extend `invite_batches`

Add:

```python
campaign_id: UUID | None
campaign_version_id: UUID | None

parent_invite_code_id: UUID | None
root_invite_code_id: UUID | None
source_redemption_id: UUID | None
root_owner_user_id: UUID | None

generation_depth: int

batch_kind: str  # root_campaign / child_after_redemption / admin_manual / payment_bundle / benefit
grant_plan_id: UUID | None
grant_duration_days: int | None
child_invite_policy_snapshot: dict
tree_policy_snapshot: dict
```

### 4.5. New table: `invite_redemptions`

Do not rely only on `invite_codes.is_used`. Create explicit redemption ledger.

```python
class InviteRedemptionModel(Base):
    __tablename__ = "invite_redemptions"

    id: UUID

    invite_code_id: UUID
    campaign_id: UUID | None
    campaign_version_id: UUID | None

    root_invite_code_id: UUID
    parent_invite_code_id: UUID | None

    inviter_user_id: UUID
    invitee_user_id: UUID

    generation_depth: int

    status: str  # redeemed / blocked / reversed
    redeemed_at: datetime | None
    blocked_at: datetime | None
    blocked_reason: str | None

    entitlement_grant_id: UUID | None
    service_identity_id: UUID | None

    granted_plan_id: UUID | None
    granted_plan_code: str | None
    granted_duration_days: int | None

    child_batch_id: UUID | None
    child_issued_count: int

    risk_decision_id: UUID | None
    idempotency_key: str

    created_at: datetime
    updated_at: datetime
```

Constraints:

```sql
UNIQUE(invite_code_id)
UNIQUE(idempotency_key)
```

### 4.6. New table: `invite_tree_edges`

```python
class InviteTreeEdgeModel(Base):
    __tablename__ = "invite_tree_edges"

    id: UUID

    campaign_id: UUID | None
    root_invite_code_id: UUID
    parent_invite_code_id: UUID | None
    invite_code_id: UUID

    source_redemption_id: UUID

    inviter_user_id: UUID
    invitee_user_id: UUID

    generation_depth: int

    child_batch_id: UUID | None
    granted_plan_id: UUID | None
    granted_plan_code: str | None

    status: str  # active/reversed/blocked
    created_at: datetime
```

### 4.7. New table: `invite_tree_closure`

Closure table for fast analytics.

```python
class InviteTreeClosureModel(Base):
    __tablename__ = "invite_tree_closure"

    id: UUID

    campaign_id: UUID | None
    root_invite_code_id: UUID

    ancestor_user_id: UUID
    descendant_user_id: UUID

    depth: int

    first_edge_id: UUID
    latest_edge_id: UUID

    created_at: datetime
```

Constraints:

```sql
UNIQUE(root_invite_code_id, ancestor_user_id, descendant_user_id)
```

### 4.8. New table: `invite_campaign_daily_rollups`

For dashboard speed.

```python
class InviteCampaignDailyRollupModel(Base):
    __tablename__ = "invite_campaign_daily_rollups"

    id: UUID
    campaign_id: UUID
    rollup_date: date

    issued_count: int
    redeemed_count: int
    blocked_count: int
    expired_count: int
    revoked_count: int

    depth_breakdown: dict
    plan_breakdown: dict
    surface_breakdown: dict

    active_vpn_count: int
    child_invites_issued_count: int

    created_at: datetime
    updated_at: datetime
```

---

## 5. Backend use cases

### 5.1. `CreateInviteCampaignUseCase`

Creates draft campaign.

Input:

```python
@dataclass
class CreateInviteCampaignCommand:
    campaign_key: str
    display_name: str
    description: str | None
    root_owner_mode: str
    root_owner_user_id: UUID | None
    allowed_surfaces: list[str]
    max_generation_depth: int
    require_no_active_access: bool
    self_redemption_block: bool
    created_by_admin_id: UUID
```

### 5.2. `PublishInviteCampaignVersionUseCase`

Validates and publishes campaign version.

Validation:
- `grant_plan_id` exists;
- hidden/admin-only plans allowed only for admin campaigns;
- `premium_smart_ru` requires Remnawave Smart RU env readiness;
- child invite count is within admin configured max;
- depth cap is within safe bounds;
- no raw code in policy snapshot;
- checksum is deterministic.

### 5.3. `CreateInviteCampaignBatchUseCase`

Creates root codes.

Input:

```python
@dataclass
class CreateInviteCampaignBatchCommand:
    campaign_id: UUID
    campaign_version_id: UUID
    count: int
    owner_user_id: UUID | None
    idempotency_key: str
    created_by_admin_id: UUID
```

Behavior:
- creates `InviteBatchModel(batch_kind="root_campaign")`;
- creates `count` invite codes;
- sets `root_invite_code_id = invite.id` for root codes;
- sets `generation_depth = 0`;
- stores grant/child/tree policy snapshots;
- raw codes are returned only once in creation response and export endpoint.

### 5.4. `RedeemPlanBackedInviteUseCase`

Replace or extend current `RedeemInviteUseCase`.

Flow:

```text
1. Normalize code.
2. Lock invite row FOR UPDATE.
3. Validate:
   - exists
   - active/issued
   - not used
   - not revoked
   - not expired
   - self redemption blocked
   - no active access if required
   - campaign active
   - depth allowed
   - surface allowed
   - risk allow
4. Determine grant mode:
   - legacy_invite_access
   - plan_snapshot
   - custom_snapshot
5. Create service identity.
6. Create entitlement grant.
7. Activate grant.
8. Mark invite used.
9. Create InviteRedemptionModel.
10. Create tree edge.
11. Update closure.
12. Generate child invites if configured.
13. Append outbox events.
14. Return redemption result.
```

Pseudo:

```python
if invite.grant_mode == "plan_snapshot":
    plan = await plan_repo.get_by_id(invite.grant_plan_id)
    entitlement_snapshot = EntitlementsService.build_snapshot(
        plan=plan,
        expires_at=None,
        status="active",
    )
    expires_at = now + timedelta(days=invite.grant_duration_days)
else:
    entitlement_snapshot = _build_legacy_invite_snapshot(invite.free_days)
```

### 5.5. `GenerateChildInvitesAfterRedemptionUseCase`

Input:

```python
@dataclass
class GenerateChildInvitesAfterRedemptionCommand:
    redemption_id: UUID
    parent_invite_code_id: UUID
    redeemer_user_id: UUID
    campaign_id: UUID | None
    campaign_version_id: UUID | None
    root_invite_code_id: UUID
    generation_depth: int
    child_policy_snapshot: dict
```

Behavior:
- if child invites disabled: no-op;
- if `generation_depth >= max_generation_depth`: no-op;
- idempotent by redemption id;
- create batch;
- create N codes;
- owner of child codes = redeemer;
- child generation depth = parent depth + 1;
- parent/root/source redemption set on every code;
- emits `invite.child_batch_issued`.

### 5.6. `BuildInviteTreeUseCase`

Returns tree for admin.

Modes:
- by campaign;
- by root invite;
- by user;
- by redemption.

Output:

```json
{
  "root": {
    "invite_code_id": "...",
    "owner_user_id": "...",
    "campaign_id": "..."
  },
  "stats": {
    "total_nodes": 123,
    "total_redeemed": 72,
    "total_child_invites_issued": 720,
    "max_depth_reached": 4
  },
  "nodes": [
    {
      "user_id": "...",
      "inviter_user_id": "...",
      "invite_code_id": "...",
      "depth": 2,
      "granted_plan_code": "premium_smart_ru",
      "redeemed_at": "...",
      "child_batch_id": "...",
      "children_count": 10
    }
  ],
  "edges": []
}
```

### 5.7. `ListInviteInventoryUseCase`

Supports all admin filters.

### 5.8. `ExportInviteBatchUseCase`

Raw code export:
- requires high permission;
- writes audit event;
- supports CSV/JSON;
- includes expiry, status, owner, campaign, depth;
- raw codes only if not revoked and export policy permits.

---

## 6. API specification

### 6.1. Admin campaigns

#### `GET /api/v1/admin/invite-campaigns`

Query:

```text
status
campaign_key
offset
limit
```

Response:

```json
{
  "items": [],
  "total": 0,
  "offset": 0,
  "limit": 50
}
```

#### `POST /api/v1/admin/invite-campaigns`

Creates draft campaign.

#### `GET /api/v1/admin/invite-campaigns/{campaign_id}`

Returns campaign + current version + stats.

#### `POST /api/v1/admin/invite-campaigns/{campaign_id}/versions`

Creates draft version.

#### `POST /api/v1/admin/invite-campaigns/{campaign_id}/versions/{version_id}/validate`

Runs validation.

#### `POST /api/v1/admin/invite-campaigns/{campaign_id}/versions/{version_id}/publish`

Publishes version.

#### `POST /api/v1/admin/invite-campaigns/{campaign_id}/pause`

#### `POST /api/v1/admin/invite-campaigns/{campaign_id}/resume`

#### `POST /api/v1/admin/invite-campaigns/{campaign_id}/archive`

### 6.2. Admin batch creation

#### `POST /api/v1/admin/invite-campaigns/{campaign_id}/batches`

Request:

```json
{
  "campaign_version_id": "uuid",
  "count": 100,
  "owner_user_id": null,
  "idempotency_key": "uuid",
  "reason": "premium smart ru wave 1"
}
```

Response:

```json
{
  "batch": {
    "id": "uuid",
    "campaign_id": "uuid",
    "requested_count": 100,
    "issued_count": 100,
    "batch_kind": "root_campaign",
    "grant_plan_id": "premium_smart_ru_365_uuid",
    "child_invite_count": 10
  },
  "codes": [
    {
      "id": "uuid",
      "code": "ABCD1234EFGH",
      "code_prefix": "ABCD",
      "status": "issued"
    }
  ]
}
```

### 6.3. Admin invite inventory

#### `GET /api/v1/admin/invite-codes`

Query:

```text
campaign_id
campaign_key
batch_id
owner_user_id
used_by_user_id
plan_id
plan_code
status
is_used
root_invite_code_id
parent_invite_code_id
generation_depth
created_from
created_to
used_from
used_to
expires_from
expires_to
code_prefix
offset
limit
```

Response:

```json
{
  "items": [
    {
      "id": "uuid",
      "code_prefix": "ABCD",
      "code_hash": "sha256...",
      "status": "issued",
      "is_used": false,
      "owner_user_id": "uuid",
      "used_by_user_id": null,
      "campaign_id": "uuid",
      "campaign_key": "premium_smart_ru_invite_wave_1",
      "batch_id": "uuid",
      "grant_plan_id": "uuid",
      "grant_plan_code": "premium_smart_ru",
      "generation_depth": 0,
      "root_invite_code_id": "uuid",
      "parent_invite_code_id": null,
      "created_at": "...",
      "expires_at": "..."
    }
  ],
  "total": 100,
  "offset": 0,
  "limit": 50
}
```

### 6.4. Admin tree

#### `GET /api/v1/admin/invite-trees`

Returns list of roots/campaign trees.

#### `GET /api/v1/admin/invite-trees/{root_invite_code_id}`

Returns full tree.

#### `GET /api/v1/admin/invite-trees/users/{user_id}`

Returns upstream/downstream relationships for user.

### 6.5. Admin analytics

#### `GET /api/v1/admin/invite-campaigns/{campaign_id}/analytics`

Response:

```json
{
  "campaign_id": "uuid",
  "issued_total": 1000,
  "redeemed_total": 421,
  "active_vpn_total": 389,
  "child_invites_issued_total": 4210,
  "max_depth_reached": 4,
  "depth_breakdown": {
    "0": 100,
    "1": 281,
    "2": 40
  },
  "conversion": {
    "issued_to_redeemed_pct": 42.1,
    "redeemed_to_connected_pct": 92.4
  }
}
```

### 6.6. Customer invite inventory

Extend:

```text
GET /api/v1/invites/my?group_by=batch
```

Add:
- campaign label;
- plan label;
- child invite count;
- tree depth;
- source "Premium Smart RU campaign".

### 6.7. Onboarding apply

Existing endpoint:

```text
POST /api/v1/customer/onboarding/growth-code/apply
```

Response must include:

```json
{
  "status": "applied",
  "code_type": "invite",
  "connection_required": true,
  "entitlement": {
    "plan_code": "premium_smart_ru",
    "display_name": "Premium Smart RU",
    "expires_at": "..."
  },
  "child_invites": {
    "issued": true,
    "batch_id": "uuid",
    "count": 10,
    "friend_plan_code": "premium_smart_ru",
    "friend_days": 365
  },
  "next_destination": "/onboarding/connect"
}
```

---

## 7. Admin UI specification

### 7.1. `/growth/invite-codes`

Replace create-only page with tabs:

```text
1. Overview
2. Campaigns
3. Create Batch
4. Inventory
5. Batches
6. Redemptions
7. Invite Tree
8. Exports & Audit
9. Settings
```

### 7.2. Overview tab

Cards:
- active campaigns;
- issued codes;
- redeemed codes;
- active VPN grants;
- child invites issued;
- max depth reached;
- risk blocked;
- expiring soon.

### 7.3. Campaigns tab

Table:

```text
Campaign
Status
Root codes
Redeemed
Child invites issued
Depth
Plan granted
Created by
Updated
Actions
```

Actions:
- View;
- Edit draft;
- Duplicate;
- Publish;
- Pause;
- Resume;
- Archive;
- Create root batch.

### 7.4. Create Campaign wizard

#### Step 1 — Basic

Fields:
- campaign key;
- display name;
- description;
- status draft;
- start/end dates.

#### Step 2 — Root codes

Fields:
- root code count;
- root owner mode;
- owner user search;
- code expiry;
- raw export policy.

#### Step 3 — Redeem grant

Fields:
- grant mode:
  - plan snapshot;
  - custom snapshot;
  - legacy invite access;
- plan picker using `plansApi.listAdmin()`;
- duration;
- require no active access;
- self redemption block.

The plan picker must show hidden/admin-only plans, especially:

```text
Premium Smart RU / premium_smart_ru / hidden / admin-only / 5 devices
```

#### Step 4 — Child invites

Fields:
- enable child invites;
- invite count;
- child plan picker;
- child duration days;
- child code expiry days;
- max generation depth;
- child issue timing:
  - immediately after redemption;
  - after VPN connected;
  - manual approval.

Default for `premium_smart_ru` campaign:

```text
enable child invites = true
invite count = 10
child plan = premium_smart_ru_365
child duration = 365
expiry = 30 days
max depth = 5
timing = immediately after redemption
```

#### Step 5 — Risk

Fields:
- max redemptions per user;
- max redemptions per device;
- max redemptions per IP / time window;
- block suspicious velocity;
- manual review threshold;
- country allow/deny;
- disposable email block.

#### Step 6 — Preview

Show generated policy JSON and simulation:

```text
Root invite ABCD****:
  grants Premium Smart RU for 365 days
  after redeem issues 10 child invites
  child invites grant Premium Smart RU for 365 days
  max depth 5
```

#### Step 7 — Publish

Require reason and confirmation.

### 7.5. Inventory tab

Filters:
- campaign;
- batch;
- owner;
- redeemer;
- plan;
- status;
- is used;
- depth;
- expiry;
- code prefix.

Columns:
- code prefix;
- status;
- campaign;
- batch;
- owner;
- redeemer;
- plan;
- depth;
- parent;
- root;
- created;
- expires;
- used;
- actions.

Actions:
- open detail;
- revoke;
- extend;
- copy safe reference;
- export raw code if permission allows.

### 7.6. Batches tab

Use existing and new backend batch endpoints.

Columns:
- batch id;
- campaign;
- kind;
- owner;
- requested;
- issued;
- used;
- revoked;
- expired;
- plan;
- depth;
- created;
- expires.

Actions:
- detail;
- export raw codes;
- revoke unused;
- extend;
- resend notification.

### 7.7. Redemptions tab

Columns:
- invite code prefix;
- inviter;
- invitee;
- campaign;
- plan granted;
- entitlement grant;
- child batch;
- depth;
- status;
- risk result;
- redeemed at.

### 7.8. Invite Tree tab

Visual tree:
- collapsible nodes;
- root/parent/child links;
- search user;
- highlight branch;
- show depth;
- show plan;
- show VPN connected state;
- show child invites issued/used.

Support display modes:
- graph;
- table;
- generation summary;
- export CSV.

### 7.9. Remove old text

Remove:

```text
Admin-покрытие здесь реальное, но узкое...
```

Replace with operational help:

```text
Управляйте invite campaigns, batches, inventory, redemptions и деревом приглашений.
Raw-коды доступны только через audited export.
```

---

## 8. Customer UX

### 8.1. After successful invite redemption

Show:

```text
Доступ активирован: Premium Smart RU
Срок: 365 дней
Устройств: 5
Smart Routing: включён

Вам выдано 10 инвайтов для друзей.
Каждый друг получит Premium Smart RU на 365 дней.
```

Buttons:
- Connect VPN;
- Show QR;
- Copy subscription link;
- My invites;
- Go to dashboard.

### 8.2. Rewards / Invites page

Group by batch:

```text
Premium Smart RU Invite Campaign
10 инвайтов · 3 использовано · 7 активны
Выдано после применения invite ABCD****
```

For each invite:
- safe code display;
- copy code;
- share;
- status;
- expiry;
- used by friend masked;
- generation depth.

### 8.3. Telegram Bot

After `/code`:

```text
✅ Premium Smart RU активирован на 365 дней.
🎁 Вам выдано 10 инвайтов для друзей.

[QR] [Ссылка подключения]
[iOS] [Android] [Windows] [macOS] [Linux]
[Я подключил] [Мои инвайты]
```

---

## 9. VPN provisioning for `premium_smart_ru`

### 9.1. Required env

Production must have:

```env
REMNAWAVE_SMART_RU_EXTERNAL_SQUAD_UUID=<uuid>
REMNAWAVE_SMART_RU_INTERNAL_SQUAD_UUID=<uuid>
REMNAWAVE_SMART_RU_PLAN_CODES=premium_smart_ru
REMNAWAVE_SMART_RU_SUBSCRIPTION_TEMPLATE_NAME="CyberVPN Premium Smart RU"
```

### 9.2. Provisioning path

For plan-backed invite/gift/purchase grants, use one unified plan-aware service:

```text
EnsureServiceIdentityForEntitlementUseCase
```

It must:
- read entitlement snapshot plan_code;
- detect `premium_smart_ru`;
- add Remnawave external squad UUID;
- add active internal squad UUIDs;
- create subscription-scoped service identity;
- save subscription_url;
- support connection bootstrap.

### 9.3. No trial provisioning for plan-backed invites

Do not route `premium_smart_ru` invite redemption through trial provisioning. Trial provisioning is only for legacy trial access.

---

## 10. Cabinet-only / RSC production hardening

Because invite/rewards pages are part of this workflow, production must not break RSC navigation.

### 10.1. Mandatory cabinet prefixes

Backend runtime config must always union stored `cabinet_allowed_prefixes` with mandatory system prefixes:

```text
/dashboard
/subscriptions
/payment-history
/referral
/rewards
/rewards/referral
/rewards/gifts
/rewards/invites
/rewards/codes
/rewards/notifications
/messages
/wallet
/settings
/support
/servers
/onboarding
```

### 10.2. RSC cross-origin redirect ban

For requests with:

```text
?_rsc=
RSC: 1
Next-Router-State-Tree
Next-Router-Prefetch
Accept: text/x-component
```

proxy must never return cross-origin redirect.

Instead:
- allow if route is cabinet route;
- return 404/204 safe response if route is invalid;
- only browser navigation may redirect cross-origin.

### 10.3. Deploy smoke

Add smoke URLs:

```text
https://my.cyber-vpn.net/en-EN/rewards
https://my.cyber-vpn.net/en-EN/rewards/invites
https://my.cyber-vpn.net/en-EN/rewards/gifts
https://my.cyber-vpn.net/en-EN/rewards/codes
https://my.cyber-vpn.net/en-EN/rewards/notifications
https://my.cyber-vpn.net/en-EN/messages
https://my.cyber-vpn.net/en-EN/onboarding/code
```

Also add RSC probe smoke:

```bash
curl -I 'https://my.cyber-vpn.net/en-EN/rewards/invites?_rsc=smoke'
```

Must not return `Location: https://cyber-vpn.net/...`.

---

## 11. Security, audit, anti-abuse

### 11.1. Raw code handling

Raw invite codes:
- returned only on creation/export;
- never logged;
- never included in generic list;
- export requires elevated permission;
- export writes audit entry;
- export can be disabled per campaign.

### 11.2. Idempotency

Required idempotency keys:

```text
campaign create: admin-invite-campaign:{admin_id}:{client_key}
root batch: invite-root-batch:{campaign_id}:{version_id}:{client_key}
redeem: invite-redeem:{invite_code_id}:{redeemer_user_id}
child batch: invite-child-batch:{redemption_id}
tree edge: invite-tree-edge:{redemption_id}
```

### 11.3. Risk controls

At redemption:
- self redemption block;
- active access block;
- velocity per IP/device/user;
- duplicate device fingerprint;
- suspicious repeated attempts;
- max depth;
- disposable email;
- country restrictions;
- risk decision stored.

### 11.4. Reversal

Support:
- revoke unused child invites;
- reverse entitlement if abuse/refund/manual;
- mark tree branch as blocked/reversed;
- no hard delete.

---

## 12. Migration plan

### Phase 1 — Data model

- Add new tables:
  - `invite_campaigns`;
  - `invite_campaign_versions`;
  - `invite_redemptions`;
  - `invite_tree_edges`;
  - `invite_tree_closure`;
  - `invite_campaign_daily_rollups`.
- Extend:
  - `invite_codes`;
  - `invite_batches`.

### Phase 2 — Backend use cases

- `CreateInviteCampaignUseCase`
- `PublishInviteCampaignVersionUseCase`
- `CreateInviteCampaignBatchUseCase`
- `RedeemPlanBackedInviteUseCase`
- `GenerateChildInvitesAfterRedemptionUseCase`
- `BuildInviteTreeUseCase`
- `ListInviteInventoryUseCase`

### Phase 3 — API

Add admin campaign/inventory/tree endpoints.

### Phase 4 — Admin UI

Replace create-only invite page with full console.

### Phase 5 — Customer UX

Update onboarding response + invite inventory.

### Phase 6 — Telegram Bot / Mini App

Show child invites after code application.

### Phase 7 — Rollups

Daily rollups and admin analytics.

### Phase 8 — Production smoke / monitoring

Add smoke and dashboards.

---

## 13. Backfill

### 13.1. Legacy invites

For existing invite codes:
- `grant_mode = "legacy_invite_access"`;
- `generation_depth = 0`;
- `root_invite_code_id = id`;
- no campaign.

### 13.2. Existing batches

For existing `invite_batches`:
- `batch_kind` inferred from source_type;
- campaign null;
- root/parent null unless source payload has data.

### 13.3. Existing redemptions

For used invites:
- create `invite_redemptions`;
- create tree edge only if `owner_user_id` and `used_by_user_id` exist;
- create closure records.

---

## 14. Tests

### 14.1. Unit tests

- campaign validation;
- policy checksum;
- root batch idempotency;
- plan-backed invite snapshot;
- premium_smart_ru snapshot;
- child invite policy;
- tree edge creation;
- closure creation;
- self-redemption block;
- active-access block;
- max-depth block;
- raw code redaction.

### 14.2. Integration tests

#### Test: premium_smart_ru root invite

```text
Given premium_smart_ru_365 exists
And campaign child_invite_count = 10
When admin creates root batch
And new user redeems root invite in onboarding
Then user gets premium_smart_ru entitlement
And 10 child invites are issued to user
And child batch has parent/root/redemption ids
And connection bootstrap returns Smart RU connection profile
```

#### Test: tree

```text
A invites B
B invites C
C invites D
Admin opens tree for root invite
Tree contains A->B->C->D with depths 0/1/2/3
```

#### Test: max depth

```text
max_generation_depth = 2
Depth 2 user redeems invite
User gets plan
No child invites are generated
```

#### Test: admin inventory

```text
GET /admin/invite-codes?campaign_id=...
returns all codes with status and tree fields
```

#### Test: raw export audit

```text
GET /admin/invite-batches/{id}/export
returns raw codes
writes audit event
```

#### Test: RSC

```text
GET /en-EN/rewards/invites?_rsc=...
Host my.cyber-vpn.net
must not redirect to cyber-vpn.net
```

### 14.3. E2E tests

- Web registration → OTP → invite → Premium Smart RU → connection modal → child invites visible.
- Mini App login → invite → QR → child invites visible.
- Telegram Bot `/code` → QR → child invites.
- Admin create campaign → root batch → export → tree view.

---

## 15. Acceptance Criteria

### Functional

- Admin can create invite campaign for `premium_smart_ru`.
- Admin can set how many invites are created.
- Admin can set which plan invite grants.
- Admin can set how many child invites redeemer receives.
- Admin can set which plan child invites grant.
- Admin can set expiry, depth, limits and risk.
- User can enter invite in onboarding and get target plan.
- User receives configured child invites.
- Tree is fully trackable.
- Admin can list/search/revoke/extend/export invites.
- Admin can view redemptions and tree.
- Admin UI no longer shows "coverage narrow" message.

### Security

- Raw codes are not leaked in logs/list endpoints.
- Raw export is audited.
- Self-redemption blocked.
- Active access block works.
- Idempotency prevents duplicate child batches.
- Risk decisions are stored.
- Telegram Bot does not send VPN config in groups.

### Production

- `premium_smart_ru` provisioning works with Remnawave Smart RU env.
- RSC navigation in cabinet does not redirect cross-origin.
- `/rewards/*` and `/messages` work in cabinet-only mode.
- Deployment smoke covers onboarding/rewards/messages.

---

## 16. Recommended first campaign config

```json
{
  "campaign_key": "premium_smart_ru_invite_wave_1",
  "display_name": "Premium Smart RU Invite Wave 1",
  "status": "draft",
  "root_owner_mode": "system",
  "allowed_surfaces": ["web", "miniapp", "telegram_bot"],
  "max_generation_depth": 5,
  "require_no_active_access": true,
  "self_redemption_block": true,
  "root_invite_policy": {
    "count": 100,
    "expiry_mode": "relative",
    "expiry_days": 30
  },
  "redemption_policy": {
    "grant_mode": "plan_snapshot",
    "grant_plan_code": "premium_smart_ru",
    "grant_duration_days": 365
  },
  "child_invite_policy": {
    "enabled": true,
    "count": 10,
    "grant_mode": "plan_snapshot",
    "grant_plan_code": "premium_smart_ru",
    "grant_duration_days": 365,
    "expiry_mode": "relative",
    "expiry_days": 30
  },
  "risk_policy": {
    "per_user_redeem_cap": 1,
    "block_self_redemption": true,
    "block_active_access": true,
    "velocity_window_minutes": 60,
    "max_redemptions_per_ip_per_window": 5
  }
}
```

---

## 17. Definition of Done

The task is complete only when:

1. `premium_smart_ru` can be granted by invite code during onboarding.
2. Redeemer automatically receives configured child invites.
3. Invite tree is persisted and visible in admin.
4. Admin page supports campaigns, inventory, batches, redemptions, tree and exports.
5. `plansApi.listAdmin()` is used for admin plan picker.
6. Legacy invites remain compatible.
7. Gift codes still work.
8. RSC/cabinet navigation is stable.
9. Full test suite and production smoke pass.
10. Documentation for operators is added:
    - how to create Premium Smart RU campaign;
    - how to export root codes;
    - how to inspect tree;
    - how to revoke branch/batch;
    - how to verify Remnawave Smart RU provisioning.

---

## 18. Operator checklist for production rollout

Before enabling campaign:

```text
[ ] premium_smart_ru plans exist for target durations
[ ] premium_smart_ru plans are active
[ ] REMNAWAVE_SMART_RU_EXTERNAL_SQUAD_UUID is set
[ ] REMNAWAVE_SMART_RU_INTERNAL_SQUAD_UUID is set
[ ] connection bootstrap works for premium_smart_ru test grant
[ ] admin can create draft invite campaign
[ ] campaign simulation passes
[ ] root batch creation returns raw codes
[ ] onboarding redeem test passes
[ ] child invite batch issued
[ ] invite tree shows root -> redeemer
[ ] rewards/invites page shows child batch
[ ] Telegram Bot /code works in private chat
[ ] RSC smoke passes
```
