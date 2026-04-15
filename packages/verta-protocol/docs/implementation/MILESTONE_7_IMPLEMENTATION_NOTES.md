# Milestone 7 Implementation Notes

This note records milestone-7 implementation behavior that is compatible with the current Verta specs but not yet frozen as independent protocol law.
Normative behavior still lives in `docs/spec/`.

## Scope

Milestone 7 closes three practical gaps in the baseline:

- the raw QUIC/H3 relay-data slice now lives behind a reusable carrier runtime instead of a test-local forwarding loop
- the bridge-store backend seam now includes a semantic service-backed adapter path, while still failing closed until a real remote backend exists
- the bridge HTTP service now runs through explicit runtime/config composition instead of demo-only serve wiring

These notes describe the implementation choices used for this milestone.

## Reusable H3 Relay Runtime

Milestone 7 promotes the raw relay forwarding logic into `ns-carrier-h3::forward_raw_tcp_relay`.
The active implementation shape is:

- `ns-session::RelayStreamIo` now exposes `send_raw`, `recv_raw`, and `finish_raw`
- `ns-session::EstablishedCarrierSession::open_relay_stream` now takes the full `StreamOpen` preamble
- `ns-session::SessionController` now exposes `release_relay` so accepted-relay capacity can be reclaimed explicitly
- `ns-carrier-h3` now owns the reusable raw relay loop, close-reason mapping, byte counters, idle timeout handling, and bounded raw prebuffering

Execution rules:

- the carrier runtime is only entered after a validated `STREAM_ACCEPT`
- client EOF causes `finish_raw()` toward the upstream side instead of abruptly dropping the relay
- upstream EOF causes a clean carrier-side raw finish toward the client
- relay closure is reported with a stable close-reason category instead of an unclassified transport shutdown

This keeps session-core transport-agnostic while moving the live raw relay path out of the test harness and into the carrier crate where it belongs.

## Service-Backed Bridge Store Seam

Milestone 7 keeps `BridgeStore` as the bridge-domain contract and extends `ns-storage` with:

- `ServiceBackedBridgeStoreConfig`
- `ServiceBackedBridgeStoreAdapter`
- `ServiceBackedBridgeStore`

Current implementation posture:

- the service-backed backend is semantic, not fictional
- the default implementation is fail-closed and reports backend unavailability for every operation
- `ServiceBackedBridgeStore` reports `SharedDurable` deployment scope so bridge composition can reason about it the same way it reasons about other shared durable backends

Implementation rule:

- future remote or managed durable backends must be added behind this seam in `ns-storage`
- bridge-domain, bridge-api, session-core, and carrier crates must not learn service-specific storage details

Milestone 7 does not yet implement a real remote store protocol.
It only creates the production-shaped seam and keeps it honest by failing closed until a real backend exists.

## Explicit Bridge Runtime Composition

Milestone 7 replaces the direct demo-style bridge serve path with an explicit runtime/config assembly in `apps/ns-bridge`.

The current serve-mode composition now makes these values first-class:

- selected bridge-store backend
- shared-store validation
- JSON and webhook body budgets
- webhook signature requirement
- token JWKS publication

Serve-mode rule:

- public bridge serve mode now requires a `SharedDurable` backend
- in-memory and local-only file-backed stores remain acceptable for tests and isolated local runs, but not as the public serve default

HTTP composition rules:

- JSON client-facing routes use the tighter JSON body budget
- verified webhook ingress uses the larger webhook body budget
- refresh-path manifest fetch keeps `ETag` and `304 Not Modified` behavior in the HTTP layer

## Observability and Guardrails

Milestone 7 adds or sharpens these implementation-facing observability points:

- relay overload warnings
- relay prebuffer overflow warnings
- relay idle-timeout warnings
- reusable relay close-reason reporting
- explicit route-scoped HTTP body-limit behavior at the bridge service boundary

These are implementation diagnostics, not new protocol fields.

## What Remains Deferred

- a real remote or managed service-backed bridge-store backend
- live datagram transport
- 0-RTT enablement
- broader live interop beyond localhost
- production bridge deployment concerns such as external auth layers, tenancy, and admin surfaces

## ADR Status

No new ADR was added for milestone 7.
The changes stay within the existing architectural rules:

- session-core remains transport-agnostic
- Remnawave remains external to the bridge boundary
- the new store seam stays inside `ns-storage`
- the new relay runtime stays inside `ns-carrier-h3`
