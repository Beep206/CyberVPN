# CyberVPN Platform Foundation P3.4 Operator-Driven Workflows Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live workflow evidence pending  
**Packet:** `P3.4`  
**Primary owners:** `fleet-platform`  
**Supporting owners:** `infra-platform`, `transport-backend`, `docs-program`

---

## 1. Packet Role

This document is the execution packet for `P3.4` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [2026-04-22-platform-foundation-p3-3-external-node-service-baseline-execution-packet.md](2026-04-22-platform-foundation-p3-3-external-node-service-baseline-execution-packet.md)
- [../api/node-fleet-controller-operator-command-model.md](../api/node-fleet-controller-operator-command-model.md)

`P3.4` exists to turn frozen operator-command vocabulary into controller-native workflow
surfaces for:

- `node-add`
- `node-replace`
- `node-drain`
- `node-quarantine`
- node-pool capacity workflows

Implementation note:

- this packet is executed as a pre-launch `repo/validation` slice because there is no live
  controller deployment, no live operator wrapper, and no live external infrastructure in the
  current session;
- the repository slice is implemented and locally validated;
- remaining closure work is live controller execution and durable workflow evidence against
  real fleet nodes and node pools.

---

## 2. Canonical Decisions For P3.4

1. Generic `POST /requests` remains available, but operator workflows now have typed controller
   routes instead of relying on raw `RequestType` payloads.
2. `NodePool` becomes a durable controller record used for capacity-oriented operator flows.
3. `node-add` derives or uses a durable pool and increments desired capacity before submitting
   a provisioning request.
4. `node-replace`, `node-drain`, and `node-quarantine` require a real target node record.
5. Capacity adjustments create provisioning or drain requests based on desired-capacity delta.

---

## 3. Scope

In scope for `P3.4`:

- extend `services/node-fleet-controller/` with:
  - durable `NodePool` record
  - operator command service
  - typed API routes for operator command families
  - typed node-pool create/read and capacity-adjust routes
- add service and API tests for operator-driven workflows;
- update packet evidence and program records.

Out of scope for this repository slice:

- live CLI or `make` wrapper implementation
- live approval workflow
- live OpenTofu execution from operator commands
- live drain/quarantine effects on runtime adapters

---

## 4. Resulting Repository Touchpoints

- `services/node-fleet-controller/src/application/services/operator_command_service.py`
- `services/node-fleet-controller/src/infra/database/models.py`
- `services/node-fleet-controller/src/infra/database/repositories.py`
- `services/node-fleet-controller/src/api/router.py`
- `services/node-fleet-controller/src/api/schemas.py`
- `services/node-fleet-controller/tests/test_p3_4_operator_commands.py`
- [../evidence/platform-foundation/2026-04-22/p3-4-operator-driven-workflows/evidence-pack.md](../evidence/platform-foundation/2026-04-22/p3-4-operator-driven-workflows/evidence-pack.md)
