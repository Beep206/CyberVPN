# Private Rust Transport Platform Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a private transport platform to CyberVPN with a Rust control-plane adapter, a Rust node daemon, and a feature-flagged desktop runtime while keeping Remnawave authoritative for users, subscriptions, and node inventory.

**Architecture:** Keep `Remnawave` as the system of record and do not deep-fork it in phase one. Introduce a new internal `services/private-transport-adapter` service that owns private transport manifests, node capability registry, rollout state, and health aggregation. Introduce a new `services/private-transport-node` Rust daemon that runs only on selected nodes and exposes versioned config, health, metrics, and rollback hooks. The existing FastAPI backend remains the authenticated API facade for admin and user flows, and the Tauri desktop client gains an experimental third core with hard fallback to `sing-box` or `xray`. Use @documentation-lookup, @fastapi-clean-architecture, @security-review, @security-review-2, and @code-review during execution, and fetch official docs via Context7 before touching FastAPI, Axum, Tokio, Reqwest, Tauri, Docker Compose, or Prometheus APIs.

**Tech Stack:** Remnawave 2.x, FastAPI/Python 3.13, Rust 1.80+, Axum, Tokio, Reqwest, Serde, Tauri 2, Docker Compose, PostgreSQL 17, Valkey/Redis 8, Prometheus/Grafana, TaskIQ

---

## What I Would Build First

1. Keep `Remnawave` intact as the truth source for users, plans, subscriptions, node inventory, and billing entitlements.
2. Add a separate private transport adapter service instead of writing transport lifecycle logic into `Remnawave` directly.
3. Build the node daemon in Rust before touching mobile.
4. Integrate the first client only in `apps/desktop-client`.
5. Treat mobile as a later program gated on desktop beta stability.
6. Ship a hard kill switch at every layer so the whole experiment can be disabled without touching billing or user records.

## Scope

### In Scope

- New internal Rust adapter service for private transport control-plane logic.
- New Rust node daemon for selected transport-enabled nodes.
- Backend integration with authenticated admin and desktop-facing APIs.
- Desktop Tauri support for an experimental third core.
- Infra, telemetry, rollout, rollback, and incident runbooks.
- Separate shared contract package for manifests, health payloads, and client capability documents.

### Out of Scope For Phase One

- Deep `Remnawave` panel fork.
- Full mobile implementation.
- Billing model changes.
- Mass migration of all users to the private transport.
- Replacing `sing-box` or `xray` as the default core.
- Public marketing copy or public docs that expose wire-level implementation details.

## Target Repository Layout

```text
backend/
  src/
    infrastructure/private_transport/
    application/services/private_transport_service.py
    presentation/api/v1/private_transport/

services/
  private-transport-adapter/
  private-transport-node/
  task-worker/

packages/
  private-transport-contract/

apps/
  desktop-client/
    src/
    src-tauri/

docs/
  private_transport/
  plans/
  security/

infra/
  private-transport/
  prometheus/
  grafana/
```

## Phase Windows

1. Phase 0: Contracts and architecture guardrails - `3-5 days`
2. Phase 1: Adapter service skeleton - `4-7 days`
3. Phase 2: Adapter persistence and manifest pipeline - `5-8 days`
4. Phase 3: Backend integration - `4-6 days`
5. Phase 4: Node daemon - `7-10 days`
6. Phase 5: Infra and observability - `4-6 days`
7. Phase 6: Desktop experimental core - `6-10 days`
8. Phase 7: Worker automation and rollout controls - `3-5 days`
9. Phase 8: Canary, rollback drill, and go/no-go protocol - `3-5 days`
10. Phase 9: Hardening and production decision - `3-5 days`

## Strict Execution Order

1. Task 1 is mandatory before any service code is written.
2. Task 2 must land before Task 3.
3. Task 3 must land before any backend or desktop integration.
4. Task 4 must land before desktop code can request manifests.
5. Task 5 and Task 6 can overlap only after Task 3 is stable.
6. Task 7 depends on Tasks 4-6.
7. Task 8 depends on Task 7.
8. Task 9 is the first production gate.
9. Task 10 is the final hardening gate and must happen before wider rollout.

## Non-Negotiable Rules

- `Remnawave` stays the source of truth for users, subscriptions, plans, and node inventory.
- Do not write transport-specific state into `Remnawave` tables. Use a separate schema or separate service-owned tables.
- Do not expose adapter admin routes directly to the public Internet. Route admin access through the authenticated backend.
- Every new service must expose `/healthz`, `/readyz`, and `/metrics`.
- Every transport manifest must be versioned, signed, and traceable to a rollout ID.
- Every node update must support last-known-good rollback.
- Desktop must keep a hard fallback to `sing-box` or `xray`.
- Mobile remains blocked until desktop beta metrics are acceptable for at least one full release window.
- Keep protocol-specific internals private to the codebase and internal docs; public docs should speak in terms of capability and support, not implementation specifics.

## Success Criteria

- A privileged admin can see transport-enabled nodes and rollout state through the backend.
- The adapter can resolve an entitled user to a signed desktop manifest without mutating `Remnawave`.
- The node daemon can fetch, apply, validate, and roll back a versioned config bundle.
- The desktop client can opt into the experimental core behind a feature flag and recover automatically to a stable core if health checks fail.
- The full system can be disabled from the backend and infra without breaking current `xray` or `sing-box` users.
- Prometheus, Grafana, logs, and alerts cover adapter health, node health, manifest versions, rollout errors, and desktop fallback rate.

## Key Metrics To Watch

- `private_transport_manifest_issued_total`
- `private_transport_manifest_resolve_latency_ms`
- `private_transport_node_heartbeat_stale_total`
- `private_transport_rollout_failed_total`
- `private_transport_desktop_connect_success_rate`
- `private_transport_desktop_fallback_total`
- `private_transport_config_apply_duration_seconds`
- `private_transport_last_known_good_restore_total`

---

### Task 1: Contracts, Architecture Docs, and Guardrails

**Blocked by:** nothing  
**Unlocks:** all later tasks

**Files:**
- Create: `docs/private_transport/README.md`
- Create: `docs/private_transport/architecture.md`
- Create: `docs/private_transport/contracts.md`
- Create: `packages/private-transport-contract/package.json`
- Create: `packages/private-transport-contract/README.md`
- Create: `packages/private-transport-contract/schema/manifest.schema.json`
- Create: `packages/private-transport-contract/schema/node-heartbeat.schema.json`
- Create: `packages/private-transport-contract/schema/client-capabilities.schema.json`
- Create: `packages/private-transport-contract/examples/manifest.example.json`
- Create: `packages/private-transport-contract/examples/node-heartbeat.example.json`
- Create: `packages/private-transport-contract/examples/client-capabilities.example.json`
- Create: `packages/private-transport-contract/scripts/validate-contracts.mjs`

**Step 1: Write the architecture source of truth**

- Add `docs/private_transport/README.md` with the vocabulary, service boundaries, and ownership rules.
- Add `docs/private_transport/architecture.md` with one diagram for:
  - Remnawave
  - backend
  - private transport adapter
  - private transport node daemon
  - desktop client
- Add `docs/private_transport/contracts.md` describing the three contracts:
  - manifest
  - node heartbeat
  - client capabilities

**Step 2: Create the shared contract package**

- Add `packages/private-transport-contract/package.json`.
- Add JSON Schemas for manifest, heartbeat, and client capabilities.
- Add example JSON payloads for each schema.

**Step 3: Add contract validation tooling**

- Add `packages/private-transport-contract/scripts/validate-contracts.mjs`.
- Validate that every example JSON conforms to its schema.

**Step 4: Verify contracts before any code work**

Run:

```bash
node packages/private-transport-contract/scripts/validate-contracts.mjs
```

Expected: PASS with all contract fixtures validated.

**Step 5: Commit**

```bash
git add docs/private_transport packages/private-transport-contract
git commit -m "docs: add private transport architecture and shared contracts"
```

---

### Task 2: Bootstrap the Rust Adapter Service

**Blocked by:** Task 1  
**Unlocks:** Task 3 and Task 4

**Files:**
- Create: `services/private-transport-adapter/Cargo.toml`
- Create: `services/private-transport-adapter/.env.example`
- Create: `services/private-transport-adapter/Dockerfile`
- Create: `services/private-transport-adapter/README.md`
- Create: `services/private-transport-adapter/src/main.rs`
- Create: `services/private-transport-adapter/src/config.rs`
- Create: `services/private-transport-adapter/src/app_state.rs`
- Create: `services/private-transport-adapter/src/error.rs`
- Create: `services/private-transport-adapter/src/metrics.rs`
- Create: `services/private-transport-adapter/src/http/mod.rs`
- Create: `services/private-transport-adapter/src/http/routes/health.rs`
- Create: `services/private-transport-adapter/src/http/routes/internal.rs`
- Create: `services/private-transport-adapter/src/http/routes/admin.rs`
- Create: `services/private-transport-adapter/src/remnawave/client.rs`
- Create: `services/private-transport-adapter/tests/health_routes.rs`

**Step 1: Scaffold a minimal Rust web service**

- Use `axum`, `tokio`, `serde`, `reqwest`, `tracing`, and `prometheus`-friendly middleware.
- Start with only:
  - config loading
  - app state
  - `/healthz`
  - `/readyz`
  - `/metrics`

**Step 2: Add internal Remnawave client wrapper**

- Add `src/remnawave/client.rs` with:
  - base URL
  - auth token
  - timeouts
  - typed helper methods for node inventory reads
- Keep it read-only in phase one.

**Step 3: Make the service production-shaped early**

- Add structured logging.
- Add graceful shutdown.
- Add config fields for:
  - adapter bind address
  - Remnawave URL and token
  - database URL placeholder
  - metrics prefix
  - internal auth token for backend-to-adapter calls

**Step 4: Verify the adapter skeleton**

Run:

```bash
cargo fmt --manifest-path services/private-transport-adapter/Cargo.toml --check
cargo clippy --manifest-path services/private-transport-adapter/Cargo.toml --all-targets -- -D warnings
cargo test --manifest-path services/private-transport-adapter/Cargo.toml
```

Expected: PASS with health route coverage and zero clippy warnings.

**Step 5: Commit**

```bash
git add services/private-transport-adapter
git commit -m "feat(adapter): scaffold private transport adapter service"
```

---

### Task 3: Add Adapter Persistence, Registry, and Manifest Pipeline

**Blocked by:** Task 2  
**Unlocks:** Task 4, Task 5, and Task 7

**Files:**
- Create: `services/private-transport-adapter/migrations/0001_init.sql`
- Create: `services/private-transport-adapter/src/db/mod.rs`
- Create: `services/private-transport-adapter/src/db/pool.rs`
- Create: `services/private-transport-adapter/src/node_registry/model.rs`
- Create: `services/private-transport-adapter/src/node_registry/repository.rs`
- Create: `services/private-transport-adapter/src/node_registry/service.rs`
- Create: `services/private-transport-adapter/src/manifests/model.rs`
- Create: `services/private-transport-adapter/src/manifests/renderer.rs`
- Create: `services/private-transport-adapter/src/manifests/signer.rs`
- Create: `services/private-transport-adapter/src/manifests/store.rs`
- Modify: `services/private-transport-adapter/src/http/routes/internal.rs`
- Modify: `services/private-transport-adapter/src/http/routes/admin.rs`
- Modify: `services/private-transport-adapter/src/main.rs`
- Create: `services/private-transport-adapter/tests/node_registry.rs`
- Create: `services/private-transport-adapter/tests/manifest_store.rs`

**Step 1: Create service-owned persistence**

- Add a dedicated schema or dedicated tables for:
  - transport-enabled nodes
  - manifest versions
  - rollout batches
  - node heartbeat snapshots
  - last known good bundle references
- Do not reuse or mutate `Remnawave` tables directly.

**Step 2: Implement the node registry**

- Sync allowed node metadata from `Remnawave` via public API.
- Store only service-local fields in adapter tables, such as:
  - transport enabled flag
  - rollout channel
  - adapter node label
  - last heartbeat timestamp
  - daemon version

**Step 3: Implement manifest rendering and signing**

- Render desktop-targeted and node-targeted manifests from the shared contract package.
- Sign manifests and record manifest version metadata.
- Require manifest version IDs and rollout IDs in every generated payload.

**Step 4: Expose internal and admin routes**

- `internal` routes for backend-only calls:
  - resolve manifest for entitled user
  - fetch node rollout status
  - fetch client capability defaults
- `admin` routes for service operations:
  - list transport-enabled nodes
  - publish rollout batch
  - pause rollout
  - revoke manifest version

**Step 5: Verify persistence and manifest behavior**

Run:

```bash
cargo test --manifest-path services/private-transport-adapter/Cargo.toml node_registry -- --nocapture
cargo test --manifest-path services/private-transport-adapter/Cargo.toml manifest_store -- --nocapture
```

Expected: PASS with registry persistence, manifest versioning, and signed payload coverage.

**Step 6: Commit**

```bash
git add services/private-transport-adapter
git commit -m "feat(adapter): add registry, manifests, and rollout persistence"
```

---

### Task 4: Integrate the Existing Backend With the Adapter

**Blocked by:** Task 3  
**Unlocks:** Task 6, Task 7, and Task 8

**Files:**
- Modify: `backend/src/config/settings.py`
- Modify: `backend/src/main.py`
- Create: `backend/src/infrastructure/private_transport/__init__.py`
- Create: `backend/src/infrastructure/private_transport/client.py`
- Create: `backend/src/application/services/private_transport_service.py`
- Create: `backend/src/presentation/api/v1/private_transport/__init__.py`
- Create: `backend/src/presentation/api/v1/private_transport/routes.py`
- Create: `backend/src/presentation/api/v1/private_transport/schemas.py`
- Modify: `backend/src/presentation/api/v1/router.py`
- Create: `backend/tests/unit/infrastructure/private_transport/test_client.py`
- Create: `backend/tests/integration/api/v1/private_transport/test_private_transport_routes.py`
- Create: `backend/tests/security/test_private_transport_admin_auth.py`

**Step 1: Add backend configuration and typed client**

- Add settings for:
  - `PRIVATE_TRANSPORT_ENABLED`
  - `PRIVATE_TRANSPORT_ADMIN_ENABLED`
  - `PRIVATE_TRANSPORT_ADAPTER_URL`
  - `PRIVATE_TRANSPORT_ADAPTER_TOKEN`
  - `PRIVATE_TRANSPORT_DEFAULT_CHANNEL`
- Add `backend/src/infrastructure/private_transport/client.py` as an internal HTTP client.

**Step 2: Add service-layer orchestration**

- Add `backend/src/application/services/private_transport_service.py` to:
  - check feature flags
  - verify user entitlement from existing backend/Remnawave data
  - call adapter internal routes
  - shape responses for desktop clients and admins

**Step 3: Add new API routes through the existing backend**

- Add authenticated user routes for desktop manifest resolution and capability retrieval.
- Add admin routes for:
  - rollout visibility
  - node visibility
  - rollout pause/resume
  - manifest revoke
- Add a new OpenAPI tag in `backend/src/main.py`.

**Step 4: Verify auth boundaries**

- Ensure adapter admin functionality is unreachable without existing backend auth and role checks.
- Ensure user routes return nothing when the feature flag is disabled or the user lacks entitlement.

**Step 5: Verify backend integration**

Run:

```bash
pytest backend/tests/unit/infrastructure/private_transport/test_client.py -q
pytest backend/tests/integration/api/v1/private_transport/test_private_transport_routes.py -q
pytest backend/tests/security/test_private_transport_admin_auth.py -q
```

Expected: PASS with correct auth behavior and adapter client contract coverage.

**Step 6: Commit**

```bash
git add backend/src backend/tests
git commit -m "feat(backend): integrate private transport adapter APIs"
```

---

### Task 5: Build the Rust Node Daemon

**Blocked by:** Task 3  
**Unlocks:** Task 6, Task 7, Task 8, and Task 9

**Files:**
- Create: `services/private-transport-node/Cargo.toml`
- Create: `services/private-transport-node/.env.example`
- Create: `services/private-transport-node/Dockerfile`
- Create: `services/private-transport-node/README.md`
- Create: `services/private-transport-node/src/main.rs`
- Create: `services/private-transport-node/src/config.rs`
- Create: `services/private-transport-node/src/error.rs`
- Create: `services/private-transport-node/src/metrics.rs`
- Create: `services/private-transport-node/src/state.rs`
- Create: `services/private-transport-node/src/http/mod.rs`
- Create: `services/private-transport-node/src/http/routes.rs`
- Create: `services/private-transport-node/src/control_plane/client.rs`
- Create: `services/private-transport-node/src/runtime/mod.rs`
- Create: `services/private-transport-node/src/runtime/bundle_store.rs`
- Create: `services/private-transport-node/src/runtime/process_supervisor.rs`
- Create: `services/private-transport-node/src/runtime/health.rs`
- Create: `services/private-transport-node/src/runtime/rollback.rs`
- Create: `services/private-transport-node/tests/config_cycle.rs`
- Create: `services/private-transport-node/tests/rollback.rs`

**Step 1: Bootstrap the daemon lifecycle**

- Add startup config loading and persistent state directory selection.
- Add adapter client config and auth token handling.
- Add local state for:
  - active manifest version
  - pending manifest version
  - last-known-good bundle
  - daemon instance ID

**Step 2: Implement versioned config apply**

- Poll or fetch assigned manifest versions from the adapter.
- Store bundles atomically on disk.
- Apply new config only after validation and health gate success.

**Step 3: Implement health and rollback**

- Expose `/healthz`, `/readyz`, and `/metrics`.
- Track whether the runtime becomes healthy after config application.
- Revert to last known good bundle automatically on failed health gate.

**Step 4: Add tests for the dangerous parts**

- Config apply sequence test.
- Rollback test.
- State restoration test after daemon restart.

**Step 5: Verify the daemon**

Run:

```bash
cargo fmt --manifest-path services/private-transport-node/Cargo.toml --check
cargo clippy --manifest-path services/private-transport-node/Cargo.toml --all-targets -- -D warnings
cargo test --manifest-path services/private-transport-node/Cargo.toml
```

Expected: PASS with rollback and health-gated config apply covered.

**Step 6: Commit**

```bash
git add services/private-transport-node
git commit -m "feat(node): add private transport node daemon with rollback support"
```

---

### Task 6: Add Infra Profiles, Metrics, and Local Lab Support

**Blocked by:** Tasks 3 and 5  
**Unlocks:** Task 8 and Task 9

**Files:**
- Modify: `infra/docker-compose.yml`
- Modify: `infra/docker-compose.dev.yml`
- Modify: `infra/.env.example`
- Modify: `infra/README.md`
- Create: `infra/private-transport/adapter.env.example`
- Create: `infra/private-transport/node.env.example`
- Modify: `infra/prometheus/prometheus.yml`
- Create: `infra/prometheus/rules/private_transport_alerts.yml`
- Create: `infra/grafana/dashboards/private-transport-dashboard.json`
- Modify: `infra/grafana/provisioning/dashboards/dashboards.yml`
- Create: `infra/tests/test_private_transport_stack.sh`

**Step 1: Add optional compose profiles**

- Add a `private-transport` profile for the adapter.
- Add a `private-transport-lab` profile for one local node daemon instance.
- Keep both profiles off by default.

**Step 2: Wire metrics and alerts**

- Scrape adapter and node daemon metrics.
- Add alerts for:
  - stale node heartbeat
  - failed rollout
  - manifest issuance errors
  - repeated rollback events

**Step 3: Document local lab setup**

- Extend `infra/README.md` with a lab section.
- Document how to start:
  - Remnawave
  - backend
  - adapter
  - one local node daemon

**Step 4: Verify the infra wiring**

Run:

```bash
docker compose -f infra/docker-compose.yml config > /tmp/private-transport-compose.out
bash infra/tests/test_private_transport_stack.sh
```

Expected: PASS with valid compose config and metrics endpoints resolving.

**Step 5: Commit**

```bash
git add infra
git commit -m "chore(infra): add private transport lab profiles and monitoring"
```

---

### Task 7: Add the Experimental Desktop Core

**Blocked by:** Tasks 4 and 5  
**Unlocks:** Task 8 and Task 9

**Files:**
- Modify: `apps/desktop-client/src/shared/api/ipc.ts`
- Modify: `apps/desktop-client/src/pages/Settings/index.tsx`
- Create: `apps/desktop-client/src/pages/__tests__/settings-core-selector.test.tsx`
- Modify: `apps/desktop-client/src-tauri/Cargo.toml`
- Modify: `apps/desktop-client/src-tauri/src/lib.rs`
- Modify: `apps/desktop-client/src-tauri/src/ipc/mod.rs`
- Modify: `apps/desktop-client/src-tauri/src/engine/mod.rs`
- Modify: `apps/desktop-client/src-tauri/src/engine/store.rs`
- Modify: `apps/desktop-client/src-tauri/src/engine/manager.rs`
- Modify: `apps/desktop-client/src-tauri/src/engine/provision.rs`
- Create: `apps/desktop-client/src-tauri/src/engine/private_transport/mod.rs`
- Create: `apps/desktop-client/src-tauri/src/engine/private_transport/client.rs`
- Create: `apps/desktop-client/src-tauri/src/engine/private_transport/config.rs`
- Create: `apps/desktop-client/src-tauri/src/engine/private_transport/process.rs`
- Create: `apps/desktop-client/src-tauri/src/engine/private_transport/health.rs`
- Create: `apps/desktop-client/src-tauri/tests/private_transport_core.rs`

**Step 1: Extend the core model cleanly**

- Extend the active core enum from `"sing-box" | "xray"` to include `"private-transport"`.
- Persist the new value in the existing settings store.
- Keep all old values backward-compatible.

**Step 2: Add feature-flagged desktop runtime integration**

- Add adapter manifest retrieval logic.
- Add provisioning or bundled sidecar support for the new runtime.
- Add connect, disconnect, and health checks for the experimental core.

**Step 3: Add explicit fallback behavior**

- If manifest resolution fails, health checks fail, or the runtime exits early, the app must:
  - record the failure reason
  - increment fallback telemetry
  - offer or automatically restore a stable core

**Step 4: Expose the new core in settings only behind a feature flag**

- Update `SettingsPage` to show the experimental core only when the backend capability or local flag allows it.
- Keep the current `sing-box` and `xray` UX unchanged for everyone else.

**Step 5: Verify the desktop integration**

Run:

```bash
npm --prefix apps/desktop-client run build
cargo test --manifest-path apps/desktop-client/src-tauri/Cargo.toml
```

Expected: PASS with the third core selectable in lab mode and fallback tests passing.

**Step 6: Commit**

```bash
git add apps/desktop-client/src apps/desktop-client/src-tauri
git commit -m "feat(desktop): add experimental private transport core"
```

---

### Task 8: Add Worker Automation, Health Audits, and Rollout Jobs

**Blocked by:** Tasks 4, 5, 6, and 7  
**Unlocks:** Task 9 and Task 10

**Files:**
- Modify: `services/task-worker/src/config.py`
- Modify: `services/task-worker/src/utils/constants.py`
- Modify: `services/task-worker/src/schedules/definitions.py`
- Create: `services/task-worker/src/services/private_transport_service.py`
- Create: `services/task-worker/src/tasks/sync/private_transport_rollouts.py`
- Create: `services/task-worker/src/tasks/monitoring/private_transport_health.py`
- Modify: `services/task-worker/src/tasks/__init__.py`
- Create: `services/task-worker/tests/unit/services/test_private_transport_service.py`
- Create: `services/task-worker/tests/unit/tasks/test_private_transport_health.py`

**Step 1: Add adapter client configuration to the worker**

- Add worker settings for adapter URL and auth token.
- Add a small service wrapper for adapter admin and health endpoints.

**Step 2: Add two explicit worker jobs**

- `private_transport_rollouts` for rollout audit and stuck rollout detection.
- `private_transport_health` for stale heartbeat and rollback anomaly detection.

**Step 3: Schedule and alert**

- Wire jobs into `services/task-worker/src/schedules/definitions.py`.
- Add alert hooks through the existing worker notification paths.

**Step 4: Verify worker automation**

Run:

```bash
pytest services/task-worker/tests/unit/services/test_private_transport_service.py -q
pytest services/task-worker/tests/unit/tasks/test_private_transport_health.py -q
```

Expected: PASS with schedule registration and alert thresholds covered.

**Step 5: Commit**

```bash
git add services/task-worker/src services/task-worker/tests
git commit -m "feat(worker): add private transport rollout and health automation"
```

---

### Task 9: Canary Rollout, Rollback Drill, and Go / No-Go Protocol

**Blocked by:** Task 8  
**Unlocks:** Task 10 and any wider beta

**Files:**
- Create: `docs/plans/2026-03-30-private-rust-transport-go-no-go-protocol.md`
- Create: `docs/private_transport/canary-checklist.md`
- Create: `docs/private_transport/node-bootstrap.md`
- Create: `docs/private_transport/rollback-drill.md`
- Modify: `backend/docs/INCIDENT_RESPONSE_RUNBOOK.md`
- Modify: `infra/README.md`

**Step 1: Define the first canary boundary**

- Limit the first rollout to:
  - one staging or lab node
  - one production-like node only after staging is green
  - five internal desktop users max
- Document the exact entry and exit criteria.

**Step 2: Write the rollback drill**

- Define how to disable:
  - backend feature flag
  - adapter rollout channel
  - desktop core selection
  - node daemon manifest assignment
- Require a timed rollback rehearsal before any production canary.

**Step 3: Define the go / no-go rules**

- The new go/no-go doc must gate on:
  - manifest success rate
  - heartbeat freshness
  - desktop connect success rate
  - fallback rate
  - zero unresolved rollback failures

**Step 4: Verify the rollout docs against reality**

- Run one tabletop exercise with backend, desktop, and infra owners.
- Update `backend/docs/INCIDENT_RESPONSE_RUNBOOK.md` with the adapter and node daemon incident trees.

**Step 5: Commit**

```bash
git add docs/private_transport docs/plans/2026-03-30-private-rust-transport-go-no-go-protocol.md backend/docs/INCIDENT_RESPONSE_RUNBOOK.md infra/README.md
git commit -m "docs: add private transport canary and rollback protocol"
```

---

### Task 10: Hardening, Threat Model, and Production Decision Gate

**Blocked by:** Task 9  
**Unlocks:** wider desktop beta and later mobile work

**Files:**
- Create: `docs/security/private-transport-threat-model.md`
- Create: `docs/testing/private-transport-load-test-plan.md`
- Create: `backend/tests/load/test_private_transport_load.py`
- Create: `infra/tests/verify_private_transport_rollback.sh`
- Modify: `docs/secret-rotation.md`
- Modify: `docs/PROJECT_OVERVIEW.md`

**Step 1: Write the threat model**

- Document trust boundaries, secrets, signing keys, internal auth tokens, and rollback authorities.
- Document what is allowed to fail closed and what must fail open to stable cores.

**Step 2: Add load and failure drills**

- Add backend load coverage for manifest resolution.
- Add infra rollback verification script.
- Define resource ceilings for adapter CPU, memory, and node heartbeat fan-out.

**Step 3: Update long-lived project docs**

- Add the private transport platform to `docs/PROJECT_OVERVIEW.md`.
- Extend `docs/secret-rotation.md` with:
  - manifest signing key rotation
  - adapter internal token rotation
  - node bootstrap credential rotation

**Step 4: Run the final decision gate**

Run:

```bash
pytest backend/tests/load/test_private_transport_load.py -q
bash infra/tests/verify_private_transport_rollback.sh
```

Expected: PASS with acceptable latency, successful rollback drill, and no critical gaps in the threat model.

**Step 5: Commit**

```bash
git add docs/security docs/testing backend/tests/load infra/tests docs/secret-rotation.md docs/PROJECT_OVERVIEW.md
git commit -m "docs: add private transport hardening and production gate"
```

---

## Deferred Phase: Mobile Entry Gate

Do not begin mobile implementation until the following are true for at least one full desktop release window:

- desktop connect success rate is acceptable
- fallback rate is stable and low
- node rollout drift is under control
- rollback drill passed on the latest release
- adapter manifest contract is stable for one full release cycle

When that gate opens, the first mobile task should touch only these files and nothing else:

- Modify: `cybervpn_mobile/lib/features/vpn/data/datasources/vpn_engine_datasource.dart`
- Modify: `cybervpn_mobile/lib/features/vpn/data/datasources/xray_config_generator.dart`
- Modify: `cybervpn_mobile/lib/features/vpn/data/repositories/vpn_repository_impl.dart`
- Modify: `cybervpn_mobile/lib/features/vpn/domain/repositories/vpn_repository.dart`
- Modify: `cybervpn_mobile/lib/features/vpn/presentation/providers/vpn_connection_notifier.dart`
- Modify: `cybervpn_mobile/lib/features/vpn/presentation/providers/vpn_connection_provider.dart`
- Create: `cybervpn_mobile/lib/features/vpn/data/datasources/private_transport_datasource.dart`
- Create: `cybervpn_mobile/lib/features/vpn/domain/entities/private_transport_config.dart`
- Create: `cybervpn_mobile/lib/features/vpn/domain/usecases/connect_private_transport.dart`
- Create: `cybervpn_mobile/test/features/vpn/private_transport_connection_test.dart`

## Open Questions To Resolve Before Coding Task 2

1. Will the adapter store state in the existing PostgreSQL instance under a separate schema, or in a separate database?
2. Will the desktop runtime use an embedded Rust module, a bundled sidecar, or a provisioned binary?
3. Will the adapter expose polling, push, or hybrid manifest delivery for node daemons?
4. Which admin roles in the existing backend are allowed to:
   - enable nodes
   - start rollouts
   - revoke manifests
   - trigger rollback
5. What is the minimum production canary size before the first external beta?

## Final Recommendation

If I were running this implementation, I would keep the first release intentionally narrow:

1. Desktop only.
2. One internal rollout channel.
3. One node group.
4. One hard off-switch in backend config.
5. One rollback drill before any public beta.

That path preserves your current business platform, keeps `Remnawave` stable, and gives you a controlled way to evaluate the private transport as a product capability instead of turning it into a repo-wide rewrite.
