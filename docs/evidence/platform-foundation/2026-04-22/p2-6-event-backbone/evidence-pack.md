# CyberVPN Platform Foundation P2.6 Event Backbone Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P2.6`  
**Phase:** `P2`  
**Primary owners:** `backend-platform` / `transport-backend`  
**Supporting owners:** `infra-platform`, `sre-platform`, `docs-program`  
**Purpose:** record the repository, validation, and operator-surface changes completed for `P2.6`, plus the remaining live evidence required before the packet can be declared complete.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p2-6-event-backbone-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p2-6-event-backbone-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- `Gate B` is also not passed because `P1` still carries unresolved live-evidence residuals.
- `Gate C` cannot be claimed because `P2.1` through `P2.6` still carry live-closure exceptions.
- this evidence pack carries `EX-026` as the formal reason `P2.6` may remain in progress while later `P2` repo-slice work begins.

---

## 2. Result Snapshot

Current `P2.6` result:

- canonical helper added at `infra/scripts/event_backbone_bootstrap.py`;
- helper renders and validates:
  - active stream declarations
  - subject route map
  - active durable consumer contracts
  - reserved-next service-side consumer contracts
  - replay plan scaffold
- canonical stream and replay spec added at:
  - `docs/api/platform-foundation-nats-streams-consumers-and-replay-spec.md`
- active stream scope is frozen as:
  - `PARTNER_EVENTS`
- active durable consumers are frozen as:
  - `analytics_mart`
  - `operational_replay`
- reserved-next service-side consumers are frozen as:
  - `notification_delivery`
  - `realtime_gateway_projection`

This packet is **not yet claimed complete** because:

- no live non-prod JetStream stream creation evidence exists yet;
- no live dispatcher publish evidence exists from the current outbox backlog into JetStream;
- no live durable consumer reconciliation evidence exists yet;
- no live replay drill has been executed;
- no live retirement or narrowing of the legacy Redis SSE or direct WebSocket paths has been proven yet.

That is intentional. `P2.6` first freezes and validates the repository contract, then carries the runtime closure debt explicitly.

---

## 3. Repository Changes Recorded

### 3.1 Helper And Tests

- `infra/scripts/event_backbone_bootstrap.py`
  - parses the current frozen partner-platform event taxonomy from source
  - parses the current default outbox consumers from source
  - renders the first stream, consumer, and replay scaffold
  - validates that the current repository still matches the frozen `P2.6` baseline

- `infra/tests/test_event_backbone_bootstrap.py`
  - validates scaffold rendering
  - validates stream declarations and subject route generation
  - validates the current repository baseline through the helper

### 3.2 Canonical Spec

- `docs/api/platform-foundation-nats-streams-consumers-and-replay-spec.md`
  - freezes the active `P2.6` stream, subject, consumer, and replay posture

### 3.3 Operator Docs

- `infra/README.md`
  - now documents `event_backbone_bootstrap.py` as the canonical helper for `P2.6`

### 3.4 Packet And Program Records

- `docs/plans/2026-04-22-platform-foundation-p2-6-event-backbone-execution-packet.md`
- `docs/plans/2026-04-21-platform-foundation-temporary-exceptions-register.md`
  - now carries `EX-026`

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 Helper Unit Tests

Command:

```bash
python -m unittest infra.tests.test_event_backbone_bootstrap
```

Result:

- `Ran 2 tests`
- `OK`

### 4.2 Python Syntax Check

Command:

```bash
python -m py_compile infra/scripts/event_backbone_bootstrap.py
```

Result:

- compilation completed successfully

### 4.3 Helper Render Smoke

Command shape:

```bash
python infra/scripts/event_backbone_bootstrap.py render-scaffold \
  --repo-root . \
  --output-dir <temporary-dir>
```

Result:

- helper completed successfully against the current repository workspace
- rendered scaffold includes:
  - `backend/dispatcher/stream-declarations.yaml`
  - `backend/dispatcher/subject-route-map.yaml`
  - `backend/dispatcher/consumers/analytics-mart.yaml`
  - `backend/dispatcher/consumers/operational-replay.yaml`
  - `backend/replay/replay-plan.example.yaml`
  - `services/task-worker/reserved-consumers/notification-delivery.yaml`
  - `services/task-worker/reserved-consumers/realtime-gateway-projection.yaml`

### 4.4 Repo Validation Command

Command:

```bash
python infra/scripts/event_backbone_bootstrap.py validate --repo-root .
```

Observed validated baseline:

- current default outbox consumers are still:
  - `analytics_mart`
  - `operational_replay`
- partner event families are still readable from source
- helper reported:
  - `partner_event_families=18`
  - `partner_transport_subjects=68`
- outbox repository still contains claim, submit, publish, and fail transitions
- canonical outbox, consumer, and stream-spec docs all exist
- current legacy realtime delivery paths are still explicitly tracked

### 4.5 Workspace Readiness Check For Live Closure

Observed in the current workspace on 2026-04-22:

- no live non-prod stream state exists;
- no live NATS auth or stream-management credentials exist;
- no live dispatcher process exists;
- no live durable consumer exists for the first active stream;
- no replay drill evidence exists.

Meaning:

- the packet cannot honestly claim the durable event backbone is operational yet;
- `P2.6` must therefore carry a formal residual until real stream, dispatcher, consumer, and replay evidence are attached.

---

## 5. Remaining Live Closure Requirements

`P2.6` can only move from “repo slice complete” to “packet complete” when the following evidence exists:

1. live `PARTNER_EVENTS` stream creation exists on the non-prod NATS cluster;
2. live dispatcher evidence exists for:
   - claim
   - publish
   - publish metadata persistence in `publication_payload`
3. at least one real durable consumer path exists for:
   - `analytics_mart` or
   - `operational_replay`
4. replay tooling has a real non-prod execution record;
5. backlog and lag evidence exists for the first active path;
6. `EX-026` is removed from the exceptions register.
