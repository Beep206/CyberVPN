# CyberVPN Platform Foundation P2.6 Event Backbone Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live dispatcher and JetStream evidence pending  
**Packet:** `P2.6`  
**Primary owners:** `backend-platform` / `transport-backend`  
**Supporting owners:** `infra-platform`, `sre-platform`, `docs-program`

---

## 1. Packet Role

This document is the execution packet for `P2.6` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../api/platform-foundation-event-taxonomy.md](../api/platform-foundation-event-taxonomy.md)
- [../api/platform-foundation-outbox-contract.md](../api/platform-foundation-outbox-contract.md)
- [../api/platform-foundation-consumer-contract.md](../api/platform-foundation-consumer-contract.md)
- [../api/platform-foundation-nats-streams-consumers-and-replay-spec.md](../api/platform-foundation-nats-streams-consumers-and-replay-spec.md)

`P2.6` exists to freeze the first application-side event backbone contract that bridges the current persisted outbox to the future NATS transport layer:

- the current PostgreSQL outbox remains the authoritative publication boundary;
- the first active transport scope is the current partner-platform event subset;
- the first active NATS-aligned stream contract is `PARTNER_EVENTS`;
- the first active durable consumers remain:
  - `analytics_mart`
  - `operational_replay`
- service-side notification and realtime gateway consumers are frozen as reserved-next contracts for `P2.7`, not silently activated early.

Implementation note:

- this packet is executed as a pre-launch `repo/validation` slice because the current workspace does not contain live NATS credentials, live non-prod stream state, or a live dispatcher rollout target;
- the repository slice is implemented and locally validated;
- remaining closure work is live stream creation, dispatcher publish proof, consumer proof, replay proof, and runtime backlog metrics evidence.

---

## 2. Current Baseline

Before this packet:

- the current backend already had a persisted transactional outbox with:
  - `outbox_events`
  - `outbox_publications`
  - claim, submit, publish, and fail transitions
- the current backend already had named default consumer keys:
  - `analytics_mart`
  - `operational_replay`
- the current backend event names already followed the frozen partner-platform taxonomy, but had no repo-side NATS stream contract or dispatcher scaffold;
- service-side realtime delivery still relied on transient paths such as Redis SSE and direct WebSocket fan-out.

Observed strengths:

- the outbox state model already exists and is durable enough to anchor later transport work;
- the Phase 0 taxonomy, outbox contract, and consumer contract already froze the correct boundaries;
- the non-prod NATS substrate was already defined in `P1.3`.

Observed implementation risks:

- without a canonical stream and consumer spec, later code could introduce ad hoc subjects, anonymous consumers, or direct-publish shortcuts;
- without a repo-side dispatcher scaffold, future live cut-in could drift away from the frozen outbox semantics;
- without a reserved-next consumer contract, `P2.7` could reactivate legacy SSE or notification paths without a durable ownership model.

---

## 3. Canonical Decisions For P2.6

`P2.6` fixes the following decisions:

1. The existing persisted PostgreSQL outbox remains the only business-critical publication boundary for the current backend subset.
2. The first active transport scope is the partner-platform outbox subset already implemented in the backend.
3. The first active stream contract is:
   - `PARTNER_EVENTS`
4. Current application event names stay versionless in the outbox rows; transport subjects become:
   - `partner.<event_name>.v1`
5. Active durable consumers remain:
   - `analytics_mart`
   - `operational_replay`
6. Default business-side durable consumers use:
   - durable consumers
   - pull mode
   - explicit acknowledgements
7. Replay-original or ordered-consumer behavior is an inspection tool, not the default business side-effect path.
8. `notification_delivery` and `realtime_gateway_projection` are frozen as reserved-next consumers for `P2.7`.
9. Direct Redis SSE and direct WebSocket broadcast remain temporary downstream delivery surfaces and must not be treated as the durable event backbone.

---

## 4. Scope

In scope for `P2.6`:

- add a canonical helper under [infra/scripts/event_backbone_bootstrap.py](../../infra/scripts/event_backbone_bootstrap.py);
- add unit coverage for the helper;
- add the first repo-side stream, consumer, and replay spec at [../api/platform-foundation-nats-streams-consumers-and-replay-spec.md](../api/platform-foundation-nats-streams-consumers-and-replay-spec.md);
- render backend dispatcher scaffold for:
  - stream declarations
  - subject route map
  - active consumer contracts
  - replay plan scaffold
- render service-side reserved-next consumer contracts for:
  - `notification_delivery`
  - `realtime_gateway_projection`
- update operator docs so the helper is discoverable from `infra/README.md`;
- record packet evidence and a formal carry-forward residual.

Out of scope for the current repository slice executed in this workspace:

- live stream creation on the non-prod NATS cluster;
- live dispatcher deployment or backlog drain;
- live durable consumer reconciliation;
- live replay drill execution;
- live retirement of Redis SSE or direct WebSocket delivery.

---

## 5. Official Constraints

The execution of `P2.6` follows current primary-source guidance:

- JetStream streams store published messages while consumers track delivery and acknowledgments;
- pull consumers are recommended for new projects, especially where scalability and controlled error handling matter;
- durable consumers persist state and recover from inactivity or failure;
- stream deduplication uses the `Nats-Msg-Id` header;
- replay-original behavior is a push-consumer capability and therefore belongs to inspection or operator replay, not the default business durable-consumer mode.

Primary sources:

- JetStream overview: https://docs.nats.io/nats-concepts/jetstream
- Streams: https://docs.nats.io/nats-concepts/jetstream/streams
- Consumers: https://docs.nats.io/nats-concepts/jetstream/consumers
- JetStream model deep dive: https://docs.nats.io/using-nats/developer/develop_jetstream/model_deep_dive

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P2.6`:

### 6.1 Helper And Tests

- [infra/scripts/event_backbone_bootstrap.py](../../infra/scripts/event_backbone_bootstrap.py)
- [infra/tests/test_event_backbone_bootstrap.py](../../infra/tests/test_event_backbone_bootstrap.py)

### 6.2 Canonical Spec Added During P2.6

- [../api/platform-foundation-nats-streams-consumers-and-replay-spec.md](../api/platform-foundation-nats-streams-consumers-and-replay-spec.md)

### 6.3 Existing Surfaces Updated During P2.6

- [infra/README.md](../../infra/README.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)

### 6.4 Packet Evidence

- [../evidence/platform-foundation/2026-04-22/p2-6-event-backbone/evidence-pack.md](../evidence/platform-foundation/2026-04-22/p2-6-event-backbone/evidence-pack.md)

---

## 7. Workboard

### 7.1 `T2.6.1` Freeze The First Active Stream Contract

**Goal:** make the first NATS-aligned stream contract explicit and tied to the real current outbox subset.

Deliverables:

- active stream spec
- subject route map
- deduplication header and publish metadata contract

Acceptance criteria:

- the first active stream is frozen as `PARTNER_EVENTS`;
- current partner-platform event names map to `partner.<event_name>.v1`;
- publication metadata requirements remain downstream of the outbox boundary.

### 7.2 `T2.6.2` Freeze The Active Durable Consumer Registry

**Goal:** make the current durable consumers governed rather than implicit.

Deliverables:

- consumer contracts for:
  - `analytics_mart`
  - `operational_replay`

Acceptance criteria:

- both consumer keys already present in code are promoted to first-class governed consumers;
- consumer mode, ack posture, idempotency posture, and replay posture are explicit.

### 7.3 `T2.6.3` Freeze Reserved-Next Service Consumers

**Goal:** stop the later realtime and notification cut-in from inventing anonymous consumers.

Deliverables:

- reserved-next consumer contracts for:
  - `notification_delivery`
  - `realtime_gateway_projection`

Acceptance criteria:

- reserved consumers are explicit;
- the packet does not pretend they are live yet;
- their ownership and transport boundary are documented before `P2.7`.

### 7.4 `T2.6.4` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable before any real stream or consumer exists in non-prod.

Deliverables:

- helper unit tests
- local validation command
- render smoke
- packet evidence pack
- formal carry-forward residual for missing live dispatcher, consumer, and replay evidence

Acceptance criteria:

- the repository slice is locally validated;
- the current outbox baseline and consumer keys are checked by code;
- live closure requirements are explicit.

---

## 8. State-Boundary Rules

`P2.6` must keep the following invariants:

1. PostgreSQL outbox tables remain the publication source of truth for the current active subset.
2. NATS transport metadata is downstream of the outbox, not a replacement for it.
3. Direct Redis SSE or direct WebSocket fan-out remain temporary downstream paths only.
4. Service-side reserved-next consumers must not be misread as active cut-in proof.
5. `P2.6` must not claim live dispatcher or JetStream success from repository-only work.
