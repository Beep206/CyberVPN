# CyberVPN Platform Foundation P3.2 Controller Executor, Bootstrap, And Enrollment Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P3.2`  
**Phase:** `P3`  
**Primary owners:** `fleet-platform` / `infra-platform`  
**Supporting owners:** `backend-platform`, `security`, `transport-backend`, `docs-program`

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p3-2-controller-execution-bootstrap-enrollment-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p3-2-controller-execution-bootstrap-enrollment-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-22-platform-foundation-p3-1-node-fleet-controller-foundation-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p3-1-node-fleet-controller-foundation-execution-packet.md)

Important gate note:

- `Gate D` still cannot be claimed.
- `P3.2` carries `EX-031` as the formal reason later work may continue while live integration
  proof is still absent.

---

## 2. Result Snapshot

Current `P3.2` result:

- the controller now persists:
  - `Node`
  - `BootstrapToken`
  - `NodeCertificate`
  - `OperationStep`
- an auditable OpenTofu executor preview exists with:
  - state locking requirement
  - policy-check requirement
  - workspace isolation key
  - plan artifact reference
  - redacted variables
- an OpenBao manager exists with preview-safe:
  - bootstrap token issuance
  - fleet certificate issuance
- enrollment completion now:
  - consumes bootstrap material
  - issues certificate-backed identity
  - advances node state
- certificate rotation now exists as an explicit controller flow

This packet is **not yet claimed complete** because:

- no live OpenTofu runner exists;
- no live OpenBao issue/unwrap proof exists;
- no live external node enrollment exists;
- no live certificate rotation evidence exists.

---

## 3. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 3.1 Service Unit And API Tests

```bash
cd services/node-fleet-controller
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Result:

- `Ran 7 tests`
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

- executor preview stores an auditable step and redacts sensitive variables
- bootstrap issuance creates a durable bootstrap token record
- enrollment consumes bootstrap material and issues a certificate record
- rotation revokes the prior active certificate and creates a new one
- API exposes node, executor-preview, bootstrap, enrollment, and rotation routes

---

## 4. Remaining Live Closure Requirements

`P3.2` can only move from "repo slice complete" to "packet complete" when:

1. a live controller runtime performs guarded OpenTofu execution through the approved runner
   model;
2. OpenBao bootstrap issuance and unwrap are proven against the real non-prod cluster;
3. at least one node completes bootstrap and enrollment through the controller flow;
4. certificate rotation is exercised and audited end to end;
5. `EX-031` is removed from the exceptions register.
