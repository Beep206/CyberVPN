# CyberVPN Platform Foundation P3.5 Failover Policy Engine Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live failover evidence pending  
**Packet:** `P3.5`  
**Primary owners:** `fleet-platform`  
**Supporting owners:** `infra-platform`, `transport-backend`, `security`, `docs-program`

---

## 1. Packet Role

This document is the execution packet for `P3.5` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [2026-04-22-platform-foundation-p3-4-operator-driven-workflows-execution-packet.md](2026-04-22-platform-foundation-p3-4-operator-driven-workflows-execution-packet.md)
- [../api/node-fleet-controller-domain-model.md](../api/node-fleet-controller-domain-model.md)
- [../api/node-fleet-controller-operator-command-model.md](../api/node-fleet-controller-operator-command-model.md)

`P3.5` exists to turn the frozen failover guardrail vocabulary into controller-native
policy records and typed failover evaluation flow for:

- budget guardrails
- rate-limit and cooldown guardrails
- confidence and signal-source guardrails
- approval thresholds
- typed `node-failover` workflow entry

Implementation note:

- this packet is executed as a pre-launch `repo/validation` slice because there is no live
  controller deployment, no live external fleet, and no live provider impairment simulator
  in the current session;
- the repository slice is implemented and locally validated;
- remaining closure work is live failover signal ingestion, policy-backed workflow entry,
  and real guarded failover evidence against real fleet nodes and node pools.

---

## 2. Canonical Decisions For P3.5

1. Failover automation is allowed only through explicit durable policy records.
2. Policy evaluation may create a durable failover request in:
   - `accepted`
   - `awaiting_approval`
   - `blocked_policy`
3. A blocked or approval-gated failover request is still a durable controller fact and is
   not discarded as a transient validation error.
4. `node-failover` remains the typed operator workflow entry; it does not bypass the
   durable request model.
5. NATS command publication occurs only when a failover request is truly `accepted`.

---

## 3. Scope

In scope for `P3.5`:

- extend `services/node-fleet-controller/` with:
  - durable budget policy records
  - durable rate-limit and cooldown policy records
  - durable approval policy records
  - durable failover guardrail policy records
  - failover policy bundle service and evaluation logic
  - typed API routes for policy upsert/read
  - typed `node-failover` route with blocked/approval/accepted outcomes
- extend request handling so blocked or approval-gated requests persist durably without
  pretending they were published to NATS;
- add service and API tests for failover guardrails;
- update packet evidence and program records.

Out of scope for this repository slice:

- live signal aggregation from deployed health agents
- live provider impairment correlation
- live approval workflow UI or human approval executor
- live failover canary and traffic shift execution

---

## 4. Resulting Repository Touchpoints

- `services/node-fleet-controller/src/domain/entities.py`
- `services/node-fleet-controller/src/domain/exceptions.py`
- `services/node-fleet-controller/src/infra/database/models.py`
- `services/node-fleet-controller/src/infra/database/repositories.py`
- `services/node-fleet-controller/src/application/services/request_service.py`
- `services/node-fleet-controller/src/application/services/failover_policy_service.py`
- `services/node-fleet-controller/src/api/dependencies.py`
- `services/node-fleet-controller/src/api/router.py`
- `services/node-fleet-controller/src/api/schemas.py`
- `services/node-fleet-controller/tests/test_p3_5_failover_policy.py`
- `services/node-fleet-controller/README.md`
- [../evidence/platform-foundation/2026-04-22/p3-5-failover-policy-engine/evidence-pack.md](../evidence/platform-foundation/2026-04-22/p3-5-failover-policy-engine/evidence-pack.md)
