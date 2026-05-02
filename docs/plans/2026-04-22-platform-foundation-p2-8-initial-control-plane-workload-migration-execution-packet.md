# CyberVPN Platform Foundation P2.8 Initial Control-Plane Workload Migration Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live non-prod rollout evidence pending  
**Packet:** `P2.8`  
**Primary owners:** `backend-platform` / `infra-platform`  
**Supporting owners:** `sre-platform`, `security`, `docs-program`

---

## 1. Packet Role

This document is the execution packet for `P2.8` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../api/platform-foundation-initial-control-plane-workloads-spec.md](../api/platform-foundation-initial-control-plane-workloads-spec.md)
- [../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md](../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md)

`P2.8` exists to freeze the first real Kubernetes runtime contract for CyberVPN
control-plane workloads:

- `backend`
- `task-worker`
- `task-scheduler`

Implementation note:

- this packet is being executed as a pre-launch `repo/validation` slice because no live
  workload cluster, no live OpenBao-backed secret materialization, and no live Flux rollout
  exist in the current session;
- the repository slice is implemented and locally validated;
- the remaining closure work is real non-prod rollout, secret delivery proof, migration-job
  proof, and deploy or rollback evidence.

---

## 2. Current Baseline

Before this packet:

- `P2.2` froze the workload-cluster platform-services baseline:
  - `External Secrets Operator`
  - `kube-prometheus-stack`
  - `Alloy`
- `P2.5` froze the first OCI Helm and GitOps delivery contract for `backend` and
  `task-worker`;
- `P2.6` froze the current NATS-backed event transport contract;
- current host-based runtime still deploys:
  - `backend`
  - `worker`
  - `scheduler`
  - `helix-adapter`
  through Compose or Ansible-era rollout surfaces.

Observed strengths:

- current source images already exist for:
  - `backend`
  - `task-worker`
- current runtime surfaces already prove:
  - backend metrics and health endpoints
  - worker multiprocess metrics pattern
  - scheduler command family
  - backend Alembic migration authority

Observed implementation risks:

- `P2.8` could silently reintroduce host-local `.env` thinking unless OpenBao-backed secret
  delivery is frozen now;
- task-scheduler could drift into an ad hoc one-off release instead of a deliberate second
  release of the task-worker chart;
- chart scaffolds from `P2.5` are too generic to count as a real migration contract unless
  service monitors, migration hook, and runtime-command shape are made explicit.

---

## 3. Canonical Decisions For P2.8

`P2.8` fixes the following decisions:

1. The first Kubernetes runtime migration set is:
   - `backend`
   - `task-worker`
   - `task-scheduler`
2. `task-scheduler` is a second release of the `cybervpn-task-worker` chart, not a new
   image family.
3. `backend` carries a pre-install and pre-upgrade migration `Job` using:
   - `alembic upgrade head`
4. OpenBao-backed secret delivery is mandatory for the first migration set.
5. The initial OpenBao extract keys are:
   - `kv-apps/data/nonprod/platform/backend`
   - `kv-apps/data/nonprod/platform/task-worker`
6. `task-worker` and `task-scheduler` intentionally share the same OpenBao extract key until
   a real configuration divergence exists.
7. Rollout order is frozen as:
   - namespace
   - backend
   - task-worker
   - task-scheduler
8. `helix-adapter` and `telegram-bot` are explicitly excluded from this packet.
9. Public ingress cutover is not claimed by `P2.8`; this packet freezes workload runtime
   shape only.

---

## 4. Scope

In scope for `P2.8`:

- add a canonical helper under [infra/scripts/control_plane_workload_migration.py](../../infra/scripts/control_plane_workload_migration.py);
- add unit coverage for the helper;
- render source-repo chart scaffolds for:
  - `cybervpn-backend`
  - `cybervpn-task-worker`
- render GitOps-repo scaffolds for:
  - namespace foundation
  - backend release
  - task-worker release
  - task-scheduler release
  - explicit cluster-local rollout ordering
- freeze the OpenBao-backed secret contract for the first migration set;
- update operator docs, phased-plan residual tracking, and packet evidence.

Out of scope for the current repository slice executed in this workspace:

- live non-prod rollout;
- live OpenBao secret values or auth credentials;
- live Flux reconciliation;
- live deploy or rollback evidence;
- `helix-adapter` migration;
- `telegram-bot` migration;
- final backend public ingress cutover.

---

## 5. Official Constraints

The execution of `P2.8` follows current primary-source guidance:

- Flux `HelmRelease` remains the workload delivery contract for chart-based releases;
- External Secrets Operator remains the maintained OpenBao-compatible controller path;
- Helm hooks remain the chart-native way to run pre-install and pre-upgrade jobs;
- `ServiceMonitor` remains the canonical Prometheus Operator integration object for
  service-backed metrics targets;
- Kubernetes runtime objects stay on stable APIs:
  - `apps/v1` for `Deployment`
  - `batch/v1` for `Job`
  - `policy/v1` for `PodDisruptionBudget`

Primary sources:

- Flux Helm releases: https://v2-6.docs.fluxcd.io/flux/guides/helmreleases/
- External Secrets Operator Vault/OpenBao provider: https://external-secrets.io/latest/provider/hashicorp-vault/
- Helm chart hooks: https://helm.sh/docs/v3/topics/charts_hooks/
- Prometheus Operator getting started and `ServiceMonitor`: https://prometheus-operator.dev/docs/developer/getting-started/
- Kubernetes Jobs: https://kubernetes.io/docs/concepts/workloads/controllers/job/
- Kubernetes PodDisruptionBudget: https://kubernetes.io/docs/tasks/run-application/configure-pdb/

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P2.8`:

### 6.1 Helper And Tests

- [infra/scripts/control_plane_workload_migration.py](../../infra/scripts/control_plane_workload_migration.py)
- [infra/tests/test_control_plane_workload_migration.py](../../infra/tests/test_control_plane_workload_migration.py)

### 6.2 Canonical Spec

- [../api/platform-foundation-initial-control-plane-workloads-spec.md](../api/platform-foundation-initial-control-plane-workloads-spec.md)

### 6.3 Operator Docs

- [infra/README.md](../../infra/README.md)

### 6.4 Packet Evidence

- [../evidence/platform-foundation/2026-04-22/p2-8-initial-control-plane-workload-migration/evidence-pack.md](../evidence/platform-foundation/2026-04-22/p2-8-initial-control-plane-workload-migration/evidence-pack.md)

---

## 7. Workboard

### 7.1 `T2.8.1` Freeze The First Runtime Migration Set

**Goal:** stop the first workload migration wave from drifting into unowned or overly broad
scope.

Deliverables:

- explicit initial set:
  - `backend`
  - `task-worker`
  - `task-scheduler`
- explicit exclusions:
  - `helix-adapter`
  - `telegram-bot`
- canonical rollout order

Acceptance criteria:

- the migration set is frozen in one canonical spec;
- exclusions are written down instead of being implied;
- rollout order is encoded in GitOps-facing objects.

### 7.2 `T2.8.2` Freeze The OpenBao-Backed Runtime Secret Contract

**Goal:** remove ambiguity about where runtime configuration for the first migration set
comes from.

Deliverables:

- backend runtime secret contract
- task-worker runtime secret contract
- task-scheduler runtime secret contract
- explicit reuse of the worker extract key by the scheduler release

Acceptance criteria:

- no host-local `.env` values are part of the target packet contract;
- secret keys and target secret names are explicit;
- OpenBao remains the secret authority.

### 7.3 `T2.8.3` Freeze The Runtime Chart And Rollout Shape

**Goal:** make the first migration set count as a real runtime contract instead of a generic
delivery placeholder.

Deliverables:

- backend chart scaffold with:
  - migration hook
  - service monitor
  - PDB
  - HTTP and metrics ports
- task-worker chart scaffold with:
  - worker mode
  - scheduler mode
  - multiprocess metrics support
  - service monitor
  - PDB for the worker release
- GitOps release scaffolds for:
  - backend
  - task-worker
  - task-scheduler

Acceptance criteria:

- scheduler shape is explicit and reusable;
- backend migration authority is encoded in chart form;
- observability hooks are part of the runtime contract.

### 7.4 `T2.8.4` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable before any live non-prod cluster exists.

Deliverables:

- helper unit tests;
- helper render smoke;
- helper validation command;
- packet evidence pack;
- formal carry-forward residual for missing live rollout and secret-materialization proof.

Acceptance criteria:

- the repository slice is locally validated;
- live closure requirements are explicit;
- later packets may proceed without pretending the first migrated runtime set is already
  operational in non-prod.

---

## 8. State-Boundary Rules

`P2.8` must keep the following invariants:

1. Desired state still belongs to `platform-gitops`, not to chart directories or manual
   `kubectl` history.
2. OpenBao remains the secret authority; Kubernetes `Secret` objects are derived runtime
   material only.
3. Runtime charts must not embed secret values.
4. Scheduler remains part of the task-worker family, not a third image lineage.
5. `P2.8` must not silently pull `helix-adapter` or `telegram-bot` into the first migration
   set.
6. `P2.8` must not claim final public ingress cutover for backend traffic.

---

## 9. Risks And Guardrails

| Risk | Why it matters | Guardrail |
|---|---|---|
| host-local `.env` semantics leak into the migration contract | OpenBao-backed secret delivery never becomes authoritative | freeze extract keys and target secret names now |
| scheduler becomes a one-off deployment shape | task-worker family drifts into duplicated runtime patterns | freeze scheduler as a second release of the task-worker chart |
| backend migrations stay manual | deploy success depends on operator memory | freeze Helm hook migration job in the chart contract |
| `helix-adapter` is silently included | fleet/runtime adapter work contaminates the first migration wave | write the exclusion explicitly in the spec and packet |
| backend public ingress is accidentally implied | packet claims more runtime readiness than it proves | keep public ingress cutover explicitly out of scope |

---

## 10. Packet Exit For The Repository Slice

The repository slice for `P2.8` is considered complete only when:

1. the helper and tests exist in git;
2. the canonical runtime spec exists in git;
3. source-repo and GitOps-repo scaffolds render successfully;
4. operator docs point to the helper;
5. local validation passes;
6. the evidence pack records the honest residual that still blocks live packet closure.

This does **not** equal packet completion in the live program. Full `P2.8` closure additionally requires:

- live non-prod Flux reconciliation of:
  - backend
  - task-worker
  - task-scheduler
- live OpenBao-backed `ExternalSecret` materialization evidence for the migrated set;
- successful backend migration-job execution evidence;
- runtime metrics evidence for all three releases;
- at least one non-prod deploy or rollback proof;
- explicit narrowing or removal of the host-based runtime path for those migrated workloads.
