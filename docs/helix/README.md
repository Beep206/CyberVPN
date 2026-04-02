# Helix Platform

> Internal architecture and product-quality source of truth for CyberVPN Helix.
> Do not publish wire-level protocol behavior or censorship-resilience internals in public-facing docs.

## Mission

CyberVPN is building a Helix platform that must be:

- stable enough for daily use as a premium desktop feature;
- competitive with, and in target conditions better than, the current `VLESS` and `XHTTP` baselines on connect success, latency stability, and session continuity;
- compatible with the current `Remnawave` operational model and existing node estate;
- resilient to partial blocking, fingerprint pressure, or degradation that may affect baseline transports;
- reversible at every layer without breaking the current `xray` or `sing-box` user experience.

This initiative is **desktop-first**, not because quality is reduced, but because the desktop client is the safest place to establish a high-confidence runtime, telemetry model, rollback discipline, and transport-quality bar before mobile is considered.

---

## Document Map

- `docs/helix/README.md`: source of truth for mission, invariants, and locked planning decisions
- `docs/helix/benchmarking.md`: benchmark topology, metric definitions, and pass/fail thresholds
- `docs/helix/compatibility-matrix.md`: desktop, node, and rollout channel support matrix
- `docs/helix/decision-log.md`: frozen architecture decisions and approval state
- `docs/helix/release-gates.md`: promotion rules for `lab`, `canary`, and `stable`
- `docs/helix/slo-sla.md`: metric ownership, escalation, and phase expectations
- `docs/helix/architecture.md`: component boundaries and runtime flows
- `docs/helix/contracts.md`: shared contract definitions and lifecycle semantics
- `docs/helix/protocol-agility.md`: adaptability rules for profile rotation, compatibility windows, and fast response to blocking pressure
- `docs/helix/agent-handoff-and-roadmap.md`: current implementation snapshot, handoff context, and phased roadmap to internal beta and release
- `docs/testing/helix-benchmark-plan.md`: repeatable benchmark scenarios and reporting format
- `docs/security/helix-restricted-governance.md`: storage and access rules for restricted transport internals
- `docs/plans/2026-03-31-private-rust-transport-aaa-implementation-plan.md`: strategic implementation plan
- `docs/plans/2026-03-31-private-rust-transport-aaa-execution-document.md`: hard execution contract

---

## AAA+ Product Standard

For this project, `AAA+` means the transport is treated as a premium system capability, not an experiment hidden behind a switch.

### `A1` Availability and Stability

- No rollout without versioned manifests, rollback hooks, and last-known-good restore.
- No release if session interruption rate, fallback rate, or apply-failure rate exceed baseline guardrails.
- No node update without health-gated apply and automatic recovery.

### `A2` Anti-Blocking Continuity

- The platform must continue to operate when current mainstream transports are partially degraded or selectively blocked.
- Transport agility, capability negotiation, rollout rotation, and path-quality monitoring are first-class requirements.
- Specific resilience techniques stay in restricted internal materials, not in public docs or user-facing copy.

### `A2.1` Fast Adaptation Requirement

- The transport must be updateable primarily through profile, policy, and manifest evolution before binary replacement is required.
- The control plane must support quick revoke, quick profile rotation, and controlled compatibility overlap between current and candidate transport profiles.
- A future change that needs a repo-wide rewrite for a config-level transport adjustment is considered an architecture failure.

### `A3` Adaptability and Operability

- The system must fit the current CyberVPN platform without forcing a deep fork of `Remnawave`.
- Operations must be observable: manifests, rollout batches, health state, node capabilities, desktop runtime failures, and fallback reasons all need first-class telemetry.
- Admins need controlled rollout channels, explicit pause/resume, revoke, and rollback authority.

### `+` Controlled Excellence

- Release quality is measured against baselines, not gut feel.
- Cross-region benchmark evidence is required before promotion between channels.
- Desktop users must always retain a hard recovery path to stable cores.

---

## Non-Negotiable Constraints

- `Remnawave` remains the source of truth for users, subscriptions, plans, billing entitlements, and base node inventory.
- Transport-specific state must live in service-owned tables or a dedicated schema, not in `Remnawave` tables.
- Phase one stays `desktop-only`; mobile work remains blocked until desktop proves stable across at least one full release window.
- The FastAPI backend remains the authenticated public facade for admin and user flows.
- Adapter admin routes are never exposed directly to the public Internet.
- Every manifest is versioned, signed, and traceable to a rollout ID.
- Every node rollout supports last-known-good restore.
- Every desktop failure mode must prefer safe recovery over silent degradation.

---

## Product Quality Gates

The Helix is not considered promotion-ready unless the following are met in the target environment and compared against the current best baseline transport on the same nodes and regions.

### Performance Gates

- Median connect time must not be more than `5%` slower than baseline.
- `p95` connect time must not be more than `15%` slower than baseline.
- Median throughput must stay at or above `95%` of baseline.
- Added steady-state latency overhead should remain small enough that users do not perceive the transport as slower under normal conditions.

### Reliability Gates

- Desktop connect success rate in clean networks: `>= 99.5%`.
- Desktop connect success rate in challenged networks during canary: `>= 98.0%`.
- Unexpected disconnect rate must be no worse than baseline.
- Desktop fallback rate must remain below the release threshold for the target channel.

### Control-Plane Gates

- Manifest resolve `p95` must be within an internal SLA for the rollout region.
- Node heartbeat freshness and rollout-state accuracy must remain within the defined operational threshold.
- Rollback recovery time must stay bounded and rehearsed.

### Operational Gates

- No promotion without successful rollback rehearsal.
- No promotion without benchmark evidence across multiple network conditions.
- No promotion without dashboard coverage, alerting, and incident runbooks.

---

## Architecture Principles

### 1. Keep Remnawave Authoritative

`Remnawave` stays authoritative for:

- users;
- subscriptions and plans;
- billing entitlements;
- node inventory;
- current mainstream transport operations.

The Helix platform layers on top of that authority instead of replacing it.

### 2. Introduce a Dedicated Control Plane

A new `helix-adapter` service owns:

- transport manifests;
- node capability registry;
- rollout policy and channels;
- manifest signing metadata;
- health aggregation;
- transport-specific service state.
- transport profile selection and compatibility filtering.

### 3. Introduce a Dedicated Node Daemon

A new `helix-node` Rust daemon runs only on selected nodes and is responsible for:

- fetching versioned assignments;
- applying config bundles atomically;
- validating runtime health;
- restoring last-known-good on failure;
- exposing `/healthz`, `/readyz`, and `/metrics`.

### 4. Keep the Backend as the Public API Facade

The FastAPI backend remains the only authenticated facade for:

- desktop manifest resolution;
- capability discovery;
- admin visibility and rollout controls.

### 5. Treat Desktop as a Premium Runtime

The Tauri desktop client must:

- support the Helix behind capability and feature gates;
- retrieve manifests safely;
- supervise the private runtime;
- track health and fallback reason codes;
- restore a stable core when the experimental core is unhealthy.
- support profile-driven adaptation rather than assuming one immutable transport behavior.

---

## Compatibility Rules

### With Remnawave

- Read-only inventory sync in phase one.
- Service-local metadata only in adapter-owned storage.
- No mutation of `Remnawave` core tables for transport-specific rollout state.

### With Nodes

- The node daemon must coexist with current Remnawave-managed node services.
- Port allocation, process ownership, file paths, and firewall policy must stay isolated.
- Node bootstrap and rollback must not interfere with current baseline transport availability.

### With Desktop

- The private runtime must fit the existing Tauri process-management model without weakening current `sing-box` and `xray` support.
- Core selection, health, logs, and recovery must be unified under one desktop runtime contract.

---

## Locked Decisions For Planning

These decisions are fixed unless the architecture document is formally revised.

- Adapter state uses the existing PostgreSQL instance under a dedicated `helix` schema in phase one.
- Desktop runtime is shipped as a **bundled, signed sidecar** with an emergency hotfix path reserved for urgent compatibility updates.
- Manifest delivery is **hybrid**: cache-friendly version checks and long-poll style refresh for normal operation, plus a fast invalidate/revoke path for emergency control actions.
- Protocol adaptability is **profile-driven**: the manifest contract must evolve toward `transport_profile_id`, `policy_version`, and compatibility-window semantics so transport changes can be rolled out faster than full binary replacement cycles.
- Rollout topology is **multi-channel** from the start: `lab`, `canary`, and `stable`.
- Node grouping is explicit from the start: `lab`, `prod-like`, and `regional` groups are managed separately.

---

## What Phase One Is Not

Phase one is not:

- a deep `Remnawave` fork;
- a public protocol whitepaper;
- a mass migration of all users;
- a mobile release;
- a downgrade in quality expectations in exchange for speed.

Phase one is the foundation for a transport platform that can become a market-level differentiator without destabilizing the current business platform.

---

## Current Build Order

The active implementation order is:

1. `Phase 0`: freeze benchmark rules, compatibility limits, release gates, and restricted governance
2. `Phase 1`: create versioned contracts, examples, and validation tooling
3. `Phase 2+`: service code starts only after `Phase 0` and `Phase 1` are complete
