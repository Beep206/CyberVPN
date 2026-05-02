# CyberVPN Platform Foundation P2.1 Workload-Cluster Bootstrap Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P2.1`  
**Phase:** `P2`  
**Primary owners:** `infra-platform` / `platform-architecture`  
**Supporting owners:** `sre-platform`, `security`  
**Purpose:** record the repository, validation, and operator-surface changes completed for `P2.1`, plus the remaining live evidence required before the packet can be declared complete.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p2-1-workload-cluster-bootstrap-execution-packet.md](../../../plans/2026-04-22-platform-foundation-p2-1-workload-cluster-bootstrap-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- `Gate B` is also not passed because `P1` still carries unresolved live-evidence residuals.
- this evidence pack currently carries `EX-021` as the formal reason `P2.1` may remain in progress while later `P2` repo-slice work begins.

---

## 2. Result Snapshot

Current `P2.1` result:

- canonical helper added at `infra/scripts/workload_cluster_bootstrap.py`;
- helper renders one workload-cluster scaffold for the frozen first non-prod cluster id `nonprod-hetzner-hel1-core`;
- helper renders the management-cluster-side contract path under `infrastructure/nonprod-mgmt/workload-clusters/nonprod-hetzner-hel1-core`;
- helper freezes the day-1 network-baseline intent for:
  - `Cloudflare`
  - provider-native `LoadBalancer`
  - `Cilium Gateway API`
  - `cert-manager`
  - `trust-manager`
- operator docs updated so `P2.1` is discoverable from `infra/README.md`.

This packet is **not yet claimed complete** because:

- no live `nonprod-mgmt` cluster is available in this evidence window;
- no operator-validated `CAPH_TEMPLATE_URL` has been attached yet;
- no real workload-cluster manifest has been generated against a running management cluster yet;
- no real workload-cluster creation evidence exists yet;
- no real provider-native L4 load balancer or Cloudflare edge-mapping evidence is attached yet.

That is intentional. `P2.1` first closes the reproducible repo and contract slice, while leaving live workload-cluster creation and runtime network-baseline proof explicit.

---

## 3. Repository Changes Recorded

### 3.1 Helper And Tests

- `infra/scripts/workload_cluster_bootstrap.py`
  - renders:
    - the root workload-cluster scaffold README
    - the management-cluster-side workload-cluster contract
    - `workload-cluster-inputs.env`
    - guarded `render-workload-cluster.sh`
    - the reserved workload-cluster-local GitOps paths
    - the network-baseline values and intent files
  - freezes `MachineDeployment` as the day-1 worker posture
  - refuses to proceed without an explicit `CAPH_TEMPLATE_URL`

- `infra/tests/test_workload_cluster_bootstrap.py`
  - validates scaffold rendering against synthetic inputs
  - validates the `clusterctl generate cluster` guard
  - validates the intentionally minimal trust-manager baseline

### 3.2 Operator Docs

- `infra/README.md`
  - now documents `workload_cluster_bootstrap.py` as the canonical `P2.1` operator surface

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 Helper Unit Tests

Command:

```bash
python -m unittest infra.tests.test_workload_cluster_bootstrap
```

Result:

- `Ran 2 tests`
- `OK`

### 4.2 Python Syntax Check

Command:

```bash
python -m py_compile infra/scripts/workload_cluster_bootstrap.py
```

Result:

- compilation completed successfully

### 4.3 Helper Smoke Render

Command shape:

```bash
python infra/scripts/workload_cluster_bootstrap.py render-scaffold \
  --output-dir <temporary-dir>
```

Result:

- helper completed successfully against synthetic inputs
- expected artifacts were created:
  - `README.md`
  - `apps/nonprod-hetzner-hel1-core/README.md`
  - `clusters/nonprod-hetzner-hel1-core/README.md`
  - `infrastructure/nonprod-hetzner-hel1-core/network/README.md`
  - `infrastructure/nonprod-hetzner-hel1-core/network/cilium-values.yaml`
  - `infrastructure/nonprod-hetzner-hel1-core/network/cert-manager-values.yaml`
  - `infrastructure/nonprod-hetzner-hel1-core/network/trust-manager-values.yaml`
  - `infrastructure/nonprod-hetzner-hel1-core/network/edge-baseline.env`
  - `infrastructure/nonprod-mgmt/workload-clusters/nonprod-hetzner-hel1-core/README.md`
  - `infrastructure/nonprod-mgmt/workload-clusters/nonprod-hetzner-hel1-core/workload-cluster-inputs.env`
  - `infrastructure/nonprod-mgmt/workload-clusters/nonprod-hetzner-hel1-core/render-workload-cluster.sh`
  - `versions.env`

### 4.4 Workspace Readiness Check For Live Workload-Cluster Evidence

Observed in the current workspace on 2026-04-22:

- no live `nonprod-mgmt` kubeconfig or Talos client inputs are present in the current session;
- no operator-validated `CAPH_TEMPLATE_URL` is present in the current session;
- no `TF_VAR_hcloud_token` or equivalent provider credentials are present for real workload-cluster creation;
- no real `platform-gitops` target repository or workload-cluster path handoff is attached in this evidence window;
- no real provider-native L4 load balancer or Cloudflare mapping evidence is present in this workspace.

Meaning:

- the packet cannot honestly claim live workload-cluster creation yet;
- the packet cannot honestly claim runtime network-baseline proof yet;
- `P2.1` must therefore carry a formal residual until those steps are executed against the real non-prod substrate.

---

## 5. Remaining Live Closure Requirements

`P2.1` can only move from “repo slice complete” to “packet complete” when the following evidence exists:

1. an operator-approved `CAPH_TEMPLATE_URL` is attached to the live change record;
2. a real workload-cluster manifest is generated from `nonprod-mgmt` using the guarded render path;
3. live workload-cluster reconciliation evidence exists for `nonprod-hetzner-hel1-core`;
4. live cluster-health evidence exists for:
   - `kubectl get clusters.cluster.x-k8s.io -A`
   - `kubectl get machines.cluster.x-k8s.io -A`
   - `kubectl get nodes`
5. live network-baseline evidence exists for:
   - provider-native L4 entrypoint creation or reservation
   - recorded Cloudflare edge-mapping intent for the cluster-facing origin
6. an explicit operator record exists that cluster-local add-on installation for `Cilium`, `cert-manager`, and `trust-manager` is deferred to `P2.2`, not silently assumed complete as part of `P2.1`.
