# Milestone 11 Implementation Notes

## Scope

Milestone 11 turns the milestone-10 deployment topology into the first operator-shaped bridge deployment slice and closes the most important remaining compatibility and hardening gaps before datagrams.

Normative behavior still lives in:

- `docs/spec/northstar_remnawave_bridge_spec_v0_1.md`
- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/northstar_threat_model_v0_1.md`
- `docs/spec/northstar_protocol_rfc_draft_v0_1.md`

This note records implementation choices and verification scope only.

## What Changed

### 1. Remote/shared bridge-store mode now supports ordered endpoint failover

`ServiceBackedBridgeStoreConfig` now supports multiple authenticated service endpoints.
`HttpServiceBackedBridgeStoreAdapter` may fail over across those endpoints when the failure class is transport or availability related.

This remains fail-closed for unauthorized outcomes:

- `401` and `403` stay terminal
- authorization failures do not cascade to other endpoints
- remote mode still requires explicit auth at app-composition time

This keeps the bridge-store seam operator-shaped for multi-instance deployments without widening bridge-domain contracts.

### 2. Deployment topology is now a first-class runtime shape

`apps/ns-bridge` now has explicit topology startup and shutdown composition rather than only a long-running serve path.

The deployment-shaped topology now covers:

- startup of a local shared-durable backend
- startup of a separate internal store-service runtime
- authenticated health verification of the remote/shared service-backed view
- startup of a separate public bridge runtime over that authenticated remote/shared path
- tested clean shutdown
- tested fail-closed startup when remote-store auth is mismatched

### 3. HTTP Remnawave adapter coverage now runs through the topology path

The public bridge runtime can complete manifest fetch, device registration, and token exchange through the deployment topology path while using the real `HttpRemnawaveAdapter` against a realistic upstream test server.

This keeps the non-fork integration path real at runtime-composition level without widening `ns-bridge-domain` contracts.

### 4. Frozen protocol error mapping is now locked in code and live coverage

`ns-core` now includes an explicit registry-lock test for the frozen v0.1 `ProtocolErrorCode` mapping.

Live overload rejection on the relay path now uses:

- `STREAM_REJECT`
- frozen `FLOW_LIMIT_REACHED`

instead of a generic control-frame error surface.

This closes a compatibility gap found during the milestone-11 transport review.

### 5. Relay observability assertions now rely on stable runtime events

`ns-gateway-runtime` now tests structured guard-event emission for:

- relay overload
- relay prebuffer overflow
- relay idle timeout

These assertions intentionally live on the gateway-runtime surface instead of only on returned error values so runtime regressions are visible through stable low-cardinality diagnostics.

## No New ADR

Milestone 11 does not add a new ADR.

The milestone changes:

- deployment composition
- remote/shared store failover behavior
- coverage and compatibility hardening

but do not change the frozen public bridge contract, session-core transport ownership, or the existing manifest-signing decision already recorded in ADR 0001.

## Deferred On Purpose

These items remain follow-on work and should not be inferred as complete:

- a broader multi-node remote/shared backend beyond the current semantic HTTP store service
- a real upstream Remnawave deployment pass outside the realistic upstream test server path
- live datagram traffic
- 0-RTT enablement

## Verification Scope

Milestone 11 is considered complete only after:

- targeted bridge, storage, carrier, gateway-runtime, and core tests passed
- full-workspace formatting, clippy, and tests passed
- implementation docs were synchronized with the new topology, compatibility, and observability behavior
