# CyberVPN Platform Foundation P2.9 Production Management Cluster Foundation Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live production apply/bootstrap/provider evidence pending  
**Packet:** `P2.9`  
**Primary owners:** `infra-platform` / `platform-architecture`  
**Supporting owners:** `sre-platform`, `security`, `docs-program`

---

## 1. Packet Role

This document is the execution packet for `P2.9` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [2026-04-21-platform-foundation-naming-and-boundary-registry.md](2026-04-21-platform-foundation-naming-and-boundary-registry.md)
- [../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md](../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md)

`P2.9` exists to establish the first canonical production Kubernetes management substrate for
the program:

- canonical management-cluster id `prod-mgmt`;
- Talos Linux plus upstream Kubernetes;
- at least three control-plane nodes and at least two worker nodes in the initial production posture;
- provider-native L4 load balancer for the stable Kubernetes API endpoint;
- Cluster API core plus Talos bootstrap/control-plane provider installation path;
- explicit Hetzner provider pinning workflow that does not silently fall back to an incompatible stable release line.

Implementation note:

- the repository slice for this packet is already implemented and locally validated;
- the stack pins the same validated stable provider set as `P1.5`:
  - `hetznercloud/hcloud v1.60.1`
  - `siderolabs/talos v0.10.1`
- the remaining closure work is focused on live production Hetzner apply/bootstrap evidence,
  live load-balancer endpoint evidence, live Talos and kubeconfig retrieval evidence, and real
  provider-install evidence on the running management cluster.

---

## 2. Current Baseline

Before this packet:

- `P1.5` established the first canonical non-prod management-cluster path under
  `infra/terraform/live/staging/nonprod-mgmt`;
- the repository had no canonical `prod-mgmt` stack;
- there was no production management-cluster bootstrap path under `infra/terraform/live/production`;
- the repo had no frozen answer for the production Kubernetes API endpoint beyond a single-node
  reserved IP posture inherited from the non-prod packet;
- the repo already carried the current upstream mismatch between supported `CAPI v1.13.x` and the
  latest stable `CAPH v1.0.x` release line.

Observed strengths:

- `P1.1` already established `OpenTofu` as the canonical IaC engine and preserved state boundaries;
- the target-state architecture already froze `prod-mgmt` as a separate Talos management cluster;
- `P1.5` already established the helper, Talos provider, and packet discipline patterns needed here;
- current official Talos, Cluster API, and Hetzner load-balancer docs support the selected baseline.

Observed implementation risks:

- copying the non-prod single-endpoint pattern into production would reintroduce a control-plane
  single point of failure for the canonical Kubernetes API endpoint;
- production bootstrap can accidentally drift back into legacy `production` naming unless canonical
  ids are repeated across stack outputs, docs, and helper bundles;
- falling back to `clusterctl` defaults for Hetzner would still currently select `CAPH v1.0.x`,
  which upstream documents as incompatible with `CAPI v1.11+`.

---

## 3. Canonical Decisions For P2.9

`P2.9` fixes the following decisions:

1. The first production management-cluster implementation path is `infra/terraform/live/production/prod-mgmt`, but the canonical environment id remains `prod`.
2. The canonical management-cluster id is `prod-mgmt`.
3. Day-1 production topology is at least three control-plane nodes and at least two worker nodes.
4. Day-1 Kubernetes API exposure uses a dedicated Hetzner L4 load balancer, not a single primary IP attached to one control-plane node.
5. Talos node bootstrap uses the official `siderolabs/talos` provider for machine secrets, machine configuration apply, bootstrap, and kubeconfig retrieval.
6. The production stack provisions raw Talos-capable nodes and applies configuration after node creation; it does not template ad hoc Talos YAML into git-tracked files.
7. `clusterctl init` installs Cluster API core plus Talos bootstrap/control-plane providers only.
8. The Hetzner infrastructure provider remains an explicit pinned follow-up install step because the latest stable `CAPH v1.0.x` release line is upstream-documented as incompatible with `CAPI v1.11+`.
9. The rendered helper bundle is the canonical operator path for provider-install commands and version pinning for `prod-mgmt`.

---

## 4. Scope

In scope for `P2.9`:

- add a production management-cluster stack under [infra/terraform/live/production/prod-mgmt](../../infra/terraform/live/production/prod-mgmt);
- add the provider-native L4 Kubernetes API endpoint and production firewall baseline;
- add first-pass Talos bootstrap resources and sensitive outputs for `talosconfig` and `kubeconfig`;
- add a canonical bootstrap helper under [infra/scripts/prod_mgmt_bootstrap.py](../../infra/scripts/prod_mgmt_bootstrap.py);
- add unit coverage and local render smoke for the helper;
- update operator docs and evidence path for the new production management-cluster foundation.

Out of scope for `P2.9`:

- production workload-cluster creation through Cluster API;
- production Flux bootstrap;
- production workload cutover;
- MachineHealthCheck, autoscaling, or workload-cluster remediation policies;
- Cloudflare workload-edge mapping for production workloads;
- final OpenBao-backed Talos secret persistence;
- final validated CAPH release-line promotion strategy beyond the explicit bundle hook.

---

## 5. Official Constraints

The execution of `P2.9` follows current primary-source guidance:

- Talos on Hetzner is supported and Hetzner-specific docs still describe bootstrap around a stable control-plane endpoint and explicit control-plane bootstrap;
- Talos `v1.12.x` supports Kubernetes `v1.35.x`;
- Cluster API `v1.13.0` supports management clusters on Kubernetes `v1.32.x` through `v1.35.x`;
- `clusterctl init` installs the latest versions by default unless providers are pinned explicitly;
- Talos providers should be installed with explicit `clusterctl` overrides because the GitHub org rename can leave default discovery ambiguous;
- Hetzner load balancers are first-class provider resources and are the correct production substrate for a stable Kubernetes API endpoint in this provider baseline;
- CAPH upstream documents `v1.0.x` as incompatible with `CAPI v1.11+`, while `v1.1.x` is the line intended for `CAPI v1.11+` through `v1.12+`.

Primary sources:

- Talos Hetzner install guide: https://docs.siderolabs.com/talos/v1.12/platform-specific-installations/cloud-platforms/hetzner
- Talos support matrix: https://docs.siderolabs.com/talos/v1.12/getting-started/support-matrix
- Cluster API `clusterctl init`: https://main.cluster-api.sigs.k8s.io/clusterctl/commands/init.html
- Cluster API v1.13.0 release notes: https://github.com/kubernetes-sigs/cluster-api/releases/tag/v1.13.0
- Hetzner load balancer overview: https://docs.hetzner.com/cloud/load-balancers/overview/
- Hetzner Terraform provider load-balancer schema: https://registry.terraform.io/providers/hetznercloud/hcloud/latest/docs/data-sources/load_balancer
- CABPT README: https://github.com/siderolabs/cluster-api-bootstrap-provider-talos
- CACPPT README: https://github.com/siderolabs/cluster-api-control-plane-provider-talos
- CAPH compatibility table (`v1.1.x` docs): https://raw.githubusercontent.com/syself/cluster-api-provider-hetzner/v1.1.x/docs/caph/01-getting-started/01-introduction.md

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P2.9`:

### 6.1 Infrastructure Stack

- [infra/terraform/live/production/prod-mgmt](../../infra/terraform/live/production/prod-mgmt)

### 6.2 Bootstrap Assets And Tests

- [infra/scripts/prod_mgmt_bootstrap.py](../../infra/scripts/prod_mgmt_bootstrap.py)
- [infra/tests/test_prod_mgmt_bootstrap.py](../../infra/tests/test_prod_mgmt_bootstrap.py)

### 6.3 Operator Docs

- [infra/terraform/README.md](../../infra/terraform/README.md)
- [infra/README.md](../../infra/README.md)
- [infra/terraform/live/production/prod-mgmt/README.md](../../infra/terraform/live/production/prod-mgmt/README.md)

---

## 7. Workboard

### 7.1 `T2.9.1` Provision The Production Management-Cluster State Boundary

**Goal:** create one clean state object for the canonical `prod-mgmt` bootstrap.

Deliverables:

- dedicated stack under `live/production/prod-mgmt`;
- separate state from `foundation`, `edge`, `dns`, `control-plane`, and all non-prod stacks;
- explicit outputs for the load-balancer endpoint, node inventory, `talosconfig`, and `kubeconfig`.

Acceptance criteria:

- the stack validates independently under `tofu`;
- no existing state object is extended or merged;
- canonical `prod` and `prod-mgmt` naming appears everywhere.

### 7.2 `T2.9.2` Freeze The Production Talos Topology And API Endpoint

**Goal:** make the production management cluster reproducible and predictable.

Deliverables:

- provider-native L4 endpoint for the Kubernetes API;
- at least three control-plane nodes;
- at least two worker nodes;
- management firewall with Talos API, Kubernetes API, and node-mesh rules.

Acceptance criteria:

- the topology matches the frozen target state;
- the bootstrap path does not rely on a single control-plane IP;
- the load balancer is the authoritative Kubernetes API endpoint for this packet.

### 7.3 `T2.9.3` Establish The Production Bootstrap And Provider-Install Path

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

### 7.4 `T2.9.4` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable without faking live production evidence.

Deliverables:

- `tofu validate` on the new stack;
- unit tests and local render smoke for the helper;
- packet evidence pack documenting what is complete and what still requires operator-provided live inputs.

Acceptance criteria:

- local repo slice is validated;
- live closure requirements are written explicitly;
- later `P2` and `P3` work may proceed without pretending that `prod-mgmt` already exists.

---

## 8. State-Boundary Rules

`P2.9` must keep the following invariants:

1. `production/prod-mgmt` is a separate remote state object.
2. `production/prod-mgmt` does not read legacy host bootstrap state from `foundation`.
3. The canonical ids remain `environment = prod` and `management_cluster_id = prod-mgmt`.
4. The provider-native L4 endpoint belongs only to this stack.
5. `clusterctl` default Hetzner provider discovery must not be trusted implicitly for this packet.
6. No production workload packet may claim readiness until real `prod-mgmt` bootstrap and provider-install evidence exists.

---

## 9. Risks And Guardrails

| Risk | Why it matters | Guardrail |
|---|---|---|
| production API endpoint drifts back to a single node | reintroduces a control-plane single point of failure | freeze a dedicated Hetzner load balancer for the Kubernetes API |
| management firewall is too narrow | Talos bootstrap or default Flannel traffic fails silently | keep admin-only Talos access, allow load-balancer plus cluster-node Kubernetes API ingress, and allow node-mesh TCP/UDP |
| `clusterctl` installs the default stable Hetzner provider line | management cluster receives an upstream-incompatible infrastructure provider | install core and Talos providers first; require explicit `CAPH_COMPONENTS_URL` |
| Talos bootstrap secrets are treated as casual outputs | operator credentials or machine secrets leak | mark outputs sensitive and document out-of-band storage only |
| repo slice is treated as full closure | later packets assume a live production substrate exists already | carry forward a formal residual until live apply/bootstrap/load-balancer/provider evidence is attached |
