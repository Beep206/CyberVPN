# CyberVPN Platform Foundation P3.8 Production Control-Plane Cutover Execution Packet

**Date:** 2026-04-23  
**Status:** implementation in progress; repo foundation slice complete, live production cutover evidence pending  
**Packet:** `P3.8`  
**Primary owners:** `infra-platform` / `backend-platform`  
**Supporting owners:** `sre-platform`, `security`, `data-platform`, `docs-program`

---

## 1. Packet Role

This document is the execution packet for `P3.8` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [2026-04-22-platform-foundation-p2-8-initial-control-plane-workload-migration-execution-packet.md](2026-04-22-platform-foundation-p2-8-initial-control-plane-workload-migration-execution-packet.md)
- [2026-04-22-platform-foundation-p2-9-prod-mgmt-foundation-execution-packet.md](2026-04-22-platform-foundation-p2-9-prod-mgmt-foundation-execution-packet.md)
- [../api/platform-foundation-production-control-plane-cutover-spec.md](../api/platform-foundation-production-control-plane-cutover-spec.md)
- [../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md](../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md)

`P3.8` exists to freeze the first production GitOps-managed Kubernetes target state for
CyberVPN control-plane workloads:

- `backend`
- `task-worker`
- `task-scheduler`

with the following production prerequisites represented in Git:

- `Flux`-managed reconciliation
- `Flagger` progressive delivery
- `Gateway API` routing attachment
- `CloudNativePG` database runtime
- backup contract
- alerting contract

Implementation note:

- this packet is executed as a pre-launch `repo/validation` slice because no live
  `prod-mgmt`, no live production workload cluster, no live Cloudflare cutover, and no
  live production Flux reconciliation exist in the current session;
- the repository slice is implemented and locally validated;
- the remaining closure work is real production cluster reconciliation, canary promotion
  and rollback proof, CNPG and backup proof, and deploy or rollback evidence.

---

## 2. Current Baseline

Before this packet:

- `P2.8` froze the first non-prod runtime contract for:
  - `backend`
  - `task-worker`
  - `task-scheduler`
- `P2.9` froze the production management-cluster substrate under `prod-mgmt`;
- `P2.2`, `P2.4`, and `P2.5` froze the non-prod platform-services, data-protection, and
  application-delivery contracts that production now has to inherit rather than redefine;
- `P3.1` through `P3.5` established the first external fleet-control-loop slices but did
  not change the first production control-plane workload set.

Observed strengths:

- the first runtime set is already deliberately narrow and matches the target-state order;
- source-repo chart and GitOps delivery contracts already exist for the first workload set;
- management-cluster naming and provider-L4 substrate are already frozen for production.

Observed implementation risks:

- production cutover could drift back to legacy Ansible or host rollout memory if no
  production GitOps contract is frozen now;
- progressive delivery could become ad hoc without an explicit Flagger plus Gateway API
  baseline;
- CloudNativePG monitoring could inherit deprecated automatic `enablePodMonitor`
  behavior unless production monitoring ownership is made explicit now;
- production alerting can silently lag cutover unless it is rendered into the same packet
  instead of being left to manual follow-up.

---

## 3. Canonical Decisions For P3.8

`P3.8` fixes the following decisions:

1. The first production workload cluster is `prod-hetzner-fsn1-core`.
2. The management authority for that production runtime remains `prod-mgmt`.
3. The first production runtime set is still:
   - `backend`
   - `task-worker`
   - `task-scheduler`
4. The backend is the only first-wave progressive workload in this packet.
5. Progressive delivery is implemented with:
   - `Flagger`
   - `Gateway API`
6. Production database runtime authority for the first cutover wave is:
   - `CloudNativePG`
7. Production CloudNativePG monitoring uses a manually managed `PodMonitor`, not operator
   auto-generated `enablePodMonitor`.
8. Production backup contract is represented by a Git-managed `ScheduledBackup`.
9. Production control-plane alerting is Git-managed and attached to the same packet.
10. Legacy host-based production rollout must not be treated as the production source of
    truth for this packet.

---

## 4. Scope

In scope for `P3.8`:

- add a canonical helper under [infra/scripts/prod_control_plane_cutover.py](../../infra/scripts/prod_control_plane_cutover.py);
- add unit coverage for the helper;
- add a canonical production cutover spec under
  [../api/platform-foundation-production-control-plane-cutover-spec.md](../api/platform-foundation-production-control-plane-cutover-spec.md);
- render `platform-gitops` scaffold for:
  - production progressive-delivery substrate
  - production data-runtime substrate
  - production observability and alerting substrate
  - production app namespace and workload releases
- update operator docs so the helper is discoverable from `infra/README.md`;
- record packet evidence and formal carry-forward residual.

Out of scope for the current repository slice executed in this workspace:

- live `prod-mgmt` or workload-cluster creation;
- live Flux reconciliation on production clusters;
- live Cloudflare or provider-L4 traffic cutover;
- live `Flagger` canary promotion or rollback;
- live CNPG bootstrap, backup, or restore proof;
- live deployment or rollback evidence for the production runtime set.

---

## 5. Official Constraints

The execution of `P3.8` follows current primary-source guidance:

- Flagger supports progressive delivery with `Gateway API` and a `Canary` resource that
  references `gatewayRefs`, rollout metrics, and threshold controls;
- Flagger supports weighted canary analysis and rollback based on HTTP metrics and canary
  analysis thresholds;
- CloudNativePG currently recommends manually managed `PodMonitor` resources and marks
  `.spec.monitoring.enablePodMonitor` as deprecated;
- CloudNativePG uses `ScheduledBackup` as the canonical scheduled-backup resource;
- Flux remains the Helm-based reconciliation substrate for chart-driven releases.

Primary sources:

- Flagger Gateway API progressive delivery:
  https://docs.flagger.app/main/tutorials/gatewayapi-progressive-delivery
- Flagger deployment strategies:
  https://docs.flagger.app/main/usage/deployment-strategies
- CloudNativePG monitoring:
  https://cloudnative-pg.io/docs/1.29/monitoring/
- CloudNativePG backup:
  https://cloudnative-pg.io/docs/1.28/backup
- Flux Helm controller:
  https://fluxcd.io/flux/components/helm/

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P3.8`:

### 6.1 Helper And Tests

- [infra/scripts/prod_control_plane_cutover.py](../../infra/scripts/prod_control_plane_cutover.py)
- [infra/tests/test_prod_control_plane_cutover.py](../../infra/tests/test_prod_control_plane_cutover.py)

### 6.2 Canonical Spec

- [../api/platform-foundation-production-control-plane-cutover-spec.md](../api/platform-foundation-production-control-plane-cutover-spec.md)

### 6.3 Operator Docs

- [infra/README.md](../../infra/README.md)

### 6.4 Packet Evidence

- [../evidence/platform-foundation/2026-04-23/p3-8-production-control-plane-cutover/evidence-pack.md](../evidence/platform-foundation/2026-04-23/p3-8-production-control-plane-cutover/evidence-pack.md)

---

## 7. Workboard

### 7.1 `T3.8.1` Freeze The Production Cutover Boundary

**Goal:** stop production control-plane cutover from drifting into legacy authority or
unowned scope.

Deliverables:

- canonical production workload cluster id
- canonical production runtime set
- explicit production exclusions
- explicit source-of-truth boundary for production rollout

Acceptance criteria:

- production cluster and management-cluster ids are frozen in one canonical spec;
- the first production runtime set is explicit;
- legacy production rollout authority is explicitly disallowed as a silent fallback.

### 7.2 `T3.8.2` Freeze Progressive Delivery And Routing

**Goal:** make the first production backend rollout progressive by contract, not by future
operator improvisation.

Deliverables:

- `Flagger` installation scaffold
- `Gateway API` provider baseline
- backend `Canary` resource scaffold
- production routing references for the public gateway

Acceptance criteria:

- the first progressive workload is explicit;
- canary analysis and rollback thresholds are represented in Git;
- gateway attachment is explicit rather than left to operator memory.

### 7.3 `T3.8.3` Freeze Production Data, Backup, And Alerting Prerequisites

**Goal:** represent the production prerequisites required for a real control-plane cutover.

Deliverables:

- `CloudNativePG` production cluster scaffold
- manual `PodMonitor`
- `ScheduledBackup`
- production control-plane `PrometheusRule`

Acceptance criteria:

- production data authority is explicit;
- deprecated automatic monitoring ownership is not relied upon;
- alerting and backup are represented in the same packet as the cutover contract.

### 7.4 `T3.8.4` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable without faking live production evidence.

Deliverables:

- helper unit tests
- local render smoke
- local validation command
- packet evidence pack
- formal carry-forward residual for missing live production cutover evidence

Acceptance criteria:

- repository slice is locally validated;
- live closure requirements are explicit;
- later `P3` work may proceed without pretending production cutover is already operational.

---

## 8. State-Boundary Rules

`P3.8` must keep the following invariants:

1. `platform-gitops` remains the production desired-state authority.
2. Legacy host-based rollout files must not become the production truth for this packet.
3. The first production workload set remains narrow and does not silently absorb fleet or
   adapter workloads.
4. Production database authority for this cutover packet is `CloudNativePG`.
5. Production alerting belongs in Git and is not a post-cutover memory task.
6. `P3.8` must not claim any live production rollout success from repository-only work.

---

## 9. Exit Conditions

`P3.8` may move from repo-slice complete to packet complete only when:

- production Flux reconciliation evidence exists for the rendered cutover surfaces;
- `Flagger` proves a real production backend promotion and rollback path;
- production `CloudNativePG`, backup, and alerting evidence exists;
- backend, task-worker, and task-scheduler deploy or rollback evidence exists;
- `EX-037` is removed from the temporary exceptions register.
