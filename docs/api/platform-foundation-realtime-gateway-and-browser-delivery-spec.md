# CyberVPN Platform Foundation Realtime Gateway And Browser Delivery Spec

**Date:** 2026-04-22  
**Status:** `P2.7` implementation baseline

This document freezes the first canonical browser-delivery contract that sits downstream of the event backbone introduced in `P2.6`.

It is the implementation companion to:

- [platform-foundation-nats-streams-consumers-and-replay-spec.md](platform-foundation-nats-streams-consumers-and-replay-spec.md)
- [platform-foundation-outbox-contract.md](platform-foundation-outbox-contract.md)
- [platform-foundation-consumer-contract.md](platform-foundation-consumer-contract.md)
- [2026-04-22-platform-foundation-p2-7-realtime-delivery-execution-packet.md](../plans/2026-04-22-platform-foundation-p2-7-realtime-delivery-execution-packet.md)

This spec does not claim that the realtime gateway is already deployed. It freezes the repo-side contract that later non-prod cut-in must follow.

## 1. Canonical Path

The first canonical business/browser realtime path is:

```text
PostgreSQL commit
  -> persisted outbox
  -> NATS PARTNER_EVENTS
  -> realtime_gateway_projection
  -> realtime gateway
  -> browser delivery
```

Rules:

1. the browser never becomes the durable publication boundary;
2. Redis pub/sub and direct WebSocket broadcast remain temporary compatibility paths only;
3. operational monitoring sockets remain separate from the business/browser feed.

## 2. First Canonical Channel

The first canonical browser channel is:

- `partner.workspace.feed`

It is fed by:

- stream: `PARTNER_EVENTS`
- consumer: `realtime_gateway_projection`

Initial subject families:

- `partner.growth_code.>`
- `partner.order.>`
- `partner.settlement.>`
- `partner.reporting.>`

Source-of-truth boundary:

- `postgres.partner_control_db`

## 3. Primary Browser Delivery Protocol

The first business/browser path uses `SSE` as the primary delivery protocol.

Why:

- the first target path is one-way fact propagation from server to browser;
- the browser does not need to command the gateway to create new business facts;
- the simpler one-way transport avoids mixing the business feed with the existing operational WebSocket topic model.

Frozen endpoint target:

- `/api/v1/realtime/partner/events`

Expected server event fields:

- `id`
- `event`
- `data`
- `retry`

Expected browser payload fields inside `data`:

- `event_id`
- `channel`
- `event_type`
- `aggregate_type`
- `aggregate_id`
- `occurred_at`
- `delivered_at`
- `cursor`
- `payload`

## 4. WebSocket Boundary

WebSocket remains allowed, but not as the default for the first business/browser feed.

Allowed uses:

- future interactive subscription models
- explicit operator tooling
- operational monitoring topics

Prohibited uses for this packet:

- reclassifying `/api/v1/ws/monitoring` as the canonical business feed
- treating `/api/v1/ws/notifications` as already migrated
- skipping the durable projection and sending business-critical facts directly from request handlers to sockets

Reserved future endpoint:

- `/api/v1/ws/realtime/partner`

That endpoint is reserved for future interactive cases. It is not the default `P2.7` browser path.

## 5. Existing Realtime Surfaces And Their Status

### Business-path legacy surfaces

- [services/task-worker/src/services/sse_publisher.py](/home/beep/projects/VPNBussiness/services/task-worker/src/services/sse_publisher.py:1)
  - status: `temporary`
  - reason: direct Redis pub/sub, not durable

- [backend/src/infrastructure/messaging/websocket_manager.py](/home/beep/projects/VPNBussiness/backend/src/infrastructure/messaging/websocket_manager.py:1)
  - status: `temporary`
  - reason: direct socket fan-out, not durable

- [backend/src/application/events/handlers/notification_handler.py](/home/beep/projects/VPNBussiness/backend/src/application/events/handlers/notification_handler.py:1)
- [backend/src/application/use_cases/webhooks/remnawave_webhook.py](/home/beep/projects/VPNBussiness/backend/src/application/use_cases/webhooks/remnawave_webhook.py:1)
  - status: `legacy direct broadcast`

### Operational-only surfaces

- [backend/src/presentation/api/v1/ws/monitoring.py](/home/beep/projects/VPNBussiness/backend/src/presentation/api/v1/ws/monitoring.py:1)
  - status: `operational_only`

- [admin/src/features/integrations/lib/realtime.ts](/home/beep/projects/VPNBussiness/admin/src/features/integrations/lib/realtime.ts:1)
- [partner/src/features/integrations/lib/realtime.ts](/home/beep/projects/VPNBussiness/partner/src/features/integrations/lib/realtime.ts:1)
  - status: `operational_only browser clients`

### Legacy notification route

- [backend/src/presentation/api/v1/ws/notifications.py](/home/beep/projects/VPNBussiness/backend/src/presentation/api/v1/ws/notifications.py:1)
  - status: `legacy_temporary`

## 6. Realtime Gateway Projection Contract

The gateway projection contract is:

- consumer: `realtime_gateway_projection`
- stream: `PARTNER_EVENTS`
- projection store: durable PostgreSQL offset or projection state
- browser fan-out: downstream from projection only
- cursor model: `Last-Event-ID` compatible cursor
- replay policy: rebuild from stream supported

Rules:

1. gateway fan-out metadata must not become the authoritative state owner;
2. browser-delivery cursors are delivery aids, not replacements for the projection store;
3. the gateway may keep ephemeral connection registries in memory, but the authoritative event position remains durable.

## 7. Guidance Applied In This Spec

This spec follows current primary-source guidance:

- FastAPI supports WebSocket endpoints and dependency-based auth or context injection;
- browser `EventSource` is a one-way server-to-client model for text-event-stream delivery;
- browser `WebSocket` is bidirectional and therefore should be reserved for cases that actually need interactive semantics rather than used by default for one-way business fact delivery.

Primary sources:

- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/
- MDN Using server-sent events: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
- MDN WebSocket: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket

## 8. Closure Boundary

`P2.7` is not complete only because this spec exists.

The packet is complete only when later live evidence exists for:

1. a deployed realtime gateway or equivalent projection-to-browser component;
2. at least one real non-prod browser feed replacing polling for a chosen dashboard flow;
3. a durable `realtime_gateway_projection` consumer running against `PARTNER_EVENTS`;
4. explicit runtime narrowing or retirement of the legacy direct SSE or WebSocket business-path surfaces;
5. end-to-end proof for the chosen browser flow.
