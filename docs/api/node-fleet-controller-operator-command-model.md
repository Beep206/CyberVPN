# CyberVPN Node Fleet Controller Operator Command Model

**Date:** 2026-04-22  
**Status:** Frozen baseline for `T0.5`

This document freezes the operator command model behind future fleet commands such as `make node-add COUNTRY=jp`.

It is the `Phase 0` companion to:

- [2026-04-21-platform-foundation-target-state-architecture.md](../plans/2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-phase-0-execution-packet.md](../plans/2026-04-21-platform-foundation-phase-0-execution-packet.md)
- [node-fleet-controller-domain-model.md](node-fleet-controller-domain-model.md)
- [platform-foundation-node-lifecycle-state-machine.md](../runbooks/platform-foundation-node-lifecycle-state-machine.md)

This document exists so future operator UX does not quietly become the source of truth.

## 1. Canonical Decisions Frozen Here

The following decisions are fixed and are not reopened by this document:

1. Operator commands are request-creation UX only.
2. Durable source of truth is the controller API plus durable request records in the controller database.
3. `make` wrappers, shell helpers, and local scripts must never call `OpenTofu` or mutate provider state directly as the canonical path.
4. Every operator command maps to one durable request type and one or more `OperationRun` records.
5. Command success is determined by durable controller state, not terminal output alone.

## 2. Canonical Command Flow

Frozen command flow:

```text
operator command or UI action
  -> Fleet API request
  -> durable request record created
  -> policy validation
  -> approval gate if required
  -> OperationRun created
  -> OpenTofu / OpenBao / runtime adapter steps executed
  -> lifecycle state updated
  -> NATS lifecycle events published
  -> terminal durable status recorded
```

Rules:

1. The wrapper returns a `request_id` or `operation_run_id`, not a fake guarantee that the node is already usable.
2. Provider-side work must be traceable back to the durable request.
3. Every request must be auditable even if it is blocked before execution.

## 3. Canonical Operator Commands

Approved command families:

| UX command family | Durable request type | Scope |
|---|---|---|
| `node-add` | `ProvisioningRequest` | add or scale out capacity |
| `node-replace` | `ReplacementRequest` | replace one existing node |
| `node-drain` | `DrainRequest` | remove traffic eligibility gracefully |
| `node-quarantine` | `QuarantineRequest` | isolate a node immediately |
| `node-failover` | `FailoverRequest` | create policy-driven or operator-driven failover action |

Representative UX forms:

```text
make node-add COUNTRY=jp CLASS=standard PROVIDER=auto
make node-replace NODE_ID=node_jp_01 REASON=dpi_detected
make node-drain NODE_ID=node_jp_01 REASON=planned_rotation
make node-quarantine NODE_ID=node_jp_01 REASON=health_impairment
make node-failover COUNTRY=jp REASON=provider_impairment
```

These examples are convenience syntax only. They are not the durable contract by themselves.

## 4. Durable Request Semantics

Every command must create a durable request object before any provider mutation happens.

Minimum frozen request fields:

- `request_id`
- `request_type`
- `requested_by`
- `requested_at`
- `environment`
- `country`
- `provider_selector`
- `region_selector`
- `node_class`
- `node_pool_id`
- `target_node_id`
- `reason_code`
- `correlation_id`
- `idempotency_key`
- `approval_mode`
- `requested_capacity_delta`
- `status`

Rules:

1. Fields may be empty only when not applicable to the request type.
2. `idempotency_key` is mandatory for every command path.
3. Requests must remain queryable after completion for audit and replay analysis.

## 5. Request Status Model

Frozen request statuses:

```text
accepted
blocked_policy
awaiting_approval
running
completed
failed
cancelled
superseded
```

Rules:

1. `accepted` means the request exists durably.
2. `running` means at least one `OperationRun` is actively executing or reconciling work.
3. `completed` means the durable success condition is true, not merely that one shell command exited successfully.
4. `failed` means the controller reached a terminal failure state for the request.
5. `superseded` means a newer request intentionally replaced this one.

## 6. Idempotency Model

The operator command model is at-least-once from the perspective of request submission and workflow retries.

Frozen invariants:

1. Repeated `node-add` or `node-replace` submissions with the same `idempotency_key` must not silently create duplicate durable requests or duplicate provider mutations.
2. `OperationRun` retries must remain tied to the owning durable request.
3. Provider retries, bootstrap retries, and adapter retries must be visible as `OperationStep` attempts, not hidden in shell logs only.

Representative idempotency guidance:

| Request type | Canonical idempotency basis |
|---|---|
| `ProvisioningRequest` | operator request key or derived planned-capacity action |
| `ReplacementRequest` | `target_node_id + reason_code + generation` |
| `DrainRequest` | `target_node_id + reason_code + requested window` |
| `QuarantineRequest` | `target_node_id + reason_code + severity bucket` |
| `FailoverRequest` | impairment incident or signal-group id |

## 7. Approval And Policy Model

Commands must be policy-checked before infrastructure mutation.

Minimum frozen policy inputs:

- country and provider allowlists;
- node class allowlist;
- budget impact;
- rate-limit posture;
- cooldown posture;
- confidence score for failover actions;
- emergency stop posture.

Rules:

1. Commands may be accepted durably and still land in `blocked_policy` or `awaiting_approval`.
2. High-risk actions may require approval even when invoked by operators.
3. Automatic failover creates the same durable request types; it does not bypass the request model.

## 8. Request-To-Workflow Mapping

Frozen mapping:

| Durable request type | Normal workflow intent |
|---|---|
| `ProvisioningRequest` | place -> plan -> apply infra -> bootstrap -> enroll -> verify -> traffic eligible |
| `ReplacementRequest` | create replacement capacity -> verify -> drain old node -> terminate old node |
| `DrainRequest` | stop new traffic -> wait for drain conditions -> mark retired or ready for termination |
| `QuarantineRequest` | remove from traffic -> revoke/limit trust as needed -> hold for investigation or replacement |
| `FailoverRequest` | evaluate guardrails -> create parallel capacity -> canary -> shift traffic -> drain/quarantine impaired node |

`OperationRun` is the durable execution container for these flows.

## 9. Wrapper UX Boundary

Frozen rule:

`make node-add ...` and similar wrappers are allowed only as thin clients over the Fleet API.

Consequences:

1. The wrapper may validate local arguments and display the resulting `request_id`.
2. The wrapper may poll status from the Fleet API.
3. The wrapper must not become the only place where request semantics live.
4. The wrapper must not be the only audit trail.
5. The wrapper must not directly hold long-lived provider or bootstrap secrets as the target model.

## 10. Runtime Adapter Boundary

Runtime adapters such as `helix-adapter` may acknowledge:

- registration success;
- runtime readiness;
- traffic eligibility confirmation;
- quarantine acceptance;
- rollout status.

They do not own:

- durable request creation;
- approval policy;
- desired capacity;
- durable replacement semantics;
- bootstrap authority;
- node identity authority.

## 11. Implementation Implications For Later Phases

This document freezes these later-phase expectations:

1. Controller API and CLI work must expose the durable request model defined here.
2. Future `make` targets must map one-to-one to approved durable request families.
3. Legacy shell-driven rollout sequences must be converted into explicit request creation plus workflow observation.
4. Any later UI or API surface must use the same request types, status model, and idempotency rules.
