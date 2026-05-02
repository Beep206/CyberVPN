# CyberVPN Platform Foundation P3.4 Operator-Driven Workflows Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P3.4`  
**Phase:** `P3`  
**Primary owners:** `fleet-platform`  
**Supporting owners:** `infra-platform`, `transport-backend`, `docs-program`

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p3-4-operator-driven-workflows-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p3-4-operator-driven-workflows-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-22-platform-foundation-p3-3-external-node-service-baseline-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p3-3-external-node-service-baseline-execution-packet.md)

Important gate note:

- `Gate D` still cannot be claimed.
- `P3.4` carries `EX-033` as the formal reason later work may continue while live operator
  workflow proof is still absent.

---

## 2. Result Snapshot

Current `P3.4` result:

- the controller now persists:
  - `NodePool`
- typed operator workflow surfaces now exist for:
  - `node-add`
  - `node-replace`
  - `node-drain`
  - `node-quarantine`
  - `node-pool capacity adjustment`
- capacity workflows now map desired-capacity delta into:
  - provisioning requests for scale-out
  - drain requests for scale-in
  - explicit no-op result when desired capacity already matches target

This packet is **not yet claimed complete** because:

- no live operator wrapper is invoking these routes;
- no live controller deployment is executing these requests;
- no live node-pool reconciliation exists;
- no live drain, quarantine, or replacement evidence exists.

---

## 3. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 3.1 Service Unit And API Tests

```bash
cd services/node-fleet-controller
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Result:

- `Ran 12 tests`
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

- `node-add` creates or reuses a durable node pool and emits a provisioning request
- `capacity-adjust` updates desired capacity and maps delta to provisioning or drain requests
- `node-replace`, `node-drain`, and `node-quarantine` require a real target node
- typed operator routes exist instead of pushing operators through raw generic request payloads

---

## 4. Remaining Live Closure Requirements

`P3.4` can only move from "repo slice complete" to "packet complete" when:

1. at least one live operator command enters the controller through the typed operator surface;
2. a live node-pool capacity change reconciles through the controller;
3. live `replace`, `drain`, or `quarantine` workflow evidence exists for a real node;
4. `EX-033` is removed from the exceptions register.
