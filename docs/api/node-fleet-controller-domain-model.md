# CyberVPN Node Fleet Controller Domain Model

**Date:** 2026-04-22  
**Status:** Frozen baseline for `T0.5`

This document freezes the canonical durable domain model for the `Node Fleet Controller`.

It is the `Phase 0` companion to:

- [2026-04-21-platform-foundation-target-state-architecture.md](../plans/2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-phase-0-execution-packet.md](../plans/2026-04-21-platform-foundation-phase-0-execution-packet.md)
- [2026-04-21-platform-foundation-naming-and-boundary-registry.md](../plans/2026-04-21-platform-foundation-naming-and-boundary-registry.md)
- [platform-foundation-event-taxonomy.md](platform-foundation-event-taxonomy.md)
- [node-fleet-controller-operator-command-model.md](node-fleet-controller-operator-command-model.md)
- [platform-foundation-node-lifecycle-state-machine.md](../runbooks/platform-foundation-node-lifecycle-state-machine.md)

This document exists so later phases do not invent fleet-control types, state ownership, or workflow aggregates from scratch.

## 1. Canonical Decisions Frozen Here

The following decisions are fixed and are not reopened by this document:

1. `Node Fleet Controller` is the canonical orchestrator for external VPN and edge fleet lifecycle.
2. `Node Fleet Controller DB` is the durable source of truth for fleet desired state, observed state, request lifecycle, traffic eligibility, and audit history.
3. `OpenTofu` remains the infrastructure declaration and execution authority for external VM resources, but it is not the fleet workflow source of truth.
4. `OpenBao` remains the bootstrap, secrets, and node identity plane.
5. `NATS` remains the durable event backbone, not the durable fleet-control store.
6. Runtime adapters such as `helix-adapter` are service-integration surfaces, not the source of truth for fleet lifecycle.
7. Operator commands such as `make node-add ...` are convenience wrappers around controller flows, not the source of truth.

## 2. Current-State Mapping

The current repository still reflects a migration-era fleet model:

- [infra/ansible/README.md](/home/beep/projects/VPNBussiness/infra/ansible/README.md:1) documents manual or semi-manual edge rollout flows where vaulted variables, node identifiers, transport ports, and rollout commands are coordinated by operators.
- [services/helix-adapter/README.md](/home/beep/projects/VPNBussiness/services/helix-adapter/README.md:1) shows a runtime adapter that manages service-owned registry and manifest persistence, but it is not a full fleet lifecycle controller.

Consequences:

1. Existing Ansible rollout steps are legacy operational procedures, not the target-state fleet source of truth.
2. Runtime adapters may continue to own service-specific registration or readiness handshakes, but they do not replace the controller domain model.
3. Future implementation work must map current rollout data into the durable entities frozen here.

## 3. Boundary Model

Frozen ownership boundaries:

| Surface | Canonical ownership | Explicit non-ownership |
|---|---|---|
| `Node Fleet Controller DB` | desired and observed fleet state, durable requests, operation runs, traffic eligibility, audit | provider VM state backend, secrets, runtime service registry alone |
| `OpenTofu` | declarative external VM resources, IPs, DNS, firewall objects, execution artifacts | desired node lifecycle state, approvals, traffic eligibility |
| `OpenBao` | wrapped bootstrap material, bootstrap TTL, renewable node identity, certificate issuance and revocation | provider resource topology, traffic eligibility, workflow history |
| `Runtime adapters` | service-specific registration, rollout hooks, runtime readiness acknowledgement | durable fleet desired state, request semantics, policy guardrails |
| `NATS` | lifecycle and health event propagation | durable fleet source of truth |

Rules:

1. A node is not considered durable state simply because it exists in provider infrastructure.
2. A node is not traffic-eligible simply because a runtime adapter accepted it.
3. A request is not complete because a shell command returned zero; completion is a durable controller fact.

## 4. Canonical Durable Entities

The following entities are frozen as the minimum durable controller model.

### 4.1 Topology And Policy Entities

| Entity | Purpose | Canonical examples of fields |
|---|---|---|
| `Provider` | infrastructure vendor reference | `provider_id`, `slug`, `status`, `api_profile` |
| `ProviderRegion` | provider-native region or datacenter scope | `region_id`, `provider_id`, `region_slug`, `country`, `capacity_posture` |
| `CountryPolicy` | customer-facing country routing and commercial policy | `country`, `allowed_providers`, `preferred_regions`, `emergency_stop` |
| `NodeClass` | declarative sizing and capability profile | `node_class`, `cpu_profile`, `memory_profile`, `transport_profile`, `cost_class` |
| `NodePool` | durable fleet grouping and desired capacity anchor | `node_pool_id`, `environment`, `country`, `role`, `node_class`, `desired_capacity` |
| `BudgetPolicy` | automation spending boundary | `budget_policy_id`, `scope`, `monthly_limit`, `burst_limit` |
| `RateLimitPolicy` | automation churn boundary | `rate_limit_policy_id`, `scope`, `max_actions_per_window`, `cooldown_seconds` |
| `ApprovalPolicy` | approval gates for risky actions | `approval_policy_id`, `scope`, `risk_threshold`, `approval_mode` |

### 4.2 Node Inventory And State Entities

| Entity | Purpose | Canonical examples of fields |
|---|---|---|
| `Node` | durable inventory record for one external fleet node | `node_id`, `environment`, `role`, `country`, `provider`, `region`, `node_class`, `current_lifecycle_state` |
| `NodeDesiredState` | what the controller wants this node to be | `target_lifecycle_state`, `target_role`, `target_pool_id`, `drain_requested`, `quarantine_requested` |
| `NodeObservedState` | what the controller currently knows to be true | `observed_lifecycle_state`, `last_seen_at`, `enrollment_status`, `services_status`, `synthetic_status` |
| `TrafficEligibility` | traffic admission state and rationale | `eligibility_state`, `eligible_at`, `blocked_reason`, `adapter_ack_state` |
| `HealthSignal` | normalized health telemetry sample | `signal_id`, `node_id`, `signal_type`, `severity`, `observed_at`, `source` |
| `DpiSignal` | normalized DPI impairment evidence | `dpi_signal_id`, `node_id`, `confidence_hint`, `observed_at`, `source` |
| `BootstrapToken` | one-time or narrow bootstrap secret reference | `token_id`, `node_id`, `operation_run_id`, `expires_at`, `wrapped_ref`, `consumed_at` |
| `NodeCertificate` | steady-state renewable node identity material reference | `certificate_id`, `node_id`, `serial`, `issued_at`, `expires_at`, `revoked_at` |

### 4.3 Request And Workflow Entities

| Entity | Purpose | Canonical examples of fields |
|---|---|---|
| `ProvisioningRequest` | request to create or scale out capacity | `request_id`, `node_pool_id`, `country`, `provider_selector`, `node_class`, `requested_by` |
| `ReplacementRequest` | request to replace an existing node | `request_id`, `target_node_id`, `reason_code`, `replacement_mode`, `requested_by` |
| `FailoverRequest` | request created from policy or operator to shift capacity after impairment | `request_id`, `trigger_reason`, `confidence_score`, `source_signal_group`, `requested_by` |
| `DrainRequest` | request to stop new traffic and retire a node gracefully | `request_id`, `target_node_id`, `reason_code`, `deadline_at` |
| `QuarantineRequest` | request to isolate a node from traffic and sensitive trust flows | `request_id`, `target_node_id`, `reason_code`, `severity` |
| `OperationRun` | durable execution record for one orchestrated flow | `operation_run_id`, `request_type`, `request_id`, `status`, `started_at`, `finished_at` |
| `OperationStep` | durable step record inside an operation | `operation_step_id`, `operation_run_id`, `step_name`, `status`, `attempt`, `error_code` |

Rules:

1. Requests are durable objects, not transient API payloads.
2. `OperationRun` exists even when the infrastructure action fails before VM creation.
3. `Node` identity outlives any single VM boot attempt; provider resource churn must not erase audit history.

## 5. Canonical State Facets

The following state facets are frozen and must appear consistently in later controller design:

| State facet | Meaning |
|---|---|
| `desired_state` | what the controller intends |
| `observed_state` | what the controller currently believes is true |
| `traffic_state` | whether the node may receive traffic |
| `health_state` | current impairment/health posture |
| `bootstrap_state` | whether bootstrap material exists, is valid, or is consumed |
| `certificate_state` | steady-state identity issuance and revocation posture |
| `provider_resource_state` | provider-side VM/network resource posture |

Rules:

1. These facets must not be collapsed into one ambiguous status field.
2. A healthy VM with invalid certificates is not traffic-eligible.
3. A booting VM with issued bootstrap material is not the same thing as an enrolled node.

## 6. Aggregate Relationships

Frozen relationship model:

```text
Provider
  -> ProviderRegion

CountryPolicy
  -> allowed ProviderRegion set

NodePool
  -> NodeClass
  -> CountryPolicy
  -> desired capacity

Node
  -> NodePool
  -> NodeDesiredState
  -> NodeObservedState
  -> TrafficEligibility
  -> BootstrapToken history
  -> NodeCertificate history
  -> HealthSignal stream
  -> DpiSignal stream

ProvisioningRequest / ReplacementRequest / FailoverRequest / DrainRequest / QuarantineRequest
  -> OperationRun
  -> OperationStep(s)
```

Rules:

1. `NodePool` is the preferred durable unit for capacity policy.
2. `Node` is the preferred durable unit for lifecycle and traffic admission.
3. Requests reference nodes or pools; they do not replace them.

## 7. Failover Guardrail Inputs

The following guardrail input names are frozen:

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

These names must remain stable across later controller code, policy documents, and runbooks.

## 8. Non-Goals

This document intentionally does not:

- define the physical database schema;
- define the exact API transport;
- define UI payload shapes for operator consoles;
- replace runtime adapter contracts;
- replace OpenTofu module design.

It freezes the durable domain language and ownership boundaries that later implementation must obey.

## 9. Implementation Implications For Later Phases

This document freezes these later-phase expectations:

1. Any controller implementation must map directly to the durable entities defined here.
2. Future runtime adapters must integrate through these ownership boundaries rather than introducing competing state stores.
3. Legacy Ansible inventory and vaulted rollout values must eventually map into `Node`, `NodePool`, request, and identity objects rather than staying operator-only knowledge.
4. Fleet policy, request, and audit behavior must remain inspectable even when provider actions fail or nodes are replaced.
