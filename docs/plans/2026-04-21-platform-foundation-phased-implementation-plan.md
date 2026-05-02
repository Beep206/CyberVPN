# CyberVPN Platform Foundation Phased Implementation Plan

**Date:** 2026-04-21  
**Status:** Canonical phased execution companion  
**Purpose:** translate the platform foundation target-state architecture into an executable multi-phase rollout program with explicit dependencies, temporary exceptions, monorepo impact, validation gates, and production-readiness criteria.

---

## 1. Document Role

This document is the execution companion to the CyberVPN platform foundation target-state architecture.

It exists to answer:

- what must be built first and what must wait;
- which workstreams can run in parallel;
- which temporary exceptions are allowed during migration;
- what counts as phase-complete evidence;
- how the monorepo changes across the program;
- what must be true before implementation moves from non-production to production-critical cutovers.

This document should be read together with:

- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)

This document is not:

- the canonical target-state architecture;
- a ticket-by-ticket engineering backlog;
- a cutover runbook;
- a team staffing plan.

Those are separate companion artifacts.

---

## 2. Execution Principles

The rollout follows these principles:

1. No throwaway MVP stack is allowed. Every phase must build toward the final operating model.
2. Contract and governance freeze comes before irreversible platform implementation.
3. Foundational control planes must exist before workload migration depends on them.
4. `prod` and `non-prod` remain separate control surfaces even when implementation starts in `non-prod`.
5. One canonical path per concern must replace parallel patterns rather than coexist indefinitely.
6. Manual procedures may survive only as documented temporary exceptions with removal deadlines.
7. External VPN fleet automation is a first-class platform concern, not late hardening.
8. Product analytics and operational observability remain separate domains throughout the rollout.
9. Event-driven delivery must be built on authoritative state boundaries, not as direct publish-from-handler shortcuts.
10. No phase is complete without validation evidence, recovery evidence, and explicit exit gates.

---

## 3. Dependency Order

The program follows this hard dependency order:

1. freeze contracts, taxonomies, ownership, privacy, and phase gates;
2. establish external control planes and trust anchors;
3. bootstrap management substrate and GitOps control plane;
4. establish secrets delivery, observability, PKI, and backup baselines;
5. establish event backbone and durable consumer contracts;
6. migrate platform workloads to Kubernetes and GitOps;
7. build external fleet control loop on top of OpenTofu, OpenBao, and NATS;
8. build product analytics and experiment layer on top of authoritative event and privacy boundaries;
9. execute hardening, drills, and production conformance validation.

This means:

- `Node Fleet Controller` cannot be treated as “just a service to build later” if external node provisioning is still manual.
- `NATS` cannot be cut into critical paths before outbox and consumer contracts exist.
- `PostHog` cannot be considered rolled out before privacy controls and server-side commercial-event paths exist.
- `Flux` cannot become the source of deployment truth before `OpenBao`, base cluster services, and observability exist in the target shape.

---

## 4. Workstream Topology

| Workstream | Scope | Primary outputs |
|---|---|---|
| `WS0` Governance, Contracts, And Standards | phase governance, naming, event taxonomy, privacy rules, exit criteria, temporary exceptions | frozen contracts and acceptance model |
| `WS1` Control Planes And Trust Anchors | OpenTofu migration, AWS KMS, OpenBao, NATS, PostHog infrastructure foundations | external control-plane substrate |
| `WS2` Kubernetes Management And Platform Substrate | Talos management clusters, Cluster API, GitOps, cert-manager, trust-manager, Gateway API baseline | workload platform substrate |
| `WS3` Observability And DR | Alloy migration, LGTM stack, backup/restore, CNPG, Velero, drills, alerts | operations and recovery baseline |
| `WS4` Eventing And Realtime Delivery | outbox standard, dispatcher, streams, consumers, realtime gateways, replay tooling | durable event backbone |
| `WS5` Fleet Automation | Node Fleet Controller, executor safety, node enrollment, runtime adapters, failover policy | external fleet control loop |
| `WS6` Product Intelligence | PostHog rollout, product taxonomy, server-side analytics bridge, flags, experiments | product analytics and rollout controls |
| `WS7` Workload Migration And Production Hardening | application Helm packaging, Flux cutover, progressive delivery, conformance, residual retirement | full target-state conformance |

`WS0` spans the full program. `WS1` through `WS4` start earliest. `WS5` and `WS6` begin once foundations are ready. `WS7` closes the program.

---

## 5. Phase Overview

| Phase | Primary focus | Main workstreams | Major unlocks |
|---|---|---|---|
| `P0` | contract freeze and execution scaffold | `WS0` | frozen vocabulary, governance, and migration rules |
| `P1` | foundational control planes and non-prod substrate | `WS1`, `WS2`, `WS3` | OpenBao, NATS, PostHog, Talos/CAPI/GitOps foundations |
| `P2` | platform workload substrate and core cut-in | `WS2`, `WS3`, `WS4`, `WS7` | GitOps-managed clusters, secrets delivery, observability, event backbone in real workloads |
| `P3` | external fleet automation, product intelligence, and production conformance | `WS4`, `WS5`, `WS6`, `WS7` | Node Fleet Controller, PostHog authoritative paths, prod hardening, drills, full conformance |

Parallelism model:

- `P1` allows `NATS` and `PostHog` foundations to run in parallel after `P0` freezes contracts and privacy rules.
- `P2` allows observability migration, Kubernetes platform services, and outbox/event work to run in parallel once the base substrate exists.
- `P3` allows `Node Fleet Controller` and `PostHog` integration work to run in parallel once NATS, OpenBao, and GitOps-backed workload deployment exist.

---

## 6. Detailed Phase Decomposition

## 6.1 Phase P0. Contract Freeze And Execution Mobilization

**Goal:** remove ambiguity before foundational control planes and migration code begin.

**Entry prerequisites:**

- target-state architecture accepted;
- canonical decisions index accepted.

**Implementation packets:**

| Packet | Description | Main workstreams | Blocking inputs |
|---|---|---|---|
| `P0.1` | freeze canonical naming for environments, clusters, providers, regions, node classes, repos, and secrets paths | `WS0` | target-state architecture |
| `P0.2` | freeze event taxonomy, canonical event envelope, stream domains, and consumer contract template | `WS0`, `WS4` | target-state architecture |
| `P0.3` | freeze OpenBao path conventions, namespace model, auth mount naming, and PKI naming | `WS0`, `WS1` | target-state architecture |
| `P0.4` | freeze product analytics taxonomy, blocked-property list, privacy baseline, and feature-flag governance | `WS0`, `WS6` | target-state architecture |
| `P0.5` | freeze Node Fleet Controller durable data model, lifecycle state machine, and operator command model | `WS0`, `WS5` | target-state architecture |
| `P0.6` | perform monorepo-wide inventory of current deploy paths, collectors, secrets sprawl, manual node procedures, and existing event flows | `WS0`, `WS3`, `WS4`, `WS5` | repository state |
| `P0.7` | define phase gates, evidence templates, and conformance scoring model | `WS0` | target-state architecture |
| `P0.8` | define temporary exceptions register and removal deadlines | `WS0` | repository state |

**Monorepo impact areas:**

- `docs/plans/`
- `docs/runbooks/`
- `docs/security/`
- `infra/`
- `.github/workflows/`
- architecture and prompt docs that still describe retired patterns

**Primary outputs:**

- frozen event and analytics vocabulary;
- frozen fleet state and lifecycle vocabulary;
- documented temporary exceptions register;
- baseline inventory of legacy deployment and observability patterns;
- phase evidence template and conformance scoring model.

**Temporary exceptions allowed at phase exit:**

- manual Docker Compose deploys continue;
- Ansible remains active for current fleet;
- Promtail and legacy OTEL references may still exist, but every occurrence must be inventoried;
- no critical production path may depend on NATS or PostHog yet.

**Phase exit evidence:**

- approved glossary and standards pack;
- approved event and analytics taxonomy pack;
- approved fleet state and control contract pack;
- approved temporary exceptions register;
- repository inventory report covering `infra`, `backend`, `services`, `frontend`, `partner`, `admin`, and docs.
- authoritative closure record:
  - [../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md](../evidence/platform-foundation/phase-0-signoff-and-blocker-pack.md)

---

## 6.2 Phase P1. Foundational Control Planes And Non-Prod Substrate

**Goal:** establish the external control planes and non-production substrate required for all later migrations.

**Entry prerequisites:**

- Phase `P0` complete.

**Implementation packets:**

| Packet | Description | Main workstreams | Blocking inputs |
|---|---|---|---|
| `P1.1` | migrate current Terraform estate to OpenTofu-compatible operation and clean state boundaries | `WS1` | `P0.1`, `P0.6` |
| `P1.2` | provision `non-prod OpenBao` with AWS KMS auto-unseal, Raft storage, auth mounts, policies, and bootstrap automation | `WS1` | `P0.3` |
| `P1.3` | provision `shared non-prod NATS JetStream` with TLS, accounts, subject permissions, storage layout, monitoring, and alerting | `WS1`, `WS4` | `P0.2` |
| `P1.4` | provision `non-prod PostHog` with dedicated VM/Docker deployment, reverse proxy, TLS, baseline backup, and access controls | `WS1`, `WS6` | `P0.4` |
| `P1.5` | bootstrap `nonprod-mgmt` Talos management cluster and install Cluster API plus required providers | `WS2` | `P1.1` |
| `P1.6` | create separate `platform-gitops` repository and bootstrap Flux control path in non-prod | `WS2` | `P1.5` |
| `P1.7` | establish non-prod observability substrate for new control planes, including Alloy-only collection for newly introduced systems | `WS3` | `P1.2`, `P1.3`, `P1.4`, `P1.5` |
| `P1.8` | establish baseline backup and restore for OpenBao, NATS, management-cluster etcd metadata, and PostHog | `WS3` | `P1.2`, `P1.3`, `P1.4`, `P1.5` |

**Parallelism notes:**

- `P1.3` and `P1.4` may run in parallel once contracts and privacy rules are frozen.
- `P1.5` may begin after `P1.1` even while `P1.2` through `P1.4` are progressing.
- `P1.7` and `P1.8` begin as each foundational component becomes available.

**Monorepo impact areas:**

- `infra/terraform/`
- `infra/ansible/`
- `infra/docker-compose.yml`
- `infra/grafana/`, `infra/prometheus/`, `infra/loki/`, `infra/tempo/`
- new platform bootstrap docs and runbooks
- `.github/workflows/` for GitOps bootstrap and validation

**Primary outputs:**

- working non-prod external control planes for `OpenBao`, `NATS`, and `PostHog`;
- bootstrapped `nonprod-mgmt` cluster;
- working `Flux` bootstrap path and `platform-gitops` repo baseline;
- non-prod monitoring and backup baselines for control-plane components.

**Temporary exceptions allowed at phase exit:**

- legacy workload deployment may still use Compose or manual host rollout;
- `prod` may still rely on current runtime shape;
- existing apps may still read legacy `.env` sources until secrets migration begins;
- Promtail may still exist on old stacks, but all new stacks must use Alloy-only patterns.
- `EX-013` may remain temporarily only as a carry-forward exception while `P1.2+` starts; it still blocks `P1.1 complete`, `P1 complete`, and `Gate B passed` until real remote-backend OpenTofu evidence is attached.
- `EX-014` may remain temporarily only as a carry-forward exception while `P1.3+` starts; it still blocks `P1.2 complete`, `P1 complete`, and `Gate B passed` until real non-prod OpenBao apply/bootstrap evidence is attached.
- `EX-015` may remain temporarily only as a carry-forward exception while `P1.4+` starts; it still blocks `P1.3 complete`, `P1 complete`, and `Gate B passed` until real shared non-prod NATS apply/bootstrap/smoke evidence is attached.
- `EX-016` may remain temporarily only as a carry-forward exception while `P1.5+` starts; it still blocks `P1.4 complete`, `P1 complete`, and `Gate B passed` until real non-prod PostHog apply/bundle/proxy/TLS/capture evidence is attached.
- `EX-017` may remain temporarily only as a carry-forward exception while `P1.6+` starts; it still blocks `P1.5 complete`, `P1 complete`, and `Gate B passed` until real non-prod management-cluster apply/bootstrap/provider-install evidence is attached.
- `EX-018` may remain temporarily only as a carry-forward exception while `P1.7+` starts; it still blocks `P1.6 complete`, `P1 complete`, and `Gate B passed` until real `platform-gitops` bootstrap and Flux reconciliation evidence is attached.
- `EX-019` may remain temporarily only as a carry-forward exception while `P1.8+` starts; it still blocks `P1.7 complete`, `P1 complete`, and `Gate B passed` until real external control-plane Alloy rollout, Prometheus scrape, Loki ingest, and Grafana evidence are attached.
- `EX-020` may remain temporarily only as a carry-forward exception after `P1.8` repo-slice completion; it still blocks `P1.8 complete`, `P1 complete`, and `Gate B passed` until real control-plane backup captures and restore or rebuild evidence are attached.

**Phase exit evidence:**

- successful OpenBao unseal, auth, and secret-read tests in non-prod;
- successful NATS stream creation, publish, consumer, replay, and credential rotation tests in non-prod;
- successful PostHog self-host access, proxy, capture, and backup smoke tests in non-prod;
- successful Talos management cluster bootstrap evidence;
- GitOps repository bootstrap and first reconciliation evidence;
- restore drill evidence for at least one OpenBao snapshot and one NATS backup/rebuild scenario.

---

## 6.3 Phase P2. Platform Workload Substrate And Core Cut-In

**Goal:** establish Kubernetes workload substrate, GitOps delivery, secrets delivery, observability, and event backbone inside real platform workloads.

**Entry prerequisites:**

- Phase `P1` complete.

Pre-launch execution note:

- before formal `P1` closure, `P2` packets may proceed only as `repo/validation` slices;
- those slices do not override the formal `P1`-complete prerequisite for `P2` as a phase;
- every such slice must carry an explicit blocking residual until live substrate evidence exists.

**Implementation packets:**

| Packet | Description | Main workstreams | Blocking inputs |
|---|---|---|---|
| `P2.1` | create non-prod workload cluster via Cluster API and apply network baseline: Cloudflare edge mapping, provider L4 LB, Cilium Gateway API, cert-manager, trust-manager | `WS2` | `P1.5`, `P1.6` |
| `P2.2` | deploy base platform services in non-prod through Flux: cert-manager, trust-manager, operator-based OpenBao integration, Alloy, Loki, Tempo, kube-prometheus-stack; no standalone ingress controller beyond the frozen `Cilium Gateway API` substrate | `WS2`, `WS3` | `P1.2`, `P1.6`, `P2.1` |
| `P2.3` | implement repo-wide Alloy migration plan for all new Kubernetes and VM targets, and begin retiring Promtail/legacy OTEL assumptions | `WS3` | `P0.6`, `P1.7`, `P2.2` |
| `P2.4` | introduce CloudNativePG, Barman plugin, Velero, CSI snapshot strategy, and cluster backup orchestration in non-prod | `WS3` | `P2.1`, `P2.2` |
| `P2.5` | package first-party platform workloads as OCI Helm charts and convert deployment flow to GitHub Actions -> GitOps PR -> Flux | `WS2`, `WS7` | `P1.6`, `P2.2` |
| `P2.6` | implement transactional outbox standard, dispatcher, stream declarations, durable consumer framework, and replay tooling in backend and services | `WS4`, `WS7` | `P0.2`, `P1.3` |
| `P2.7` | introduce canonical realtime delivery path: outbox -> NATS -> projection or realtime gateway -> SSE/WebSocket delivery | `WS4`, `WS7` | `P2.6` |
| `P2.8` | migrate initial control-plane services and workers to Kubernetes + GitOps using OpenBao-backed secret delivery | `WS2`, `WS7` | `P2.2`, `P2.5`, `P2.6` |
| `P2.9` | bootstrap `prod-mgmt` cluster and prepare production substrate in parallel after non-prod evidence is sufficient | `WS1`, `WS2`, `WS3` | `P1.1`, `P1.2`, `P1.3`, `P2.1` |

**Recommended first workload candidates:**

- `services/task-worker`
- platform background consumers
- non-edge internal API services with limited external blast radius
- new realtime gateway component

**Monorepo impact areas:**

- `backend/src/`, `backend/migrations/`, `backend/tests/`
- `services/`
- `infra/`
- `.github/workflows/`
- Helm chart directories to be introduced
- docs for runbooks, alerts, and recovery

**Primary outputs:**

- non-prod Kubernetes workload cluster with target platform controllers;
- Flux-managed base platform services;
- OpenBao-backed secret delivery in Kubernetes;
- first real NATS-backed event paths in application code;
- first real realtime gateway path replacing polling for selected flows;
- first GitOps-managed application deployments.
- production management-cluster substrate prepared in repo with the frozen provider-native L4 endpoint posture.

**Temporary exceptions allowed at phase exit:**

- production workloads may still run on legacy host-based deployment;
- some low-risk browser update paths may still use old Redis pub/sub while upstream business path is being cut over;
- some legacy `.env` consumers may remain on non-migrated workloads with explicit removal tickets.
- `EX-021` may remain temporarily only as a carry-forward exception while `P2.2+` starts; it still blocks `P2.1 complete`, `P2 complete`, and `Gate C passed` until real workload-cluster creation and network-baseline evidence are attached.
- `EX-022` may remain temporarily only as a carry-forward exception while `P2.3+` starts; it still blocks `P2.2 complete`, `P2 complete`, and `Gate C passed` until real workload-cluster platform-services reconciliation and controller-readiness evidence are attached.
- `EX-023` may remain temporarily only as a carry-forward exception after `P2.3` repo-slice completion; it still blocks `P2.3 complete`, `P2 complete`, and `Gate C passed` until remaining tracked legacy collector surfaces are actually retired or replaced and the live Alloy cutover evidence is attached.
- `EX-024` may remain temporarily only as a carry-forward exception after `P2.4` repo-slice completion; it still blocks `P2.4 complete`, `P2 complete`, and `Gate C passed` until workload-cluster data-protection reconciliation, runtime credential and snapshot inputs, and live backup/restore evidence are attached.
- `EX-025` may remain temporarily only as a carry-forward exception after `P2.5` repo-slice completion; it still blocks `P2.5 complete`, `P2 complete`, and `Gate C passed` until OCI chart publication, GitOps promotion PR evidence, and first-workload Flux rollout evidence are attached.
- `EX-026` may remain temporarily only as a carry-forward exception after `P2.6` repo-slice completion; it still blocks `P2.6 complete`, `P2 complete`, and `Gate C passed` until live `PARTNER_EVENTS` stream creation, dispatcher publish evidence, durable-consumer evidence, and replay proof are attached.
- `EX-027` may remain temporarily only as a carry-forward exception after `P2.7` repo-slice completion; it still blocks `P2.7 complete`, `P2 complete`, and `Gate C passed` until a live realtime gateway, durable projection consumer, browser delivery endpoint, and one real polling replacement flow are attached.
- `EX-028` may remain temporarily only as a carry-forward exception after `P2.8` repo-slice completion; it still blocks `P2.8 complete`, `P2 complete`, and `Gate C passed` until live non-prod rollout, OpenBao-backed secret materialization, backend migration-job proof, and deploy or rollback evidence exist for the first migrated control-plane workload set.
- `EX-029` may remain temporarily only as a carry-forward exception after `P2.9` repo-slice completion; it still blocks `P2.9 complete`, `P2 complete`, and `Gate C passed` until live `prod-mgmt` apply, provider-native L4 endpoint, Talos bootstrap, and provider-install evidence are attached.

**Phase exit evidence:**

- successful deploy, rollback, and Flagger analysis in non-prod for at least one real workload;
- successful OpenBao operator-based secret delivery for at least one workload in cluster;
- successful outbox -> NATS -> consumer path for one critical event class;
- successful realtime gateway path replacing polling for one chosen dashboard flow;
- successful non-prod backup/restore drill for CNPG and Velero-managed resources;
- documented list of remaining legacy collectors and legacy deploy paths with removal phases attached.

---

## 6.4 Phase P3. External Fleet Automation, Product Intelligence, And Production Conformance

**Goal:** complete the target-state by replacing manual fleet operations, making PostHog authoritative for product intelligence, and validating production conformance.

**Entry prerequisites:**

- Phase `P2` complete;
- `prod-mgmt` substrate ready or in final readiness state;
- outbox and event contracts proven in non-prod.

**Implementation packets:**

| Packet | Description | Main workstreams | Blocking inputs |
|---|---|---|---|
| `P3.1` | build Node Fleet Controller service foundation: API, DB, reconciler, workflow engine, audit trail, and NATS adapter | `WS5` | `P0.5`, `P1.3`, `P2.5` |
| `P3.2` | implement OpenTofu executor safety model, OpenBao bootstrap manager, enrollment service, and node identity rotation model | `WS5` | `P1.1`, `P1.2`, `P3.1` |
| `P3.3` | standardize external node service baseline: Alloy, health agents, enrollment hooks, synthetic verification, runtime-adapter readiness | `WS3`, `WS5` | `P3.2` |
| `P3.4` | implement operator-driven `node-add`, `replace`, `drain`, `quarantine`, and capacity workflows through the controller | `WS5` | `P3.1`, `P3.2`, `P3.3` |
| `P3.5` | implement DPI/provider/health failover policy engine with explicit budget, rate-limit, cooldown, confidence, and approval guardrails | `WS5` | `P3.4` |
| `P3.6` | connect PostHog to canonical product event taxonomy, server-side analytics bridge, and safe feature-flag wrapper model | `WS6`, `WS4`, `WS7` | `P1.4`, `P2.6` |
| `P3.7` | introduce checkout, onboarding, partner, and retention dashboards backed by privacy-reviewed events and authoritative server-side commercial signals | `WS6` | `P3.6` |
| `P3.8` | migrate production control-plane workloads to GitOps-managed Kubernetes target state with Flux, Flagger, Alloy, CNPG, backup, and alerting in place | `WS2`, `WS3`, `WS7` | `P2.9`, `P2.*`, `P3.1` as needed |
| `P3.9` | execute production drills and conformance validation for NATS, OpenBao, PostgreSQL, GitOps recovery, PostHog, and fleet reprovisioning | all workstreams | all prior packets |

**Monorepo impact areas:**

- `services/node-fleet-controller/`
- `services/helix-adapter/` and related runtime adapters
- `backend/src/` for analytics bridge and event standards
- `frontend/`, `partner/`, `admin/` for PostHog instrumentation and feature-flag wrappers
- `infra/` for external node bootstrap, OpenTofu executor plumbing, and runbooks
- docs, runbooks, and conformance evidence packages

**Primary outputs:**

- manual node provisioning retired from steady-state operations;
- policy-driven external fleet automation in place;
- PostHog integrated as product-intelligence layer with safe boundaries;
- production workloads operating through GitOps and platform substrate;
- production drills proving target-state conformance.

**Temporary exceptions allowed at phase exit:**

- only explicitly documented legacy workloads not yet migrated, each with final removal phase and owner;
- no undocumented manual node provisioning may remain;
- no undocumented secret copy procedures may remain.

**Phase exit evidence:**

- successful `node-add`, `node-replace`, and `node-quarantine` controller-driven executions;
- successful guarded failover simulation after synthetic DPI/provider impairment;
- successful PostHog server-side commercial event capture and flag fallback tests;
- successful production-grade NATS replay and outage drill evidence;
- successful production-grade OpenBao, CNPG, GitOps, and fleet reprovisioning drills;
- successful validation against the conformance criteria listed in the target-state document.
- `EX-030` may remain temporarily only as a carry-forward exception after `P3.1`
  repo-slice completion; it still blocks `P3.1 complete`, `P3 complete`, and `Gate D`
  passed claims until a live controller deployment, durable DB persistence, and NATS
  publication evidence are attached.
- `EX-031` may remain temporarily only as a carry-forward exception after `P3.2`
  repo-slice completion; it still blocks `P3.2 complete`, `P3 complete`, and `Gate D`
  passed claims until live OpenTofu runner wiring, live OpenBao bootstrap and unwrap,
  live enrollment, and live certificate rotation evidence are attached.
- `EX-032` may remain temporarily only as a carry-forward exception after `P3.3`
  repo-slice completion; it still blocks `P3.3 complete`, `P3 complete`, and `Gate D`
  passed claims until live external-node baseline reporting, synthetic verification,
  runtime-adapter acknowledgement, and traffic-eligibility evidence are attached.
- `EX-033` may remain temporarily only as a carry-forward exception after `P3.4`
  repo-slice completion; it still blocks `P3.4 complete`, `P3 complete`, and `Gate D`
  passed claims until live operator workflow entry, node-pool reconciliation, and live
  replace/drain/quarantine evidence are attached.
- `EX-034` may remain temporarily only as a carry-forward exception after `P3.5`
  repo-slice completion; it still blocks `P3.5 complete`, `P3 complete`, and `Gate D`
  passed claims until live failover signal ingestion, guarded policy evaluation, and live
  failover workflow evidence are attached.
- `EX-035` may remain temporarily only as a carry-forward exception after `P3.6`
  repo-slice completion; it still blocks `P3.6 complete`, `P3 complete`, and `Gate D`
  passed claims until live `PostHog` authoritative capture, identified server-side flag
  evaluation, and governed frontend event evidence are attached.
- `EX-036` may remain temporarily only as a carry-forward exception after `P3.7`
  repo-slice completion; it still blocks `P3.7 complete`, `P3 complete`, and `Gate D`
  passed claims until live `PostHog` dashboard population, deployed checkout/onboarding
  capture proof, and retention follow-up evidence are attached.
- `EX-037` may remain temporarily only as a carry-forward exception after `P3.8`
  repo-slice completion; it still blocks `P3.8 complete`, `P3 complete`, and `Gate D`
  passed claims until live production workload-cluster reconciliation, `Flagger` canary
  promotion and rollback proof, `CloudNativePG` and backup evidence, and production deploy
  or rollback proof for the first control-plane workload set are attached.
- `EX-038` may remain temporarily only as a carry-forward exception after `P3.9`
  repo-slice completion; it still blocks `P3.9 complete`, `P3 complete`, and `Gate D`
  passed claims until live production drill transcripts exist for all mandatory domains,
  the final scorecard snapshot is populated with evidence-backed scores, and the final
  Gate `D` evidence pack is assembled and signed off.

---

## 7. Monorepo Change Map By Phase

| Area | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| `.github/workflows/` | inventory and standards | GitOps bootstrap and validation | OCI chart, GitOps PR, deploy, conformance CI | production gates, controller tests, drill automation |
| `infra/terraform/` | inventory | OpenTofu migration start, control-plane VM infra | workload-cluster and platform infra growth | fleet executor and production hardening |
| `infra/ansible/` | inventory and exception tagging | still active as migration bridge | reduced scope, break-glass only | retired from steady-state provisioning |
| `infra/docker-compose.yml` | inventory | legacy only | shrinking local-only role | no production authority |
| `backend/` | outbox and event standards definition | minimal prep | dispatcher, consumers, secrets, realtime path | analytics bridge, conformance cleanup |
| `services/` | service inventory | foundational service decisions | Kubernetes packaging and migration | Node Fleet Controller and final adapters |
| `frontend/`, `partner/`, `admin/` | analytics and flag contract prep | optional non-prod instrumentation scaffold | realtime and flag wrappers begin | full PostHog instrumentation and cleanup |
| `docs/runbooks/` | templates | control-plane runbooks | migration and DR runbooks | production drill evidence and closure |
| `docs/plans/` | roadmap and standards | control-plane implementation docs | execution packet docs | closure and residual tracking |

---

## 8. Temporary Exceptions Register Model

Authoritative register:

- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)

Every temporary exception must carry:

- `exception_id`
- `scope`
- `current behavior`
- `target behavior`
- `why exception exists`
- `risk if kept`
- `owning team`
- `creation phase`
- `required removal phase`
- `verification needed for removal`

Exception classes expected early in the program:

- manual Compose-based deploys;
- host-local `.env` secrets;
- Ansible-managed node procedures;
- Promtail or legacy OTEL assumptions;
- Redis pub/sub browser fan-out paths that still exist while upstream event path is being cut over;
- legacy dashboards or alerts tied to old collector names.

No exception may survive beyond `P3` without explicit architectural supersession.
No undocumented exception may survive after `T0.7`; the linked register is the source of truth.

---

## 9. Phase Gates Into Implementation

Implementation should proceed with these program-level gates:

1. `Gate A` after `P0`: contracts and taxonomies frozen, temporary exceptions documented.
2. `Gate B` after `P1`: non-prod control planes exist and can be operated safely.
3. `Gate C` after `P2`: non-prod workload substrate, GitOps, OpenBao secrets, NATS event path, and observability are working end to end.
4. `Gate D` after `P3`: external fleet automation, product intelligence, and production conformance evidence are complete.

Authoritative gate-evidence companions:

- [../evidence/platform-foundation/platform-foundation-phase-evidence-template.md](../evidence/platform-foundation/platform-foundation-phase-evidence-template.md)
- [../testing/platform-foundation-conformance-scorecard.md](../testing/platform-foundation-conformance-scorecard.md)

Interpretation rules:

- every gate claim must attach a concrete evidence pack built from the canonical phase-evidence template;
- every gate claim for `P1`, `P2`, and `P3` must include a scorecard snapshot using the canonical conformance scorecard;
- `Gate B` and `Gate C` may close on non-prod readiness evidence for in-scope systems;
- `Gate D` may close only on production-conformance evidence and satisfied scorecard floors.

If any gate fails:

- pause further rollout;
- document the blocking residual;
- attach owner and remediation phase;
- do not silently work around the failure by creating a new unofficial path.

---

## 10. Recommended Immediate Next Documents

The fastest path from roadmap into implementation is to create the following companion documents next:

1. [Platform Foundation Phase 0 Execution Packet](2026-04-21-platform-foundation-phase-0-execution-packet.md)
2. [Platform Foundation P1.1 OpenTofu Migration And State-Boundary Execution Packet](2026-04-22-platform-foundation-p1-1-opentofu-migration-and-state-boundary-execution-packet.md)
3. [Platform Foundation P1.2 OpenBao Non-Prod Foundation Execution Packet](2026-04-22-platform-foundation-p1-2-openbao-nonprod-foundation-execution-packet.md)
4. [NATS JetStream Streams, Consumers, And Replay Spec](../api/platform-foundation-nats-streams-consumers-and-replay-spec.md)
5. `Alloy Monorepo Migration Plan`
6. `Platform GitOps Bootstrap Plan`
7. `Node Fleet Controller Technical Design`
8. `PostHog Product Analytics And Privacy Spec`
9. `Platform Foundation DR And Drill Plan`

These documents should decompose the roadmap into implementation packets without reopening target-state decisions that are already fixed.
