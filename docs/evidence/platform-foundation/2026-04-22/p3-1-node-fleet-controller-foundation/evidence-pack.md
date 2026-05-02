# CyberVPN Platform Foundation P3.1 Node Fleet Controller Foundation Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P3.1`  
**Phase:** `P3`  
**Primary owners:** `fleet-platform` / `backend-platform`  
**Supporting owners:** `infra-platform`, `transport-backend`, `security`, `docs-program`  
**Purpose:** record the repository, validation, and operator-surface changes completed for `P3.1`, plus the remaining live evidence required before the packet can be declared complete.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p3-1-node-fleet-controller-foundation-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p3-1-node-fleet-controller-foundation-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- `Gate B` is not passed because `P1` still carries unresolved live-evidence residuals.
- `Gate C` is not passed because `P2.1` through `P2.9` still carry live-closure exceptions.
- `Gate D` cannot be claimed because `P3.1` itself still carries a live-closure residual.
- this evidence pack carries `EX-030` as the formal reason `P3.1` may remain in progress while later work continues.

---

## 2. Result Snapshot

Current `P3.1` result:

- a first-class controller service now exists at:
  - `services/node-fleet-controller/`
- the service contains:
  - FastAPI API surface
  - durable request, operation-run, and audit models
  - idempotent request submission service
  - deterministic workflow planner
  - reconcile preview service
  - canonical NATS adapter for `node.command.*.v1`
- the service intentionally stops before:
  - OpenTofu execution
  - OpenBao bootstrap issuance
  - enrollment handling
  - runtime-adapter readiness wiring

This packet is **not yet claimed complete** because:

- no live controller database is deployed;
- no live NATS JetStream publish evidence exists from this service;
- no live Kubernetes deployment or GitOps rollout exists for the service;
- no live operator request flow, OpenTofu executor, or OpenBao bootstrap proof exists yet.

That is intentional. `P3.1` claims the service foundation and local validation, then carries
the live controller-closure debt explicitly.

---

## 3. Repository Changes Recorded

### 3.1 New Service

- `services/node-fleet-controller/pyproject.toml`
- `services/node-fleet-controller/README.md`
- `services/node-fleet-controller/src/config.py`
- `services/node-fleet-controller/src/main.py`
- `services/node-fleet-controller/src/api/`
- `services/node-fleet-controller/src/application/services/`
- `services/node-fleet-controller/src/domain/`
- `services/node-fleet-controller/src/infra/database/`
- `services/node-fleet-controller/src/infra/messaging/`

### 3.2 Validation Tests

- `services/node-fleet-controller/tests/test_request_service.py`
- `services/node-fleet-controller/tests/test_workflow_engine.py`
- `services/node-fleet-controller/tests/test_nats_adapter.py`
- `services/node-fleet-controller/tests/test_api.py`

### 3.3 Program Records

- `docs/plans/2026-04-22-platform-foundation-p3-1-node-fleet-controller-foundation-execution-packet.md`
- `docs/plans/2026-04-21-platform-foundation-temporary-exceptions-register.md`
  - now carries `EX-030`
- `docs/plans/2026-04-21-platform-foundation-phased-implementation-plan.md`
  - now records the `P3.1` carry-forward residual
- `services/README.md`
  - now acknowledges `node-fleet-controller` as the canonical `P3` service directory

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 Service Unit And API Tests

Command:

```bash
cd services/node-fleet-controller
.venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

Result:

- service tests completed successfully

### 4.2 Python Syntax Check

Command:

```bash
cd services/node-fleet-controller
.venv/bin/python -m py_compile $(find src -name '*.py' -print)
```

Result:

- compilation completed successfully

### 4.3 Local Service Foundation Coverage

Observed validated baseline:

- durable request creation persists:
  - `fleet_requests`
  - `operation_runs`
  - `audit_entries`
- repeated request submission with the same `idempotency_key` does not create duplicate
  durable requests
- reconcile preview returns workflow plans for accepted requests
- API exposes:
  - `/api/v1/health/live`
  - `/api/v1/requests`
  - `/api/v1/requests/{request_id}`
  - `/api/v1/requests/{request_id}/audit`
  - `/api/v1/reconcile/preview`
- NATS adapter builds canonical `node.command.*.v1` envelopes even when live publication is
  disabled

### 4.4 Workspace Readiness Check For Live Closure

Observed in the current workspace on 2026-04-22:

- no live controller DB instance exists;
- no live NATS JetStream evidence exists for request publication;
- no live Flux or Kubernetes deployment exists for the service;
- no live OpenTofu executor or OpenBao bootstrap wiring exists yet.

Meaning:

- the packet cannot honestly claim the controller foundation is operational in non-prod yet;
- `P3.1` must therefore carry a formal residual until real deployment and integration
  evidence are attached.

---

## 5. Remaining Live Closure Requirements

`P3.1` can only move from "repo slice complete" to "packet complete" when the following
evidence exists:

1. the service is deployed to the chosen non-prod runtime surface;
2. the controller persists requests, operations, and audit entries in a real durable
   database;
3. canonical `node.command.*.v1` publication is proven against the non-prod NATS cluster;
4. at least one operator-visible request flow is exercised end to end against the deployed
   service;
5. deployment or rollback evidence exists for the service runtime;
6. `EX-030` is removed from the exceptions register.
