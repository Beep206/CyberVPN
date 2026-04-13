# Milestone 5 Implementation Notes

This note records milestone-5 implementation behavior that is compatible with the current Northstar specs but not yet frozen as independent protocol law.
Normative behavior still lives in `docs/spec/`.

## Scope

Milestone 5 closes three practical gaps in the baseline:

- the bridge now has a shared durable coordination path through `SqliteBridgeStore`
- the first carrier path now reaches a live relay-stream preamble after a successful hello
- gateway pre-auth budgets and signed H3 request-header restrictions now exist as explicit code-level guards

These notes describe the implementation choices used for this milestone.

## Shared Durable Bridge Store

Milestone 5 adds `ns_storage::SqliteBridgeStore` as the first shared durable bridge-store implementation.
Its current scope is intentionally narrow:

- SQLite-backed persistence for bootstrap-redemption markers
- SQLite-backed persistence for device records
- SQLite-backed persistence for refresh-credential records keyed by digest
- SQLite-backed persistence for verified-webhook replay fingerprints
- SQLite-backed persistence for bridge metadata values

Execution rules:

- the store enables WAL mode and a bounded busy timeout
- each operation opens a configured SQLite connection and performs short, typed bridge-state work
- `apps/ns-bridge` now defaults to the SQLite-backed store
- `InMemoryBridgeStore` and `FileBackedBridgeStore` remain available for tests and isolated local runs

Milestone 5 treats this as the first shared coordination path for multiple bridge instances that can see the same SQLite file.
It is not yet the final remote or service-backed multi-node bridge-store architecture.

## Atomic Device And Refresh Registration

Milestone 5 moves device-limit and refresh-credential issuance onto a store-level registration operation rather than a split read-count-write flow.
The active implementation rule is:

- device-limit checks, revoked-device checks, device upsert, and refresh-credential storage happen as one bridge-store operation

This keeps the bridge boundary non-fork and avoids widening Remnawave assumptions while tightening replay and policy behavior under concurrent bridge access.

## Signed H3 Request-Header Surface

Milestone 5 keeps manifest-driven H3 request construction centralized in `crates/ns-carrier-h3`.
The allowed signed header surface is intentionally narrow:

- ordinary lowercase request headers only
- no pseudo-headers from the manifest
- no hop-by-hop headers from the manifest
- no `host`
- no `content-length`
- no `expect`

The current explicit reject set is:

- `connection`
- `proxy-connection`
- `keep-alive`
- `upgrade`
- `transfer-encoding`
- `te`
- `trailer`
- `content-length`
- `host`
- `expect`

This keeps signed carrier-profile headers operator-controlled without letting manifest input override core H3 request construction or body semantics.

## Gateway Pre-Auth Budgets

Milestone 5 adds explicit gateway-side pre-auth budgets through `ns_gateway_runtime::GatewayPreAuthBudgets`.
The default implementation values are:

- `max_pending_hellos = 256`
- `max_control_body_bytes = 16 KiB`
- `handshake_deadline_ms = 1000`

The current enforcement posture is:

- reject new hello work when the pending-hello budget is saturated
- reject control bodies above the configured pre-auth size bound before session admission
- reject pre-auth attempts that exceed the wall-clock hello deadline
- keep 0-RTT disabled

These are implementation defaults, not frozen wire-level invariants.

## Live Carrier Milestone Boundary

Milestone 5 extends the live QUIC/H3 path to cover:

- successful control-stream hello over localhost
- auth-failure rejection over the same live path
- relay-stream request creation after successful hello
- `STREAM_OPEN` on the relay request body
- `STREAM_ACCEPT` from the gateway-side relay preamble path

Milestone 5 does not yet implement:

- raw relay payload forwarding after `STREAM_ACCEPT`
- live datagram traffic
- multi-stream operator-facing session orchestration

Those remain follow-on milestones.
