# CyberVPN Platform Foundation P3.1 Node Fleet Controller Foundation Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live controller rollout evidence pending  
**Packet:** `P3.1`  
**Primary owners:** `fleet-platform` / `backend-platform`  
**Supporting owners:** `infra-platform`, `transport-backend`, `security`, `docs-program`

---

## 1. Packet Role

This document is the execution packet for `P3.1` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../api/node-fleet-controller-domain-model.md](../api/node-fleet-controller-domain-model.md)
- [../api/node-fleet-controller-operator-command-model.md](../api/node-fleet-controller-operator-command-model.md)
- [../runbooks/platform-foundation-node-lifecycle-state-machine.md](../runbooks/platform-foundation-node-lifecycle-state-machine.md)

`P3.1` exists to create the first real implementation surface for the `Node Fleet Controller`
instead of leaving fleet automation as pure architecture prose.

Implementation note:

- this packet is executed as a pre-launch `repo/validation` slice because no live controller
  database, no live NATS cluster integration, no live OpenTofu executor wiring, and no live
  OpenBao bootstrap path exist in the current session;
- the repository slice is implemented and locally validated;
- the remaining closure work is a real controller deployment, live DB persistence, real
  NATS publication proof, and operator-facing request flow evidence.

---

## 2. Current Baseline

Before this packet:

- `P0.5` froze the durable controller model, lifecycle vocabulary, and operator command
  model;
- `P1.3` froze the non-prod NATS control-plane substrate;
- `P2.5` froze the first GitOps-backed workload delivery model that later controller
  deployment will use;
- the repository still has no dedicated `Node Fleet Controller` service directory, meaning
  fleet automation would otherwise remain split between docs, legacy Ansible procedures, and
  runtime adapters.

Observed strengths:

- the durable domain language is already frozen and stable;
- the program already knows where fleet state boundaries belong:
  - controller DB
  - OpenTofu
  - OpenBao
  - NATS
  - runtime adapters
- NATS subject taxonomy is already frozen for `node.command.*`, `node.lifecycle.*`,
  `node.health.*`, and `provider.health.*`.

Observed implementation risks:

- without a real service scaffold, later `P3` packets would be forced to invent API, DB,
  workflow, and audit surfaces ad hoc;
- a late controller start would create pressure to let shell wrappers or runtime adapters
  quietly become the source of truth;
- NATS could be misused as the fleet store if the controller does not claim durable request
  and audit ownership first.

---

## 3. Canonical Decisions For P3.1

`P3.1` fixes the following decisions:

1. The first controller implementation lives in:
   - `services/node-fleet-controller/`
2. The service language is Python and the API language is FastAPI.
3. Durable request, operation-run, and audit state live in the controller database layer.
4. The first API surface includes:
   - health
   - durable request creation
   - durable request inspection
   - audit inspection
   - reconcile preview
5. The first workflow engine is a deterministic planner over the frozen request families:
   - `provisioning`
   - `replacement`
   - `drain`
   - `quarantine`
   - `failover`
6. The first NATS adapter publishes canonical `node.command.*.v1` envelopes but does not
   claim live completion in this packet.
7. `P3.1` does not yet execute OpenTofu, OpenBao bootstrap, enrollment, or runtime-adapter
   calls; those remain explicitly deferred to later `P3` packets.

---

## 4. Scope

In scope for `P3.1`:

- create `services/node-fleet-controller/` with:
  - FastAPI app entry point
  - service settings
  - domain enums, entities, and exceptions
  - SQLAlchemy async database layer
  - durable request repository
  - request-submission service
  - workflow planner
  - reconcile preview service
  - audit-trail service
  - NATS adapter
- add unit and API tests for the foundation slice;
- update `services/README.md`;
- add packet evidence and program-record updates.

Out of scope for the current repository slice executed in this workspace:

- live controller deployment on Kubernetes;
- live PostgreSQL-backed controller DB;
- live NATS publication acknowledgement from non-prod;
- OpenTofu executor safety implementation;
- OpenBao bootstrap manager implementation;
- node enrollment and certificate rotation implementation;
- runtime-adapter integration;
- operator CLI wrapper implementation.

---

## 5. Official Constraints

The execution of `P3.1` follows current primary-source guidance:

- FastAPI recommends splitting larger applications with `APIRouter` modules instead of one
  monolithic entrypoint;
- SQLAlchemy async guidance uses `async_sessionmaker` for reusable `AsyncSession` factories
  and warns that one `AsyncSession` instance must not be shared across concurrent tasks;
- `pydantic-settings` keeps runtime configuration in `BaseSettings` / `SettingsConfigDict`;
- JetStream publication through `nats.py` remains the canonical Python client path for
  durable request publication.

Primary sources:

- FastAPI bigger applications: https://fastapi.tiangolo.com/tutorial/bigger-applications/
- SQLAlchemy asyncio / `async_sessionmaker`: https://docs.sqlalchemy.org/20/orm/extensions/asyncio.html
- SQLAlchemy session safety notes: https://docs.sqlalchemy.org/en/20/orm/session_basics.html
- Pydantic settings management: https://docs.pydantic.dev/usage/settings/
- NATS JetStream: https://docs.nats.io/nats-concepts/jetstream
- `nats.py` client reference: https://github.com/nats-io/nats.py

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P3.1`:

### 6.1 New Service

- [services/node-fleet-controller/README.md](../../services/node-fleet-controller/README.md)
- [services/node-fleet-controller/pyproject.toml](../../services/node-fleet-controller/pyproject.toml)
- [services/node-fleet-controller/src/main.py](../../services/node-fleet-controller/src/main.py)
- [services/node-fleet-controller/src/api/router.py](../../services/node-fleet-controller/src/api/router.py)
- [services/node-fleet-controller/src/application/services/request_service.py](../../services/node-fleet-controller/src/application/services/request_service.py)
- [services/node-fleet-controller/src/application/services/reconciler.py](../../services/node-fleet-controller/src/application/services/reconciler.py)
- [services/node-fleet-controller/src/application/services/workflow_engine.py](../../services/node-fleet-controller/src/application/services/workflow_engine.py)
- [services/node-fleet-controller/src/application/services/audit_service.py](../../services/node-fleet-controller/src/application/services/audit_service.py)
- [services/node-fleet-controller/src/infra/database/repositories.py](../../services/node-fleet-controller/src/infra/database/repositories.py)
- [services/node-fleet-controller/src/infra/messaging/nats_adapter.py](../../services/node-fleet-controller/src/infra/messaging/nats_adapter.py)

### 6.2 Service Tests

- [services/node-fleet-controller/tests/test_request_service.py](../../services/node-fleet-controller/tests/test_request_service.py)
- [services/node-fleet-controller/tests/test_workflow_engine.py](../../services/node-fleet-controller/tests/test_workflow_engine.py)
- [services/node-fleet-controller/tests/test_nats_adapter.py](../../services/node-fleet-controller/tests/test_nats_adapter.py)
- [services/node-fleet-controller/tests/test_api.py](../../services/node-fleet-controller/tests/test_api.py)

### 6.3 Packet Evidence

- [../evidence/platform-foundation/2026-04-22/p3-1-node-fleet-controller-foundation/evidence-pack.md](../evidence/platform-foundation/2026-04-22/p3-1-node-fleet-controller-foundation/evidence-pack.md)

---

## 7. Workboard

### 7.1 `T3.1.1` Create The Service Boundary

**Goal:** turn the frozen controller domain into a real service directory with a stable
runtime shape.

Deliverables:

- new service root under `services/node-fleet-controller/`
- runtime config
- FastAPI entry point
- API router split

Acceptance criteria:

- the service exists as a first-class monorepo surface;
- `FastAPI` app creation does not depend on live infrastructure;
- service-local validation can run from the repository workspace.

### 7.2 `T3.1.2` Claim Durable Request, Operation, And Audit State

**Goal:** make the controller DB boundary real before any executor or enrollment work begins.

Deliverables:

- SQLAlchemy async models
- durable repository
- request submission service
- audit service

Acceptance criteria:

- request creation yields a durable request record and an operation-run record;
- audit history is persisted with the request;
- idempotency is enforced at the durable request layer.

### 7.3 `T3.1.3` Freeze Workflow Planning And Reconcile Preview

**Goal:** give later controller work a stable workflow spine.

Deliverables:

- workflow engine
- reconcile preview service
- deterministic mapping from request families to workflow steps

Acceptance criteria:

- each frozen request type produces a stable plan;
- reconcile preview operates on durable request state;
- no live executor or runtime adapter side effect is required for the preview layer.

### 7.4 `T3.1.4` Add Canonical NATS Adapter Boundary

**Goal:** make NATS publication a real adapter surface without pretending live transport is
already proven.

Deliverables:

- `node.command.*.v1` subject mapping
- canonical envelope builder
- guarded publish path that can remain disabled in local validation

Acceptance criteria:

- request publication shape matches the frozen taxonomy;
- the adapter can produce canonical envelopes without a live cluster;
- the packet remains honest about missing live JetStream evidence.

### 7.5 `T3.1.5` Produce Local Validation And Honest Residual Tracking

**Goal:** finish the repo slice with evidence and explicit carry-forward debt.

Deliverables:

- service unit and API tests
- evidence pack
- `EX-030` in the exceptions register

Acceptance criteria:

- local tests pass in the current workspace;
- the packet states exactly what remains missing for live closure;
- later `P3` work may proceed without pretending `P3.1` is fully complete.

