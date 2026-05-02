# CyberVPN Platform Foundation P1.3 NATS Non-Prod Foundation Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live apply/bootstrap evidence pending  
**Packet:** `P1.3`  
**Primary owners:** `infra-platform` / `sre-platform`  
**Supporting owners:** `platform-architecture`, `security`

---

## 1. Packet Role

This document is the execution packet for `P1.3` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../api/platform-foundation-event-taxonomy.md](../api/platform-foundation-event-taxonomy.md)
- [../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md](../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md)

`P1.3` exists to establish the first canonical shared `NATS JetStream` control plane for the program:

- external to Kubernetes;
- canonical environment id `nonprod`;
- canonical cluster id `nats-nonprod`;
- 3-node JetStream baseline with local SSD-backed storage;
- TLS on client and route traffic;
- frozen account and subject-permission posture aligned with `T0.2`.

Implementation note:

- the repository slice for this packet is already implemented and locally validated;
- the remaining closure work is focused on live stack apply evidence, live bundle installation evidence, JetStream smoke/replay evidence, and operator-supplied backend/cloud credentials.

---

## 2. Current Baseline

Before this packet:

- the repository had no canonical `NATS` stack under [infra/terraform/live](../../infra/terraform/live);
- target-state `NATS` topology, stream domains, and consumer contract existed only at the documentation layer;
- current platform runtime still relies on polling, Redis pub/sub, and direct realtime surfaces under temporary exceptions `EX-008`, `EX-009`, and `EX-010`;
- no shared non-prod event backbone existed for later outbox, realtime gateway, or fleet-automation work.

Observed strengths:

- `T0.2` already froze canonical event domains and subject versioning;
- `P1.1` already established `OpenTofu` as the canonical IaC engine;
- Hetzner provider and remote-state patterns already exist in the repo;
- existing Prometheus and firewall patterns are reusable enough to host an external event control plane.

Observed implementation risks:

- a new `NATS` stack can accidentally drift back into legacy `staging` naming unless canonical ids are repeated everywhere;
- monitoring can be overexposed if the local NATS monitor port is treated like a normal metrics endpoint;
- generated bootstrap bundles can become ad hoc and unsafe unless TLS, route credentials, and account permissions are rendered consistently;
- exporter targets can silently collide with existing `alloy-edge` file_sd if Prometheus globs are not narrowed intentionally.

---

## 3. Canonical Decisions For P1.3

`P1.3` fixes the following decisions:

1. `NATS JetStream` remains outside Kubernetes on dedicated VMs.
2. The first implementation path is `infra/terraform/live/staging/nats`, but the canonical environment id inside the stack is `nonprod`.
3. The canonical cluster id is `nats-nonprod`.
4. The non-prod baseline is a 3-node JetStream cluster.
5. JetStream storage uses node-local disk only; no shared filesystem posture is introduced.
6. NATS client traffic and route traffic are both TLS-enabled.
7. The NATS monitoring port is loopback-only on each node.
8. Prometheus scraping uses a separate `prometheus-nats-exporter` process on a firewalled port.
9. The first bootstrap path renders config, TLS, account credentials, and per-node install scripts out of band.
10. The initial account posture is a bounded non-prod baseline, not the final production multi-account mesh.

---

## 4. Scope

In scope for `P1.3`:

- add a dedicated `NATS` VM module under [infra/terraform/modules/nats_node](../../infra/terraform/modules/nats_node);
- add a non-prod implementation stack under [infra/terraform/live/staging/nats](../../infra/terraform/live/staging/nats);
- create the canonical `nats-nonprod` 3-node layout, firewall, and remote-state boundary;
- add pinned cloud-init/systemd/bootstrap path for `nats-server` and `prometheus-nats-exporter`;
- add source-controlled example account and subject-permission posture under [infra/nats/examples](../../infra/nats/examples);
- add a canonical bootstrap helper under [infra/scripts/nats_bootstrap.py](../../infra/scripts/nats_bootstrap.py);
- add unit coverage and smoke validation for the bootstrap helper;
- add Prometheus scrape and alerting baseline for `nats-exporter`;
- update operator docs and evidence path for the new non-prod foundation.

Out of scope for `P1.3`:

- production `NATS`;
- 5-node or multi-zone JetStream topology;
- final production-grade multi-account import/export topology;
- workload cut-over from Redis pub/sub or polling to `NATS`;
- declarative stream or consumer provisioning for real services;
- backup/rebuild drill automation beyond documenting the residual for `P1.8`;
- live credential rotation or route-password rotation automation.

---

## 5. Official Constraints

The execution of `P1.3` must follow the current official `NATS` guidance:

- JetStream clustering requires unique `server_name` values, a cluster name, and a quorum-backed cluster size; the recommended baseline is `3` or `5` JetStream-enabled servers;
- JetStream should use a persisted local log on each node, ideally backed by fast SSD storage;
- the monitoring endpoint has no built-in authentication or authorization and should not be exposed publicly; binding it to localhost is explicitly recommended;
- security posture should be expressed through accounts, users, subject permissions, and TLS for client and route traffic;
- JetStream is foundational stateful infrastructure, not a hidden source of truth for business data.

Primary sources:

- JetStream clustering: https://docs.nats.io/running-a-nats-service/configuration/clustering/jetstream_clustering
- Authentication and accounts: https://docs.nats.io/running-a-nats-service/configuration/securing_nats/auth_intro
- TLS: https://docs.nats.io/running-a-nats-service/configuration/securing_nats/tls
- Monitoring: https://docs.nats.io/running-a-nats-service/configuration/monitoring
- Server configuration reference: https://docs.nats.io/running-a-nats-service/configuration

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P1.3`:

### 6.1 Infrastructure Modules And Stacks

- [infra/terraform/modules/firewall_policy](../../infra/terraform/modules/firewall_policy)
- [infra/terraform/modules/nats_node](../../infra/terraform/modules/nats_node)
- [infra/terraform/live/staging/nats](../../infra/terraform/live/staging/nats)

### 6.2 Bootstrap And Baseline Assets

- [infra/nats/examples/accounts.json.example](../../infra/nats/examples/accounts.json.example)
- [infra/scripts/nats_bootstrap.py](../../infra/scripts/nats_bootstrap.py)
- [infra/tests/test_nats_bootstrap.py](../../infra/tests/test_nats_bootstrap.py)

### 6.3 Monitoring And Operator Docs

- [infra/prometheus/prometheus.yml](../../infra/prometheus/prometheus.yml)
- [infra/prometheus/rules/nats_alerts.yml](../../infra/prometheus/rules/nats_alerts.yml)
- [infra/terraform/README.md](../../infra/terraform/README.md)
- [infra/README.md](../../infra/README.md)
- [infra/terraform/live/staging/nats/README.md](../../infra/terraform/live/staging/nats/README.md)

---

## 7. Workboard

### 7.1 `T1.3.1` Provision The Shared Non-Prod Stack Boundary

**Goal:** create one clean, isolated state object for the shared `NATS` non-prod foundation.

Deliverables:

- dedicated stack under `live/staging/nats`;
- explicit outputs for node access, ports, and exporter targets;
- separate state boundary from `foundation`, `edge`, `dns`, and legacy `control-plane`.

Acceptance criteria:

- the stack validates independently under `tofu`;
- it reads shared SSH key names from `foundation` only;
- it does not merge itself into legacy control-plane state.

### 7.2 `T1.3.2` Bootstrap Safe External NATS Nodes

**Goal:** make first boot predictable and non-ad hoc.

Deliverables:

- pinned `nats-server` and `prometheus-nats-exporter` install path through cloud-init;
- systemd units for both processes;
- loopback-only monitor port;
- TLS/config bundle install path gated out of band.

Acceptance criteria:

- no route credentials, account passwords, or private keys are written into git-tracked Terraform inputs;
- operator-created bundle install is the only supported service-start path;
- firewall exposes only SSH, client ingress, route ingress between nodes, and exporter metrics on approved CIDRs.

### 7.3 `T1.3.3` Freeze The Baseline Account, TLS, And Bootstrap Flow

**Goal:** stop config and subject-permission drift before later packets depend on them.

Deliverables:

- example accounts spec with bounded non-prod account/users posture;
- bootstrap helper that renders CA, per-node server certs, route credentials, account credentials, config, exporter env, and install scripts;
- Prometheus file_sd target artifact for `nats-exporter`.

Acceptance criteria:

- the helper renders a reproducible bundle from stack outputs and a source-controlled account spec;
- the helper does not require hand-edited ad hoc shell snippets;
- the generated output is obviously marked as sensitive and kept outside git.

### 7.4 `T1.3.4` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable without faking live NATS evidence.

Deliverables:

- `tofu validate` on the new stack;
- unit tests and local render smoke for the bootstrap helper;
- packet evidence pack documenting what is done and what still requires operator-provided credentials and live nodes.

Acceptance criteria:

- local repo slice is validated;
- residuals are written explicitly;
- later packets may begin without pretending that live NATS evidence already exists.

---

## 8. State-Boundary Rules

`P1.3` must keep the following invariants:

1. `staging/nats` is its own remote state object.
2. `staging/nats` may read `staging/foundation` through remote state for SSH key names only.
3. `staging/nats` must not write into legacy `foundation`, `edge`, `dns`, or `control-plane` state.
4. The stack path may remain under legacy `staging/`, but the canonical environment id in resource names and labels remains `nonprod`.
5. No application workload may claim `NATS` dependency readiness until real stream, consumer, replay, and credential tests exist.
6. Prometheus `file_sd` for `nats-exporter` must remain distinct from existing `alloy-edge` target discovery.

---

## 9. Risks And Guardrails

| Risk | Why it matters | Guardrail |
|---|---|---|
| local monitor port is exposed publicly | monitoring endpoint has no auth and becomes an unnecessary attack surface | bind monitor to `127.0.0.1` and expose only exporter metrics through firewall |
| shared filesystem or ad hoc storage posture creeps in | JetStream durability and failure semantics become misleading | keep JetStream on node-local disk only |
| generated credentials or CA key leak into repo | event backbone security posture collapses before workloads even use it | generate bundles out of band and treat bundle directories as sensitive |
| `alloy-edge` and `nats-exporter` file_sd targets collide | Prometheus scrapes wrong targets under the wrong job labels | narrow `alloy-edge` globs and add dedicated `nats-exporter` scrape job |
| operators assume 3 nodes means fully proven HA | later readiness claims become misleading | document 3-node non-prod as topology baseline only; live failure drills remain pending |
| bounded non-prod account posture is mistaken for final production tenancy | later security posture becomes frozen too early | describe current account model as non-prod foundation only |

---

## 10. Exit Criteria

`P1.3` is complete only when all of the following are true:

1. The dedicated `NATS` stack validates under `OpenTofu`.
2. The non-prod `NATS` VM module, stack, bootstrap helper, example account spec, and monitoring assets exist in the repository.
3. Operator docs point to the new stack and bootstrap helper.
4. A real non-prod stack apply has been executed against a real backend and cloud credentials.
5. The rendered bootstrap bundle has been installed on all three nodes.
6. Live evidence exists for:
   - successful cluster formation;
   - at least one JetStream stream create/publish/consume path;
   - at least one replay test;
   - at least one Prometheus scrape of `nats-exporter`;
   - at least one bounded credential rotation or credential replacement rehearsal.

Until then, `P1.3` may be described only as:

- repository slice implemented;
- local validation complete;
- live non-prod cut-in pending.
