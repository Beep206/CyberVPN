# CyberVPN Platform Foundation P2.7 Realtime Delivery Evidence Pack

**Date:** 2026-04-22  
**Status:** in progress  
**Packet:** `P2.7`  
**Phase:** `P2`  
**Primary owners:** `transport-backend` / `backend-platform`  
**Supporting owners:** `infra-platform`, `sre-platform`, `docs-program`  
**Purpose:** record the repository, validation, and operator-surface changes completed for `P2.7`, plus the remaining live evidence required before the packet can be declared complete.

---

## 1. Scope And Packet Links

This evidence pack belongs to:

- [2026-04-22-platform-foundation-p2-7-realtime-delivery-execution-packet.md](../../../../plans/2026-04-22-platform-foundation-p2-7-realtime-delivery-execution-packet.md)
- [2026-04-21-platform-foundation-phased-implementation-plan.md](../../../../plans/2026-04-21-platform-foundation-phased-implementation-plan.md)
- [phase-0-signoff-and-blocker-pack.md](../../phase-0-signoff-and-blocker-pack.md)

Important gate note:

- `Gate A` is still formally blocked by pending human sign-off.
- `Gate B` is also not passed because `P1` still carries unresolved live-evidence residuals.
- `Gate C` cannot be claimed because `P2.1` through `P2.7` still carry live-closure exceptions.
- this evidence pack carries `EX-027` as the formal reason `P2.7` may remain in progress while later `P2` repo-slice work begins.

---

## 2. Result Snapshot

Current `P2.7` result:

- canonical helper added at `infra/scripts/realtime_delivery_bootstrap.py`;
- helper renders and validates:
  - realtime gateway channel registry
  - projection contract
  - SSE endpoint contract
  - WebSocket boundary contract
  - legacy compatibility map
- canonical browser-delivery spec added at:
  - `docs/api/platform-foundation-realtime-gateway-and-browser-delivery-spec.md`
- first canonical business/browser channel is frozen as:
  - `partner.workspace.feed`
- primary business/browser delivery protocol is frozen as:
  - `SSE`
- `WebSocket` is frozen as:
  - operational-only for current monitoring socket
  - legacy-temporary for current notifications socket
  - future-interactive or secondary for future business-specific cases

This packet is **not yet claimed complete** because:

- no live realtime gateway deployment exists yet;
- no live `realtime_gateway_projection` consumer proof exists yet;
- no live SSE endpoint exists yet;
- no live browser flow has replaced polling yet;
- no live narrowing or retirement of the legacy business-path SSE or WebSocket surfaces has been proven yet.

That is intentional. `P2.7` first freezes and validates the repository contract, then carries the runtime closure debt explicitly.

---

## 3. Repository Changes Recorded

### 3.1 Helper And Tests

- `infra/scripts/realtime_delivery_bootstrap.py`
  - validates the current repo anchors for legacy and operational realtime surfaces
  - renders the first realtime-gateway and browser-delivery scaffold

- `infra/tests/test_realtime_delivery_bootstrap.py`
  - validates scaffold rendering
  - validates the current repository baseline through the helper

### 3.2 Canonical Spec

- `docs/api/platform-foundation-realtime-gateway-and-browser-delivery-spec.md`
  - freezes the active `P2.7` browser-delivery contract

### 3.3 Operator Docs

- `infra/README.md`
  - now documents `realtime_delivery_bootstrap.py` as the canonical helper for `P2.7`

### 3.4 Packet And Program Records

- `docs/plans/2026-04-22-platform-foundation-p2-7-realtime-delivery-execution-packet.md`
- `docs/plans/2026-04-21-platform-foundation-temporary-exceptions-register.md`
  - now carries `EX-027`

---

## 4. Verification Evidence

All commands below were executed on 2026-04-22 in the repository workspace.

### 4.1 Helper Unit Tests

Command:

```bash
python -m unittest infra.tests.test_realtime_delivery_bootstrap
```

Result:

- `Ran 2 tests`
- `OK`

### 4.2 Python Syntax Check

Command:

```bash
python -m py_compile infra/scripts/realtime_delivery_bootstrap.py
```

Result:

- compilation completed successfully

### 4.3 Helper Render Smoke

Command shape:

```bash
python infra/scripts/realtime_delivery_bootstrap.py render-scaffold \
  --output-dir <temporary-dir>
```

Result:

- helper completed successfully against the current repository workspace
- rendered scaffold includes:
  - `backend/realtime-gateway/channel-registry.yaml`
  - `backend/realtime-gateway/projections/partner-workspace-feed.yaml`
  - `backend/realtime-gateway/delivery/sse-endpoints.yaml`
  - `backend/realtime-gateway/delivery/websocket-endpoints.yaml`
  - `backend/realtime-gateway/legacy-boundaries.yaml`
  - `frontend/legacy-ui-notes.md`

### 4.4 Repo Validation Command

Command:

```bash
python infra/scripts/realtime_delivery_bootstrap.py validate --repo-root .
```

Observed validated baseline:

- the repo still carries the legacy direct Redis SSE surface
- the repo still carries the legacy direct WebSocket surface
- the repo still carries the operational monitoring websocket route
- the repo still carries the legacy notifications websocket route
- the admin and partner operational realtime browser helpers are still explicitly tracked
- helper reported:
  - `primary_browser_delivery=sse`
  - `secondary_browser_delivery=websocket`
  - `first_canonical_channel=partner.workspace.feed`
  - `legacy_operational_socket=/api/v1/ws/monitoring`
  - `legacy_notifications_socket=/api/v1/ws/notifications`

### 4.5 Workspace Readiness Check For Live Closure

Observed in the current workspace on 2026-04-22:

- no live realtime gateway exists;
- no live SSE endpoint exists;
- no live `realtime_gateway_projection` consumer exists;
- no live browser feed has replaced polling;
- no live frontend cutover evidence exists.

Meaning:

- the packet cannot honestly claim canonical browser realtime is operational yet;
- `P2.7` must therefore carry a formal residual until real gateway, endpoint, and browser-cutover evidence are attached.

---

## 5. Remaining Live Closure Requirements

`P2.7` can only move from “repo slice complete” to “packet complete” when the following evidence exists:

1. a deployed realtime gateway or equivalent projection-to-browser component exists in non-prod;
2. a durable `realtime_gateway_projection` consumer runs against `PARTNER_EVENTS`;
3. `/api/v1/realtime/partner/events` or the final equivalent SSE endpoint exists and is exercised;
4. at least one chosen dashboard flow uses the canonical browser-delivery path instead of polling;
5. the legacy business-path SSE or WebSocket surfaces are retired or explicitly narrowed;
6. `EX-027` is removed from the exceptions register.
