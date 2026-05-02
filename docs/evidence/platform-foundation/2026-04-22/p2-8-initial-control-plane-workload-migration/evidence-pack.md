# CyberVPN Platform Foundation P2.8 Initial Control-Plane Workload Migration Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P2.8`  
**Phase:** `P2`  
**Primary owners:** `backend-platform` / `infra-platform`  
**Supporting owners:** `sre-platform`, `security`, `docs-program`  
**Purpose:** record the repository, validation, and operator-surface changes completed for `P2.8`, plus the remaining live evidence required before the packet can be declared complete.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p2-8-initial-control-plane-workload-migration-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p2-8-initial-control-plane-workload-migration-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- `Gate B` is also not passed because `P1` still carries unresolved live-evidence residuals.
- `Gate C` cannot be claimed because `P2.1` through `P2.8` still carry live-closure exceptions.
- this evidence pack carries `EX-028` as the formal reason `P2.8` may remain in progress while later work continues.

---

## 2. Result Snapshot

Current `P2.8` result:

- canonical helper added at `infra/scripts/control_plane_workload_migration.py`;
- helper renders and validates:
  - source-repo chart scaffolds for `backend` and `task-worker`
  - a second scheduler release of the task-worker chart
  - GitOps rollout ordering for namespace -> backend -> task-worker -> task-scheduler
  - OpenBao-backed runtime secret contracts for the first migration set
- canonical runtime spec added at:
  - `docs/api/platform-foundation-initial-control-plane-workloads-spec.md`
- first migrated control-plane workload set is frozen as:
  - `backend`
  - `task-worker`
  - `task-scheduler`
- explicit exclusions are frozen as:
  - `helix-adapter`
  - `telegram-bot`

This packet is **not yet claimed complete** because:

- no live non-prod workload cluster rollout exists yet;
- no live OpenBao-backed `ExternalSecret` materialization proof exists yet;
- no live backend migration-job proof exists yet;
- no live deploy or rollback evidence exists yet for the migrated set.

That is intentional. `P2.8` first freezes and validates the repository contract, then carries the runtime closure debt explicitly.

---

## 3. Repository Changes Recorded

### 3.1 Helper And Tests

- `infra/scripts/control_plane_workload_migration.py`
  - validates the current repo anchors for backend, worker, scheduler, Compose, and Ansible-era runtime surfaces
  - renders the first Kubernetes runtime scaffold for the migrated control-plane set

- `infra/tests/test_control_plane_workload_migration.py`
  - validates scaffold rendering
  - validates the current repository baseline through the helper

### 3.2 Canonical Spec

- `docs/api/platform-foundation-initial-control-plane-workloads-spec.md`
  - freezes the active `P2.8` runtime migration contract

### 3.3 Operator Docs

- `infra/README.md`
  - now documents `control_plane_workload_migration.py` as the canonical helper for `P2.8`

### 3.4 Packet And Program Records

- `docs/plans/2026-04-22-platform-foundation-p2-8-initial-control-plane-workload-migration-execution-packet.md`
- `docs/plans/2026-04-21-platform-foundation-temporary-exceptions-register.md`
  - now carries `EX-028`

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 Helper Unit Tests

Command:

```bash
python -m unittest infra.tests.test_control_plane_workload_migration
```

Result:

- `Ran 2 tests`
- `OK`

### 4.2 Python Syntax Check

Command:

```bash
python -m py_compile infra/scripts/control_plane_workload_migration.py
```

Result:

- compilation completed successfully

### 4.3 Helper Render Smoke

Command shape:

```bash
python infra/scripts/control_plane_workload_migration.py render-scaffold \
  --output-dir <temporary-dir>
```

Result:

- helper completed successfully against the current repository workspace
- rendered scaffold includes:
  - `source-repo/charts/cybervpn-backend`
  - `source-repo/charts/cybervpn-task-worker`
  - `platform-gitops/apps/nonprod-hetzner-hel1-core/platform-workloads/backend`
  - `platform-gitops/apps/nonprod-hetzner-hel1-core/platform-workloads/task-worker`
  - `platform-gitops/apps/nonprod-hetzner-hel1-core/platform-workloads/task-scheduler`
  - `platform-gitops/clusters/nonprod-hetzner-hel1-core/platform-control-plane-backend.yaml`
  - `platform-gitops/clusters/nonprod-hetzner-hel1-core/platform-control-plane-task-worker.yaml`
  - `platform-gitops/clusters/nonprod-hetzner-hel1-core/platform-control-plane-task-scheduler.yaml`

### 4.4 Repo Validation Command

Command:

```bash
python infra/scripts/control_plane_workload_migration.py validate --repo-root .
```

Observed validated baseline:

- current repo still carries the host-based backend, worker, and scheduler deployment surfaces;
- current repo still carries backend Alembic migration authority;
- current repo still carries task-worker multiprocess metrics pattern;
- helper reported:
  - `initial_workloads=backend,task-worker,task-scheduler`
  - `excluded_workloads=helix-adapter,telegram-bot`
  - `backend_secret_key=kv-apps/data/nonprod/platform/backend`
  - `task_worker_secret_key=kv-apps/data/nonprod/platform/task-worker`
  - `task_scheduler_secret_key=kv-apps/data/nonprod/platform/task-worker`
  - `backend_migration_job=alembic upgrade head`
  - `backend_metrics_port=9091`
  - `task_worker_metrics_port=9091`
  - `scheduler_command=taskiq scheduler src.broker:scheduler`
  - `rollout_order=namespace,backend,task-worker,task-scheduler`

### 4.5 Workspace Readiness Check For Live Closure

Observed in the current workspace on 2026-04-22:

- no live non-prod workload cluster rollout exists;
- no live OpenBao-backed runtime secret materialization exists;
- no live backend migration-job run exists;
- no live deploy or rollback proof exists for the migrated set.

Meaning:

- the packet cannot honestly claim the first migrated control-plane set is operational yet;
- `P2.8` must therefore carry a formal residual until real rollout, secret, and migration evidence are attached.

---

## 5. Remaining Live Closure Requirements

`P2.8` can only move from "repo slice complete" to "packet complete" when the following evidence exists:

1. backend, task-worker, and task-scheduler reconcile on the real non-prod workload cluster;
2. OpenBao-backed `ExternalSecret` materialization is proven for all three releases;
3. the backend migration job runs successfully during first install or upgrade;
4. metrics for all three releases are scraped through the canonical Prometheus baseline;
5. at least one non-prod deploy or rollback proof exists for the migrated set;
6. `EX-028` is removed from the exceptions register.
