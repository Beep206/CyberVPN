# CyberVPN Platform Foundation P2.1 Workload-Cluster Bootstrap Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live workload-cluster evidence pending  
**Packet:** `P2.1`  
**Primary owners:** `infra-platform` / `platform-architecture`  
**Supporting owners:** `sre-platform`, `security`

---

## 1. Packet Role

This document is the execution packet for `P2.1` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-naming-and-boundary-registry.md](2026-04-21-platform-foundation-naming-and-boundary-registry.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md](../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md)

`P2.1` exists to establish the first non-prod workload-cluster substrate contract for the program:

- workload cluster id `nonprod-hetzner-hel1-core`;
- management-cluster-side Cluster API contract on `nonprod-mgmt`;
- day-1 worker model based on `MachineDeployment`;
- day-1 network baseline intent for:
  - Cloudflare public edge
  - provider-native L4 load balancer
  - Cilium Gateway API
  - cert-manager
  - trust-manager

Implementation note:

- this packet is being executed as a pre-launch `repo/validation` slice because live infrastructure is not available in the current session;
- the repository slice is implemented and locally validated;
- the remaining closure work is live workload-cluster creation and runtime network-baseline evidence.

---

## 2. Current Baseline

Before this packet:

- `P1.5` introduced the non-prod management-cluster bootstrap path;
- `P1.6` froze the separate `platform-gitops` repository boundary and the first cluster bootstrap surface;
- no canonical workload-cluster id, cluster contract, or network-baseline scaffold existed in the repository;
- no repo-local operator artifact existed for generating a workload-cluster manifest through a validated CAPH template path.

Observed strengths:

- the naming registry already froze the workload-cluster naming pattern and gave `nonprod-hetzner-hel1-core` as a canonical example;
- the target-state architecture already froze `MachineDeployment`, `Cilium Gateway API`, `cert-manager`, and `trust-manager` as the day-1 direction;
- `P1.5` already refused to silently trust CAPH defaults and required explicit validated provider artifacts.

Observed implementation risks:

- `P2.1` can drift into ad hoc cluster manifests unless the management-cluster-side contract is frozen now;
- network baseline can regress into `L2 announcements` or `BGP` as day-1 defaults unless the repo says otherwise explicitly;
- workload cluster repo paths can drift away from the `platform-gitops` boundary unless the scaffold is created before live infra exists.

---

## 3. Canonical Decisions For P2.1

`P2.1` fixes the following decisions:

1. The first workload cluster id is `nonprod-hetzner-hel1-core`.
2. The workload-cluster contract is reconciled from `nonprod-mgmt`.
3. `MachineDeployment` is the day-1 worker model.
4. `ClusterClass` remains out of scope for this packet because it is still frozen as experimental in the architecture baseline.
5. `MachinePool` remains out of scope for this packet.
6. Public web and control-plane HTTP(S) traffic remains behind Cloudflare.
7. The workload cluster exposes its gateway entrypoint through a provider-native L4 `LoadBalancer`.
8. In-cluster ingress is `Cilium Gateway API`.
9. `cert-manager` and `trust-manager` are part of the network substrate intent, but real add-on deployment remains a later live packet concern.
10. `Cilium` `L2 announcements` and `BGP` are fallback paths only, not the day-1 default.

---

## 4. Scope

In scope for `P2.1`:

- add a canonical helper under [infra/scripts/workload_cluster_bootstrap.py](../../infra/scripts/workload_cluster_bootstrap.py);
- render a platform-gitops-style scaffold for:
  - `clusters/nonprod-hetzner-hel1-core`
  - `infrastructure/nonprod-hetzner-hel1-core/network`
  - `apps/nonprod-hetzner-hel1-core`
  - `infrastructure/nonprod-mgmt/workload-clusters/nonprod-hetzner-hel1-core`
- render an operator-facing `clusterctl generate cluster` script with a validated template URL guard;
- render network baseline intent files and values files for:
  - `Cilium`
  - `cert-manager`
  - `trust-manager`
- add unit coverage and local render smoke for the helper;
- update operator docs and residual tracking for honest `P2.1` closure.

Out of scope for the current repository slice executed in this workspace:

- live workload-cluster creation;
- live Cilium, cert-manager, or trust-manager install;
- live Cloudflare DNS or provider load balancer mutation;
- application deployment into the workload cluster;
- production workload clusters.

---

## 5. Official Constraints

The execution of `P2.1` follows current primary-source guidance:

- Cluster API continues to treat `ClusterTopology` / `ClusterClass` as experimental, so day-1 workload-cluster bootstrap should not depend on it;
- Cilium Gateway API support is enabled with `gatewayAPI.enabled=true`;
- Cilium `L2 announcements` remain a beta feature and are not the day-1 default;
- cert-manager should be installed exactly once per cluster and the OCI Helm chart is the source of truth;
- trust-manager is installed after cert-manager, and current docs explicitly note ongoing API evolution toward `ClusterBundle`.

Primary sources:

- Cluster API experimental features: https://main.cluster-api.sigs.k8s.io/tasks/experimental-features/experimental-features
- Cilium Gateway API: https://docs.cilium.io/en/latest/network/servicemesh/gateway-api/gateway-api.html
- Cilium L2 announcements: https://docs.cilium.io/en/latest/network/l2-announcements/
- cert-manager Helm install: https://cert-manager.io/docs/installation/helm/
- trust-manager install: https://cert-manager.io/docs/trust/trust-manager/installation/
- trust-manager API evolution note: https://cert-manager.io/announcements/2025/09/05/trust-manager-clusterbundle-future/
- CAPH repository and compatibility guidance: https://github.com/syself/cluster-api-provider-hetzner

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P2.1`:

### 6.1 Helper And Tests

- [infra/scripts/workload_cluster_bootstrap.py](../../infra/scripts/workload_cluster_bootstrap.py)
- [infra/tests/test_workload_cluster_bootstrap.py](../../infra/tests/test_workload_cluster_bootstrap.py)

### 6.2 Operator Docs

- [infra/README.md](../../infra/README.md)

### 6.3 Packet Evidence

- [../evidence/platform-foundation/2026-04-22/p2-1-workload-cluster-bootstrap/evidence-pack.md](../evidence/platform-foundation/2026-04-22/p2-1-workload-cluster-bootstrap/evidence-pack.md)

---

## 7. Workboard

### 7.1 `T2.1.1` Freeze The Workload-Cluster Id And GitOps Surface

**Goal:** stop future workload-cluster work from drifting across ad hoc names and repo paths.

Deliverables:

- cluster id `nonprod-hetzner-hel1-core`
- scaffolded GitOps paths for `clusters/`, `infrastructure/`, and `apps/`
- management-cluster-side workload-cluster contract path

Acceptance criteria:

- the scaffold renders reproducibly;
- naming matches the frozen naming registry;
- the cluster-local and management-cluster-local paths are clearly separated.

### 7.2 `T2.1.2` Freeze The Management-Cluster-Side CAPI Contract

**Goal:** capture how the workload cluster is generated without baking unvalidated provider assumptions into the repo.

Deliverables:

- `workload-cluster-inputs.env`
- guarded `render-workload-cluster.sh`
- explicit operator requirement for `CAPH_TEMPLATE_URL`

Acceptance criteria:

- the script uses `clusterctl generate cluster`;
- the script refuses to proceed without an explicit operator-validated provider template URL;
- `MachineDeployment` remains the default worker model in the contract layer.

### 7.3 `T2.1.3` Freeze The Day-1 Network Baseline Intent

**Goal:** make the network substrate explicit before the cluster exists.

Deliverables:

- `edge-baseline.env`
- `cilium-values.yaml`
- `cert-manager-values.yaml`
- `trust-manager-values.yaml`
- `network/README.md`

Acceptance criteria:

- Cloudflare plus provider-native L4 is explicit;
- `Cilium Gateway API` is explicit;
- `L2 announcements` and `BGP` are explicitly non-default;
- `cert-manager` and `trust-manager` are carried as cluster-local add-on intent without pretending they are already installed.

### 7.4 `T2.1.4` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable before any real workload cluster exists.

Deliverables:

- helper unit tests;
- local render smoke;
- packet evidence pack;
- formal carry-forward residual for missing live workload-cluster and network-baseline evidence.

Acceptance criteria:

- local repo slice is validated;
- live closure requirements are explicit;
- later packets may begin without pretending the workload cluster already exists.

---

## 8. State-Boundary Rules

`P2.1` must keep the following invariants:

1. Workload-cluster desired state still belongs to `platform-gitops`, not to manual shell history.
2. The workload-cluster declaration is applied from `nonprod-mgmt`.
3. `ClusterClass` and `MachinePool` remain out of scope for the day-1 baseline.
4. Cloudflare is mandatory for public web/control-plane HTTP(S), not for VPN data-plane traffic.
5. Provider-native L4 load balancer remains the default cluster entrypoint in front of `Cilium Gateway API`.

---

## 9. Risks And Guardrails

| Risk | Why it matters | Guardrail |
|---|---|---|
| cluster manifests get invented ad hoc | later live rollout drifts away from frozen naming and repo boundaries | helper renders the management-cluster-side contract path now |
| CAPH defaults are trusted blindly | provider incompatibility or template drift leaks into the cluster contract | require explicit `CAPH_TEMPLATE_URL` at render time |
| network baseline silently falls back to beta paths | day-1 ingress posture becomes unstable | keep `L2 announcements` and `BGP` explicit as fallback only |
| `P2.1` is treated as live-complete without a real cluster | later packets assume substrate exists | carry forward a formal residual until live cluster and network-baseline evidence exist |
