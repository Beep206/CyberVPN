# CyberVPN Platform Foundation NATS Streams, Consumers, And Replay Spec

**Date:** 2026-04-22  
**Status:** `P2.6` implementation baseline

This document translates the frozen `T0.2` taxonomy and outbox rules into the first active NATS-aligned implementation contract for the repository.

It is the implementation companion to:

- [platform-foundation-event-taxonomy.md](platform-foundation-event-taxonomy.md)
- [platform-foundation-outbox-contract.md](platform-foundation-outbox-contract.md)
- [platform-foundation-consumer-contract.md](platform-foundation-consumer-contract.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](../plans/2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-22-platform-foundation-p2-6-event-backbone-execution-packet.md](../plans/2026-04-22-platform-foundation-p2-6-event-backbone-execution-packet.md)

This spec does not claim that live JetStream streams or consumers already exist. It freezes the first repo-side contract that later live non-prod cut-in must follow.

## 1. Current Implementation Anchor

The current durable publication anchor remains the persisted PostgreSQL outbox:

- [backend/src/application/events/outbox.py](/home/beep/projects/VPNBussiness/backend/src/application/events/outbox.py:1)
- [backend/src/infrastructure/database/models/outbox_event_model.py](/home/beep/projects/VPNBussiness/backend/src/infrastructure/database/models/outbox_event_model.py:1)
- [backend/src/infrastructure/database/repositories/outbox_repo.py](/home/beep/projects/VPNBussiness/backend/src/infrastructure/database/repositories/outbox_repo.py:1)

Frozen rule for `P2.6`:

1. the current outbox tables and lease model stay authoritative;
2. the first NATS-aligned transport contract sits downstream of those tables;
3. `P2.6` does not introduce direct request-handler publish;
4. `P2.6` does not promote Redis pub/sub or direct WebSocket fan-out into the durable source of truth.

## 2. Active Stream Scope For P2.6

The first active NATS-aligned stream scope in the repository is deliberately narrow:

- active stream: `PARTNER_EVENTS`
- active event domain: current partner-platform outbox events
- active durable consumers:
  - `analytics_mart`
  - `operational_replay`

Why the scope is narrow:

- the current backend outbox already validates against the frozen partner-platform taxonomy;
- the repository does not yet contain canonical billing or node-fleet NATS-backed event paths;
- `P2.6` must align the real existing durable event boundary before later phases expand it.

Reserved future streams remain frozen by `T0.2`:

- `BILLING_EVENTS`
- `SUBSCRIPTION_EVENTS`
- `NODE_LIFECYCLE_EVENTS`
- `NODE_HEALTH_EVENTS`
- `ANALYTICS_EVENTS`
- `SYSTEM_ADVISORIES`

## 3. Subject Mapping

Current application event names remain versionless facts such as:

- `growth_code.issued`
- `settlement.statement.generated`
- `reporting.mart.refreshed`

Transport mapping for `P2.6`:

- `event_type = growth_code.issued`
  - `subject = partner.growth_code.issued.v1`
- `event_type = settlement.statement.generated`
  - `subject = partner.settlement.statement.generated.v1`
- `event_type = reporting.mart.refreshed`
  - `subject = partner.reporting.mart.refreshed.v1`

Rules:

1. current stored `event_name` remains unchanged in the outbox rows;
2. transport subjects add the `partner.` namespace plus `.v1` suffix;
3. stream routing for all current partner-platform outbox events is:
   - `subject -> PARTNER_EVENTS`
4. publication metadata must persist:
   - `subject`
   - `stream`
   - `event_version`
   - `published_at`
   - `broker_sequence` or equivalent ack metadata
   - `publish_attempt`

## 4. Dispatcher Contract

`P2.6` freezes the first dispatcher contract:

- the dispatcher claims publication rows through the existing repository lease model;
- the dispatcher maps each claimed publication to:
  - `subject`
  - `stream`
  - `event_version`
  - `idempotency header`
- the dispatcher persists publish evidence back into `publication_payload`;
- the dispatcher does not bypass `mark_publication_submitted` and `mark_publication_published`;
- dispatcher outage is allowed to create backlog, not event loss.

Canonical dispatch posture:

- `Nats-Msg-Id` is the deduplication header for publish attempts;
- the initial active stream is file-backed with three replicas in target runtime topology;
- active publish semantics are at-least-once from the application point of view;
- the durable dedupe source remains application-level idempotency, not broker magic.

## 5. Durable Consumer Baseline

The current active durable consumers are:

### `analytics_mart`

- class: `projection`
- owner: `backend-platform`
- owning service: `backend-reporting`
- stream: `PARTNER_EVENTS`
- filter subjects: `partner.>`
- source-of-truth boundary: `postgres.partner_control_db`
- default mode: durable pull consumer
- idempotency store: durable PostgreSQL publication or projection state
- replay policy: `full_replay_supported`

### `operational_replay`

- class: `orchestration`
- owner: `backend-platform`
- owning service: `backend-reporting`
- stream: `PARTNER_EVENTS`
- filter subjects: `partner.>`
- source-of-truth boundary: `postgres.partner_control_db`
- default mode: durable pull consumer
- replay policy: `full_replay_supported`

These two consumers are active because they already exist as named consumer keys in:

- [backend/src/application/events/outbox.py](/home/beep/projects/VPNBussiness/backend/src/application/events/outbox.py:1)

## 6. Reserved Next Consumers

`P2.6` also freezes the next service-side consumers, but does not silently activate them:

### `notification_delivery`

- status: `reserved_for_p2_7`
- owning service: `task-worker`
- intent: durable notification fan-out downstream of outbox -> NATS

### `realtime_gateway_projection`

- status: `reserved_for_p2_7`
- owning service: future realtime gateway
- intent: durable projection or bridge feeding SSE or WebSocket delivery

Reason they stay reserved:

- the current realtime and notification paths are still legacy surfaces:
  - [services/task-worker/src/services/sse_publisher.py](/home/beep/projects/VPNBussiness/services/task-worker/src/services/sse_publisher.py:1)
  - [backend/src/infrastructure/messaging/websocket_manager.py](/home/beep/projects/VPNBussiness/backend/src/infrastructure/messaging/websocket_manager.py:1)
- `P2.7` is the packet that introduces the canonical realtime path downstream of the durable event boundary.

## 7. Replay Model

Current replay rules for `P2.6`:

1. business-critical consumers default to durable pull consumers;
2. replay for rebuilds uses durable pull consumers and explicit approval;
3. ordered or replay-original consumers are inspection or operator tools, not the default business side-effect path;
4. replay never overrides the PostgreSQL outbox as the publication source of truth.

Two replay modes are allowed:

- `durable_pull_rebuild`
  - used for durable rebuild of projections or lagging consumers
- `ordered_inspection`
  - used for operator inspection or timing-sensitive staging analysis

## 8. NATS Guidance Applied In This Spec

This spec follows current official NATS guidance:

- JetStream streams store messages and consumers track delivery and acknowledgments;
- pull consumers are recommended for new projects where scalability and controlled error handling matter;
- durable consumers persist state and can recover from inactivity or failure;
- stream deduplication uses the `Nats-Msg-Id` header;
- `ReplayOriginal` is a push-consumer capability and therefore stays an inspection tool, not the default business durable-consumer mode.

Primary sources:

- https://docs.nats.io/nats-concepts/jetstream
- https://docs.nats.io/nats-concepts/jetstream/streams
- https://docs.nats.io/nats-concepts/jetstream/consumers
- https://docs.nats.io/using-nats/developer/develop_jetstream/model_deep_dive

## 9. Repo-Side Artifacts Introduced By P2.6

The packet introduces the following repo-side implementation helpers:

- [infra/scripts/event_backbone_bootstrap.py](/home/beep/projects/VPNBussiness/infra/scripts/event_backbone_bootstrap.py:1)
- [infra/tests/test_event_backbone_bootstrap.py](/home/beep/projects/VPNBussiness/infra/tests/test_event_backbone_bootstrap.py:1)

These helpers render and validate:

- active stream declarations;
- subject route map;
- active consumer contracts;
- reserved next-consumer contracts;
- replay plan scaffold.

## 10. Closure Boundary

`P2.6` is not complete only because this spec exists.

The packet is complete only when later live evidence exists for:

1. non-prod stream creation on the real NATS cluster;
2. dispatcher publish evidence from the real outbox backlog into JetStream;
3. at least one durable consumer processing a real event path;
4. replay tooling exercised in non-prod;
5. live removal or narrowing of `EX-010` and the new `P2.6` closure residual.
