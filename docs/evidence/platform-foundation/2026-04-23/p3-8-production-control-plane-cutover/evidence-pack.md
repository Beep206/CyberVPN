# CyberVPN Platform Foundation P3.8 Production Control-Plane Cutover Evidence Pack

**Date:** 2026-04-23  
**Status:** in progress  
**Packet:** `P3.8`  
**Phase:** `P3`  
**Primary owners:** `infra-platform`, `backend-platform`  
**Supporting owners:** `sre-platform`, `security`, `data-platform`, `docs-program`

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-23-platform-foundation-p3-8-production-control-plane-cutover-execution-packet.md](../../../../plans/2026-04-23-platform-foundation-p3-8-production-control-plane-cutover-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [platform-foundation-production-control-plane-cutover-spec.md](../../../../api/platform-foundation-production-control-plane-cutover-spec.md)

Important gate note:

- `Gate D` still cannot be claimed.
- `P3.8` carries `EX-037` as the formal reason later work may continue while live
  production cutover evidence is still absent.

---

## 2. Result Snapshot

Current `P3.8` result:

- the repository now contains a canonical production cutover spec for the first production
  Kubernetes-managed control-plane wave;
- a repo-side helper can render the production cutover scaffold for:
  - `Flagger`
  - `CloudNativePG`
  - production `PrometheusRule`
  - production app namespace and workload releases
- the scaffold freezes `prod-hetzner-fsn1-core` and `prod-mgmt` as the production cluster
  boundary for the first control-plane cutover wave;
- the backend now has a frozen production canary contract via `Flagger + Gateway API`;
- worker and scheduler production releases are sequenced after backend production cutover
  prerequisites rather than relying on operator memory.

This packet is **not yet claimed complete** because:

- there is no live `prod-mgmt` or live production workload cluster in the current
  workspace;
- there is no live Flux reconciliation against the rendered production scaffolds;
- there is no live `Flagger` canary promotion or rollback proof;
- there is no live `CloudNativePG` production bootstrap, backup, or alerting proof;
- there is no live production deploy or rollback evidence for the first control-plane
  workload set.

---

## 3. Verification Evidence

All commands below were executed on 2026-04-23 in the repository workspace.

### 3.1 Helper Unit Tests

```bash
python -m unittest infra.tests.test_prod_control_plane_cutover
```

Result:

- `Ran 2 tests in 0.006s`
- `OK`
- validator output:
  - `validated production cutover prerequisites: cluster=prod-hetzner-fsn1-core management=prod-mgmt progressive_delivery=flagger-gatewayapi cnpg=manual-podmonitor`

### 3.2 Helper Syntax Check

```bash
python -m py_compile infra/scripts/prod_control_plane_cutover.py
```

Result:

- compilation completed successfully

### 3.3 Render Smoke

```bash
python infra/scripts/prod_control_plane_cutover.py render-scaffold --output-dir /tmp/p3-8-prod-cutover
```

Result:

- scaffold directory is rendered successfully
- production progressive-delivery, data, observability, and workload paths exist

### 3.4 Baseline Validation

```bash
python infra/scripts/prod_control_plane_cutover.py validate --repo-root .
```

Result:

- validation succeeded against the current repository baseline
- validation output:
  - `validated production cutover prerequisites: cluster=prod-hetzner-fsn1-core management=prod-mgmt progressive_delivery=flagger-gatewayapi cnpg=manual-podmonitor`

---

## 4. Remaining Live Closure Requirements

`P3.8` can only move from "repo slice complete" to "packet complete" when:

1. a real `prod-mgmt` and production workload cluster exist with operator-approved access;
2. Flux reconciles the rendered production progressive-delivery, data, observability, and
   workload kustomizations successfully;
3. `Flagger` proves at least one backend canary promotion and one rollback on the real
   production workload cluster;
4. `CloudNativePG` production cluster bootstrap, manual `PodMonitor`, and
   `ScheduledBackup` evidence exist;
5. backend, task-worker, and task-scheduler deploy or rollback evidence exists on the real
   production workload cluster;
6. legacy host-based production workload authority is retired or explicitly demoted to
   break-glass only;
7. `EX-037` is removed from the exceptions register.
