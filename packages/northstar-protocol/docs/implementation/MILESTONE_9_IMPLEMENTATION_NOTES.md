# Milestone 9 Implementation Notes

This note records milestone-9 behavior that fits the current Northstar specs and ADR set but is still implementation guidance rather than independent protocol law.
Normative behavior remains in `docs/spec/`.

## Scope

Milestone 9 closes three practical gaps in the current baseline:

- the service-backed bridge-store seam now has a real authenticated remote/shared HTTP backend path instead of only a local semantic wrapper
- `apps/ns-bridge` now composes either a fake Remnawave adapter or the initial real HTTP Remnawave adapter through explicit runtime/config selection
- the reusable QUIC/H3 relay runtime now has broader assertions around both-direction half-close, stable close reasons, and structured relay/bridge failure events

## Remote Shared Store Path

Milestone 9 keeps `BridgeStore` as the only bridge-domain contract and extends the service-backed path rather than widening domain interfaces.

Implementation rules:

- `ServiceBackedBridgeStore` still fails closed when the remote backend is unavailable
- startup health checks are still mandatory before the public bridge app treats the backend as shared durable
- the semantic store service can now require `Authorization: Bearer <token>` on both `/internal/store/v1/health` and `/internal/store/v1/command`
- the client-side `HttpServiceBackedBridgeStoreAdapter` now carries request timeout, auth, schema-drift, and unexpected-scope handling through one typed seam
- the SQLite-backed bridge store now re-runs idempotent schema initialization on each opened working connection so remote/shared service tests do not depend on one lucky bootstrap connection

This keeps remote/shared replay, refresh, and device-policy state inside `ns-storage` and avoids introducing a second bridge-domain contract.

## Explicit Remnawave Adapter Selection

Milestone 9 keeps Remnawave external to the bridge boundary and adds explicit runtime/config selection in `apps/ns-bridge`:

- `--remnawave-adapter-backend fake`
- `--remnawave-adapter-backend http`
- `--remnawave-base-url`
- `--remnawave-api-token`
- `--remnawave-request-timeout-ms`

The fake adapter remains the default local-validation path.
The HTTP adapter exists so the bridge runtime can compose against a real upstream API shape without widening `ns-bridge-domain`.

## Relay Runtime And Observability

Milestone 9 keeps session core transport-agnostic and extends the reusable `ns-carrier-h3` runtime rather than reintroducing test-local forwarding loops.

Covered implementation behaviors now include:

- both clean half-close directions
- bounded idle-timeout termination
- bounded prebuffer overflow rejection
- stable close-reason strings suitable for low-cardinality observability fields
- structured bridge-store service health and failure events
- structured bridge HTTP body-limit rejection events

These are implementation diagnostics and test assertions only.
They do not change wire behavior, manifest shape, or public bridge contract fields.

## What Remains Deferred

- a deployed upstream Remnawave integration pass against a real service environment
- broader remote/shared bridge-store deployment beyond the current authenticated semantic HTTP store path
- live datagrams
- 0-RTT enablement
- broader non-localhost relay interoperability

## ADR Status

No new ADR was added for milestone 9.
The milestone stays within the existing architectural rules:

- session core remains transport-agnostic
- Remnawave remains external to the bridge boundary
- the remote/shared store path stays behind `BridgeStore`
- public bridge HTTP behavior remains on the frozen `/v0/*` surface
