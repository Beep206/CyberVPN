# CyberVPN Platform Foundation Node Lifecycle State Machine

**Date:** 2026-04-22  
**Status:** Frozen baseline for `T0.5`

This document freezes the canonical node lifecycle states, state-facet tracking, and admission criteria for external fleet nodes managed by the `Node Fleet Controller`.

It is the `Phase 0` companion to:

- [2026-04-21-platform-foundation-target-state-architecture.md](../plans/2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-phase-0-execution-packet.md](../plans/2026-04-21-platform-foundation-phase-0-execution-packet.md)
- [node-fleet-controller-domain-model.md](../api/node-fleet-controller-domain-model.md)
- [node-fleet-controller-operator-command-model.md](../api/node-fleet-controller-operator-command-model.md)

This runbook exists so later controller implementation, drills, and runbooks all use the same lifecycle vocabulary.

## 1. Canonical Lifecycle States

Frozen lifecycle states:

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

Rules:

1. These state names are canonical and must not be renamed casually in later docs or code.
2. A node may have additional facet states, but lifecycle reporting must still map back to this state machine.
3. `traffic_eligible` is a lifecycle fact, not just a provider or adapter hint.

## 2. State Facets That Must Be Tracked Separately

The lifecycle state machine does not replace the required state facets.

Frozen facets:

- `desired_state`
- `observed_state`
- `traffic_state`
- `health_state`
- `bootstrap_state`
- `certificate_state`
- `provider_resource_state`

Rules:

1. A node may be `vm_created` while `bootstrap_state` is still pending.
2. A node may be `ready` while `traffic_state` is still blocked.
3. A node may be `quarantined` while `provider_resource_state` is still active.
4. A node may be `failed` while later reconciliation still decides whether to retry, replace, or terminate.

## 3. Canonical State Table

| Lifecycle state | Meaning | Typical entry condition | Typical next states |
|---|---|---|---|
| `requested` | durable request accepted for new or changed node lifecycle | request row created | `placement_selected`, `failed` |
| `placement_selected` | provider, region, country, and node class chosen | placement policy resolved | `plan_created`, `failed` |
| `plan_created` | OpenTofu plan created and attached to operation | plan artifact stored | `plan_approved`, `failed` |
| `plan_approved` | approvals and policy gates passed | risk and budget gates satisfied | `applying_infra`, `failed` |
| `applying_infra` | provider resources are being created or changed | OpenTofu apply running | `vm_created`, `failed` |
| `vm_created` | provider VM and base infrastructure objects exist | provider resources created successfully | `bootstrap_issued`, `failed` |
| `bootstrap_issued` | wrapped bootstrap secret and initial handoff prepared | OpenBao bootstrap material issued | `booting`, `failed` |
| `booting` | machine is starting and consuming bootstrap context | VM reachable and boot sequence started | `enrolling`, `failed` |
| `enrolling` | node is registering with controller/runtime services | enrollment handshake in progress | `configuring`, `failed` |
| `configuring` | node receives steady-state config, certs, service setup | enrollment accepted and config handoff started | `verifying`, `failed` |
| `verifying` | health, synthetic, and runtime checks are being evaluated | expected services up and checks running | `ready`, `failed` |
| `ready` | node passed baseline checks but is not yet serving traffic | verification green | `traffic_eligible`, `draining`, `quarantined`, `failed` |
| `traffic_eligible` | node may receive production traffic | traffic gates passed and adapter acknowledged | `draining`, `quarantined`, `rotating`, `terminating`, `failed` |
| `draining` | node is being removed from active traffic gradually | drain request accepted | `terminating`, `ready`, `quarantined`, `failed` |
| `quarantined` | node is isolated from traffic and sensitive trust paths | quarantine request or severe impairment | `terminating`, `rotating`, `failed` |
| `rotating` | identity or service rotation is in progress | cert/service rotation initiated | `ready`, `traffic_eligible`, `failed` |
| `terminating` | node and provider resources are being retired | delete/retire path confirmed | `deleted`, `failed` |
| `deleted` | node lifecycle completed and resources retired | provider resources removed and record closed | terminal |
| `failed` | controller reached a failure state needing retry, replacement, or investigation | any unrecoverable step failure | `requested`, `quarantined`, `terminating`, terminal investigation |

## 4. Traffic Eligibility Contract

A node must not become `traffic_eligible` until all of the following are true:

1. enrollment succeeded;
2. expected services are running;
3. VPN or edge daemon health is green;
4. Alloy telemetry is flowing;
5. certificates are valid;
6. provider IP, DNS, and firewall state match policy;
7. synthetic connectivity checks pass;
8. runtime adapter acknowledges readiness;
9. no quarantine or policy block is active.

Rules:

1. `vm_created` does not imply readiness.
2. `ready` does not imply traffic eligibility.
3. Runtime adapter acknowledgement alone is insufficient without the other gates.

## 5. Failure And Retry Interpretation

Frozen failure interpretation:

1. `failed` is not a synonym for “delete immediately”.
2. The controller may retry within the same `OperationRun`, start a new `OperationRun`, replace the node, or quarantine it depending on the failure class.
3. Duplicate or repeated health impairments must not create ambiguous lifecycle language.

Typical failure classes:

- provider apply failure;
- bootstrap issuance failure;
- bootstrap consumption failure;
- enrollment rejection;
- configuration failure;
- synthetic verification failure;
- runtime adapter rejection;
- certificate issuance or rotation failure.

## 6. Lifecycle Events And Commands Mapping

Representative mapping to the platform event taxonomy:

| Type | Canonical subject | Typical lifecycle relevance |
|---|---|---|
| Command | `node.command.provision_requested.v1` | enters `requested` |
| Command | `node.command.replace_requested.v1` | replacement flow start |
| Command | `node.command.quarantine_requested.v1` | enters quarantine path |
| Event | `node.lifecycle.bootstrap_issued.v1` | enters `bootstrap_issued` |
| Event | `node.lifecycle.ready.v1` | enters `ready` |
| Event | `node.lifecycle.traffic_eligible.v1` | enters `traffic_eligible` |
| Event | `node.health.dpi_detected.v1` | may trigger failover or quarantine request |

Rules:

1. Commands request movement; events confirm movement or observed facts.
2. Durable lifecycle state remains authoritative even when events are delayed or replayed.

## 7. Operational Targets Frozen Here

Baseline targets:

- manual node-add request to `traffic_eligible`: `p95 <= 10 minutes`
- healthy replacement request to `traffic_eligible`: `p95 <= 10 minutes`
- DPI failover detection to replacement request after confidence threshold: `p95 <= 30 seconds`
- health signal ingestion: `p95 <= 5 seconds`
- manual secret copy operations in steady state: `0`

These are control-loop targets, not shell-command timing promises.

## 8. Required Drill Scenarios

The following lifecycle failure drills are frozen:

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

## 9. Implementation Implications For Later Phases

This runbook freezes these later-phase expectations:

1. Controller code, dashboards, and incidents must report node progression using this lifecycle vocabulary.
2. Runtime adapters and verification pipelines must map their readiness signals back into these states.
3. Legacy rollout procedures must eventually show where they fit into this state machine instead of inventing one-off language.
