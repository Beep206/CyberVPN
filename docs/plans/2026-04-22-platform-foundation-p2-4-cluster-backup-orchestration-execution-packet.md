# CyberVPN Platform Foundation P2.4 Cluster Backup Orchestration Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live cluster evidence pending  
**Packet:** `P2.4`  
**Primary owners:** `sre-platform` / `infra-platform`  
**Supporting owners:** `data-platform`, `security`, `docs-program`

---

## 1. Packet Role

This document is the execution packet for `P2.4` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-monorepo-inventory.md](2026-04-21-platform-foundation-monorepo-inventory.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md](../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md)

`P2.4` exists to freeze the first workload-cluster data-protection contract in repository form before live infrastructure is available:

- `CloudNativePG` is the canonical PostgreSQL operator for Kubernetes workloads;
- `Barman Cloud Plugin` is the canonical object-store and WAL-archive path for durable PostgreSQL recovery and PITR;
- CSI-backed volume snapshots are the fast same-provider restore path;
- `Velero` is the canonical Kubernetes object and portable-volume backup orchestrator;
- `Velero` file-system backup remains exception-only, not the default path.

Implementation note:

- this packet is being executed as a pre-launch `repo/validation` slice because no live workload cluster, object-store credentials, or snapshot-capable CSI substrate exists in the current session;
- the repository slice is implemented and locally validated;
- the remaining closure work is live reconciliation, credential wiring, snapshot compatibility proof, and restore evidence.

---

## 2. Current Baseline

Before this packet:

- `P2.1` froze the first workload-cluster scaffold and network-baseline intent;
- `P2.2` froze the base platform-services GitOps layer, including `cert-manager`, `External Secrets Operator`, and observability controllers;
- the target-state document already froze:
  - `CloudNativePG + Barman Cloud Plugin` for PostgreSQL backup and PITR;
  - `Velero` for Kubernetes objects and portable volume recovery;
  - CSI snapshots for fast same-provider restore;
  - `Velero` snapshot data movement to object storage as the portability path;
  - `Velero` file-system backup as an exception path only.

Observed strengths:

- the program already has a clear data-protection architecture;
- the workload-cluster GitOps shape from `P2.1`/`P2.2` gives `P2.4` an obvious repository placement model;
- the target-state already separates PostgreSQL durable recovery from generic cluster-object backup.

Observed implementation risks:

- without a repository scaffold, later packets could collapse PostgreSQL backup into generic `Velero` backup and erase the durable-source-of-truth boundary;
- upstream `Barman Cloud Plugin` installation is manifest-based, not chart-based, so repository consumers need a clear operator contract instead of an invented Helm path;
- `Velero` is easy to underspecify unless the provider plugin, CSI enablement, node-agent posture, and runtime-owned credential boundary are made explicit now.

---

## 3. Canonical Decisions For P2.4

`P2.4` fixes the following decisions:

1. `CloudNativePG` is the only target PostgreSQL operator baseline for Kubernetes workloads.
2. PostgreSQL durable recovery is not delegated to `Velero`; it remains `CloudNativePG + Barman Cloud Plugin + WAL archive`.
3. Volume snapshots are explicitly a second path for fast same-provider restore, not the authoritative long-term recovery record.
4. `Velero` is responsible for Kubernetes API objects and portable volume orchestration, not for replacing PostgreSQL-native PITR.
5. `Velero` must be rendered snapshot-first:
   - `EnableCSI`
   - `deployNodeAgent=true`
   - `defaultSnapshotMoveData=true`
   - `defaultVolumesToFsBackup=false`
6. `Barman Cloud Plugin` is installed by vendored official manifest contract, not by an invented chart path.
7. Database-specific `ObjectStore`, `ScheduledBackup`, and cluster backup snippets are template-only until a real workload exists.
8. Runtime secrets, object-store ownership, and validated `VolumeSnapshotClass` objects remain out of git and are required for live closure.

---

## 4. Scope

In scope for `P2.4`:

- add a canonical helper under [infra/scripts/cluster_backup_bootstrap.py](../../infra/scripts/cluster_backup_bootstrap.py);
- add unit coverage for the helper;
- render the first `platform-gitops` scaffold for workload-cluster data protection;
- freeze ordered Flux reconciliation for:
  - `CloudNativePG` operator
  - `Barman Cloud Plugin`
  - `Velero`
  - cluster backup policies
- freeze template-only PostgreSQL backup contracts for future database workloads;
- update operator docs so the helper is discoverable from `infra/README.md`;
- record the packet evidence and formal carry-forward residual.

Out of scope for the current repository slice executed in this workspace:

- live cluster reconciliation;
- live object-store credential creation or injection;
- live `VolumeSnapshotClass` validation;
- live `CloudNativePG` cluster deployment;
- live backup or restore drills;
- retirement of the local Compose backup path.

---

## 5. Official Constraints

The execution of `P2.4` follows current primary-source guidance:

- `CloudNativePG` scheduled backups are the recommended backup model and support `method: plugin` and `method: volumeSnapshot`;
- the `Barman Cloud Plugin` must be installed in the same namespace as the `CloudNativePG` operator and is installed from the official manifest;
- `CloudNativePG` 1.26+ is required for the plugin, and newer versions are recommended by upstream;
- `Velero` chart values support:
  - provider plugin `initContainers`
  - `deployNodeAgent`
  - CSI feature flags
  - `defaultSnapshotMoveData`
  - pre-existing credentials secret references.

Primary sources:

- CloudNativePG backup docs: https://cloudnative-pg.io/docs/1.29/backup
- CloudNativePG volume snapshot appendix: https://cloudnative-pg.io/docs/devel/appendixes/backup_volumesnapshot
- Barman Cloud Plugin intro: https://cloudnative-pg.io/plugin-barman-cloud/docs/intro/
- Barman Cloud Plugin installation: https://cloudnative-pg.io/plugin-barman-cloud/docs/installation/
- Barman Cloud Plugin usage: https://cloudnative-pg.io/plugin-barman-cloud/docs/usage/
- Velero Helm chart values: https://raw.githubusercontent.com/vmware-tanzu/helm-charts/main/charts/velero/values.yaml
- Velero file-system backup docs: https://velero.io/docs/main/file-system-backup/

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P2.4`:

### 6.1 Helper And Tests

- [infra/scripts/cluster_backup_bootstrap.py](../../infra/scripts/cluster_backup_bootstrap.py)
- [infra/tests/test_cluster_backup_bootstrap.py](../../infra/tests/test_cluster_backup_bootstrap.py)

### 6.2 Existing Surfaces Updated During P2.4

- [infra/README.md](../../infra/README.md)

### 6.3 Packet Evidence

- [../evidence/platform-foundation/2026-04-22/p2-4-cluster-backup-orchestration/evidence-pack.md](../evidence/platform-foundation/2026-04-22/p2-4-cluster-backup-orchestration/evidence-pack.md)

---

## 7. Workboard

### 7.1 `T2.4.1` Freeze The Repository Scaffold For Workload-Cluster Data Protection

**Goal:** make the frozen backup architecture concrete in `platform-gitops` form.

Deliverables:

- `cluster_backup_bootstrap.py`
- root and cluster-local scaffold `README` files
- Flux `Kustomization` ordering for data protection
- `versions.env`
- operator check helper

Acceptance criteria:

- helper renders a structurally complete scaffold for the first workload cluster;
- the scaffold distinguishes controller install from later database workload templates;
- the rendered operator check script matches the frozen control surfaces.

### 7.2 `T2.4.2` Freeze The Controller And Policy Baseline

**Goal:** encode the exact operator and policy decisions so later packets cannot drift.

Deliverables:

- `CloudNativePG` operator `HelmRelease`
- `Barman Cloud Plugin` vendored-manifest contract
- `Velero` `HelmRelease`
- `BackupStorageLocation`
- `VolumeSnapshotLocation`
- cluster backup `Schedule`

Acceptance criteria:

- `Barman Cloud Plugin` install path is clearly manifest-based;
- `Velero` is rendered snapshot-first with explicit provider plugin placeholder and runtime secret boundary;
- the backup policy layer does not imply file-system backup is the default.

### 7.3 `T2.4.3` Freeze Database Backup Templates Without Pretending A Real Cluster Exists

**Goal:** encode PostgreSQL recovery contracts while preserving the honest repo-only scope.

Deliverables:

- template-only `ObjectStore`
- template-only `ScheduledBackup` for `method: plugin`
- template-only `ScheduledBackup` for `method: volumeSnapshot`
- template-only `Cluster` backup snippet

Acceptance criteria:

- templates are intentionally outside the applied `kustomization.yaml`;
- plugin and snapshot strategies are both present;
- WAL archive and volume snapshot responsibilities remain clearly separated.

### 7.4 `T2.4.4` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable before any live workload-cluster recovery evidence exists.

Deliverables:

- helper unit tests
- local render smoke
- local syntax validation
- packet evidence pack
- formal carry-forward residual for missing live reconciliation and recovery proof

Acceptance criteria:

- repository slice is locally validated;
- live closure requirements are explicit;
- later `P2` packets may proceed without pretending non-prod Kubernetes backup is already proven.

---

## 8. State-Boundary Rules

`P2.4` must keep the following invariants:

1. PostgreSQL durable recovery stays outside generic `Velero` semantics.
2. `Velero` must not become an implicit replacement for `CloudNativePG` backup and PITR.
3. `Barman Cloud Plugin` install is manifest-based until upstream provides a maintained chart path and the program explicitly adopts it.
4. Runtime secrets, bucket ownership, KMS IDs, and snapshot classes stay out of git.
5. Template-only database backup resources must not be smuggled into the applied `kustomization.yaml` before a real database workload exists.
6. `P2.4` must not claim any live restore readiness from repository-only work.

---

## 9. Risks And Guardrails

| Risk | Why it matters | Guardrail |
|---|---|---|
| `Velero` is treated as the PostgreSQL durable recovery path | PITR and WAL responsibilities get blurred | freeze `CloudNativePG + Barman Cloud Plugin + WAL archive` as the authoritative database recovery path |
| a fake Helm-based Barman install path gets invented | live reconciliation later diverges from upstream guidance | use a vendored official-manifest contract only |
| snapshot strategy is underspecified | later live rollout fails on CSI or provider details | keep `VolumeSnapshotClass` and provider ownership explicit as runtime inputs |
| packet is mistaken for live backup readiness | later phases inherit unproven assumptions | carry forward an explicit residual until real backups and restores are demonstrated |

---

## 10. Packet Exit For The Repository Slice

The repository slice for `P2.4` is considered complete only when:

1. the helper and tests exist in git;
2. the scaffold renders the frozen controller and policy structure;
3. the operator docs point to the helper;
4. local validation passes;
5. the evidence pack records the honest residual that still blocks packet closure in runtime terms.

This does **not** equal packet completion in the live program. Full `P2.4` closure additionally requires:

- live workload-cluster reconciliation evidence for `CloudNativePG`, `Barman Cloud Plugin`, and `Velero`;
- validated object-store credentials and bucket/KMS ownership;
- validated CSI `VolumeSnapshotClass` readiness;
- live backup captures;
- live restore or rebuild drills for:
  - a `CloudNativePG` plugin backup path
  - a volume-snapshot restore path
  - a `Velero` cluster-resource restore path.
