# Platform Foundation Production Control-Plane Cutover Spec

**Date:** 2026-04-23  
**Status:** canonical `P3.8` production cutover spec  
**Purpose:** freeze the first production GitOps-managed Kubernetes runtime contract for
CyberVPN control-plane workloads after the non-prod runtime migration and `prod-mgmt`
foundation packets.

---

## 1. Role

This document freezes the first production control-plane workload cutover contract for
CyberVPN.

It exists to make five boundaries explicit:

1. which production workload cluster receives the first cutover wave;
2. which workloads move in the first production wave;
3. how progressive delivery is handled for the first public API surface;
4. how production PostgreSQL, backup, and alerting prerequisites are represented in Git;
5. which legacy authorities are explicitly disallowed from becoming hidden production
   sources of truth again.

This document does not declare production cutover complete. It freezes the repository-side
target that later live production evidence must satisfy.

---

## 2. Frozen Production Target

### 2.1 Cluster and management authority

The first production workload cluster is:

- `prod-hetzner-fsn1-core`

The management-cluster authority for that runtime is:

- `prod-mgmt`

The production workload cutover must not claim readiness before:

- `prod-mgmt` exists as a real Talos management cluster;
- Flux is running against the production workload cluster;
- production `OpenBao`, production `NATS`, and production backup primitives are live or in
  final readiness state.

### 2.2 First production runtime set

The first production cutover wave is:

- `backend`
- `task-worker`
- `task-scheduler`

The scheduler is not a new image family. It remains a second release of the
`cybervpn-task-worker` chart with a different runtime command.

### Explicit exclusions

The following remain out of scope for `P3.8`:

- `helix-adapter`
- `telegram-bot`
- external VPN/edge fleet workloads

Reason:

- `P3.8` is about production control-plane cutover, not final fleet-runtime unification.

---

## 3. GitOps And Release Authority

Production desired state is owned by `platform-gitops`.

Source-of-truth rules:

- `platform-gitops` owns:
  - pinned chart versions
  - pinned image digests
  - rollout ordering
  - production cutover manifests
- `Flux` is the reconciler, not the source of truth
- `Flagger` is the progressive-delivery controller, not the source of truth
- no Ansible inventory release manifest may become production rollout authority again
- no Compose-based host runtime may become production deployment authority again

---

## 4. Production Secret Delivery Contract

All first-wave production workloads consume runtime configuration through:

`OpenBao -> External Secrets Operator -> Kubernetes Secret`

No host-local `.env` files are part of the production runtime contract.

### 4.1 Extract keys

| Workload | OpenBao extract key | Notes |
|---|---|---|
| `backend` | `kv-apps/data/prod/platform/backend` | dedicated runtime secret surface |
| `task-worker` | `kv-apps/data/prod/platform/task-worker` | canonical worker runtime surface |
| `task-scheduler` | `kv-apps/data/prod/platform/task-worker` | intentionally shared with worker until a real divergence exists |
| `postgres bootstrap` | `kv-apps/data/prod/platform/postgres` | application and superuser bootstrap material |

### 4.2 Secret-store contract

Production cutover assumes a cluster-local maintained operator path exists and that the
cluster store is already available before workload reconciliation.

The production workload packet may reference the cluster store, but may not embed secret
values.

---

## 5. Progressive Delivery Contract

The first progressive production release is:

- `backend`

Progressive-delivery controller:

- `Flagger`

Routing provider:

- `Gateway API`

Frozen decisions:

1. `Flagger` is installed in `flagger-system`.
2. `Flagger` must use `meshProvider=gatewayapi:v1`.
3. The backend canary attaches to the production public gateway through explicit
   `gatewayRefs`.
4. Worker and scheduler are not first-wave canary workloads.
5. The first production backend cutover must support both promotion and rollback through
   the same `Canary` contract.

### 5.1 Canary baseline

The first production backend canary freezes:

- analysis interval `1m`
- failure threshold `5`
- max canary weight `50`
- step weight `10`
- success-rate and duration checks

This is the baseline contract, not evidence that production traffic has already passed
through it.

---

## 6. Production Data And Backup Contract

The first production PostgreSQL runtime authority is:

- `CloudNativePG`

The first production cluster name is:

- `cybervpn-control-plane-db`

Frozen decisions:

1. Production control-plane database state is not an unmanaged host-local PostgreSQL
   service.
2. `ScheduledBackup` is mandatory for the first production cutover wave.
3. Production monitoring ownership for CloudNativePG is explicit and Git-managed.
4. Manual `PodMonitor` resources are preferred over automatic operator-managed
   `enablePodMonitor`, matching current upstream guidance.

### 6.1 Monitoring contract

Production CloudNativePG monitoring uses:

- a manually managed `PodMonitor` in the monitoring namespace
- selector label:
  - `cnpg.io/cluster: cybervpn-control-plane-db`

### 6.2 Backup contract

The first production backup schedule is frozen as a `ScheduledBackup` object committed in
Git.

Live object-store credentials, KMS bindings, and restore evidence remain live-closure
requirements, not repository defaults.

---

## 7. Observability And Alerting Contract

The first production cutover wave must integrate with the previously frozen Alloy-only and
Prometheus-based observability posture.

Frozen rules:

- `Alloy` remains the only collector baseline
- `backend`, `task-worker`, and `task-scheduler` expose metrics through
  `ServiceMonitor`-compatible paths
- production alerting for this packet is Git-managed and includes:
  - backend unavailability
  - backend canary failure
  - first production CloudNativePG cluster degradation

This packet does not authorize reintroducing `promtail` or standalone long-lived
`otel-collector` deployment models.

---

## 8. Rollout Order

The first production cutover order is:

1. progressive-delivery substrate
2. production data substrate
3. production alerting substrate
4. workload namespace
5. backend release
6. task-worker release
7. task-scheduler release

Rationale:

- production cutover must not race its own routing, data, or alerting prerequisites;
- background workers must not overtake the public API rollout;
- scheduler must remain last because it introduces recurring work.

---

## 9. Explicit Non-Goals

`P3.8` does not by itself freeze:

- Cloudflare DNS or LB record cutover execution
- final external fleet workload migration
- PostHog production dashboard evidence
- final production conformance drills

Those remain live-closure or later-packet concerns.

---

## 10. Live Closure Requirements

`P3.8` can move from repo-slice complete to packet complete only when:

1. `prod-mgmt` and the production workload cluster both exist with operator-approved
   access;
2. the production Flux layer reconciles the progressive-delivery, data, observability, and
   workload kustomizations successfully;
3. `CloudNativePG` production database bootstrap, monitoring, and scheduled backup objects
   reconcile successfully;
4. backend production canary promotion and rollback are both proven with Flagger;
5. backend, task-worker, and task-scheduler deploy or rollback evidence exists against the
   real production workload cluster;
6. the legacy host-based production workload authority is retired or explicitly demoted to
   break-glass only;
7. `EX-037` is removed from the exceptions register.
