# CyberVPN Platform Foundation P1.5 Non-Prod Management Cluster Foundation Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live apply/bootstrap/provider evidence pending  
**Packet:** `P1.5`  
**Primary owners:** `infra-platform` / `platform-architecture`  
**Supporting owners:** `security`, `sre-platform`

---

## 1. Packet Role

This document is the execution packet for `P1.5` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [2026-04-21-platform-foundation-naming-and-boundary-registry.md](2026-04-21-platform-foundation-naming-and-boundary-registry.md)
- [../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md](../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md)

`P1.5` exists to establish the first canonical non-prod Kubernetes management substrate for the program:

- canonical management-cluster id `nonprod-mgmt`;
- Talos Linux plus upstream Kubernetes;
- one control-plane node and two worker nodes in the initial non-prod posture;
- reserved Kubernetes API endpoint IP without introducing an external load balancer on day 1;
- Cluster API core plus Talos bootstrap/control-plane provider installation path;
- explicit Hetzner provider pinning workflow that does not silently fall back to an incompatible stable release line.

Implementation note:

- the repository slice for this packet is already implemented and locally validated;
- the stack currently pins the latest resolvable stable `siderolabs/talos` provider line, `v0.10.1`, and records it in the stack-local lockfile;
- the remaining closure work is focused on live Hetzner apply/bootstrap evidence, live Talos and kubeconfig retrieval evidence, and real provider-install evidence on the running management cluster.

---

## 2. Current Baseline

Before this packet:

- the repository had no canonical `nonprod-mgmt` stack;
- there was no Talos-based management cluster bootstrap path under `infra/terraform/live`;
- there was no frozen bootstrap helper for Cluster API/Talos provider installation;
- the repo had no safe answer for the current upstream mismatch between supported `CAPI v1.13.x` and the latest stable `CAPH v1.0.x` release line.

Observed strengths:

- `P1.1` already established `OpenTofu` as the canonical IaC engine and preserved state boundaries;
- the target-state architecture already froze `nonprod-mgmt` as a separate Talos management cluster;
- current helper and packet discipline patterns already exist from `P1.2` through `P1.4`;
- current official Talos and Cluster API docs support the selected baseline versions.

Observed implementation risks:

- falling back to `clusterctl` defaults for Hetzner would currently select `CAPH v1.0.x`, which upstream documents as incompatible with `CAPI v1.11+`;
- using a load balancer for day-1 single-control-plane non-prod would add complexity without improving the initial failure model materially;
- management-cluster bootstrap can accidentally drift back into `staging` naming unless canonical ids are repeated across stack outputs, docs, and helper bundles.

---

## 3. Canonical Decisions For P1.5

`P1.5` fixes the following decisions:

1. The first management cluster implementation path is `infra/terraform/live/staging/nonprod-mgmt`, but the canonical environment id remains `nonprod`.
2. The canonical management-cluster id is `nonprod-mgmt`.
3. Day-1 non-prod topology is exactly one control-plane node and at least two worker nodes.
4. Day-1 Kubernetes API exposure uses a reserved primary IPv4 attached to the first control-plane node, not a dedicated Hetzner load balancer.
5. Talos node bootstrap uses the official `siderolabs/talos` provider for machine secrets, machine configuration apply, bootstrap, and kubeconfig retrieval.
6. The day-1 bootstrap stack provisions raw Talos-capable nodes and applies configuration after node creation; it does not template ad hoc Talos YAML into git-tracked files.
7. `clusterctl init` installs Cluster API core plus Talos bootstrap/control-plane providers only.
8. The Hetzner infrastructure provider is kept as an explicit pinned follow-up install step because the latest stable `CAPH v1.0.x` release line is upstream-documented as incompatible with `CAPI v1.11+`.
9. The rendered helper bundle is the canonical operator path for provider-install commands and version pinning.

---

## 4. Scope

In scope for `P1.5`:

- add a reusable Talos node module under [infra/terraform/modules/talos_node](../../infra/terraform/modules/talos_node);
- add a non-prod management-cluster stack under [infra/terraform/live/staging/nonprod-mgmt](../../infra/terraform/live/staging/nonprod-mgmt);
- add the reserved Kubernetes API endpoint IP and restricted management-cluster firewall baseline;
- add first-pass Talos bootstrap resources and sensitive outputs for `talosconfig` and `kubeconfig`;
- add a canonical bootstrap helper under [infra/scripts/nonprod_mgmt_bootstrap.py](../../infra/scripts/nonprod_mgmt_bootstrap.py);
- add unit coverage and local render smoke for the helper;
- update operator docs and evidence path for the new non-prod management-cluster foundation.

Out of scope for `P1.5`:

- production management cluster;
- HA management control plane or external load balancer;
- workload-cluster creation through Cluster API;
- Flux bootstrap;
- Cilium, Gateway API, cert-manager workload substrate, or tenant workloads;
- final OpenBao-backed Talos secret persistence;
- final validated CAPH release-line promotion strategy beyond the explicit bundle hook.

---

## 5. Official Constraints

The execution of `P1.5` follows current primary-source guidance:

- Talos on Hetzner is supported and Hetzner-specific docs still describe bootstrap around a stable control-plane endpoint and explicit control-plane bootstrap;
- Talos `v1.12.x` supports Kubernetes `v1.35.x`;
- Cluster API `v1.13.0` supports management clusters on Kubernetes `v1.32.x` through `v1.35.x`;
- `clusterctl init` installs the latest versions by default unless providers are pinned explicitly;
- Talos providers should be installed with explicit `clusterctl` overrides because the GitHub org rename can leave default discovery ambiguous;
- CAPH upstream now documents `v1.0.x` as incompatible with `CAPI v1.11+`, while `v1.1.x` is the line intended for `CAPI v1.11+` through `v1.12+`.

Primary sources:

- Talos Hetzner install guide: https://docs.siderolabs.com/talos/v1.12/platform-specific-installations/cloud-platforms/hetzner
- Talos support matrix: https://docs.siderolabs.com/talos/v1.12/getting-started/support-matrix
- Cluster API `clusterctl init`: https://main.cluster-api.sigs.k8s.io/clusterctl/commands/init.html
- Cluster API v1.13.0 release notes: https://github.com/kubernetes-sigs/cluster-api/releases/tag/v1.13.0
- CABPT README: https://github.com/siderolabs/cluster-api-bootstrap-provider-talos
- CACPPT README: https://github.com/siderolabs/cluster-api-control-plane-provider-talos
- CAPH compatibility table (`v1.1.x` docs): https://raw.githubusercontent.com/syself/cluster-api-provider-hetzner/v1.1.x/docs/caph/01-getting-started/01-introduction.md

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P1.5`:

### 6.1 Infrastructure Modules And Stacks

- [infra/terraform/modules/talos_node](../../infra/terraform/modules/talos_node)
- [infra/terraform/modules/firewall_policy](../../infra/terraform/modules/firewall_policy)
- [infra/terraform/live/staging/nonprod-mgmt](../../infra/terraform/live/staging/nonprod-mgmt)

### 6.2 Bootstrap Assets And Tests

- [infra/scripts/nonprod_mgmt_bootstrap.py](../../infra/scripts/nonprod_mgmt_bootstrap.py)
- [infra/tests/test_nonprod_mgmt_bootstrap.py](../../infra/tests/test_nonprod_mgmt_bootstrap.py)

### 6.3 Operator Docs

- [infra/terraform/README.md](../../infra/terraform/README.md)
- [infra/README.md](../../infra/README.md)
- [infra/terraform/live/staging/nonprod-mgmt/README.md](../../infra/terraform/live/staging/nonprod-mgmt/README.md)

---

## 7. Workboard

### 7.1 `T1.5.1` Provision The Management-Cluster State Boundary

**Goal:** create one clean state object for the canonical `nonprod-mgmt` bootstrap.

Deliverables:

- dedicated stack under `live/staging/nonprod-mgmt`;
- separate state from `foundation`, `openbao`, `nats`, `posthog`, `edge`, and `dns`;
- explicit outputs for endpoint IP, node inventory, `talosconfig`, and `kubeconfig`.

Acceptance criteria:

- the stack validates independently under `tofu`;
- no existing state object is extended or merged;
- canonical management-cluster naming appears everywhere.

### 7.2 `T1.5.2` Freeze The Day-1 Talos Topology

**Goal:** make the non-prod management cluster reproducible and predictable.

Deliverables:

- dedicated `talos_node` module;
- reserved Kubernetes API endpoint IP;
- one control-plane and at least two worker nodes;
- management firewall with Talos API, Kubernetes API, and node-mesh rules.

Acceptance criteria:

- the initial topology matches the frozen target state;
- the bootstrap path does not require ad hoc SSH setup;
- day-1 non-prod does not depend on a Hetzner load balancer.

### 7.3 `T1.5.3` Establish The Talos Bootstrap And Provider-Install Path

**Goal:** make post-apply operator actions explicit and pinned.

Deliverables:

- Talos provider resources for machine config apply, bootstrap, and kubeconfig retrieval;
- bootstrap helper bundle for `clusterctl` and follow-up provider installation;
- explicit version pins for `CAPI`, `CABPT`, and `CACPPT`;
- explicit `CAPH` pinning hook with upstream compatibility note.

Acceptance criteria:

- Talos provider resources are declared in the stack;
- helper output is reproducible and sensitive-output aware;
- the bundle refuses to silently install the wrong Hetzner provider line.

### 7.4 `T1.5.4` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable without faking live Talos/Hetzner evidence.

Deliverables:

- `tofu validate` on the new stack;
- unit tests and local render smoke for the helper;
- packet evidence pack documenting what is complete and what still requires operator-provided live inputs.

Acceptance criteria:

- local repo slice is validated;
- live closure requirements are written explicitly;
- later packets may begin without pretending that `nonprod-mgmt` already exists.

---

## 8. State-Boundary Rules

`P1.5` must keep the following invariants:

1. `staging/nonprod-mgmt` is a separate remote state object.
2. `staging/nonprod-mgmt` does not read legacy host bootstrap state from `foundation`.
3. The canonical ids remain `environment = nonprod` and `management_cluster_id = nonprod-mgmt`.
4. The reserved Kubernetes API endpoint IP belongs only to this stack.
5. `clusterctl` default Hetzner provider discovery must not be trusted implicitly for this packet.
6. No workload-cluster packet may claim readiness until real management-cluster bootstrap and provider-install evidence exists.

---

## 9. Risks And Guardrails

| Risk | Why it matters | Guardrail |
|---|---|---|
| single-control-plane endpoint drifts or changes | later bootstrap steps and operator configs become unstable | use a reserved primary IPv4 for the Kubernetes API endpoint |
| management firewall is too narrow | Talos bootstrap or default Flannel traffic fails silently | keep admin-only API exposure but allow node-mesh TCP/UDP between cluster nodes |
| `clusterctl` installs the default stable Hetzner provider line | management cluster receives an upstream-incompatible infrastructure provider | install core and Talos providers first; require explicit `CAPH_COMPONENTS_URL` |
| Talos bootstrap secrets are treated as casual outputs | operator credentials or machine secrets leak | mark outputs sensitive and document out-of-band storage only |
| repo slice is treated as full closure | later packets assume a live management cluster exists already | carry forward a formal residual until live apply/bootstrap/provider evidence is attached |
