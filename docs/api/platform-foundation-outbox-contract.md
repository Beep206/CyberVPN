# CyberVPN Platform Foundation Outbox Contract

**Date:** 2026-04-21  
**Status:** Frozen baseline for `T0.2`

This document freezes the transactional outbox contract for business-critical platform events.

The rule is simple:

**Business-critical events must be created as part of the same durable transaction that commits the state change they describe.**

Direct publish from request handlers is prohibited for business-critical events.

## 1. Scope

The outbox contract is mandatory for:

- payment and billing state changes;
- subscription lifecycle transitions;
- partner-platform business events that feed durable consumers;
- Node Fleet Controller lifecycle changes and failover workflow events;
- authoritative server-side analytics bridge events derived from commercial state;
- any future business event whose loss would produce a silent state divergence.

The outbox contract is not required for:

- ephemeral debug notifications;
- local in-memory callbacks with no cross-service durability requirement;
- transient browser-only refresh hints that are not business-critical.

## 2. Current Repository Baseline

CyberVPN already has a concrete outbox implementation in:

- [backend/src/application/events/outbox.py](/home/beep/projects/VPNBussiness/backend/src/application/events/outbox.py:1)
- [backend/src/infrastructure/database/models/outbox_event_model.py](/home/beep/projects/VPNBussiness/backend/src/infrastructure/database/models/outbox_event_model.py:1)
- [backend/src/infrastructure/database/repositories/outbox_repo.py](/home/beep/projects/VPNBussiness/backend/src/infrastructure/database/repositories/outbox_repo.py:1)
- [backend/src/application/use_cases/reporting/outbox.py](/home/beep/projects/VPNBussiness/backend/src/application/use_cases/reporting/outbox.py:1)

This current baseline already provides:

- durable `outbox_events`;
- per-consumer `outbox_publications`;
- publication leasing;
- retry state;
- publication status transitions;
- aggregate event status transitions.

## 3. Persisted Shape

### `outbox_events`

Current persisted fields:

| Field | Meaning |
|---|---|
| `id` | durable event row identifier |
| `event_key` | stable event key, unique |
| `event_name` | current application event name |
| `event_family` | current application event family |
| `aggregate_type` | durable aggregate type |
| `aggregate_id` | durable aggregate identifier |
| `partition_key` | consumer partitioning key |
| `schema_version` | schema version integer |
| `event_status` | aggregate publication state |
| `event_payload` | business payload snapshot |
| `actor_context` | principal context |
| `source_context` | request/system source context |
| `occurred_at` | business occurrence timestamp |
| `created_at` | row creation time |
| `updated_at` | row update time |

### `outbox_publications`

Current persisted fields:

| Field | Meaning |
|---|---|
| `id` | publication row identifier |
| `outbox_event_id` | owning outbox event |
| `consumer_key` | target durable consumer |
| `publication_status` | publication lifecycle state |
| `attempts` | number of claim attempts |
| `lease_owner` | worker that currently owns the lease |
| `leased_until` | lease expiry |
| `next_attempt_at` | next eligible retry time |
| `submitted_at` | submission timestamp |
| `published_at` | durable publish completion timestamp |
| `last_error` | most recent failure detail |
| `publication_payload` | transport or sink metadata |
| `created_at` | row creation time |
| `updated_at` | row update time |

## 4. Status Model

Current publication statuses:

- `pending`
- `claimed`
- `submitted`
- `published`
- `failed`

Current aggregate event statuses:

- `pending_publication`
- `partially_published`
- `published`
- `failed`

Rules:

1. Aggregate event status is derived from publication rows, not set independently by business handlers.
2. Publication retries operate through `claimed` and `failed` state transitions with lease ownership checks.
3. A publication cannot be marked published or failed by a worker that does not own its lease.

## 5. Mandatory Transaction Boundary

Canonical transaction flow:

```text
Application transaction:
  1. validate command
  2. mutate authoritative business state
  3. append outbox event row in the same transaction
  4. append outbox_publications rows in the same transaction
  5. commit
```

Canonical dispatcher flow:

```text
Dispatcher:
  1. claim eligible publication rows
  2. publish to NATS or other declared sink
  3. persist publication metadata and published_at
  4. refresh aggregate event status
```

Failure rule:

- if the business state commits but the outbox row does not, the operation is invalid;
- if the outbox row exists but the dispatcher is down, backlog is allowed;
- dispatcher outage must create backlog, not silent event loss.

## 6. Mandatory Future Transport Metadata

When the platform publishes business-critical events to NATS, `publication_payload` or its future structured replacement must persist enough metadata to reconstruct publication evidence.

Minimum expected transport metadata:

- `subject`
- `stream`
- `event_version`
- `published_at`
- `broker_sequence` or equivalent ack identifier
- `publish_attempt`

This may initially live in `publication_payload` even before dedicated columns are added.

## 7. Direct Publish Boundary

The following are prohibited for business-critical events:

- publish directly to NATS from a request handler before the owning transaction commits;
- publish directly to WebSocket or Redis and treat that as authoritative completion;
- emit business-critical cross-service events only through cron or polling workers;
- rely on browser acknowledgment as evidence that an event was delivered durably.

## 8. Known Current Publish Paths That Violate The Target State

The repository currently contains publish paths that are real-time or convenient, but do not yet satisfy the durable outbox contract for business-critical fan-out.

### Direct Redis pub/sub SSE path

- [services/task-worker/src/services/sse_publisher.py](/home/beep/projects/VPNBussiness/services/task-worker/src/services/sse_publisher.py:1)

Current behavior:

- publishes directly to Redis channel `cybervpn:sse:events`
- has no durable publication state, replay policy, or consumer ownership contract

### Direct backend WebSocket broadcast path

- [backend/src/application/events/handlers/notification_handler.py](/home/beep/projects/VPNBussiness/backend/src/application/events/handlers/notification_handler.py:1)
- [backend/src/application/use_cases/webhooks/remnawave_webhook.py](/home/beep/projects/VPNBussiness/backend/src/application/use_cases/webhooks/remnawave_webhook.py:1)
- [backend/src/infrastructure/messaging/websocket_manager.py](/home/beep/projects/VPNBussiness/backend/src/infrastructure/messaging/websocket_manager.py:1)

Current behavior:

- broadcasts directly to connected WebSocket clients
- provides no durable backlog, replay, or per-consumer publication state

### Polling-driven notification queue path

- [services/task-worker/src/tasks/notifications/process_queue.py](/home/beep/projects/VPNBussiness/services/task-worker/src/tasks/notifications/process_queue.py:1)
- [services/task-worker/src/schedules/definitions.py](/home/beep/projects/VPNBussiness/services/task-worker/src/schedules/definitions.py:75)

Current behavior:

- processes `notification_queue` on an interval schedule
- is operationally useful, but is not the target-state real-time business propagation path

### Legacy in-process event path

- [backend/src/domain/events/base.py](/home/beep/projects/VPNBussiness/backend/src/domain/events/base.py:1)

Current behavior:

- defines local domain-event dataclasses
- does not itself satisfy the platform durable publication contract

## 9. Allowed Transitional Pattern

During migration, the following transitional pattern is allowed:

```text
authoritative state change
  -> transactional outbox
  -> durable consumer or projection
  -> transient SSE/WebSocket delivery to UI
```

This means transient UI delivery can remain, but only as a downstream delivery adapter rather than as the authoritative publication boundary.

## 10. Ownership And Governance Rules

1. Every outbox publication row must target a named consumer key.
2. Default consumer sets must be explicit and code-reviewed.
3. Adding a new business-critical consumer requires:
   - a consumer contract document entry;
   - alerting expectations;
   - replay policy;
   - idempotency rule.
4. Outbox rows must not carry provider-native aliases as the canonical event name.
5. Outbox backlog metrics and failure metrics are mandatory operational signals.

## 11. Phase 0 Freeze Outcome

`T0.2` does not require immediate table redesign.

It freezes these rules:

1. transactional outbox is the canonical business-critical publication boundary;
2. current persisted outbox tables are the baseline implementation anchor;
3. future NATS publication must sit downstream of the outbox;
4. current direct Redis/WebSocket/polling publish paths are temporary and must be migrated or clearly scoped as non-authoritative.
