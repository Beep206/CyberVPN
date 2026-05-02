# CyberVPN Platform Foundation Naming And Boundary Registry

**Date:** 2026-04-21  
**Status:** Canonical naming and boundary registry  
**Purpose:** freeze the canonical machine identifiers, document terminology, and source-of-truth boundaries used by the CyberVPN platform foundation so later implementation phases do not invent conflicting names.

---

## 1. Document Role

This document defines:

- canonical names for environments, clusters, control planes, repos, providers, regions, and node classes;
- allowed machine identifiers versus prose-only labels;
- boundary rules for which system is the source of truth for each domain;
- legacy aliases that may still exist in the repository but must not become the naming model for new work.

This document is the `T0.1` output from the platform foundation `Phase 0` execution packet.

It should be read together with:

- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-phase-0-execution-packet.md](2026-04-21-platform-foundation-phase-0-execution-packet.md)

---

## 2. Naming Principles

The platform foundation uses these naming rules:

1. Machine identifiers use lowercase ASCII and kebab-case unless a provider-native region code must preserve digits.
2. Prose may use `non-production` or `non-prod`, but machine identifiers use `nonprod`.
3. New documents must not use `staging` as the umbrella term for all non-production environments.
4. Existing repository paths may keep legacy names such as `staging` or `production` until refactored, but new platform abstractions must map them back to canonical environment identifiers.
5. `control plane` in CyberVPN means CyberVPN platform workloads unless the text explicitly says `Kubernetes control plane`.
6. `management cluster` and `workload cluster` are separate concepts and must not be collapsed into `control plane`.
7. `edge node`, `vpn node`, or `fleet node` refer to external nodes outside Kubernetes. `k8s node` refers to a Kubernetes worker or control-plane machine.
8. A name is not canonical unless it implies the correct source-of-truth boundary.

---

## 3. Canonical Environment Naming

### 3.1 Canonical Environment Identifiers

| Canonical machine id | Canonical prose label | Meaning |
|---|---|---|
| `prod` | `production` | production traffic and production control surfaces |
| `nonprod` | `non-production` or `non-prod` | all non-production platform surfaces |

### 3.2 Legacy Environment Aliases

These aliases may remain in current repository paths and runbooks, but they are not the canonical naming model for new abstractions:

| Legacy alias | Canonical mapping | Where it currently appears |
|---|---|---|
| `production` | `prod` | `infra/terraform/live/production`, Ansible inventories, runbooks |
| `staging` | `nonprod` | `infra/terraform/live/staging`, Ansible inventories, runbooks |
| `non-prod` | `nonprod` | prose in architecture docs |
| `non-production` | `nonprod` | prose in architecture docs |

### 3.3 Rule

- New machine identifiers, cluster names, repo names, auth mounts, and control-plane IDs must use `prod` or `nonprod`.
- Existing path names such as `infra/terraform/live/staging` and `infra/terraform/live/production` are treated as legacy implementation aliases until a later migration phase changes them.

---

## 4. Cluster Naming

### 4.1 Management Clusters

Management cluster names are fixed:

| Cluster type | Canonical id |
|---|---|
| production management cluster | `prod-mgmt` |
| non-production management cluster | `nonprod-mgmt` |

These names must be used consistently in:

- architecture and phased implementation documents;
- GitOps bootstrap and Cluster API documentation;
- future OpenBao auth mount examples;
- cluster inventory and runbook references.

### 4.2 Workload Clusters

Workload cluster identifiers use this pattern:

```text
<env>-<provider>-<region>-<purpose>[-<ordinal>]
```

Rules:

- `<env>` is `prod` or `nonprod`
- `<provider>` is the canonical provider slug
- `<region>` is the normalized provider-native region code
- `<purpose>` is the cluster role, initially `core` unless a different role is explicitly defined
- `[-<ordinal>]` is optional and is used only when more than one cluster of the same purpose exists in the same provider-region

Examples:

- `prod-hetzner-fsn1-core`
- `nonprod-hetzner-hel1-core`
- `prod-ovh-gra1-core-a`

### 4.3 Terminology Rule

- Use `management cluster` for `prod-mgmt` and `nonprod-mgmt`.
- Use `workload cluster` for runtime clusters created through Cluster API.
- Use `Kubernetes control plane` only for API server/etcd/control-plane node discussions.
- Do not call the CyberVPN business or platform workload layer the `Kubernetes control plane`.

---

## 5. External Control-Plane Surface Naming

External foundational services outside Kubernetes use this pattern:

```text
<system>-<env>
```

Canonical system identifiers:

| System | Canonical ids |
|---|---|
| OpenBao | `openbao-prod`, `openbao-nonprod` |
| NATS JetStream | `nats-prod`, `nats-nonprod` |
| PostHog | `posthog-prod`, `posthog-nonprod` |

Rules:

- New documents and automation must refer to these surfaces with canonical IDs.
- Legacy prose like “staging OpenBao” or “production NATS” is allowed only when explicitly talking about current implementation directories or runbooks.
- These systems are called `external control planes` or `external foundational services`, not generic `apps`.

---

## 6. Repository And Desired-State Surface Naming

Canonical logical repository surfaces:

| Logical surface | Canonical name | Meaning |
|---|---|---|
| current application and infrastructure monorepo | `platform-monorepo` | current repository that contains apps, services, infra, docs, and CI |
| workload desired-state GitOps repository | `platform-gitops` | separate repository for cluster desired state reconciled by Flux |

Rules:

- `platform-monorepo` is the engineering source repository.
- `platform-gitops` is the source of truth for workload desired state in Kubernetes.
- `Flux` is the reconciler, not the source of truth.
- `GitHub Actions` is the automation path, not the deployment source of truth.

---

## 7. Provider, Region, Country, And Location Naming

### 7.1 Provider

- `provider` means the infrastructure vendor or hosting platform used by OpenTofu or Cluster API.
- Provider identifiers use lowercase kebab-case, for example `hetzner`, `aws`, `ovh`, `vultr`.
- Provider names must not be overloaded to mean country or region.

### 7.2 Region

- `region` means the provider-native deployment region or datacenter group.
- Region identifiers preserve the provider-native short code where practical, normalized to lowercase.
- Examples from the current repository baseline include `fsn1` and `hel1`.

### 7.3 Country

- `country` means the commercial or routing geography exposed in VPN fleet policies and customer-facing capacity models.
- Country identifiers use lowercase ISO-like country slugs, for example `jp`, `de`, `fi`.
- A country is not the same thing as a provider region.

### 7.4 Location

- `location` is the broad umbrella term only when the text intentionally does not distinguish between provider region and commercial country.
- New technical design docs should prefer the precise term instead of `location`.

---

## 8. Node And Fleet Naming

### 8.1 Canonical Terms

| Term | Meaning |
|---|---|
| `fleet node` | any external node managed by the Node Fleet Controller |
| `vpn node` | external VPN-serving node in the fleet |
| `edge node` | external edge runtime node in the fleet |
| `k8s node` | Kubernetes machine in a management or workload cluster |
| `node class` | declarative fleet sizing and capability profile |
| `node pool` | desired fleet grouping used by Node Fleet Controller |

### 8.2 Rule

- The word `node` alone is ambiguous and should be avoided in new design docs unless the surrounding text makes the type explicit.
- `make node-add ...` refers to an operator UX wrapper around Node Fleet Controller flows, not to a machine-local or inventory-edit workflow.

---

## 9. Infrastructure Stack Slug Mapping

The current repository already uses infrastructure stack slugs under `infra/terraform/live/*`. Their meanings are frozen here so they are not reinterpreted later.

| Stack slug | Canonical meaning |
|---|---|
| `foundation` | shared base networking, firewall, and non-workload primitives for an environment |
| `dns` | DNS and Cloudflare-related zone or record management for an environment |
| `control-plane` | current legacy VM-based control-plane runtime stack; this is a migration-era slug, not the future workload-cluster naming model |
| `edge` | external VPN/edge fleet infrastructure for an environment |

Rule:

- New Kubernetes platform work must not reuse the legacy `control-plane` slug to mean a workload cluster.
- When discussing the current repository state, it is acceptable to say `infra/terraform/live/production/control-plane`, but when discussing the target model use `workload cluster` and the canonical cluster ID pattern instead.

---

## 10. Source-Of-Truth Boundary Registry

This section freezes which system is the source of truth for each domain.

| Domain | Canonical source of truth | Allowed derived views | Must not become source of truth |
|---|---|---|---|
| business transactions, subscriptions, billing state | PostgreSQL | read models, analytics exports, dashboards | NATS, PostHog, Redis |
| infrastructure desired state for external VMs and foundational resources | OpenTofu code plus its remote state backend | inventory snapshots, generated artifacts, controller execution plans | manual shell history, ad-hoc provider console changes |
| workload desired state in Kubernetes | `platform-gitops` repository | Flux reconciliation state, cluster runtime objects | Flux internal state, kubectl hotfixes, manual helm state |
| secrets, PKI, bootstrap identity, auth mounts | OpenBao | Kubernetes Secret sync, issued certificates, wrapped bootstrap material | `.env` files, static inventory secrets, application databases |
| durable event propagation and replay transport | NATS JetStream | SSE/WebSocket delivery, downstream projections, analytics bridge | PostgreSQL business tables, browser state |
| business-critical publication boundary | transactional outbox in PostgreSQL | NATS streams, downstream consumers | direct publish from request handlers |
| fleet desired and observed lifecycle state | Node Fleet Controller database | runtime adapter projections, operator dashboards, NATS lifecycle events | NATS streams, OpenTofu state alone, shell wrappers |
| product analytics, feature-flag targeting, experiments | PostHog | product dashboards, cohort exports, UX flag evaluation | Prometheus, business transaction tables, ad-hoc frontend local storage |
| operational health, SLOs, traces, logs, alerts | Prometheus, Loki, Tempo, Grafana | dashboards, alerts, drill evidence packs | PostHog, NATS, customer-facing analytics |

### 10.1 Boundary Rules

1. `NATS` is the event backbone, not the business source of truth.
2. `PostHog` is the product-intelligence layer, not the operational-truth layer.
3. `Node Fleet Controller DB` is the durable fleet-control store, not `NATS`.
4. `OpenTofu` is the infrastructure declaration and execution authority for external VM resources, not the workflow engine.
5. `OpenBao` is the secrets and identity plane, not a general application data store.
6. `Flux` reconciles desired state but does not replace the `platform-gitops` repository as source of truth.

---

## 11. Reserved Terms And Prohibited Ambiguities

The following terms are reserved and must not be used loosely in new platform documents:

| Reserved term | Rule |
|---|---|
| `Vault` | use only when explicitly referring to HashiCorp Vault or legacy material; the canonical current system name is `OpenBao` |
| `staging` | allowed only as a legacy implementation alias for the current non-production environment |
| `control plane` | do not use alone when you actually mean `Kubernetes control plane` or `CyberVPN control-plane workloads`; be explicit |
| `node` | do not use alone when the distinction between `k8s node` and external fleet node matters |
| `telemetry` | do not use as a synonym for product analytics; distinguish operational telemetry from product analytics |
| `feature flag` | if the flag is infra, safety, or authz-related, do not classify it as a PostHog product flag |
| `realtime` | do not use to justify direct browser connections to NATS |

---

## 12. Adoption Rules

Effective immediately:

1. New planning and design docs must use the canonical environment identifiers and source-of-truth terms from this registry.
2. New implementation docs must refer to `prod-mgmt` and `nonprod-mgmt` by those exact names.
3. New control-plane surface docs must use `openbao-prod`, `openbao-nonprod`, `nats-prod`, `nats-nonprod`, `posthog-prod`, and `posthog-nonprod`.
4. New GitOps and deployment docs must use `platform-gitops` as the logical desired-state repository name.
5. Any use of a legacy alias such as `staging` or `production` in a new doc must either:
   - refer to an existing path or runbook literally; or
   - include the canonical mapping beside it.

---

## 13. Known Legacy Mappings In Current Repository

The following current repository structures are explicitly recognized as legacy mappings:

| Current path or surface | Canonical interpretation |
|---|---|
| `infra/terraform/live/staging/*` | `nonprod` environment implementation path |
| `infra/terraform/live/production/*` | `prod` environment implementation path |
| `infra/ansible/inventories/staging/*` | `nonprod` inventory and rollout surface |
| `infra/ansible/inventories/production/*` | `prod` inventory and rollout surface |
| `control-plane` stack slug in Terraform/Ansible | legacy VM-based control-plane runtime, not future workload cluster naming |

These mappings are intentional transition bridges. They must be respected during migration, but they must not drive the naming of new platform abstractions.

