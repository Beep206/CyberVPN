# Milestone 6 Implementation Notes

This note records milestone-6 implementation behavior that is compatible with the current Verta specs but not yet frozen as independent protocol law.
Normative behavior still lives in `docs/spec/`.

## Scope

Milestone 6 closes two practical gaps from the previous baseline:

- the bridge now has a production-shaped backend boundary for shared durable state, while keeping the existing in-memory, file-backed, and SQLite-backed implementations
- the first QUIC/H3 carrier path now forwards bounded raw relay bytes after `STREAM_ACCEPT`, instead of stopping at the relay preamble

These notes describe the implementation choices used for this milestone.

## Shared Bridge-Store Backend Boundary

Milestone 6 keeps `ns_storage::BridgeStore` as the semantic store contract used by bridge domain logic and adds a backend-oriented composition boundary around it:

- `BridgeStoreBackend` identifies a concrete backend plus its deployment scope
- `SharedBridgeStore` wraps `Arc<dyn BridgeStoreBackend>` so bridge composition can swap durable backends without widening the domain API
- `BridgeStoreDeploymentScope` currently distinguishes `LocalOnly` from `SharedDurable`

Current backend set:

- `InMemoryBridgeStore`
- `FileBackedBridgeStore`
- `SqliteBridgeStore`

Current durable state covered by that backend boundary:

- bootstrap redemption markers
- bootstrap grants
- device records
- refresh-credential records
- verified webhook replay fingerprints
- bridge metadata

Implementation rule:

- future service-backed or remote shared backends should implement the same backend boundary inside `ns-storage`
- bridge-domain, bridge-api, session-core, and carrier crates must not learn backend-specific storage details

Milestone 6 still treats SQLite as the only implemented shared durable backend.
The backend boundary exists so the next storage step can remain a bridge-layer change rather than a protocol or carrier change.

## Initial Bridge HTTP Service Composition

Milestone 6 adds an initial `axum`-based bridge service composition in `ns-bridge-api` and `apps/ns-bridge`.
The active route set is:

- `GET /v0/manifest`
- `POST /v0/device/register`
- `POST /v0/token/exchange`
- `GET /.well-known/jwks.json`
- `POST /internal/remnawave/webhook`

The current composition rule is intentionally thin:

- `ns-bridge-api` owns HTTP parsing, auth-mode extraction, error envelope mapping, body-size limits, and webhook header extraction
- `ns-bridge-domain` owns manifest compilation, device registration policy, refresh validation, and token issuance
- `ns-remnawave-adapter` owns bootstrap resolution and verified webhook interpretation
- `ns-storage` owns durable replay, device, and credential state

Default ingress budgets:

- `max_json_body_bytes = 16 KiB`
- `max_webhook_body_bytes = 64 KiB`

Authentication rules in the active implementation:

- `GET /v0/manifest?subscription_token=...` is bootstrap mode
- `GET /v0/manifest` with `Authorization: Bearer <refresh>` is steady-state refresh mode
- `POST /v0/device/register` uses `Authorization: Bearer <bootstrap grant or refresh credential>`
- `POST /v0/token/exchange` remains refresh-credential based

Milestone 6 also keeps `manifest_id` in the device-registration request body so the bootstrap or refresh auth context remains bound to the signed manifest the client is acting on.

## Live Relay-Data Slice

Milestone 6 extends the live QUIC/H3 path beyond `STREAM_OPEN` and `STREAM_ACCEPT`.
The current live path now covers:

- real localhost QUIC/H3 control-stream hello
- relay request creation after successful hello
- `STREAM_OPEN` decode and policy validation
- `STREAM_ACCEPT` response
- switch to raw relay-byte mode after accept
- bounded forwarding between H3 DATA and an upstream TCP socket
- echoed raw bytes returned to the client over the same accepted relay stream

Implementation rule:

- after `STREAM_ACCEPT`, Verta framing stops on that relay stream
- relay bytes are treated as opaque payload data
- datagrams remain disabled
- 0-RTT remains disabled

Milestone 6 intentionally stops at a bounded TCP relay slice.
It does not yet claim full proxy forwarding semantics, datagram transport, or broad live interoperability outside localhost integration tests.
The current raw relay path is proven through live QUIC/H3 composition and integration coverage; promoting it into a fuller reusable carrier-session abstraction remains follow-on work.

## Gateway Relay Budgets

Milestone 6 makes gateway-side relay budgets explicit in `ns-gateway-runtime`:

- `max_active_relays = 256`
- `max_relay_prebuffer_bytes = 64 KiB`
- `relay_idle_timeout_ms = 30_000`

The active enforcement posture is:

- reject accepted-relay admission when the active relay budget is saturated
- reject raw relay chunks that exceed the configured per-stream prebuffer budget
- fail relay activity that exceeds the configured idle timeout budget

Current protocol error mapping for these local guards:

- overload -> `SESSION_BUSY`
- relay prebuffer overflow -> `FLOW_CONTROL_EXCEEDED`
- relay idle timeout -> `IDLE_TIMEOUT`

These are implementation defaults, not new wire-format fields.

## What Remains Deferred

- a remote or service-backed shared bridge-store backend beyond SQLite
- full relay payload forwarding policy beyond the current bounded echo-style milestone
- promotion of the raw relay path into a fuller reusable carrier-session abstraction
- live datagram transport
- 0-RTT enablement
- production bridge deployment concerns such as admin surfaces, tenancy, and external auth layers
