# Milestone 8 Implementation Notes

This note records milestone-8 behavior that is compatible with the current Northstar specs but is still implementation guidance rather than independent protocol law.
Normative behavior remains in `docs/spec/`.

## Scope

Milestone 8 closes four practical gaps in the baseline:

- the first real non-SQLite remote bridge-store path now exists behind the existing `ServiceBackedBridgeStoreAdapter` seam
- `apps/ns-bridge` now composes its runtime explicitly from store, adapter, signer, manifest, and webhook dependencies instead of constructing demo-only defaults inside the serve builder
- the reusable `ns-carrier-h3::forward_raw_tcp_relay` runtime now has explicit half-close, timeout, overflow, and close-reason stability coverage outside the live localhost harness
- bridge and relay warning points now emit stable structured events through `ns-observability`

## Real Service-Backed Store Path

Milestone 8 keeps `BridgeStore` as the only bridge-domain contract and adds one real service-backed backend shape in `ns-storage`:

- `HttpServiceBackedBridgeStoreAdapter`
- `build_service_backed_bridge_store_router`
- semantic `/internal/store/v1/health`
- semantic `/internal/store/v1/command`

Implementation rules:

- the remote store API stays semantic and bridge-specific, not CRUD-shaped
- `ServiceBackedBridgeStore` still fails closed if the remote backend is unavailable
- service-backed startup now performs a real health check
- health passes only when the remote backend reports `SharedDurable`

This keeps shared bridge coordination inside `ns-storage` and avoids widening bridge-domain contracts.

## Explicit Bridge Runtime Composition

Milestone 8 introduces explicit runtime dependency wiring in `apps/ns-bridge`.
The serve path now receives:

- a selected shared store backend
- a `RemnawaveAdapter` implementation
- a manifest signer
- a token signer
- a manifest template
- a webhook authenticator and verification config
- HTTP ingress budgets

The current CLI still uses the fake adapter for local validation, but the runtime builder is now shaped so a future real adapter can be injected without changing bridge-domain or bridge-api contracts.

## Reusable Relay Runtime Coverage

Milestone 8 keeps the live localhost QUIC/H3 tests from milestone 7 and adds reusable runtime tests directly against `forward_raw_tcp_relay`.

Covered runtime behaviors now include:

- client-first clean half-close with stable close reason
- upstream-first clean half-close with stable close reason
- bounded idle-timeout failure
- bounded client-prebuffer overflow rejection

This keeps the relay-runtime contract testable without relying only on full H3 harness composition.

## Stable Observability Events

Milestone 8 promotes several warning-only surfaces into stable structured events:

- bridge store backend selection
- bridge store service health success or failure
- bridge HTTP body-budget rejection
- gateway relay overload, prebuffer, and idle-timeout guards
- carrier relay close events with byte totals and clean-half-close state

These are implementation diagnostics only.
They do not change wire behavior or public bridge contract fields.

## What Remains Deferred

- a real upstream Remnawave adapter implementation
- multi-node remote bridge-store deployment beyond the first HTTP-backed semantic store path
- live datagrams
- 0-RTT enablement
- broader non-localhost carrier interoperability

## ADR Status

No new ADR was added for milestone 8.
The milestone stays within the existing architectural rules:

- session core remains transport-agnostic
- Remnawave remains external to the bridge boundary
- the remote store path stays behind `BridgeStore`
- public bridge HTTP behavior remains on the frozen `/v0/*` surface
