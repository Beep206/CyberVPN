# Platform Foundation Initial Control-Plane Workloads Spec

**Date:** 2026-04-22  
**Status:** canonical `P2.8` workload-runtime spec  
**Purpose:** freeze the first Kubernetes runtime contract for CyberVPN control-plane workloads after the platform-services, workload-delivery, and event-backbone packets.

---

## 1. Role

This document freezes the first Kubernetes migration set for CyberVPN control-plane
workloads.

It exists to make four boundaries explicit:

1. which workloads move first;
2. how those workloads consume runtime secrets from OpenBao;
3. how those workloads are ordered under GitOps reconciliation;
4. which current services are intentionally excluded from the first migration set.

This document does not declare live cutover complete. It freezes the target runtime
contract that later non-prod rollout evidence must satisfy.

---

## 2. Frozen Initial Migration Set

The first Kubernetes-managed control-plane runtime set is:

- `backend`
- `task-worker`
- `task-scheduler`

The scheduler is not a new image family. It is a second release of the `task-worker`
chart with a different runtime command.

### Explicit exclusions

The following workloads are intentionally excluded from `P2.8`:

- `helix-adapter`
- `telegram-bot`

Reason:

- `helix-adapter` remains coupled to external fleet and runtime-adapter transition work;
- `telegram-bot` has separate ingress, webhook, and product-surface concerns that do not
  belong in the first control-plane migration set.

---

## 3. Runtime Objects

### 3.1 Backend

The backend runtime contract is:

- `Deployment`
- `Service`
- `ServiceMonitor`
- `PodDisruptionBudget`
- `ExternalSecret`
- pre-install and pre-upgrade database migration `Job`

The backend must expose:

- HTTP port `8000`
- metrics port `9091`

Health contract:

- liveness: `/health`
- readiness: `/readiness`

### 3.2 Task Worker

The task-worker runtime contract is:

- `Deployment`
- metrics `Service`
- `ServiceMonitor`
- `PodDisruptionBudget`
- `ExternalSecret`

The worker release uses:

- command family: `taskiq worker src.broker:broker`
- Prometheus multiprocess directory
- metrics port `9091`

### 3.3 Task Scheduler

The task-scheduler runtime contract is:

- `Deployment`
- metrics `Service`
- `ServiceMonitor`
- `ExternalSecret`

The scheduler release uses:

- command family: `taskiq scheduler src.broker:scheduler`
- the same task-worker image family
- the same OpenBao extract key as the worker release
- `replicaCount=1`
- no `PodDisruptionBudget` by default in the first packet

---

## 4. OpenBao Secret Delivery Contract

All first-migration workloads consume runtime configuration through the `OpenBao -> External Secrets Operator -> Kubernetes Secret` path frozen in `P2.2`.

No host-local `.env` files are part of the target runtime contract.

### 4.1 Extract keys

| Workload | OpenBao extract key | Notes |
|---|---|---|
| `backend` | `kv-apps/data/nonprod/platform/backend` | dedicated runtime secret surface |
| `task-worker` | `kv-apps/data/nonprod/platform/task-worker` | canonical worker runtime surface |
| `task-scheduler` | `kv-apps/data/nonprod/platform/task-worker` | intentionally shared with worker until a real divergence exists |

### 4.2 Secret targets

| Workload | Target Kubernetes Secret |
|---|---|
| `backend` | `backend-runtime` |
| `task-worker` | `task-worker-runtime` |
| `task-scheduler` | `task-scheduler-runtime` |

Rationale:

- OpenBao remains the secret authority;
- the scheduler may consume the same extracted material as the worker, but separate
  Kubernetes Secret target names keep the release boundaries explicit;
- chart values must not embed secret values.

---

## 5. GitOps Rollout Order

The first control-plane workload rollout order is:

1. `platform-workloads-namespace`
2. `platform-control-plane-backend`
3. `platform-control-plane-task-worker`
4. `platform-control-plane-task-scheduler`

Rationale:

- namespace and OpenBao-backed secret delivery must exist before workloads reconcile;
- backend goes first because it owns the application API and migration hook;
- worker goes second because background consumers depend on backend-owned schema and API
  state;
- scheduler goes last because it triggers recurring work and should not start before the
  worker baseline exists.

This order is frozen at the Flux `Kustomization` layer, not left to operator memory.

---

## 6. Database Migration Contract

The backend chart includes a Helm hook `Job` for:

- `pre-install`
- `pre-upgrade`

Command:

```text
alembic upgrade head
```

Rules:

- the migration job uses the same image family as the backend runtime;
- the migration job uses the same OpenBao-backed runtime secret target as the backend;
- later packets may refine the command shape, but the migration authority remains a
  release-scoped job rather than an ad hoc manual shell step.

---

## 7. Observability Contract

The initial workload migration set must integrate with the `P2.2` and `P2.3`
observability posture.

Frozen rules:

- `backend` exposes metrics via its own service port `9091`
- `task-worker` exposes metrics via port `9091`
- `task-scheduler` also exposes metrics via port `9091`
- `ServiceMonitor` is the canonical scrape contract for all three releases
- no `promtail` or standalone `otel-collector` sidecars are introduced here

This packet is about workload migration, not collector divergence. Collector posture stays
owned by the Alloy-only baseline.

---

## 8. Explicit Non-Goals

`P2.8` does not by itself freeze:

- public `Gateway` or `HTTPRoute` cutover for the backend;
- `helix-adapter` Kubernetes delivery;
- `telegram-bot` Kubernetes delivery;
- production rollout;
- live non-prod Flux reconciliation evidence.

Those remain later work or live-closure evidence.

---

## 9. Live Closure Requirements

`P2.8` can move from repo-slice complete to packet complete only when:

1. backend, task-worker, and task-scheduler reconcile on the real non-prod workload cluster;
2. OpenBao-backed `ExternalSecret` materialization is proven for all three releases;
3. the backend migration job runs successfully during first install or upgrade;
4. metrics for all three releases are scraped through the canonical Prometheus baseline;
5. at least one non-prod deploy or rollback proof exists for the migrated set;
6. remaining host-local `.env` or Compose authority for those migrated workloads is retired
   or explicitly narrowed.
