# CyberVPN Platform Foundation P2.4 Cluster Backup Orchestration Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P2.4`  
**Phase:** `P2`  
**Primary owners:** `sre-platform` / `infra-platform`  
**Supporting owners:** `data-platform`, `security`, `docs-program`  
**Purpose:** record the repository, validation, and operator-surface changes completed for `P2.4`, plus the remaining live evidence required before the packet can be declared complete.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p2-4-cluster-backup-orchestration-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p2-4-cluster-backup-orchestration-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- `Gate B` is also not passed because `P1` still carries unresolved live-evidence residuals.
- `Gate C` cannot be claimed because `P2.1` through `P2.4` all still carry live-closure exceptions.
- this evidence pack carries `EX-024` as the formal reason `P2.4` may remain in progress while later `P2` repo-slice work begins.

---

## 2. Result Snapshot

Current `P2.4` result:

- canonical helper added at `infra/scripts/cluster_backup_bootstrap.py`;
- helper renders the first workload-cluster `platform-gitops` data-protection scaffold for:
  - `CloudNativePG`
  - `Barman Cloud Plugin`
  - `Velero`
  - backup policies
  - template-only PostgreSQL recovery contracts
- helper freezes:
  - `CloudNativePG + Barman Cloud Plugin + WAL archive` as the PostgreSQL durable recovery path
  - CSI volume snapshots as the fast same-provider restore path
  - `Velero` CSI snapshot data movement as the portable-volume path
  - `Velero` file-system backup as exception-only
- operator docs updated so the helper is discoverable from `infra/README.md`.

This packet is **not yet claimed complete** because:

- no live workload cluster exists in the current session;
- no live object-store credentials, bucket ownership, or KMS wiring are available here;
- no validated CSI `VolumeSnapshotClass` evidence exists;
- no live `CloudNativePG`, `Barman Cloud Plugin`, or `Velero` reconciliation evidence exists;
- no backup or restore drills have been executed.

That is intentional. `P2.4` first freezes the repository contract and validation boundary, then carries the runtime closure debt explicitly.

---

## 3. Repository Changes Recorded

### 3.1 Helper And Tests

- `infra/scripts/cluster_backup_bootstrap.py`
  - renders root and cluster-local data-protection scaffolds
  - renders Flux ordering for:
    - data-protection sources
    - namespaces
    - `CloudNativePG`
    - `Barman Cloud Plugin`
    - `Velero`
    - backup policies
  - renders template-only:
    - `ObjectStore`
    - `ScheduledBackup` with `method: plugin`
    - `ScheduledBackup` with `method: volumeSnapshot`
    - cluster backup snippet showing WAL archive plus snapshot config

- `infra/tests/test_cluster_backup_bootstrap.py`
  - validates scaffold rendering
  - validates the `Velero` snapshot-first posture
  - validates the split between plugin-based durable recovery and snapshot-based fast recovery

### 3.2 Operator Docs

- `infra/README.md`
  - now documents `cluster_backup_bootstrap.py` as the canonical helper for `P2.4`

### 3.3 Packet And Program Records

- `docs/plans/2026-04-22-platform-foundation-p2-4-cluster-backup-orchestration-execution-packet.md`
- `docs/plans/2026-04-21-platform-foundation-temporary-exceptions-register.md`
  - now carries `EX-024`

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 Helper Unit Tests

Command:

```bash
python -m unittest infra.tests.test_cluster_backup_bootstrap
```

Result:

- `Ran 2 tests`
- `OK`

### 4.2 Python Syntax Check

Command:

```bash
python -m py_compile infra/scripts/cluster_backup_bootstrap.py
```

Result:

- compilation completed successfully

### 4.3 Helper Render Smoke

Command shape:

```bash
python infra/scripts/cluster_backup_bootstrap.py render-scaffold \
  --output-dir <temporary-dir>
```

Result:

- helper completed successfully against the current repository workspace
- scaffold artifacts were created for:
  - `clusters/nonprod-hetzner-hel1-core`
  - `infrastructure/nonprod-hetzner-hel1-core/data-protection`
  - `scripts/check-data-protection.sh`
- rendered output includes:
  - `CloudNativePG` operator `HelmRelease`
  - `Barman Cloud Plugin` manifest contract
  - `Velero` `HelmRelease`
  - `BackupStorageLocation`
  - `VolumeSnapshotLocation`
  - cluster backup `Schedule`
  - template-only `ObjectStore` and `ScheduledBackup` resources

### 4.4 Workspace Readiness Check For Live Closure

Observed in the current workspace on 2026-04-22:

- no live workload cluster kubeconfig exists in this session;
- no live object-store credentials or bucket/KMS ownership records exist in this session;
- no validated `VolumeSnapshotClass` or storage-class compatibility evidence exists in this session;
- no live `CloudNativePG`, `Barman Cloud Plugin`, or `Velero` reconciliation evidence exists;
- no restore drills exist yet for:
  - plugin-based PostgreSQL recovery
  - volume-snapshot recovery
  - `Velero` cluster-resource recovery

Meaning:

- the packet cannot honestly claim non-prod workload-cluster backup readiness yet;
- `P2.4` must therefore carry a formal residual until real runtime reconciliation and recovery evidence are attached.

---

## 5. Remaining Live Closure Requirements

`P2.4` can only move from “repo slice complete” to “packet complete” when the following evidence exists:

1. live workload-cluster access exists for the first non-prod cluster;
2. Flux reconciliation evidence exists for:
   - `platform-cnpg-operator`
   - `platform-barman-plugin`
   - `platform-velero`
   - `platform-backup-policies`
3. live runtime dependencies are present and recorded:
   - `velero-cloud-credentials`
   - `cnpg-barman-cloud-credentials`
   - object-store bucket, region, and KMS ownership
   - validated CSI `VolumeSnapshotClass`
4. a real `CloudNativePG` database workload is wired to:
   - `ObjectStore`
   - WAL archive via `Barman Cloud Plugin`
   - `ScheduledBackup` with `method: plugin`
   - `ScheduledBackup` with `method: volumeSnapshot` when appropriate
5. live backup and restore evidence exists for:
   - at least one plugin-based PostgreSQL backup and recovery path
   - at least one same-provider volume-snapshot restore path
   - at least one `Velero` restore for cluster resources and portable-volume metadata
6. `EX-024` is removed from the exceptions register.
