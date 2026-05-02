# CyberVPN Platform Foundation Target-State Architecture

**Date:** 2026-04-21  
**Status:** Canonical target-state architecture  
**Purpose:** define the long-lived target state for CyberVPN platform infrastructure, Kubernetes, secrets, PKI, GitOps, observability, real-time eventing, external fleet orchestration, and product intelligence without mixing that target state with phase sequencing.

---

## 1. Document Role

This document is the canonical target-state specification for the CyberVPN platform foundation.

It defines:

- what CyberVPN is and what operating problems this platform must solve;
- the evaluation criteria used to judge architectural choices;
- cluster topology and network boundaries;
- secrets and PKI operating model;
- GitOps and delivery model;
- observability target state;
- real-time eventing and external fleet-control model;
- product analytics, feature-flag, and experimentation model;
- platform-wide invariants that must remain true during implementation.

This document does **not** define the detailed rollout phases.

Delivery sequencing, execution backlog, cutover order, acceptance criteria, and migration phases must be defined in a companion phased implementation plan.

---

## 2. Executive Position

CyberVPN should move from a manual VM-and-compose operating model to a Kubernetes-first, GitOps-driven platform model that preserves strong separation between:

- public web/control-plane traffic;
- internal platform workloads;
- the external VPN/edge fleet;
- secrets and PKI control planes;
- production and non-production environments.

The target state intentionally favors:

- upstream Kubernetes over opinionated vendor distributions;
- open source control planes where practical;
- explicit failure-domain separation;
- platform automation over operator-only procedures;
- one canonical way to deliver software per concern, not parallel competing paths.

The platform target state treats NATS JetStream, OpenBao, GitOps, observability, Node Fleet Controller, and PostHog as distinct control surfaces with explicit source-of-truth boundaries. No single component is allowed to become an implicit source of truth for another domain.

---

## 3. Project Context And Purpose

### 3.1 What CyberVPN Is

CyberVPN is not a generic CRUD SaaS and not a single web application.

It is a multi-surface VPN business platform that combines:

- control-plane and business-management applications;
- backend APIs and background services;
- partner/admin and customer-facing workflows;
- desktop and mobile client ecosystem;
- external VPN and edge node fleet;
- anti-blocking transport evolution and global rollout requirements.

At the product level, the platform exists to support a **"VPN business in a box"** operating model:

- launch and run a VPN business quickly;
- expand across providers and regions without re-architecting every rollout;
- manage subscriptions, users, configs, support, and operations centrally;
- keep the public web/control-plane and the VPN data-plane as distinct operational domains;
- support premium UX while remaining resilient to blocking, provider failure, and operational mistakes.

### 3.2 Why This Project Needs A Different Infrastructure Shape

CyberVPN has a hybrid runtime shape:

- control-plane workloads want Kubernetes-style horizontal scaling, controlled rollout, and platform automation;
- VPN nodes are external infrastructure endpoints and are not naturally a good fit for "everything runs inside Kubernetes";
- secrets, PKI, node identity, and enrollment have to span both Kubernetes and non-Kubernetes systems;
- the platform must be able to grow to multiple providers and multiple regions while containing blast radius;
- the team prefers open-source and cost-conscious solutions and cannot assume enterprise-only control planes.

Because of that, the target architecture must solve both:

- modern application platform problems; and
- fleet/infrastructure/identity problems for external nodes.

Any proposal that solves only one of those halves is incomplete for this project.

---

## 4. Evaluation Criteria And Rationale Frame

This document is intended to support **objective architectural review**, not only record preferences.

The decisions below should be judged against the following criteria:

- does the choice fit a VPN business platform with both Kubernetes workloads and an external VPN fleet;
- does it reduce manual operations and secret sprawl in the current monorepo and infrastructure;
- does it improve horizontal scalability for the control plane without forcing the VPN data plane into the wrong runtime;
- does it preserve clear failure domains across clusters, providers, environments, and secrets planes;
- does it support multi-provider expansion without requiring a new platform design for every provider;
- does it remain workable with open-source or low-cost tooling;
- does it provide a credible path for backup, DR, reprovisioning, and rollback;
- does it create one clear default per concern rather than multiple competing operational patterns;
- does it fit the actual repository shape and migration path, instead of assuming a greenfield platform.

### 4.1 Why These Chosen Solution Classes Fit CyberVPN

- `Talos + upstream Kubernetes` fits because the control plane needs repeatable immutable nodes, clean lifecycle management, and horizontal scaling without carrying a heavier vendor distribution than necessary.
- `Cloudflare + provider L4 LB + Cilium Gateway API` fits because CyberVPN needs a strong public web/control-plane edge, but the VPN data plane should remain outside a mandatory HTTP edge path.
- `OpenBao` fits because the platform needs centralized secrets, PKI, node bootstrap, and auth workflows across Kubernetes and external nodes while staying on an open-source path.
- `Flux + Flagger` fits because the repository already has CI/image promotion patterns and needs Git-driven, auditable rollout control rather than more manual host deploy logic.
- `Grafana Alloy + LGTM stack` fits because CyberVPN must observe both Kubernetes workloads and external VPN/edge VMs through one collector family and one operational model.
- `OpenTofu + Cluster API split responsibility` fits because the project has two distinct automation surfaces: cluster lifecycle and external fleet lifecycle. Treating them as one would be operationally weaker.
- `Velero + CloudNativePG + object-storage-first DR` fits because the platform has mixed state types and cannot rely on one simplistic backup mechanism for everything.
- `NATS JetStream + transactional outbox bridge` fits because CyberVPN needs durable near-real-time platform reactions without turning databases into ad-hoc polling interfaces.
- `Node Fleet Controller` fits because the platform must turn external VPN node lifecycle into a reconciled control loop instead of a runbook with manual secret handling and host-by-host edits.
- `PostHog self-hosted` fits because CyberVPN needs product analytics, product-facing feature flags, and experiment workflows that complement infrastructure observability rather than trying to replace it.

### 4.2 How To Challenge Or Adjust This Document

Any future correction should state clearly:

- which requirement or criterion is not satisfied by the current decision;
- whether the concern applies to all environments or only to a subset;
- what alternative improves the fit for CyberVPN specifically;
- what new operational cost, lock-in, or migration complexity that alternative introduces.

This prevents changes from being driven by tool popularity alone and keeps the discussion grounded in the needs of this project.

---

## 5. Canonical Decisions Index

The following decisions are fixed unless this document is explicitly superseded.

| Area | Decision |
|---|---|
| Kubernetes distribution | Talos Linux + upstream Kubernetes |
| Multi-provider topology | Multiple independent clusters, not one stretched cluster |
| Workload boundary | Kubernetes for control-plane/platform workloads; VPN data plane remains outside Kubernetes |
| Public edge | Cloudflare mandatory for public web/control-plane HTTP(S) |
| Per-cluster entry | Provider-native L4 load balancer |
| In-cluster ingress | Cilium Gateway API |
| Secrets manager | OpenBao |
| Environment separation | Separate OpenBao clusters for `prod` and `non-prod` |
| OpenBao placement | Outside Kubernetes, on dedicated VMs |
| OpenBao prod topology | 3-node HA cluster |
| OpenBao non-prod topology | 1-node initially |
| OpenBao storage | Integrated Raft |
| OpenBao unseal | AWS KMS auto-unseal |
| Kubernetes secret delivery | Vault/OpenBao Secrets Operator style flow as default |
| K8s auth to OpenBao | JWT auth as default |
| Sidecar secret delivery | Agent Injector only for special cases |
| No-etcd secret case | CSI only for special cases |
| PKI root model | Offline root CA, intermediates in OpenBao |
| Internal TLS issuance | OpenBao PKI |
| K8s certificate automation | cert-manager with OpenBao issuer via JWT auth |
| Trust bundle distribution | trust-manager |
| GitOps engine | Flux |
| Progressive delivery | Flagger |
| App packaging | OCI Helm charts + HelmRelease |
| Promotion model | GitHub Actions -> PR into GitOps repo |
| Cluster observability | kube-prometheus-stack |
| Collector standard | Grafana Alloy |
| Logs backend | Loki |
| Traces backend | Tempo |
| Dashboards | Grafana |
| SLO generation | Sloth in CI/GitOps flow |
| Real-time event backbone | NATS JetStream |
| NATS placement | Outside Kubernetes on dedicated VMs |
| NATS prod topology | 3-node JetStream cluster |
| NATS shared non-prod topology | 3-node JetStream cluster |
| NATS source-of-truth boundary | NATS is the event backbone, not the business source of truth |
| Event delivery pattern | Transactional outbox -> NATS JetStream -> durable consumers |
| NATS publish boundary | Transactional outbox is mandatory for business-critical events |
| NATS delivery semantics | At-least-once delivery; idempotent consumers mandatory |
| NATS storage | Local SSD only; no NAS/NFS/shared filesystem for JetStream |
| NATS monitoring exposure | Monitoring endpoints are private and firewalled only |
| External fleet orchestrator | Node Fleet Controller |
| Fleet controller durable state | Desired state, observed state, operation runs, and audit live in the controller database |
| Fleet automation safety | Budget, rate-limit, cooldown, confidence, and approval guardrails are mandatory |
| Product analytics and experimentation | PostHog self-hosted |
| PostHog placement | Outside Kubernetes on dedicated VM/Docker stack |
| PostHog cost model | Zero license cost, non-zero operational cost |
| PostHog privacy baseline | No VPN usage, destination, or raw traffic telemetry in product analytics |
| Product feature flags | PostHog for product-facing flags and experiments, not for infrastructure or security-critical kill switches |
| PostHog flag boundary | Product flags only; no infrastructure or security kill switches |
| Authoritative backup store | AWS S3 with versioning + SSE-KMS, separate for `prod` and `non-prod` |
| Kubernetes backup orchestrator | Velero |
| Fast same-provider volume restore | CSI snapshots |
| Cross-provider volume portability | Velero CSI snapshot data movement to object storage |
| PostgreSQL backup/restore | CloudNativePG + Barman Cloud Plugin |
| OpenBao backup model | Scheduled Raft snapshots + config backup + restore drills |
| Talos control-plane backup | Scheduled `etcd` snapshots + machine config backup |
| VPN/edge DR stance | Reprovision-first, not host-backup-first |

---

## 6. Kubernetes And Network Target State

### 6.1 Cluster Model

- Each provider/region gets its own Kubernetes cluster.
- A single Kubernetes cluster must not be stretched across distant regions or multiple providers.
- Clusters are treated as failure-contained units.
- Production and non-production remain logically separate and may have different scale profiles.

### 6.2 Traffic Boundaries

- Cloudflare is mandatory public edge for web/control-plane HTTP(S).
- Cloudflare is **not** the mandatory edge for VPN data-plane traffic.
- Each cluster exposes ingress via a provider-native L4 load balancer.
- Inside the cluster, traffic is terminated and routed through Cilium Gateway API.
- Cilium BGP/L2 announcement patterns are fallback paths only, not the default entry design.

### 6.3 Workload Separation

- Kubernetes hosts platform and control-plane workloads.
- VPN nodes stay on dedicated VM-based fleet outside Kubernetes.
- Platform automation must still integrate the VPN fleet into secrets, observability, rollout, and inventory workflows.

---

## 7. Secrets And PKI Target State

### 7.1 OpenBao Platform Model

- OpenBao is the canonical secrets-plane.
- `prod` and `non-prod` use separate OpenBao clusters.
- OpenBao runs outside Kubernetes on dedicated VMs.
- `prod` uses 3-node HA with integrated Raft.
- `non-prod` starts with 1 node unless non-prod HA becomes a hard release-gate requirement.
- OpenBao uses AWS KMS auto-unseal.

Frozen `Phase 0` companion registry for this section:

- [../security/platform-foundation-openbao-and-pki-registry.md](../security/platform-foundation-openbao-and-pki-registry.md)

### 7.2 OpenBao Auth And Policy Model

- Root namespace is reserved for platform-operator and emergency functions only.
- Service-facing integrations live in dedicated child namespaces, starting with `platform`.
- Each Kubernetes cluster gets its own JWT auth mount.
- Human operator access uses OIDC auth mounts, not local usernames/passwords.
- AppRole is reserved for narrow bootstrap or legacy automation use cases.
- No standing root token is retained after bootstrap.
- Break-glass access uses recovery procedures and on-demand root generation.

### 7.3 Secret Delivery Model

- Default path: OpenBao -> secrets operator -> Kubernetes Secret -> workload env/file consumption.
- Default auth from Kubernetes to OpenBao: JWT auth.
- Agent injector is only for advanced templating, file rendering, or direct secret-consumption edge cases.
- CSI is only for specific no-`etcd` persistence cases.

### 7.4 PKI Model

- One offline root CA exists outside day-to-day platform runtime.
- `prod` OpenBao hosts `prod` intermediates.
- `non-prod` OpenBao hosts `non-prod` intermediates.
- At minimum there are separate intermediate domains for:
  - Kubernetes/internal service TLS
  - infrastructure/ops/internal endpoints
- Kubernetes certificate automation uses cert-manager with OpenBao issuer over JWT auth.
- Trust bundle distribution inside clusters uses trust-manager.
- Public browser certificates remain on Cloudflare/public edge layer, not on internal OpenBao PKI.

---

## 8. GitOps And Delivery Target State

### 8.1 Delivery Model

- Flux is the canonical GitOps engine.
- Flagger is the canonical progressive delivery controller.
- First-party applications are packaged as OCI Helm charts.
- Deployment state lives in a separate GitOps repository, not in ad-hoc runtime mutation.

### 8.2 Promotion Flow

1. GitHub Actions builds and publishes images.
2. GitHub Actions packages or updates OCI charts.
3. GitHub Actions opens a promotion PR in the GitOps repository.
4. Merge to the GitOps repository changes desired cluster state.
5. Flux reconciles that state.
6. Flagger performs progressive rollout and rollback decisions from Prometheus-backed metrics.

### 8.3 Secrets In Delivery

- Secret values are not stored in Git.
- Git stores desired secret references, operator CRs, and non-secret values only.
- Kubernetes workloads consume secrets through the OpenBao operator flow.

### 8.4 Release Governance

- Staging may auto-promote after CI and validation.
- Production promotion requires explicit approval and merge to GitOps state.
- Manual shell-based deploy logic is transitional and must be retired as GitOps replaces it.

---

## 9. Observability Target State

### 9.1 Canonical Stack

- `kube-prometheus-stack` for cluster metrics, Prometheus, Alertmanager, and baseline dashboards/rules.
- `Grafana Alloy` as the standard collector.
- `Loki` for logs.
- `Tempo` for traces.
- `Grafana` for dashboards, Explore, and unified operator workflows.
- `Sloth` for SLO rule generation in CI/GitOps.

### 9.2 Backend Modes

- Prometheus remains per-cluster through `kube-prometheus-stack`.
- Loki:
  - `prod`: microservices mode
  - `non-prod`: monolithic mode initially acceptable
- Tempo:
  - `prod`: microservices mode
  - `non-prod`: monolithic mode initially acceptable
- Mimir is deferred until cross-cluster long-term metrics becomes an explicit requirement.

### 9.3 Collector Standardization

The target collector must be **one**:

- Alloy DaemonSet in Kubernetes for node/pod logs, Prometheus scrape/discovery, and enrichment.
- Alloy Deployment in Kubernetes as OTLP gateway for application telemetry.
- Alloy on external edge/VPN VMs for host logs, host metrics, and forwarding into central observability backends.

This is a platform invariant, not an optional preference.

### 9.4 Explicit Non-Targets

The following are **not** target-state observability components:

- Promtail
- standalone long-lived OTEL Collector deployment as the primary collector standard
- Grafana Agent static/flow/operator
- hand-maintained SLO burn-rate rule sets

Promtail must be considered deprecated in CyberVPN target state and removed from steady-state platform design.

---

## 10. Monorepo-Wide Observability Migration Requirement

Before implementation phases are finalized, the team must perform a **full monorepo audit** for all observability collectors, references, and assumptions.

This audit is mandatory and must cover at least:

- runtime manifests and future Kubernetes deployment manifests;
- local Docker Compose infrastructure;
- Ansible roles and VM rollout playbooks;
- Terraform outputs and generated scrape artifacts;
- Prometheus scrape jobs, recording rules, and alert rules;
- Grafana datasources and dashboards;
- application configuration defaults and environment-variable names;
- CI validation scripts and smoke checks;
- runbooks, plans, prompts, and technical docs;
- tests that assert collector names, endpoints, jobs, labels, ports, or log paths.

The implementation plan must explicitly include repo-wide replacement work for all prior uses of:

- `promtail`
- standalone `otel-collector` assumptions where Alloy is the intended collector
- legacy Grafana Agent naming or configuration assumptions

### 10.1 Migration Invariant

Where `Promtail` or a non-target collector previously existed, the plan must replace it with the canonical Alloy model rather than preserving parallel collection paths.

### 10.2 Required Outcome

The phased implementation plan must produce a repository state where:

- Kubernetes collection uses Alloy-only target patterns;
- edge/VPN VM collection uses Alloy-only target patterns;
- docs and runbooks no longer describe Promtail as a supported steady-state collector;
- CI and validation scripts check the new Alloy-based shape;
- dashboards, alerts, and scrape jobs reference the new collector topology correctly.

### 10.3 Current Repository Signals To Include In Migration Scope

As of 2026-04-21, the repository already shows mixed collector state and therefore requires explicit cleanup:

- local infra still contains `promtail` and `otel-collector` references in `infra/docker-compose.yml`;
- docs still describe `promtail` as part of the monitoring stack;
- prompts and historical docs reference older collector assumptions;
- edge VM observability already uses Alloy, which should become the canonical pattern for external nodes.

This mixed state must be treated as a migration program, not as a documentation-only update.

---

## 11. Backup And Disaster Recovery Target State

### 11.1 Authoritative Backup Stores

- `prod` and `non-prod` use separate object-storage backup buckets.
- The canonical backup target is AWS S3 with versioning and SSE-KMS enabled.
- Backup storage for platform state must not depend on the same host-local disks as the running workload.
- Backup retention, immutability controls, and lifecycle policies must be environment-specific.

### 11.2 Kubernetes Resources And Persistent Volumes

- Velero is the canonical backup/restore orchestrator for Kubernetes API objects.
- CSI snapshots are the default fast restore path for same-provider recovery of persistent volumes.
- Velero CSI snapshot data movement to object storage is the default portability path for cross-provider or cross-cluster recovery.
- Velero file-system backup is an exception path only for workloads or storage classes that cannot use snapshot-based flows.
- Backup and restore design must assume that Kubernetes object backup alone is insufficient without volume and database recovery paths.

### 11.3 Stateful Platform Data

- PostgreSQL uses CloudNativePG with the Barman Cloud Plugin.
- PostgreSQL disaster recovery source of truth is object-store base backups plus WAL archiving plus point-in-time recovery.
- Volume snapshots may be used as an acceleration path for PostgreSQL recovery, but not as the sole authoritative recovery method.
- NATS JetStream state is durable platform state, but it is not the primary business source of truth.
- Any event stream that can be deterministically rebuilt from PostgreSQL, outbox, or controller state should be treated as replayable rather than as the only durable record.
- Any non-replayable operational stream or command state must also have a durable authoritative store in the owning service, not only in JetStream.
- OpenBao uses scheduled integrated-Raft snapshots plus backup of server configuration and platform-managed auth/policy definitions.
- Talos clusters use scheduled `etcd` snapshots plus backup of machine configuration and bootstrap metadata.
- PostHog self-hosted data and configuration must be backed up separately from platform observability, with recovery priority below platform control planes but above ad-hoc analytics loss tolerance.
- Redis/Valkey must not become the sole source of business-critical state.

### 11.4 GitOps, IaC, And External Fleet Recovery

- GitOps repositories and IaC repositories must be backed up as regular `git bundle` or equivalent off-cluster artifacts.
- Recovery must be able to rebuild clusters from Git and object storage without dependence on undocumented operator state.
- VPN and edge nodes are rebuilt through reprovisioning and re-enrollment, not by restoring whole-machine backups as the primary strategy.
- Node identity material, enrollment tokens, and certificates must live in centralized systems, not only on node disks.

### 11.5 Recovery Order

The platform recovery order is fixed:

1. Restore access to AWS account, KMS, and backup buckets.
2. Recover OpenBao if it is unavailable.
3. Recover Talos control plane and `etcd`.
4. Re-bootstrap Flux and the base platform controllers.
5. Recover PostgreSQL from object storage and WAL.
6. Restore Kubernetes resources and portable volume data through Velero.
7. Bring application workloads and rollout controllers back online.
8. Reprovision and re-enroll VPN/edge nodes as needed.
9. Restore or rehydrate product-intelligence systems such as PostHog if they were impacted.

### 11.6 Baseline Recovery Objectives

- OpenBao target: `RPO <= 15m`
- Talos/`etcd` target: `RPO <= 15m`
- PostgreSQL target: `RPO <= 5m`
- GitOps/IaC repositories: near-zero logical RPO
- Redis/queue recovery guarantees are best-effort unless a workload explicitly introduces stronger durability requirements

---

## 12. Automated Provisioning Target State

### 12.1 Separation Of Responsibility

- Kubernetes cluster lifecycle and external VM fleet lifecycle are separate concerns and must not be forced into one automation tool.
- Cluster API is the canonical lifecycle engine for Kubernetes clusters after the management plane exists.
- OpenTofu remains the canonical declarative engine for non-Kubernetes infrastructure and external VM fleets.
- Ansible is transitional and break-glass only; it is not the long-lived target-state provisioning control plane.

### 12.2 Management Cluster Model

- Each environment gets a dedicated management cluster:
  - `prod-mgmt`
  - `nonprod-mgmt`
- Management clusters run Talos Linux and upstream Kubernetes.
- Management clusters host Cluster API controllers, Talos bootstrap/control-plane providers, infrastructure providers, and related platform-management controllers.
- Management clusters do **not** host customer-facing product workloads as a normal operating pattern.
- Baseline sizing:
  - `prod-mgmt`: `3` control-plane nodes and at least `2` worker nodes
  - `nonprod-mgmt`: `1` control-plane node and at least `2` worker nodes initially; promote to HA once non-production lifecycle automation becomes a hard release gate
- Day-1 management clusters are not self-managed through Cluster API.
- Day-1 bootstrap for management clusters uses OpenTofu plus Talos bootstrap/apply flow, after which Cluster API becomes authoritative for workload clusters.

### 12.3 Workload Cluster Lifecycle Model

- Workload clusters are created and reconciled through Cluster API.
- Talos bootstrap/control-plane providers are the standard Kubernetes bootstrap path.
- Worker pools use `MachineDeployment` by default.
- `MachineHealthCheck` is required for automated remediation.
- `Cluster Autoscaler` is the default worker autoscaling path using the Cluster API provider.
- `ClusterClass` is deferred from day-1 baseline because it remains behind the `ClusterTopology` experimental feature gate in current Cluster API documentation.
- `MachinePool` is deferred from day-1 baseline because it remains beta and is not the safest initial common denominator across providers.
- Provider-specific CAPI controllers may coexist on the same management cluster, but every chosen provider combination must have a custom validation pipeline before production use.
- If a target provider lacks sufficiently mature CAPI support, the fallback path is:
  - foundation and node infrastructure through OpenTofu
  - Talos bootstrap through Talos tooling/provider
  - explicit exception status in the phased roadmap until the provider can join the standard CAPI lifecycle

### 12.4 OpenTofu Scope

OpenTofu remains authoritative for:

- provider accounts, projects, VPC/VNet/private network primitives, routing, firewalls, and security groups;
- Cloudflare DNS and edge-adjacent infrastructure declarations;
- AWS KMS, S3 backup buckets, and other external trust or storage anchors;
- OpenBao VM infrastructure;
- day-1 management-cluster compute, networking, and bootstrap prerequisites;
- external VPN and edge VM fleet infrastructure;
- any provider-specific primitives not cleanly owned by Cluster API.

The current Terraform codebase should be migrated to OpenTofu compatibility rather than re-authored from scratch.

### 12.5 VPN And Edge Fleet Provisioning Model

- VPN and edge nodes remain outside Kubernetes.
- The canonical orchestrator for external node lifecycle is the `Node Fleet Controller` defined in Section 13.
- OpenTofu provisions VM, IP, firewall attachment, DNS, labels, and bootstrap metadata.
- First boot uses cloud-init or equivalent immutable bootstrap to install the minimal host runtime and systemd-managed services.
- One-time bootstrap secrets must be delivered through OpenBao response wrapping, not by copying long-lived static secrets into host inventories.
- Narrow-scope AppRole is acceptable for bootstrap of external machines.
- Steady-state machine identity should move to certificate-based authentication where practical, using OpenBao-issued client certificates or equivalent short-lived node identity.
- Every node must be able to:
  - enroll automatically;
  - retrieve runtime configuration and certificates;
  - start the VPN/edge service set;
  - register itself into central inventory/health workflows;
  - re-enroll after replacement without manual secret recreation.
- The standard external-node service baseline includes:
  - the VPN/edge daemon for that node role;
  - Alloy collector;
  - health/watchdog automation;
  - automatic post-enrollment verification hooks.

### 12.6 Lifecycle Outcome

- Replacing a failed VPN or edge node must be a reprovision-and-re-enroll operation, not a manual rebuild.
- New provider/region rollout must primarily be an infrastructure declaration change plus controlled enrollment, not a bespoke operator procedure.
- No new steady-state provisioning workflow should depend on manually editing inventory files, manually copying environment files, or manually injecting node secrets.

---

## 13. Real-Time Eventing, Fleet Control, And Product Intelligence Target State

### 13.1 Architectural Position

- CyberVPN must stop treating polling as the primary inter-service integration pattern for business and fleet reactions.
- Polling may remain as reconciliation and safety-net logic, but not as the canonical way to propagate payments, lifecycle transitions, node health, or rollout events.
- Durable eventing is required because the platform spans Kubernetes workloads, external VPN nodes, and multiple operator-facing surfaces.
- Product analytics and experimentation are separate concerns from infrastructure observability and must use a dedicated product-intelligence stack.
- External fleet automation must be implemented as a controller-driven system, not as a collection of shell procedures wrapped in `make` targets.
- The production target state is:
  - `PostgreSQL`, `OpenBao`, GitOps state, and controller databases remain the durable sources of truth;
  - `NATS JetStream` becomes the durable real-time event backbone;
  - `Node Fleet Controller` becomes the external VPN/edge fleet control loop;
  - `PostHog` becomes the product-intelligence layer;
  - `Prometheus`, `Grafana`, `Loki`, and `Tempo` remain the operational truth for health, SLOs, logs, traces, and alerts.

| System | Canonical role | Must not become |
|---|---|---|
| PostgreSQL | Authoritative transactional and control-state store | Event backbone |
| NATS JetStream | Durable near-real-time event backbone | Business source of truth |
| Node Fleet Controller DB | Desired/observed fleet state, operation runs, and audit | Stream replacement |
| OpenBao | Secrets, PKI, bootstrap, and node identity | Application database |
| OpenTofu | Declarative infrastructure execution for external VMs | Workflow engine |
| PostHog | Product analytics, product flags, and experiments | Operational observability or infra kill switch |
| Prometheus/Grafana/Loki/Tempo | Platform health, SLO, logs, traces, and alerts | Product funnel analytics |

Frozen `Phase 0` companion contracts for this section:

- [../api/platform-foundation-event-taxonomy.md](../api/platform-foundation-event-taxonomy.md)
- [../api/platform-foundation-consumer-contract.md](../api/platform-foundation-consumer-contract.md)
- [../api/platform-foundation-outbox-contract.md](../api/platform-foundation-outbox-contract.md)

### 13.2 NATS JetStream Event Bus

- `NATS JetStream` is the canonical durable near-real-time event backbone for CyberVPN.
- It replaces polling as the primary propagation path for payment, subscription, node-lifecycle, and selected analytics events.
- It is a lightweight and operationally simple event backbone relative to heavier brokers, but in production it is still a stateful control-plane component and must be treated accordingly.
- `NATS JetStream` does **not** become the source of truth for business objects, durable fleet state, or secrets.

#### 13.2.1 NATS Production Topology

| Environment | Topology | Placement | Notes |
|---|---:|---|---|
| `prod` | `3-node` minimum, `5-node` when failure-domain growth justifies it | Dedicated VMs outside Kubernetes | Canonical production baseline |
| `shared non-prod` | `3-node` | Dedicated VMs outside Kubernetes | Release parity and failure testing |
| ephemeral dev | optional `1-node` | Local or disposable dev only | Not part of canonical target state |

- NATS stays outside Kubernetes for the same reason as OpenBao: it must remain reachable across multiple workload clusters and external fleet-control surfaces.
- NATS must remain available even if one workload cluster is degraded or being rebuilt.
- All NATS placement decisions must preserve clear failure domains and low-latency inter-node links.

#### 13.2.2 NATS Storage And Resource Management

- Production JetStream must use file-backed storage on local fast SSDs.
- Each `nats-server` instance must have its own `store_dir`.
- NAS, NFS, or shared filesystems must not be used as a pseudo-HA mechanism for JetStream.
- Stream limits, disk budgets, and consumer backlog capacity must be defined explicitly per stream class.
- Disk-watermark alerts and consumer-lag alerts are mandatory.
- Capacity planning must include stream count, consumer count, retention policy, replay load, and projected recovery time after node loss.
- Stream rebuild and data-loss expectations must be defined per stream class:
  - replayable from source-of-truth systems;
  - non-replayable and therefore additionally protected in owning service state.

#### 13.2.3 NATS Security And Subject Authorization

- NATS is reachable only through private platform networking.
- Public internet exposure of the broker is prohibited.
- TLS is required for client, route, gateway, and leaf-style connections where used.
- Subject permissions must be enforced per account or per user.
- Operator/admin credentials must be separate from application credentials.
- The system account must be configured for platform operations and monitoring workflows.
- Monitoring endpoints must remain private and firewalled because they do not provide built-in authz/authn protection.

Minimum authorization domains must exist for at least:

| Domain | Publish | Subscribe |
|---|---|---|
| billing services | `billing.*` | limited replies/advisories only |
| notification consumers | none or narrow command subjects | payment/subscription notification subjects |
| real-time gateway | none or narrow control subjects | partner projection and dashboard subjects |
| Node Fleet Controller | `node.lifecycle.*`, `node.command.*` | `node.health.*`, `provider.health.*`, selected lifecycle subjects |
| node agents | `node.health.*`, `node.telemetry.*` | only the narrow config/command subjects they require |
| analytics bridge | selected analytics/product events | selected business/product events |

#### 13.2.4 Event Envelope And Schema Governance

- CyberVPN must define one canonical event envelope for durable platform events.
- Event subjects must be versioned, for example `billing.payment.captured.v1`.
- Event schemas must live in version-controlled repository paths, not in tribal knowledge or one-off service code.
- Every durable event must declare its owner, schema reference, classification, and idempotency key semantics.
- Business-critical events without schema ownership are not production-ready.

Canonical envelope shape:

```json
{
  "event_id": "01HVZK7Q9S6Z8J4Y6X2ZKXK2B7",
  "event_type": "billing.payment.captured",
  "event_version": 1,
  "subject": "billing.payment.captured.v1",
  "source": "billing-service",
  "occurred_at": "2026-04-21T10:15:30.123Z",
  "published_at": "2026-04-21T10:15:30.456Z",
  "environment": "prod",
  "aggregate_type": "subscription",
  "aggregate_id": "sub_789",
  "correlation_id": "req_abc",
  "causation_id": "payment_webhook_xyz",
  "idempotency_key": "outbox_01HVZK7Q9S6Z8J4Y6X2ZKXK2B7",
  "pii_classification": "low",
  "schema_ref": "events/billing/payment_captured/v1.json",
  "payload": {}
}
```

Required fields include:

- `event_id`
- `event_type`
- `event_version`
- `subject`
- `source`
- `occurred_at`
- `environment`
- `aggregate_type`
- `aggregate_id`
- `correlation_id`
- `idempotency_key`
- `pii_classification`
- `schema_ref`
- `payload`

#### 13.2.5 Stream Layout And Retention Policy

- CyberVPN must not use one giant stream for all events.
- CyberVPN must also avoid creating streams at a per-micro-subject granularity that destroys operator comprehension.
- Stream layout must be domain-oriented and paired with explicit retention intent.

Recommended baseline:

| Stream | Subjects | Retention intent | Replicas |
|---|---|---|---:|
| `BILLING_EVENTS` | `billing.*.*.v1`, `payment.*.*.v1` | financial and business replay | 3 |
| `SUBSCRIPTION_EVENTS` | `subscription.*.*.v1`, `account.*.*.v1` | subscription and account projections | 3 |
| `PARTNER_EVENTS` | `partner.*.*.v1` | dashboard and partner audit projections | 3 |
| `NODE_LIFECYCLE_EVENTS` | `node.lifecycle.*.v1`, `node.command.*.v1` | fleet operations and replay | 3 |
| `NODE_HEALTH_EVENTS` | `node.health.*.v1`, `provider.health.*.v1` | shorter operational retention | 3 |
| `ANALYTICS_EVENTS` | `analytics.product.*.v1` | analytics bridge and retry, not source of truth | 3 |
| `SYSTEM_ADVISORIES` | selected `$JS.EVENT.*` or mirrored advisories | ops, audit, and debugging | 3 |

- Billing and subscription domains keep longer retention.
- Node health keeps shorter retention because of higher expected volume.
- Analytics bridge retention aligns with ingestion retry and replay requirements, not with business record retention.

#### 13.2.6 Transactional Outbox Boundary And Dispatcher SLO

- Direct publish from a request handler into NATS is prohibited for business-critical events.
- The transactional outbox pattern remains mandatory at write boundaries for business-critical events.
- Business state change and outbox insert must happen in the same database transaction.
- The outbox dispatcher publishes committed events into JetStream and records publish metadata.
- NATS downtime must create outbox backlog, not silent event loss.

Recommended outbox fields include:

- `id`
- `subject`
- `event_type`
- `event_version`
- `aggregate_type`
- `aggregate_id`
- `correlation_id`
- `causation_id`
- `idempotency_key`
- `payload`
- `headers`
- `pii_classification`
- `status`
- `attempts`
- `locked_by`
- `locked_at`
- `published_at`
- `nats_stream`
- `nats_sequence`
- `error`
- `created_at`
- `updated_at`

Baseline production targets:

- `outbox_publish_lag_seconds p95 <= 500ms`
- `outbox_publish_lag_seconds p99 <= 2s`
- `event_e2e_lag_seconds p95 <= 1s` for payment and dashboard event classes
- `consumer_ack_lag_seconds p95 <= 1s` for critical consumers

#### 13.2.7 Consumer Contract, Idempotency, And Replay

- Every durable consumer must have an owner, runbook, retry policy, and replay policy.
- Anonymous or unowned production-critical consumers are prohibited.
- Consumers must be designed for at-least-once delivery.
- Duplicate delivery is normal and must be tested.
- Every side effect must use a deterministic idempotency key.

Minimum consumer contract:

- `consumer_name`
- `owning_service`
- `owning_team`
- `stream`
- `filter_subjects`
- `delivery_policy`
- `ack_policy`
- `ack_wait`
- `max_deliver`
- `backoff`
- `max_ack_pending`
- `idempotency_store`
- `side_effect_type`
- `retry_policy`
- `dlq_policy`
- `replay_policy`
- `alert_policy`
- `slo`
- `runbook_url`

Examples of acceptable idempotency keys:

| Consumer | Idempotency key |
|---|---|
| notification delivery | `event_id + channel + recipient` |
| partner projection | `event_id` or `aggregate_id + version` |
| PostHog analytics bridge | `event_id` |
| node provisioning command handler | `operation_run_id` |
| webhook fan-out | `event_id + endpoint_id` |

#### 13.2.8 Realtime Delivery Path And NATS Failure Drills

- Browser and dashboard clients do **not** connect directly to NATS.
- Live UI updates are delivered through server-side SSE or WebSocket gateways.
- Existing Redis pub/sub or SSE delivery paths may remain temporarily for browser fan-out, but their upstream trigger path must converge on `outbox -> NATS -> realtime gateway`.
- Polling every 2-5 minutes is not an acceptable primary delivery path for payment, subscription, or fleet-critical reactions.

Required failure and replay drills:

- kill one NATS node and verify quorum behavior;
- restart an entire consumer group and verify backlog catch-up;
- simulate NATS unavailability while outbox backlog grows;
- replay selected billing events into a staging projection;
- inject duplicate events and verify idempotent side effects;
- approach disk thresholds and verify alerting behavior;
- rotate NATS credentials and verify controlled recovery.

### 13.3 Events, Commands, And State Boundaries

- The document must distinguish between events, commands, and durable state.
- An event records a fact that already happened.
- A command requests that some action be attempted.
- Durable state lives in authoritative databases and controller stores, not only in event streams.

Examples:

| Type | Example subject or state | Meaning |
|---|---|---|
| Event | `billing.payment.captured.v1` | payment already captured |
| Event | `subscription.activated.v1` | subscription already activated |
| Event | `node.health.dpi_detected.v1` | DPI signal already observed |
| Command | `node.command.provision_requested.v1` | provisioning has been requested |
| Event | `node.lifecycle.ready.v1` | node is ready |
| State | `node_pool.desired_capacity = 10` | authoritative desired state |

- Commands over NATS are acceptable, but command outcome must also be reflected in durable state and lifecycle events.

### 13.4 Node Fleet Controller

- `Node Fleet Controller` is the canonical orchestrator for VPN and edge node lifecycle.
- It is a dedicated control-plane service and must not be reduced to shell wrappers around OpenTofu, Ansible, or provider CLIs.
- It runs in Kubernetes as a platform controller, while the nodes it manages remain outside Kubernetes.
- Commands such as `make node-add COUNTRY=jp` are acceptable as operator UX only. They must be thin wrappers around the controller API or command flow, not the source of truth.
- Durable source of truth for fleet automation is the controller database: desired capacity, observed state, provisioning request, operation run, enrollment state, traffic eligibility, and audit trail.
- The `Phase 0` frozen companion docs for this section are:
  - [node-fleet-controller-domain-model.md](../api/node-fleet-controller-domain-model.md)
  - [node-fleet-controller-operator-command-model.md](../api/node-fleet-controller-operator-command-model.md)
  - [platform-foundation-node-lifecycle-state-machine.md](../runbooks/platform-foundation-node-lifecycle-state-machine.md)
- Current repository reference points remain explicitly migration-era, not target-state sources of truth:
  - [infra/ansible/README.md](/home/beep/projects/VPNBussiness/infra/ansible/README.md:1) captures current manual and semi-manual edge rollout procedures.
  - [services/helix-adapter/README.md](/home/beep/projects/VPNBussiness/services/helix-adapter/README.md:1) captures a runtime adapter surface, not the full fleet lifecycle control model.

#### 13.4.1 Node Fleet Controller Components

| Component | Responsibility |
|---|---|
| Fleet API | accepts operator, API, and Git-driven requests |
| CLI or `make` wrapper | operator UX only |
| Control DB | desired and observed state, operation runs, audit |
| Reconciler | compares desired and observed state |
| Workflow engine | executes multi-step operations with retry and rollback |
| Placement policy engine | selects provider, country, region, and node class |
| OpenTofu executor | controlled `plan`, `apply`, and `destroy` |
| OpenBao bootstrap manager | wrapped secrets, bootstrap TTL, certificates |
| Enrollment service | first registration and bootstrap handoff |
| Health evaluator | health, DPI, and provider signals to confidence score |
| Synthetic checker | post-enrollment and continuous validation |
| Traffic eligibility publisher | marks node traffic eligible or ineligible |
| Runtime adapters | Remnawave, Helix, or future adapter integrations |
| NATS adapter | publishes and consumes lifecycle and health events |
| Audit writer | durable operation history and forensic trace |

#### 13.4.2 Durable Fleet Data Model

Minimum durable entities include:

- `Provider`
- `ProviderRegion`
- `CountryPolicy`
- `NodeClass`
- `NodePool`
- `Node`
- `NodeDesiredState`
- `NodeObservedState`
- `ProvisioningRequest`
- `ReplacementRequest`
- `FailoverRequest`
- `DrainRequest`
- `QuarantineRequest`
- `OperationRun`
- `OperationStep`
- `BootstrapToken`
- `NodeCertificate`
- `HealthSignal`
- `DpiSignal`
- `TrafficEligibility`
- `BudgetPolicy`
- `RateLimitPolicy`
- `ApprovalPolicy`

#### 13.4.3 Node Lifecycle State Machine

Recommended lifecycle states:

```text
requested
placement_selected
plan_created
plan_approved
applying_infra
vm_created
bootstrap_issued
booting
enrolling
configuring
verifying
ready
traffic_eligible
draining
quarantined
rotating
terminating
deleted
failed
```

The controller must track at least:

- `desired_state`
- `observed_state`
- `traffic_state`
- `health_state`
- `bootstrap_state`
- `certificate_state`
- `provider_resource_state`

#### 13.4.4 OpenTofu Executor Safety Model

- OpenTofu execution must happen through isolated runners or a controlled worker pool.
- State locking is mandatory.
- Workspace and environment isolation are mandatory.
- The generated plan and selected variables must be stored as auditable artifacts.
- Policy validation must run before `apply`.
- Secret values must be redacted from logs.
- Every operation step must have timeout, retry semantics, and error classification.
- Approval gates must be available for actions above budget, risk, or blast-radius thresholds.
- Drift detection and orphan-resource reconciliation must be part of the operating model.

#### 13.4.5 OpenBao Bootstrap And Node Identity

- Bootstrap uses wrapped one-time OpenBao-delivered secret material with short TTL.
- Long-lived static node secrets in inventories are prohibited.
- Bootstrap tokens must be bound to the provisioning request or operation run.
- Steady-state identity must move to short-lived certificate-based or equivalent renewable identity.
- Certificate rotation must be scheduled, observable, and revocable.
- Quarantine and revocation paths must be documented and testable.
- A node must not depend indefinitely on its bootstrap token after enrollment is complete.

#### 13.4.6 DPI Failover Policy And Guardrails

- Automated failover is allowed, but only through explicit policy guardrails.
- DPI or provider impairment signals must be aggregated into confidence-scored health decisions.
- Automatic provisioning must respect budget and rate boundaries.
- Country, provider, and node-class constraints must be enforced before provisioning.

Mandatory guardrails include:

- `max_new_nodes_per_country_per_hour`
- `max_new_nodes_per_provider_per_hour`
- `max_total_monthly_provider_budget`
- `max_parallel_failovers`
- `cooldown_after_dpi_event`
- `confidence_score_threshold`
- `minimum_independent_signal_sources`
- `human_approval_above_budget_or_risk_threshold`
- `provider_exclusion_window_after_repeated_failures`
- `country_level_emergency_stop`
- `node_class_allowlist_for_automatic_provisioning`
- `traffic_canary_before_full_eligibility`
- `rollback_and_drain_policy`

#### 13.4.7 Traffic Eligibility Gates

- VM creation is not sufficient for node usability.
- A node becomes traffic eligible only after:
  - enrollment succeeds;
  - expected services are running;
  - VPN or edge daemon health is green;
  - Alloy is sending telemetry;
  - certificates are valid;
  - provider IP, DNS, and firewall state match policy;
  - synthetic connectivity checks pass;
  - runtime adapters acknowledge readiness;
  - no quarantine or policy block is active.

Baseline operational targets:

- manual node-add request to traffic-eligible: `p95 <= 10 minutes`
- healthy replacement request to traffic-eligible: `p95 <= 10 minutes`
- DPI failover detection to replacement request after confidence threshold: `p95 <= 30 seconds`
- health signal ingestion: `p95 <= 5 seconds`
- manual secret copy operations in steady state: `0`

#### 13.4.8 Fleet Failure Drills

Required drills include:

- provider API failure during infrastructure apply;
- OpenBao unavailable during bootstrap;
- node boots but fails enrollment;
- node enrolls but fails synthetic checks;
- DPI false-positive burst;
- provider region unavailable;
- duplicate failover events;
- OpenTofu state lock stuck;
- runtime adapter rejects node eligibility;
- node quarantine and certificate revocation.

### 13.5 PostHog Self-Hosted Product Intelligence Layer

- `PostHog self-hosted` is the canonical product analytics, product-facing feature flag, and experimentation platform.
- It complements `Prometheus/Grafana/Loki/Tempo`; it does **not** replace operational observability.
- CyberVPN must describe PostHog as having zero license cost, but non-zero operational cost.
- Production instrumentation must be privacy-first because CyberVPN is a VPN platform and cannot treat analytics as an excuse to collect traffic or browsing metadata.
- The `Phase 0` frozen companion docs for this section are:
  - [posthog-product-taxonomy-and-privacy-baseline.md](../growth-platform/posthog-product-taxonomy-and-privacy-baseline.md)
  - [posthog-feature-flag-governance.md](../growth-platform/posthog-feature-flag-governance.md)
- Current repository reference points remain explicitly non-canonical for target-state product intelligence:
  - [partner/src/app/api/analytics/frontend-runtime/route.ts](/home/beep/projects/VPNBussiness/partner/src/app/api/analytics/frontend-runtime/route.ts:1) is runtime observability, not PostHog product analytics.
  - [frontend/src/features/dev/lib/feature-flags.ts](/home/beep/projects/VPNBussiness/frontend/src/features/dev/lib/feature-flags.ts:1) is a dev-only local flag surface, not the production product flag model.

#### 13.5.1 PostHog Production Placement

- Production PostHog runs as a dedicated Linux VM and Docker-based self-hosted stack outside workload Kubernetes clusters.
- Production PostHog uses its own DNS/subdomain, TLS termination, access controls, monitoring, backup plan, and upgrade procedure.
- Production PostHog must remain isolated from platform-critical control planes so that analytics failure does not affect billing, auth, VPN traffic, or node operations.
- A reverse proxy in front of PostHog is the preferred production posture for ingress hardening and endpoint control.
- PostHog self-hosted has zero license cost, but non-zero operational cost that includes VM, storage, backups, upgrades, privacy operations, access governance, and monitoring.

#### 13.5.2 Product Event Taxonomy

- CyberVPN must maintain a strict event taxonomy for PostHog.
- Product analytics with uncontrolled event naming is not an acceptable steady state.
- Every tracked event must have an owner, schema, allowed property list, and blocked property list.
- Critical commercial events must be emitted from server-side or authoritative event-consumer paths, not only from browsers.

Representative product events:

- `checkout_started`
- `checkout_step_viewed`
- `checkout_step_completed`
- `checkout_payment_submitted`
- `checkout_payment_failed`
- `checkout_payment_captured`
- `subscription_activated`
- `subscription_renewed`
- `subscription_cancelled`
- `trial_started`
- `trial_converted`
- `client_download_started`
- `client_download_completed`
- `app_first_launch`
- `vpn_config_generated`
- `onboarding_started`
- `onboarding_step_completed`
- `partner_dashboard_viewed`
- `partner_invite_sent`
- `partner_user_activated`
- `feature_flag_evaluated`
- `experiment_exposure_recorded`

#### 13.5.3 VPN Privacy Baseline

- CyberVPN must not send VPN usage or browsing telemetry into PostHog.
- Raw IP addresses, VPN destination domains, visited sites, raw traffic metadata, access tokens, VPN secrets, and private keys are prohibited.
- Raw email, phone number, payment card data, and support message content are prohibited unless a specific privacy-reviewed exception exists.
- Allowed product analytics fields should prefer anonymous or hashed identifiers, plan or tier, locale or country only after privacy review, high-level lifecycle status, client version, platform type, flag exposure, and experiment cohort.
- Session replay is off by default in CyberVPN production posture and may only be enabled after privacy review.
- If session replay is enabled for an approved scope, masking must be aggressive by default.
- Autocapture must be disabled by default in production or restricted through an allowlist-only posture.

#### 13.5.4 Server-Side Analytics Bridge

- Critical commercial events must not depend solely on browser SDK delivery.
- The canonical path for critical analytics events is:

```text
PostgreSQL commit
  -> transactional outbox
  -> NATS JetStream
  -> analytics bridge consumer
  -> PostHog capture with event_id-based idempotency
```

- Frontend SDK usage remains appropriate for UX events such as view changes, funnel interactions, onboarding steps, and flag exposure where client context matters.
- Server-side capture remains authoritative for payment success, subscription activation, renewal, churn, and similar commercial milestones.

#### 13.5.5 Feature Flag Governance

- PostHog feature flags are allowed for product UX rollouts, checkout experiments, onboarding variants, partner dashboard UX, beta access, and other non-critical product releases.
- PostHog feature flags must not control secrets, PKI, OpenBao policy behavior, NATS security, authz-critical decisions, infrastructure kill switches, or cluster or VPN fail-safe controls.
- Preferred evaluation model is server-side evaluation where backend decisions own the behavior, with safe client bootstrap for UX flags to avoid flicker.
- Undefined flag results must have deterministic fallback behavior.
- Each flag must have an owner, purpose, expected removal date, allowed context, blast radius, and cleanup rule.

#### 13.5.6 Experiment Governance

- Every experiment must define:
  - a hypothesis;
  - a primary success metric;
  - guardrail metrics;
  - the target sample definition;
  - an exposure event;
  - start and stop criteria;
  - an owner;
  - a rollback rule;
  - privacy review when applicable.

- Experiments must not become unbounded long-lived configuration toggles.
- Product experiments must be removable, attributable, and auditable.

#### 13.5.7 PostHog Backup, Upgrade, And Retention Model

- PostHog requires documented backup, restore, and upgrade procedures.
- Retention policy must be explicit and aligned with privacy posture, storage cost, and product-analysis needs.
- Capture and SDK behavior must be non-blocking for user-facing flows.
- PostHog failure must not block checkout, backend request completion, or core VPN workflows.
- Reverse-proxy and trusted-proxy configuration must be documented because self-hosted PostHog relies on proxy awareness for correct client IP and TLS handling.

### 13.6 Boundaries And Non-Goals

- NATS JetStream is the platform nervous system, not the primary source of truth for business entities.
- PostgreSQL and controller databases remain the authoritative transactional and control-state stores.
- Transactional outbox remains mandatory for business-critical publication boundaries.
- PostHog is the source of product analytics and product experimentation, not the source of operational health truth.
- Prometheus/Grafana remain the source of platform SLI/SLO, alerting, and rollout-gate metrics.
- Node Fleet Controller owns orchestration and reconciliation, but OpenTofu remains the authoritative infrastructure declaration and execution layer for external VM resources.
- `make` wrappers are operator convenience only and must not become hidden source-of-truth channels.
- Polling and cron-style reconciliation may remain as defensive mechanisms, but platform correctness must not depend on multi-minute polling as the main integration path.

---

## 14. Current Implementation Implications

The phased implementation plan must assume:

- GitOps manifests and Helm charts are the new deployment source of truth;
- OpenBao-backed secret delivery must be wired into every Kubernetes workload before cutover;
- observability must be production-ready before progressive delivery gates become authoritative;
- edge/VPN fleet observability must converge on the same collector family as Kubernetes;
- business-critical state changes that need near-real-time fan-out must converge on the transactional outbox and NATS delivery path;
- NATS stream layout, subject taxonomy, and durable consumer contracts must be declared and governed before critical fan-out paths are cut over;
- external node provisioning, replacement, and failover must converge on the Node Fleet Controller rather than remaining distributed across manual procedures;
- product analytics, product-facing flags, and experiments must converge on PostHog with explicit taxonomy and privacy controls;
- PostHog rollout is not complete until privacy controls, blocked-property rules, and deterministic flag fallbacks are in place;
- no phase is complete if it leaves parallel collector standards alive without an explicit temporary exception and removal deadline.

Temporary exceptions are allowed only if they are:

- documented;
- scoped;
- time-bounded;
- attached to a removal phase.

---

## 15. Deferred But Required Companion Documents

This target-state document requires companion documents for:

- phased implementation roadmap, starting with [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md);
- gate evidence template:
  - [../evidence/platform-foundation/platform-foundation-phase-evidence-template.md](../evidence/platform-foundation/platform-foundation-phase-evidence-template.md)
- conformance scorecard:
  - [../testing/platform-foundation-conformance-scorecard.md](../testing/platform-foundation-conformance-scorecard.md)
- frozen `Phase 0` OpenBao and PKI registry:
  - [../security/platform-foundation-openbao-and-pki-registry.md](../security/platform-foundation-openbao-and-pki-registry.md)
- frozen `Phase 0` eventing contracts:
  - [../api/platform-foundation-event-taxonomy.md](../api/platform-foundation-event-taxonomy.md)
  - [../api/platform-foundation-consumer-contract.md](../api/platform-foundation-consumer-contract.md)
  - [../api/platform-foundation-outbox-contract.md](../api/platform-foundation-outbox-contract.md)
- automated provisioning for clusters and VPN/edge nodes;
- event contracts, stream topology, and consumer ownership;
- Node Fleet Controller API and reconciliation design;
- product analytics taxonomy, flag governance, and experimentation policy;
- backup/DR operational runbooks and drill procedures;
- cutover and rollback runbooks;
- acceptance and conformance criteria per phase.

Those companion documents must not contradict this target state.

---

## 16. Production Conformance Criteria

Operational scoring and phase-gate use of these criteria is defined in:

- [../testing/platform-foundation-conformance-scorecard.md](../testing/platform-foundation-conformance-scorecard.md)

The platform is considered target-state compliant only when all of the following are true:

1. Business-critical events use the transactional outbox pattern.
2. NATS streams and durable consumers are declared and governed, not created as ad-hoc production state.
3. Every durable consumer has an owner, replay policy, idempotency model, alert policy, and runbook.
4. Payment-to-notification and payment-to-dashboard `p95` event path is `<= 1s` under normal operating conditions.
5. Loss of one NATS node does not lose committed business events while quorum remains available.
6. NATS downtime creates outbox backlog and recovery work, not silent event loss.
7. Node Fleet Controller owns durable desired and observed fleet state.
8. External VPN and edge nodes are provisioned through controller workflows, not through manual secret handling or runbook-only procedures.
9. Node traffic eligibility requires enrollment, health, synthetic checks, and runtime-adapter acknowledgment.
10. DPI or provider failover automation can execute only through policy guardrails, not uncontrolled heuristics.
11. PostHog receives critical commercial events through server-side or authoritative bridge paths.
12. PostHog does not receive VPN usage, destination, or raw traffic telemetry.
13. PostHog feature flags are not used for infrastructure or security kill switches.
14. Product analytics, operational observability, and authoritative business state remain distinct domains with explicit boundaries.
15. Backup and restore drills exist for NATS, OpenBao, PostgreSQL, GitOps state, PostHog, and fleet reprovisioning.

---

## 17. Validation References

The following primary sources were used to validate time-sensitive architecture constraints in this document:

- NATS JetStream clustering guidance: `https://docs.nats.io/running-a-nats-service/configuration/clustering/jetstream_clustering`
- NATS storage and server configuration guidance: `https://docs.nats.io/running-a-nats-service/configuration`
- NATS monitoring endpoint guidance: `https://docs.nats.io/running-a-nats-service/nats_admin/monitoring`
- NATS authorization and subject permissions: `https://docs.nats.io/running-a-nats-service/configuration/securing_nats/authorization`
- PostHog self-host guidance: `https://posthog.com/docs/self-host`
- PostHog proxy configuration guidance: `https://posthog.com/docs/self-host/configure/running-behind-proxy`
- PostHog feature flag documentation: `https://posthog.com/docs/feature-flags`
- PostHog server-side local evaluation guidance: `https://posthog.com/docs/feature-flags/local-evaluation`
- PostHog client-side bootstrapping guidance: `https://posthog.com/docs/feature-flags/bootstrapping`
- PostHog privacy documentation: `https://posthog.com/docs/privacy`
- PostHog session replay privacy controls: `https://posthog.com/docs/session-replay/privacy`
- PostHog autocapture documentation: `https://posthog.com/docs/product-analytics/autocapture`
