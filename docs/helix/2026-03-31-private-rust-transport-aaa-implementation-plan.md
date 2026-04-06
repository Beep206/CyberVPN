# Private Rust Transport Platform AAA+ Implementation Plan

> Internal plan for CyberVPN.
> Keep wire-level transport behavior, censorship-resilience techniques, and fingerprint-avoidance details out of public docs.
> Detailed execution contract: `docs/plans/2026-03-31-private-rust-transport-aaa-execution-document.md`.

## Goal

Add a Helix platform to CyberVPN that is:

- fully compatible with the current `Remnawave` authority model;
- integrated first into the desktop app only;
- competitive with `VLESS` and `XHTTP` on stability and user-perceived speed;
- resilient when baseline transports are degraded or selectively blocked;
- safe to roll out, pause, revoke, and roll back at any time.

## Executive Position

This plan does **not** reduce the ambition of the product. It raises the quality bar and makes the implementation path more explicit:

- `desktop-first` remains correct;
- `Remnawave-authoritative` remains correct;
- `adapter + node daemon + backend facade + desktop runtime` remains correct;
- the plan now explicitly optimizes for `AAA+` transport quality, benchmarked competitiveness, multi-channel rollout, and stronger node/Desktop operability.

---

## Product Standard: AAA+

The Helix can only be promoted if it meets all four dimensions below.

### 1. Competitive User Experience

- Connect time must stay within an acceptable delta from the current best baseline transport.
- Throughput must remain within an acceptable band of baseline in the same region and node class.
- Session continuity must be at least as good as baseline under normal network conditions.
- Failures must be visible, attributable, and recoverable.

### 2. Resilience Under Pressure

- The platform must remain viable when baseline transports are partially blocked or degrade materially.
- Resilience must come from transport agility, rapid policy rotation, capability-aware manifests, and active black-box monitoring.
- Sensitive resilience techniques must live in restricted internal design material, not in general project documentation.

### 3. Operational Safety

- Every rollout action must be reversible.
- Every bundle must be traceable.
- Every node must have last-known-good restore.
- Every desktop failure must have safe fallback behavior.

### 4. Platform Fit

- `Remnawave` remains authoritative.
- The FastAPI backend remains the authenticated facade.
- Desktop is the only client in phase one.
- Current `xray` and `sing-box` operations remain intact and serviceable throughout the rollout.

---

## Locked Architecture Decisions

### Decision 1: Source of Truth

`Remnawave` remains the source of truth for:

- users;
- plans and subscriptions;
- billing entitlements;
- node inventory.

Transport-specific state is stored outside `Remnawave` tables.

### Decision 2: Control Plane

Create `services/helix-adapter` as a dedicated Rust service that owns:

- manifest issuance;
- manifest version registry;
- node capability registry;
- rollout channels and batches;
- health aggregation;
- service-local policy state.

### Decision 3: Node Runtime

Create `services/helix-node` as a Rust daemon that:

- runs only on selected nodes;
- fetches and validates transport assignments;
- applies bundles atomically;
- reports health and metrics;
- restores last-known-good automatically on failure.

### Decision 4: Backend Mediation

The FastAPI backend remains the only authenticated public facade for:

- desktop manifest resolution;
- client capability discovery;
- admin rollout controls;
- rollout visibility.

### Decision 5: Desktop Runtime Packaging

The private runtime is shipped as a **bundled, signed desktop sidecar** for deterministic compatibility, with a reserved emergency hotfix path for urgent transport-runtime updates.

### Decision 6: Persistence Model

Phase one uses the existing PostgreSQL deployment with a dedicated schema:

```text
helix.*
```

This is faster to operate than a separate database while preserving ownership boundaries.

### Decision 7: Manifest Delivery Model

Manifest delivery is **hybrid**:

- version checks and controlled refresh via cache-aware polling or long-poll style requests;
- rapid invalidate/revoke path for emergency withdrawal and rollback control.

### Decision 8: Rollout Topology

Rollout channels are present from the start:

- `lab`
- `canary`
- `stable`

Node groups are explicit from the start:

- `lab`
- `prod-like`
- `regional`

---

## Quality Gates and Promotion Rules

Promotion between rollout channels is blocked unless all relevant gates are green.

### Performance Gates

- Median connect time no worse than `5%` slower than the best baseline transport.
- `p95` connect time no worse than `15%` slower than baseline.
- Median throughput ratio vs baseline `>= 0.95`.
- Added steady-state latency overhead must remain below the product threshold for “not perceptibly slower”.

### Reliability Gates

- Clean-network desktop connect success `>= 99.5%`.
- Challenged-network connect success in canary `>= 98.0%`.
- Unexpected disconnect rate no worse than baseline.
- Desktop fallback rate below the channel threshold.

### Control-Plane Gates

- Manifest issuance and resolve latency inside SLA.
- Node heartbeat freshness inside SLA.
- Rollout-state reporting consistent and auditable.
- Rollback recovery drilled and within target recovery time.

### Release Discipline Gates

- No promotion without successful rollback rehearsal.
- No promotion without benchmark evidence across multiple network conditions.
- No promotion without alerts, dashboards, and runbooks.
- No promotion while there are unresolved rollback defects or unexplained fallback spikes.

---

## Scope

### In Scope

- New Rust adapter service.
- New Rust node daemon.
- Shared contract package for manifests, node health, client capabilities, benchmark reports, and rollout metadata.
- Backend integration for desktop and admin flows.
- Desktop runtime integration in `apps/desktop-client`.
- Infra, telemetry, canary control, rollback drills, and performance harnesses.

### Explicitly Out of Scope in Phase One

- Deep `Remnawave` fork.
- Mobile implementation.
- Public protocol whitepaper.
- Replacing `xray` or `sing-box` as the default user path for the whole platform.

---

## Revised Repository Targets

```text
backend/
  src/
    infrastructure/helix/
    application/services/helix_service.py
    presentation/api/v1/helix/

services/
  helix-adapter/
  helix-node/
  task-worker/

packages/
  helix-contract/

apps/
  desktop-client/
    src/
    src-tauri/

docs/
  helix/
  plans/
  security/
  testing/

infra/
  helix/
  prometheus/
  grafana/
```

---

## Phase Windows

These are realistic engineering windows for a high-quality delivery path, not best-case optimism.

1. Phase 0: Product guardrails, benchmark model, and restricted resilience governance — `4-6 days`
2. Phase 1: Contracts and architecture source of truth — `4-6 days`
3. Phase 2: Adapter service skeleton — `5-8 days`
4. Phase 3: Adapter persistence, signing, registry, and rollout policy — `6-10 days`
5. Phase 4: Node daemon and host integration — `8-12 days`
6. Phase 5: Backend integration and entitlement mediation — `5-8 days`
7. Phase 6: Lab harness, benchmark framework, and observability baseline — `6-9 days`
8. Phase 7: Desktop runtime integration and fallback hardening — `8-12 days`
9. Phase 8: Worker automation, audits, and rollout controls — `4-7 days`
10. Phase 9: Multi-channel canary, rollback drills, and go/no-go — `5-8 days`
11. Phase 10: Hardening, threat model, and production decision gate — `5-8 days`

Total realistic window: `60-94 working days`, depending on team size, parallelization, and how much new runtime behavior is required.

---

## Phase 0: Product Guardrails, Benchmark Model, and Restricted Resilience Governance

**Outcome:** The project starts with a real quality bar, not vague ambition.

### Primary Paths

- `docs/helix/README.md`
- `docs/helix/benchmarking.md`
- `docs/helix/compatibility-matrix.md`
- `docs/testing/helix-benchmark-plan.md`
- `docs/security/helix-restricted-governance.md`

### Required Work

- Define the benchmark methodology against `VLESS` and `XHTTP` baselines.
- Define what “not slower” means in measurable terms.
- Define the compatibility matrix for desktop OS versions, node classes, and rollout channels.
- Define restricted-governance rules for sensitive anti-blocking internals.
- Define release-blocking thresholds for connect success, disconnect rate, fallback rate, and rollback failures.

### Gate

No service code starts until the benchmark model, compatibility matrix, and release thresholds are written down.

---

## Phase 1: Contracts and Architecture Source of Truth

**Outcome:** The transport platform has a shared contract surface and explicit service boundaries.

### Primary Paths

- `docs/helix/architecture.md`
- `docs/helix/contracts.md`
- `packages/helix-contract/`

### Required Work

- Create versioned contracts for:
  - desktop manifests;
  - node assignment bundles;
  - node heartbeat;
  - client capabilities;
  - benchmark reports;
  - rollout state snapshots.
- Add JSON Schemas and example fixtures.
- Add validation tooling so contract drift is caught before service integration.

### Gate

All fixture contracts must validate successfully before Task 2.

---

## Phase 2: Adapter Service Skeleton

**Outcome:** A production-shaped Rust service exists before business logic expands.

### Primary Paths

- `services/helix-adapter/`

### Required Work

- Scaffold `axum` service with:
  - `/healthz`
  - `/readyz`
  - `/metrics`
- Add configuration loading, structured logging, graceful shutdown, and tracing hooks.
- Add a read-only `Remnawave` client wrapper for node inventory reads.
- Add config for:
  - bind address;
  - Remnawave URL and token;
  - database URL;
  - internal backend-to-adapter auth;
  - manifest signing placeholders;
  - metrics namespace.

### Gate

`cargo fmt`, `cargo clippy -D warnings`, and service tests must pass before persistence work begins.

---

## Phase 3: Adapter Persistence, Signing, Registry, and Rollout Policy

**Outcome:** The adapter becomes the authoritative control plane for Helix state.

### Primary Paths

- `services/helix-adapter/migrations/`
- `services/helix-adapter/src/db/`
- `services/helix-adapter/src/node_registry/`
- `services/helix-adapter/src/manifests/`
- `services/helix-adapter/src/http/routes/`

### Required Work

- Add dedicated persistence for:
  - transport-enabled nodes;
  - rollout channels;
  - rollout batches;
  - manifest versions;
  - node heartbeat snapshots;
  - last-known-good bundle references;
  - revoke and pause state.
- Implement node registry sync from `Remnawave` inventory.
- Render desktop and node manifests from shared contracts.
- Sign manifests and record signing metadata.
- Add admin and internal routes for:
  - resolve desktop manifest;
  - fetch rollout status;
  - list transport-enabled nodes;
  - publish, pause, resume, revoke, and roll back rollout actions.

### Gate

No backend or desktop integration before signed payload flow, versioning, and revoke behavior are covered by tests.

---

## Phase 4: Node Daemon and Host Integration

**Outcome:** Selected nodes can safely run and recover the Helix runtime without destabilizing existing service ownership.

### Primary Paths

- `services/helix-node/`
- `infra/helix/`
- `docs/helix/node-operations.md`

### Required Work

- Implement daemon config loading and persistent state directory layout.
- Add adapter client auth and assignment fetch logic.
- Store:
  - active bundle version;
  - pending bundle version;
  - last-known-good bundle;
  - daemon instance ID.
- Apply config bundles atomically.
- Health-gate every new bundle before promotion.
- Auto-restore last-known-good on failed health gate.
- Expose `/healthz`, `/readyz`, and `/metrics`.
- Define node-side ownership boundaries so the daemon does not interfere with Remnawave-managed services.

### Gate

No desktop manifest consumption until rollback, state restore, and health-gated apply are proven in tests and lab runs.

---

## Phase 5: Backend Integration and Entitlement Mediation

**Outcome:** The authenticated backend becomes the trusted facade for user and admin helix flows.

### Primary Paths

- `backend/src/infrastructure/helix/`
- `backend/src/application/services/helix_service.py`
- `backend/src/presentation/api/v1/helix/`
- `backend/tests/unit/infrastructure/helix/`
- `backend/tests/integration/api/v1/helix/`
- `backend/tests/security/`

### Required Work

- Add feature flags and settings for:
  - Helix enablement;
  - admin enablement;
  - adapter URL and token;
  - default rollout channel.
- Add a typed adapter client.
- Add orchestration service for entitlement checks, capability shaping, and manifest resolution.
- Add authenticated desktop routes and admin routes.
- Enforce role boundaries for:
  - node enablement;
  - rollout publish;
  - manifest revoke;
  - rollback authority.

### Role Recommendation

- `super-admin`: rollout publish, revoke, forced rollback.
- `ops-admin`: node enable/disable, pause/resume, visibility.
- `read-only-ops`: visibility only.

### Gate

Adapter admin functionality must remain unreachable without backend auth and explicit role checks.

---

## Phase 6: Lab Harness, Benchmark Framework, and Observability Baseline

**Outcome:** The team can prove the transport is competitive and observable before broader user exposure.

### Primary Paths

- `infra/docker-compose.yml`
- `infra/docker-compose.dev.yml`
- `infra/prometheus/`
- `infra/grafana/`
- `infra/tests/`
- `docs/testing/helix-benchmark-plan.md`

### Required Work

- Add optional compose profiles for:
  - adapter;
  - one local node daemon;
  - benchmark harness support.
- Wire Prometheus scrapes and alerts for:
  - stale heartbeat;
  - rollout failures;
  - manifest issuance failures;
  - repeated rollback;
  - desktop fallback spikes.
- Build the benchmark harness that compares:
  - connect time;
  - connect success;
  - throughput;
  - session continuity;
  - fallback behavior;
  - recovery time.

### Gate

No user-facing desktop exposure until benchmark collection and dashboards exist.

---

## Phase 7: Desktop Runtime Integration and Fallback Hardening

**Outcome:** The desktop app can run the Helix as a first-class runtime while protecting user experience.

### Primary Paths

- `apps/desktop-client/src/shared/api/ipc.ts`
- `apps/desktop-client/src/pages/Settings/`
- `apps/desktop-client/src-tauri/src/engine/`
- `apps/desktop-client/src-tauri/tests/`

### Required Work

- Extend the core model cleanly to include `helix`.
- Add capability-aware settings visibility.
- Add manifest retrieval and verification.
- Add bundled sidecar provisioning and version checks.
- Add connect/disconnect/status logic for the private runtime.
- Add health scoring, early-failure detection, and safe restore to stable core.
- Record structured failure reasons and fallback telemetry.

### Important Reality Check

This is not a UI-only task. The current desktop engine model is already multi-core at the setting level, but runtime orchestration is still centered around existing binaries and process assumptions. Plan for real Rust-side refactoring here, not just additional enum values.

### Gate

No canary until the desktop runtime passes integration tests and demonstrates safe recovery from startup failure, manifest failure, and unhealthy runtime exit.

---

## Phase 8: Worker Automation, Audits, and Rollout Controls

**Outcome:** Rollouts and health anomalies are continuously audited, not manually watched.

### Primary Paths

- `services/task-worker/src/`
- `services/task-worker/tests/`

### Required Work

- Add adapter client configuration to the worker.
- Add scheduled jobs for:
  - rollout audit;
  - stale-heartbeat detection;
  - rollback anomaly detection;
  - manifest error trend detection.
- Feed alerts into the current notification path.

### Gate

No stable-channel promotion until automation catches stuck rollouts and repeated rollback events.

---

## Phase 9: Multi-Channel Canary, Rollback Drills, and Go/No-Go

**Outcome:** Promotion is based on disciplined evidence rather than optimism.

### Primary Paths

- `docs/plans/2026-03-31-private-rust-transport-aaa-implementation-plan.md`
- `docs/helix/canary-checklist.md`
- `docs/helix/rollback-drill.md`
- `backend/docs/INCIDENT_RESPONSE_RUNBOOK.md`

### Required Work

- Define entry and exit criteria for:
  - `lab`
  - `canary`
  - `stable`
- Require rollback drill before every promotion step.
- Define go/no-go gates around:
  - manifest success rate;
  - heartbeat freshness;
  - desktop connect success;
  - throughput ratio vs baseline;
  - fallback rate;
  - unresolved rollback failures.

### Minimum Canary Recommendation

- `1` lab node;
- `2` production-like nodes in distinct groups;
- `20` internal desktop users across varied network conditions;
- explicit pause authority and rollback ownership.

### Gate

No external beta until canary metrics stay green for one full release window.

---

## Phase 10: Hardening, Threat Model, and Production Decision Gate

**Outcome:** The platform is either production-ready or intentionally held back with evidence.

### Primary Paths

- `docs/security/helix-threat-model.md`
- `docs/testing/helix-load-test-plan.md`
- `backend/tests/load/test_helix_load.py`
- `infra/tests/verify_helix_rollback.sh`
- `docs/secret-rotation.md`
- `docs/PROJECT_OVERVIEW.md`

### Required Work

- Document trust boundaries, key custody, token rotation, rollback authorities, and fail-open/fail-closed decisions.
- Add backend load coverage for manifest resolution and control-plane stress behavior.
- Add rollback verification scripts and release gates.
- Update long-lived project docs for:
  - signing key rotation;
  - adapter internal token rotation;
  - node bootstrap credential rotation;
  - Helix architecture placement in the platform.

### Gate

No stable channel until threat model, rollback drill, and load gates are all green.

---

## Recommended Metrics

- `helix_manifest_issued_total`
- `helix_manifest_resolve_latency_ms`
- `helix_manifest_revoke_total`
- `helix_rollout_batch_publish_total`
- `helix_rollout_failed_total`
- `helix_node_heartbeat_stale_total`
- `helix_config_apply_duration_seconds`
- `helix_last_known_good_restore_total`
- `helix_desktop_connect_success_rate`
- `helix_desktop_connect_duration_ms`
- `helix_desktop_unexpected_disconnect_total`
- `helix_desktop_fallback_total`
- `helix_desktop_fallback_reason_total`
- `helix_throughput_ratio_vs_baseline`

---

## Success Criteria

- A privileged admin can see node capability, rollout state, benchmark health, and rollback posture through the backend.
- The adapter can resolve an entitled desktop user to a signed manifest without mutating `Remnawave`.
- Selected nodes can fetch, apply, validate, and roll back versioned bundles safely.
- The desktop app can opt into the private runtime behind capability and feature gates and recover automatically to a stable core when necessary.
- The platform remains operationally manageable through `lab`, `canary`, and `stable` channels.
- The transport demonstrates benchmark competitiveness and resilience across the defined network test matrix.

---

## Deferred Mobile Gate

Do not start mobile until all of the following remain true for at least one full desktop release window:

- connect success remains within the accepted range;
- fallback rate remains low and stable;
- throughput ratio vs baseline remains acceptable;
- node rollout drift is controlled;
- rollback drill passes on the latest release;
- manifest and capability contracts remain stable across one full release cycle.

---

## Final Recommendation

Build this as a premium transport platform, not as an isolated protocol experiment.

That means:

- keep `Remnawave` authoritative;
- make desktop the proving ground;
- make node rollback and desktop recovery mandatory from day one;
- benchmark relentlessly against `VLESS` and `XHTTP`;
- keep sensitive resilience mechanics private;
- refuse promotion until the Helix earns the right to be considered the best path in the environments that matter.
