# CyberVPN Platform Foundation P2.7 Realtime Delivery Execution Packet

**Date:** 2026-04-22  
**Status:** implementation in progress; repo foundation slice complete, live realtime gateway and browser-flow evidence pending  
**Packet:** `P2.7`  
**Primary owners:** `transport-backend` / `backend-platform`  
**Supporting owners:** `infra-platform`, `sre-platform`, `docs-program`

---

## 1. Packet Role

This document is the execution packet for `P2.7` in the platform-foundation roadmap.

It is the implementation companion to:

- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-target-state-architecture.md](2026-04-21-platform-foundation-target-state-architecture.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)
- [../api/platform-foundation-nats-streams-consumers-and-replay-spec.md](../api/platform-foundation-nats-streams-consumers-and-replay-spec.md)
- [../api/platform-foundation-realtime-gateway-and-browser-delivery-spec.md](../api/platform-foundation-realtime-gateway-and-browser-delivery-spec.md)

`P2.7` exists to freeze the first canonical browser-delivery path downstream of the event backbone introduced in `P2.6`:

- the browser-facing path is:
  - outbox
  - `PARTNER_EVENTS`
  - `realtime_gateway_projection`
  - realtime gateway
  - `SSE` primary browser delivery
- the first canonical browser channel is:
  - `partner.workspace.feed`
- existing monitoring sockets remain operational-only;
- existing direct Redis SSE and direct backend WebSocket broadcast remain temporary compatibility surfaces.

Implementation note:

- this packet is executed as a pre-launch `repo/validation` slice because the current workspace has no deployed realtime gateway, no live non-prod browser feed, and no live cutover evidence;
- the repository slice is implemented and locally validated;
- the remaining closure work is live gateway deployment, live projection consumer evidence, and one real browser flow replacing polling.

---

## 2. Current Baseline

Before this packet:

- `P2.6` had already frozen the active stream scope as `PARTNER_EVENTS`;
- `realtime_gateway_projection` had already been reserved as the next consumer for `P2.7`;
- the repository still contained multiple realtime-like surfaces:
  - direct Redis SSE publish
  - direct WebSocket broadcast
  - monitoring websocket topics
  - legacy notifications websocket

Observed strengths:

- the current repo already separates operational monitoring sockets enough to keep them out of the first business/browser path;
- the event backbone contract already exists and can feed a future gateway cleanly;
- browser operational consoles already demonstrate client-side websocket plumbing that must remain explicitly scoped.

Observed implementation risks:

- without a canonical browser-delivery spec, later work could mistake the existing monitoring socket for the product dashboard feed;
- without a channel registry, browser clients could subscribe to loosely defined topics instead of durable projection channels;
- without a clear primary protocol choice, the program could add avoidable bidirectional complexity before it needs it.

---

## 3. Canonical Decisions For P2.7

`P2.7` fixes the following decisions:

1. The first canonical business/browser channel is:
   - `partner.workspace.feed`
2. The first canonical business/browser source stream is:
   - `PARTNER_EVENTS`
3. The first projection consumer is:
   - `realtime_gateway_projection`
4. The primary browser delivery protocol for the first business/browser path is:
   - `SSE`
5. `WebSocket` remains:
   - available for operational topics
   - available for future interactive cases
   - not the default protocol for one-way business fact delivery
6. The existing `/api/v1/ws/monitoring` route remains:
   - `operational_only`
7. The existing `/api/v1/ws/notifications` route remains:
   - `legacy_temporary`
8. Direct Redis SSE and direct backend WebSocket broadcast remain:
   - compatibility surfaces only
   - not the authoritative business/browser delivery boundary

---

## 4. Scope

In scope for `P2.7`:

- add a canonical helper under [infra/scripts/realtime_delivery_bootstrap.py](../../infra/scripts/realtime_delivery_bootstrap.py);
- add unit coverage for the helper;
- add the first repo-side browser-delivery spec at [../api/platform-foundation-realtime-gateway-and-browser-delivery-spec.md](../api/platform-foundation-realtime-gateway-and-browser-delivery-spec.md);
- render realtime-gateway scaffold for:
  - channel registry
  - projection contract
  - SSE endpoint contract
  - WebSocket endpoint boundary
  - legacy compatibility boundaries
- update operator docs so the helper is discoverable from `infra/README.md`;
- record packet evidence and a formal carry-forward residual.

Out of scope for the current repository slice executed in this workspace:

- live realtime gateway deployment;
- live SSE endpoint implementation;
- live browser cutover;
- live retirement of the old Redis SSE or direct WebSocket business feed paths;
- live frontend subscription integration.

---

## 5. Official Constraints

The execution of `P2.7` follows current primary-source guidance:

- FastAPI supports WebSocket endpoints and dependency-based auth or context injection;
- browser `EventSource` is a one-way server-to-client model over `text/event-stream`;
- browser `WebSocket` is bidirectional and therefore should be reserved for cases that actually need interactive semantics rather than used by default for one-way fact propagation.

Primary sources:

- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/
- MDN Using server-sent events: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events
- MDN WebSocket: https://developer.mozilla.org/en-US/docs/Web/API/WebSocket

---

## 6. Target Repository Touchpoints

Mandatory touchpoints for `P2.7`:

### 6.1 Helper And Tests

- [infra/scripts/realtime_delivery_bootstrap.py](../../infra/scripts/realtime_delivery_bootstrap.py)
- [infra/tests/test_realtime_delivery_bootstrap.py](../../infra/tests/test_realtime_delivery_bootstrap.py)

### 6.2 Canonical Spec Added During P2.7

- [../api/platform-foundation-realtime-gateway-and-browser-delivery-spec.md](../api/platform-foundation-realtime-gateway-and-browser-delivery-spec.md)

### 6.3 Existing Surfaces Updated During P2.7

- [infra/README.md](../../infra/README.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](2026-04-21-platform-foundation-phased-implementation-plan.md)
- [2026-04-21-platform-foundation-temporary-exceptions-register.md](2026-04-21-platform-foundation-temporary-exceptions-register.md)

### 6.4 Packet Evidence

- [../evidence/platform-foundation/2026-04-22/p2-7-realtime-delivery/evidence-pack.md](../evidence/platform-foundation/2026-04-22/p2-7-realtime-delivery/evidence-pack.md)

---

## 7. Workboard

### 7.1 `T2.7.1` Freeze The First Canonical Browser Channel

**Goal:** define the first browser-visible channel downstream of the durable event path.

Deliverables:

- channel registry
- projection contract
- browser payload contract

Acceptance criteria:

- `partner.workspace.feed` is explicit;
- the channel is tied to `PARTNER_EVENTS` and `realtime_gateway_projection`;
- the source-of-truth boundary remains PostgreSQL-backed projection state.

### 7.2 `T2.7.2` Freeze The Browser Delivery Protocol Boundary

**Goal:** stop browser delivery from drifting into mixed protocol semantics without intent.

Deliverables:

- SSE endpoint contract
- WebSocket boundary contract

Acceptance criteria:

- `SSE` is explicitly primary for the first business/browser path;
- `WebSocket` is explicitly secondary, operational, or future-interactive;
- operational monitoring socket scope is preserved.

### 7.3 `T2.7.3` Freeze Legacy Compatibility Boundaries

**Goal:** make existing realtime-like paths clearly temporary instead of silently canonical.

Deliverables:

- legacy boundary map for:
  - direct Redis SSE publish
  - direct backend WebSocket broadcast
  - monitoring websocket
  - notifications websocket

Acceptance criteria:

- every current realtime-like surface is classified;
- operational-only surfaces are not confused with business/browser delivery;
- the packet does not pretend cutover is already done.

### 7.4 `T2.7.4` Produce Local Validation And Honest Residual Tracking

**Goal:** make the packet auditable before any real browser cutover exists.

Deliverables:

- helper unit tests
- local validation command
- render smoke
- packet evidence pack
- formal carry-forward residual for missing live gateway and browser-cutover proof

Acceptance criteria:

- the repository slice is locally validated;
- the packet records the exact runtime work still missing;
- later `P2` packets may proceed without pretending browser realtime is already live.

---

## 8. State-Boundary Rules

`P2.7` must keep the following invariants:

1. the browser remains downstream of the realtime gateway, not the source of truth;
2. operational monitoring sockets do not become the business/browser feed by accident;
3. legacy Redis SSE and direct WebSocket business paths remain temporary only;
4. `P2.7` must not claim live browser cutover or polling replacement from repository-only work.
