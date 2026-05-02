# CyberVPN Platform Foundation P3.3 External Node Service Baseline Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live integration evidence pending  
**Packet:** `P3.3`  
**Primary owners:** `fleet-platform` / `sre-platform`  
**Supporting owners:** `infra-platform`, `transport-backend`, `docs-program`

---

## 1. Packet Role

This document is the execution packet for `P3.3` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [2026-04-22-platform-foundation-p3-2-controller-execution-bootstrap-enrollment-execution-packet.md](2026-04-22-platform-foundation-p3-2-controller-execution-bootstrap-enrollment-execution-packet.md)
- [../api/platform-foundation-external-node-service-baseline-spec.md](../api/platform-foundation-external-node-service-baseline-spec.md)
- [../runbooks/platform-foundation-node-lifecycle-state-machine.md](../runbooks/platform-foundation-node-lifecycle-state-machine.md)

`P3.3` exists to standardize the first controller-side contract for:

- external node baseline profile
- Alloy and health-agent reporting
- enrollment-hook completion
- synthetic verification
- runtime-adapter readiness
- durable traffic-eligibility evaluation

Implementation note:

- this packet is executed as a pre-launch `repo/validation` slice because there are no live
  external nodes, no live runtime-adapter acknowledgements, and no live synthetic probes in
  the current session;
- the repository slice is implemented and locally validated;
- the remaining closure work is live node reporting, live runtime-adapter ack, and real
  traffic-eligibility evidence.

---

## 2. Canonical Decisions For P3.3

1. The controller now owns durable records for:
   - `NodeObservedState`
   - `HealthSignal`
   - `SyntheticCheck`
   - `RuntimeReadiness`
   - `TrafficEligibility`
2. `Alloy` is fixed as a required external-node baseline service.
3. Synthetic verification and runtime-adapter acknowledgement are separate gates.
4. `traffic_eligible` is reached through explicit controller evaluation, not by direct
   runtime-adapter mutation.

---

## 3. Scope

In scope for `P3.3`:

- extend `services/node-fleet-controller/` with:
  - external-node baseline profile service
  - observed-state persistence
  - health-signal ingestion
  - synthetic-check ingestion
  - runtime-readiness ingestion
  - traffic-eligibility evaluator
  - API routes for:
    - baseline profile inspection
    - observed-state reporting
    - health-signal reporting
    - synthetic-check reporting
    - runtime-readiness reporting
    - traffic-eligibility read and evaluation
- add service and API tests for the baseline flow;
- update packet evidence and program records.

Out of scope for this repository slice:

- live Alloy deployment on nodes
- live health-agent rollout
- live synthetic runners
- live runtime-adapter acknowledgement from `helix-adapter`
- live traffic-admission changes against external fleet

---

## 4. Official Constraints

The execution of `P3.3` follows the frozen platform baseline:

- traffic eligibility requires enrollment, health, synthetic checks, and runtime-adapter
  acknowledgement;
- Alloy is the required collector baseline for external VMs;
- runtime adapters are integration surfaces and not the source of truth for fleet state.

Primary sources:

- target-state architecture: [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- node lifecycle runbook: [../runbooks/platform-foundation-node-lifecycle-state-machine.md](../runbooks/platform-foundation-node-lifecycle-state-machine.md)
- Grafana Alloy docs: https://grafana.com/docs/alloy/latest/

---

## 5. Resulting Repository Touchpoints

- `services/node-fleet-controller/src/application/services/external_node_baseline_service.py`
- `services/node-fleet-controller/src/infra/database/models.py`
- `services/node-fleet-controller/src/infra/database/repositories.py`
- `services/node-fleet-controller/src/api/router.py`
- `services/node-fleet-controller/src/api/schemas.py`
- `services/node-fleet-controller/tests/test_p3_3_baseline.py`
- `services/node-fleet-controller/tests/test_p3_3_api.py`
- [../evidence/platform-foundation/2026-04-22/p3-3-external-node-service-baseline/evidence-pack.md](../evidence/platform-foundation/2026-04-22/p3-3-external-node-service-baseline/evidence-pack.md)
