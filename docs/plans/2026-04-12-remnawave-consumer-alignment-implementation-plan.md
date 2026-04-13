# Remnawave Consumer Alignment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Align all downstream consumers of the Remnawave integration with the new `2.7.4` contract so that background jobs, Helix inventory sync, frontend types, and admin UX all reflect the same validated backend baseline.

**Architecture:** Keep the backend `backend/src/infrastructure/remnawave/contracts.py` as the canonical contract. Do not spread new raw Remnawave parsing into consumers. Instead, introduce small consumer-local normalization layers where direct reuse is impractical, then sync the frontend typed contract from backend OpenAPI and expose only the operationally useful `metadata`, `recap`, `node_version`, and plugin governance surfaces in the admin UI.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, httpx, pytest, Rust, reqwest, serde, cargo test, Next.js 16, React 19, TanStack Query v5, openapi-typescript, Vitest

---

## Delivery Order

1. `P0` Task-worker normalization and contract hardening
2. `P0` Helix adapter node inventory alignment
3. `P0` Backend OpenAPI export and frontend type regeneration
4. `P1` Admin monitoring upgrade for `metadata` and `recap`
5. `P1` Admin server governance upgrade for `node_version` and plugin state
6. `P2` CI guardrails and regression coverage

## Phase Summary

| Phase | Scope | Estimate | Risk if skipped |
| --- | --- | --- | --- |
| `P0.1` | Task-worker normalization foundation | `0.5-1 day` | silent analytics and cron drift |
| `P0.2` | Task-worker task migration | `1-2 days` | stale status/traffic logic remains in prod jobs |
| `P0.3` | Helix adapter inventory alignment | `1-2 days` | node registry drift or broken sync on upstream shape changes |
| `P0.4` | OpenAPI and frontend type regeneration | `0.5 day` | frontend compiles against stale contract |
| `P1.1` | Monitoring metadata/recap UI | `1 day` | ops value from new endpoints stays unused |
| `P1.2` | Server governance UI | `1 day` | node/plugin drift stays invisible in admin |
| `P2` | CI guardrails and follow-up docs | `0.5-1 day` | same drift can reappear unnoticed |

---

## Phase `P0.1`: Task-worker normalization foundation

**Outcome:** `services/task-worker` stops depending on raw Remnawave payload quirks and gets one normalization path for users and nodes.

### Task 1: Add normalized Remnawave adapter helpers for task-worker

**Files:**
- Create: `services/task-worker/src/services/remnawave_normalizers.py`
- Modify: `services/task-worker/src/services/remnawave_client.py`
- Test: `services/task-worker/tests/test_services.py`
- Test: `services/task-worker/tests/unit/test_remnawave_normalizers.py`

**Step 1: Write the failing tests**

Cover these cases:
- user status normalization from `ACTIVE` to `active`
- user online detection from nested or aliased fields
- user traffic normalization when usage is nested instead of flat
- node identity normalization with `uuid`, `name`, `address`
- node traffic normalization with current `2.7.4` fields and safe zero fallback

Run:

```bash
cd /home/beep/projects/VPNBussiness/services/task-worker
~/.pyenv/versions/3.13.11/bin/python -m pytest \
  tests/test_services.py \
  tests/unit/test_remnawave_normalizers.py -q
```

Expected: FAIL because the normalizer module and behaviors do not exist yet.

**Step 2: Implement the minimal normalization layer**

Add helper functions with a narrow surface:

```python
def normalize_user(payload: dict[str, object]) -> dict[str, object]: ...
def normalize_node(payload: dict[str, object]) -> dict[str, object]: ...
def normalize_users(payloads: list[dict[str, object]]) -> list[dict[str, object]]: ...
def normalize_nodes(payloads: list[dict[str, object]]) -> list[dict[str, object]]: ...
```

Rules:
- normalize statuses to lowercase
- preserve original identifiers
- expose stable keys used by worker tasks:
  - users: `uuid`, `username`, `status`, `is_online`, `expire_at`, `traffic_limit_bytes`, `used_traffic_bytes`, `telegram_id`
  - nodes: `uuid`, `name`, `address`, `is_connected`, `is_disabled`, `traffic_up`, `traffic_down`, `current_bandwidth`

**Step 3: Route client collection methods through the normalizer**

Update:
- `get_nodes()`
- `get_users()`
- `get_user()`

Do not rewrite the entire client yet. Only normalize the payloads returned by these public helpers.

**Step 4: Run the targeted test suite**

Run:

```bash
cd /home/beep/projects/VPNBussiness/services/task-worker
~/.pyenv/versions/3.13.11/bin/python -m pytest \
  tests/test_services.py \
  tests/unit/test_remnawave_normalizers.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add services/task-worker/src/services/remnawave_client.py \
  services/task-worker/src/services/remnawave_normalizers.py \
  services/task-worker/tests/test_services.py \
  services/task-worker/tests/unit/test_remnawave_normalizers.py
git commit -m "feat(task-worker): normalize remnawave user and node payloads"
```

**Acceptance Criteria:**
- one normalization entry point exists for task-worker user and node payloads
- tests prove compatibility with `2.7.4`-style payloads
- no worker task still needs to understand uppercase status directly

**Risk Notes:**
- keep the adapter intentionally small; do not recreate the whole backend contract package inside task-worker

---

## Phase `P0.2`: Task-worker task migration

**Outcome:** analytics, sync, monitoring, and subscription tasks consume normalized payloads instead of raw fields.

### Task 2: Migrate analytics and monitoring tasks to normalized fields

**Files:**
- Modify: `services/task-worker/src/tasks/analytics/daily_stats.py`
- Modify: `services/task-worker/src/tasks/analytics/realtime_metrics.py`
- Modify: `services/task-worker/src/tasks/monitoring/bandwidth.py`
- Test: `services/task-worker/tests/test_analytics.py`
- Test: `services/task-worker/tests/test_monitoring.py`

**Step 1: Write the failing task tests**

Cover:
- active user counting with normalized lowercase status
- online user counting using normalized `is_online`
- bandwidth aggregation using normalized `traffic_up` and `traffic_down`
- realtime metrics not depending on missing `currentBandwidth`

Run:

```bash
cd /home/beep/projects/VPNBussiness/services/task-worker
~/.pyenv/versions/3.13.11/bin/python -m pytest \
  tests/test_analytics.py \
  tests/test_monitoring.py -q
```

Expected: FAIL on old field assumptions.

**Step 2: Implement the migration**

Update tasks to consume normalized keys only:

```python
active_users = sum(1 for u in users if u.get("status") == "active")
online_users = sum(1 for u in users if u.get("is_online", False))
total_bandwidth = sum(u.get("used_traffic_bytes", 0) or 0 for u in users)
bytes_up = node.get("traffic_up", 0) or 0
bytes_down = node.get("traffic_down", 0) or 0
```

Fallback rule:
- if `current_bandwidth` is absent, derive it from the normalized traffic counters or return zero explicitly

**Step 3: Run the targeted tests**

Run:

```bash
cd /home/beep/projects/VPNBussiness/services/task-worker
~/.pyenv/versions/3.13.11/bin/python -m pytest \
  tests/test_analytics.py \
  tests/test_monitoring.py -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add services/task-worker/src/tasks/analytics/daily_stats.py \
  services/task-worker/src/tasks/analytics/realtime_metrics.py \
  services/task-worker/src/tasks/monitoring/bandwidth.py \
  services/task-worker/tests/test_analytics.py \
  services/task-worker/tests/test_monitoring.py
git commit -m "refactor(task-worker): use normalized remnawave fields in analytics"
```

**Acceptance Criteria:**
- analytics and monitoring tasks no longer read raw `ACTIVE`, `trafficUp`, `trafficDown`, `usedTrafficBytes`
- task suite passes against normalized fixtures

### Task 3: Migrate sync and subscription tasks to normalized fields

**Files:**
- Modify: `services/task-worker/src/tasks/sync/user_stats.py`
- Modify: `services/task-worker/src/tasks/sync/node_configs.py`
- Modify: `services/task-worker/src/tasks/subscriptions/disable_expired.py`
- Modify: `services/task-worker/src/tasks/subscriptions/auto_renew.py`
- Modify: `services/task-worker/src/tasks/subscriptions/check_expiring.py`
- Test: `services/task-worker/tests/test_sync.py`
- Test: `services/task-worker/tests/test_subscriptions.py`

**Step 1: Write the failing tests**

Cover:
- expired user detection from normalized `expire_at`
- disable path ignores already disabled normalized users
- user stats use normalized `status`, `is_online`, `traffic_limit_bytes`, `used_traffic_bytes`
- node config sync stores normalized node objects consistently

Run:

```bash
cd /home/beep/projects/VPNBussiness/services/task-worker
~/.pyenv/versions/3.13.11/bin/python -m pytest \
  tests/test_sync.py \
  tests/test_subscriptions.py -q
```

Expected: FAIL on old `expiresAt`, `dataLimit`, `dataUsed`, `telegramId` assumptions.

**Step 2: Implement the migration**

Replace raw field reads with normalized keys:

```python
expire_at = user.get("expire_at")
data_limit = user.get("traffic_limit_bytes", 0)
data_used = user.get("used_traffic_bytes", 0)
telegram_id = user.get("telegram_id")
```

Keep cache payloads stable for downstream readers. If a Redis payload shape is externally consumed, normalize internally but preserve the outer cache contract until a follow-up cleanup.

**Step 3: Run the targeted tests**

Run:

```bash
cd /home/beep/projects/VPNBussiness/services/task-worker
~/.pyenv/versions/3.13.11/bin/python -m pytest \
  tests/test_sync.py \
  tests/test_subscriptions.py -q
```

Expected: PASS.

**Step 4: Run a wider worker smoke**

Run:

```bash
cd /home/beep/projects/VPNBussiness/services/task-worker
~/.pyenv/versions/3.13.11/bin/python -m pytest \
  tests/test_services.py \
  tests/test_sync.py \
  tests/test_subscriptions.py \
  tests/test_analytics.py \
  tests/test_monitoring.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add services/task-worker/src/tasks/sync/user_stats.py \
  services/task-worker/src/tasks/sync/node_configs.py \
  services/task-worker/src/tasks/subscriptions/disable_expired.py \
  services/task-worker/src/tasks/subscriptions/auto_renew.py \
  services/task-worker/src/tasks/subscriptions/check_expiring.py \
  services/task-worker/tests/test_sync.py \
  services/task-worker/tests/test_subscriptions.py
git commit -m "refactor(task-worker): consume normalized remnawave payloads in jobs"
```

**Acceptance Criteria:**
- sync and subscription jobs no longer depend on raw `2.6.x`/early `2.7.x` payload assumptions
- worker tests pass without custom monkeypatches for uppercase status or old traffic fields

---

## Phase `P0.3`: Helix adapter node inventory alignment

**Outcome:** `services/helix-adapter` reads Remnawave node inventory safely against `2.7.4`.

### Task 4: Update Helix Remnawave inventory DTO and mapping

**Files:**
- Modify: `services/helix-adapter/src/remnawave/client.rs`
- Modify: `services/helix-adapter/src/node_registry/service.rs`
- Test: `services/helix-adapter/tests/node_registry.rs`
- Test: `services/helix-adapter/tests/node_assignment.rs`

**Step 1: Write the failing Rust tests**

Add fixtures for `2.7.4` node payloads containing:
- `uuid`
- `address`
- `isDisabled`
- `isConnected`
- `versions`
- `activePluginUuid`

Run:

```bash
cd /home/beep/projects/VPNBussiness/services/helix-adapter
cargo test node_registry -- --nocapture
```

Expected: FAIL because the current DTO expects `id`, `hostname`, and `enabled`.

**Step 2: Update the DTO**

Replace the old inventory shape with a `2.7.4`-compatible model:

```rust
pub struct NodeInventoryItem {
    pub uuid: String,
    pub name: String,
    pub address: Option<String>,
    pub is_disabled: Option<bool>,
    pub is_connected: Option<bool>,
    pub active_plugin_uuid: Option<String>,
    pub versions: Option<NodeVersions>,
}
```

If the endpoint still needs compatibility with old fixtures, add `#[serde(alias = "...")]` for transitional support.

**Step 3: Update `inventory_to_upsert` mapping**

Rules:
- map `remnawave_node_id` from `uuid`
- derive `hostname` from `address` only when it is a hostname-like value
- derive `transport_enabled` from `!is_disabled.unwrap_or(false)`
- keep future governance signals available for follow-up use

**Step 4: Run the Rust tests**

Run:

```bash
cd /home/beep/projects/VPNBussiness/services/helix-adapter
cargo test node_registry node_assignment -- --nocapture
```

Expected: PASS.

**Step 5: Commit**

```bash
git add services/helix-adapter/src/remnawave/client.rs \
  services/helix-adapter/src/node_registry/service.rs \
  services/helix-adapter/tests/node_registry.rs \
  services/helix-adapter/tests/node_assignment.rs
git commit -m "fix(helix-adapter): align remnawave node inventory with 2.7.4"
```

**Acceptance Criteria:**
- Helix node registry can deserialize `2.7.4` node payloads
- sync no longer depends on legacy `id/hostname/enabled` shape

**Risk Notes:**
- do not turn `helix-adapter` into a second full Remnawave contract package; keep only the inventory slice it actually needs

---

## Phase `P0.4`: Backend OpenAPI export and frontend type regeneration

**Outcome:** frontend uses the real backend contract, including `metadata`, `recap`, `node_version`, and `active_plugin_uuid`.

### Task 5: Refresh backend OpenAPI and frontend generated types

**Files:**
- Modify: `backend/docs/api/openapi.json`
- Modify: `frontend/src/lib/api/generated/types.ts`
- Modify: `frontend/src/lib/api/monitoring.ts`
- Modify: `frontend/src/lib/api/servers.ts`

**Step 1: Export the backend OpenAPI spec**

Run:

```bash
cd /home/beep/projects/VPNBussiness/backend
~/.pyenv/versions/3.13.11/bin/python scripts/export_openapi.py
```

Expected:
- `backend/docs/api/openapi.json` contains:
  - `/api/v1/monitoring/metadata`
  - `/api/v1/monitoring/recap`
  - `node_version`
  - `active_plugin_uuid`

**Step 2: Regenerate frontend types**

Run:

```bash
cd /home/beep/projects/VPNBussiness/frontend
npm run generate:api-types
```

Expected: generated file updates without manual edits.

**Step 3: Extend the thin API clients**

Add:

```ts
metadata: () => apiClient.get<MetadataResponse>('/monitoring/metadata')
getRecap: () => apiClient.get<RecapResponse>('/monitoring/recap')
```

Keep `serversApi` typed against the regenerated `ServerResponse`.

**Step 4: Verify generated contract alignment**

Run:

```bash
cd /home/beep/projects/VPNBussiness
rg -n '"/api/v1/monitoring/(metadata|recap)"|node_version|active_plugin_uuid' \
  backend/docs/api/openapi.json \
  frontend/src/lib/api/generated/types.ts
```

Expected: all new surfaces are present in both files.

**Step 5: Commit**

```bash
git add backend/docs/api/openapi.json \
  frontend/src/lib/api/generated/types.ts \
  frontend/src/lib/api/monitoring.ts \
  frontend/src/lib/api/servers.ts
git commit -m "chore(frontend): regenerate api types for remnawave 2.7.4 surfaces"
```

**Acceptance Criteria:**
- frontend generated types include all new monitoring and server governance fields
- there is no stale typed boundary between backend and frontend

---

## Phase `P1.1`: Admin monitoring upgrade

**Outcome:** admin monitoring and dashboard use the new Remnawave operational surfaces instead of only the legacy trio.

### Task 6: Add `metadata` and `recap` to admin monitoring and dashboard

**Files:**
- Modify: `frontend/src/app/[locale]/(dashboard)/dashboard/hooks/useDashboardData.ts`
- Modify: `frontend/src/app/[locale]/(dashboard)/dashboard/components/DashboardStats.tsx`
- Modify: `frontend/src/app/[locale]/(dashboard)/monitoring/components/MonitoringClient.tsx`
- Test: `frontend/src/app/[locale]/(dashboard)/monitoring/components/__tests__/MonitoringClient.test.tsx`
- Create: `frontend/src/app/[locale]/(dashboard)/dashboard/components/__tests__/DashboardStats.test.tsx`

**Step 1: Write the failing frontend tests**

Cover:
- metadata card renders version, build time, and git data
- recap cards render users, nodes, traffic, and countries
- fallback UI works when metadata or recap endpoints return placeholders

Run:

```bash
cd /home/beep/projects/VPNBussiness/frontend
npm run test:run -- "src/app/[locale]/(dashboard)/monitoring/components/__tests__/MonitoringClient.test.tsx"
```

Expected: FAIL because UI does not request or render those fields yet.

**Step 2: Add query hooks**

Extend `useDashboardData.ts` with:

```ts
export function useSystemMetadata() { ... }
export function useSystemRecap() { ... }
```

Match existing React Query patterns:
- shared query keys
- stale times
- visibility-aware polling

**Step 3: Render the new monitoring surfaces**

Update:
- monitoring page for full build/version/git details
- dashboard cards for compact recap values:
  - total users
  - total nodes
  - total traffic
  - distinct countries

Do not overload the hero section. Use compact cards or a small operational strip.

**Step 4: Run the frontend tests**

Run:

```bash
cd /home/beep/projects/VPNBussiness/frontend
npm run test:run -- "src/app/[locale]/(dashboard)/monitoring/components/__tests__/MonitoringClient.test.tsx"
```

Expected: PASS.

**Step 5: Commit**

```bash
git add 'frontend/src/app/[locale]/(dashboard)/dashboard/hooks/useDashboardData.ts' \
  'frontend/src/app/[locale]/(dashboard)/dashboard/components/DashboardStats.tsx' \
  'frontend/src/app/[locale]/(dashboard)/monitoring/components/MonitoringClient.tsx' \
  'frontend/src/app/[locale]/(dashboard)/monitoring/components/__tests__/MonitoringClient.test.tsx' \
  'frontend/src/app/[locale]/(dashboard)/dashboard/components/__tests__/DashboardStats.test.tsx'
git commit -m "feat(admin): surface remnawave metadata and recap"
```

**Acceptance Criteria:**
- admin can see Remnawave panel version/build/git in the monitoring UI
- dashboard exposes the high-signal recap values without opening the monitoring page

---

## Phase `P1.2`: Admin server governance upgrade

**Outcome:** server pages expose the new node-level governance fields from the backend.

### Task 7: Add `node_version` and plugin governance state to server views

**Files:**
- Modify: `frontend/src/entities/server/model/types.ts`
- Modify: `frontend/src/features/servers/hooks/useServers.ts`
- Modify: `frontend/src/widgets/servers-data-grid.tsx`
- Modify: `frontend/src/app/[locale]/(dashboard)/dashboard/components/ServerGrid.tsx`
- Create: `frontend/src/features/servers/hooks/__tests__/useServers.test.ts`

**Step 1: Write the failing tests**

Cover:
- server mapper preserves `xray_version`
- server mapper adds `node_version`
- server mapper adds plugin/governance display state derived from `active_plugin_uuid`

Run:

```bash
cd /home/beep/projects/VPNBussiness/frontend
npm run test:run -- "src/features/servers/hooks/__tests__/useServers.test.ts"
```

Expected: FAIL because the display model does not carry those fields yet.

**Step 2: Extend the frontend display model**

Add optional fields:

```ts
nodeVersion?: string | null
xrayVersion?: string | null
activePluginUuid?: string | null
governanceState?: 'plugin-active' | 'plugin-missing'
```

Map them in `useServers.ts` from the typed backend response.

**Step 3: Render governance information**

Add:
- `node_version` and `xray_version` badges or rows
- plugin state badge:
  - `Plugin active`
  - `No plugin`

Show it in:
- desktop grid
- card grid
- mobile list if feasible without clutter

**Step 4: Run the relevant frontend tests**

Run:

```bash
cd /home/beep/projects/VPNBussiness/frontend
npm run test:run -- "src/features/servers/hooks/__tests__/useServers.test.ts"
```

Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/entities/server/model/types.ts \
  frontend/src/features/servers/hooks/useServers.ts \
  frontend/src/widgets/servers-data-grid.tsx \
  'frontend/src/app/[locale]/(dashboard)/dashboard/components/ServerGrid.tsx' \
  frontend/src/features/servers/hooks/__tests__/useServers.test.ts
git commit -m "feat(admin): expose remnawave node governance details"
```

**Acceptance Criteria:**
- server UI shows node and xray versions
- plugin/governance state is visible without opening Remnawave directly

---

## Phase `P2`: CI guardrails and regression coverage

**Outcome:** contract drift is caught automatically in consumers and not rediscovered manually.

### Task 8: Add guardrails for consumer drift

**Files:**
- Modify: `backend/tests/contract/remnawave/test_repo_docs_alignment.py`
- Modify: `services/task-worker/tests/test_services.py`
- Modify: `services/helix-adapter/tests/node_registry.rs`
- Modify: `frontend/src/app/[locale]/(dashboard)/monitoring/components/__tests__/MonitoringClient.test.tsx`
- Modify: `frontend/scripts/generate-api-types.mjs`
- Modify: `docs/runbooks/REMNAWAVE_UPGRADE_GUARDRAILS.md`

**Step 1: Add explicit consumer checks**

Add or extend tests so they fail when:
- task-worker reintroduces raw status assumptions
- helix-adapter expects the legacy node inventory shape
- frontend generated types miss `metadata`, `recap`, `node_version`, or `active_plugin_uuid`

**Step 2: Add a reproducible verification block**

Document and run:

```bash
cd /home/beep/projects/VPNBussiness/backend
~/.pyenv/versions/3.13.11/bin/python -m pytest \
  tests/contract/remnawave/test_vendored_sdk_contracts.py \
  tests/contract/remnawave/test_repo_docs_alignment.py

cd /home/beep/projects/VPNBussiness/services/task-worker
~/.pyenv/versions/3.13.11/bin/python -m pytest \
  tests/test_services.py tests/test_sync.py tests/test_subscriptions.py \
  tests/test_analytics.py tests/test_monitoring.py

cd /home/beep/projects/VPNBussiness/services/helix-adapter
cargo test node_registry node_assignment -- --nocapture

cd /home/beep/projects/VPNBussiness/frontend
npm run generate:api-types
npm run test:run -- "src/app/[locale]/(dashboard)/monitoring/components/__tests__/MonitoringClient.test.tsx"
```

**Step 3: Commit**

```bash
git add backend/tests/contract/remnawave/test_repo_docs_alignment.py \
  services/task-worker/tests/test_services.py \
  services/helix-adapter/tests/node_registry.rs \
  'frontend/src/app/[locale]/(dashboard)/monitoring/components/__tests__/MonitoringClient.test.tsx' \
  frontend/scripts/generate-api-types.mjs \
  docs/runbooks/REMNAWAVE_UPGRADE_GUARDRAILS.md
git commit -m "test(remnawave): add consumer drift guardrails"
```

**Acceptance Criteria:**
- consumer drift is caught by tests before release
- upgrade runbook includes the consumer verification block

---

## Final Acceptance Criteria

- `services/task-worker` uses normalized Remnawave payloads instead of raw `2.6.x` assumptions
- `services/helix-adapter` can sync Remnawave `2.7.4` node inventory safely
- frontend generated API types match the current backend OpenAPI
- admin monitoring renders `metadata` and `recap`
- admin server views render `node_version` and plugin governance state
- test coverage exists across Python, Rust, and frontend consumers

## Rollback Plan

If the execution becomes unstable:

1. revert frontend UI-only phases first
2. keep regenerated OpenAPI/types only if they match the deployed backend
3. revert consumer migrations independently:
   - task-worker
   - helix-adapter
4. do not revert backend Remnawave contract hardening from phases `1-6` unless a separate root-cause proves it is at fault

## Handoff Notes

- Prefer small, isolated commits per task.
- Do not combine `task-worker`, `helix-adapter`, and frontend changes in one giant branch without checkpoints.
- Use the backend contract as the source of truth; do not invent parallel consumer-specific payload shapes beyond thin normalization layers.
