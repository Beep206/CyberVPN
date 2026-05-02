# CyberVPN Platform Foundation P3.3 External Node Service Baseline Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P3.3`  
**Phase:** `P3`  
**Primary owners:** `fleet-platform` / `sre-platform`  
**Supporting owners:** `infra-platform`, `transport-backend`, `docs-program`

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p3-3-external-node-service-baseline-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p3-3-external-node-service-baseline-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-22-platform-foundation-p3-2-controller-execution-bootstrap-enrollment-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p3-2-controller-execution-bootstrap-enrollment-execution-packet.md)

Important gate note:

- `Gate D` still cannot be claimed.
- `P3.3` carries `EX-032` as the formal reason later work may continue while live external
  node reporting and readiness proof are still absent.

---

## 2. Result Snapshot

Current `P3.3` result:

- the controller now persists:
  - `NodeObservedState`
  - `HealthSignal`
  - `SyntheticCheck`
  - `RuntimeReadiness`
  - `TrafficEligibility`
- a baseline profile exists for external nodes with:
  - `alloy`
  - `fleet-health-agent`
  - role-specific primary service
  - `node-enrollment-hook`
  - `egress-connectivity` synthetic probe
  - `helix-adapter` runtime adapter
- traffic-eligibility evaluation now distinguishes:
  - `blocked`
  - `ready`
  - `eligible`
- the controller advances nodes to:
  - `verifying`
  - `ready`
  - `traffic_eligible`
  based on explicit observed-state inputs

This packet is **not yet claimed complete** because:

- no live external node is reporting Alloy or health-agent state;
- no live synthetic runner is posting real probe results;
- no live runtime adapter is acknowledging readiness;
- no live traffic-eligibility promotion has been exercised end to end.

---

## 3. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 3.1 Service Unit And API Tests

```bash
cd services/node-fleet-controller
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Result:

- `Ran 9 tests`
- `OK`

### 3.2 Python Syntax Check

```bash
cd services/node-fleet-controller
.venv/bin/python -m py_compile $(find src -name '*.py' -print)
```

Result:

- compilation completed successfully

### 3.3 Local Foundation Coverage

Observed validated baseline:

- baseline profile returns canonical Alloy, health-agent, hook, synthetic, and adapter contract
- observed-state reporting stores service posture and hook completion
- health-signal ingestion folds severity into node health posture
- synthetic-check reporting updates durable verification state
- runtime-readiness reporting updates durable adapter acknowledgement
- controller evaluation moves a node from `ready` to `eligible` only after adapter ack

---

## 4. Remaining Live Closure Requirements

`P3.3` can only move from "repo slice complete" to "packet complete" when:

1. at least one real external node reports Alloy and health-agent state through the controller;
2. a real synthetic runner posts probe results for that node;
3. a real runtime adapter acknowledges readiness for that node;
4. the controller promotes that node to `traffic_eligible` under live conditions;
5. `EX-032` is removed from the exceptions register.
