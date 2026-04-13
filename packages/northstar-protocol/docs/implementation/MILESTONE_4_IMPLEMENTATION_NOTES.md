# Milestone 4 Implementation Notes

This note records milestone-4 implementation behavior that is compatible with the current Northstar specs but not yet frozen as independent protocol law.
Normative behavior still lives in `docs/spec/`.

## Scope

Milestone 4 closes two practical gaps in the implementation baseline:

- a durable local bridge-state backend now exists for replay/device/refresh state
- the first carrier path now executes a real localhost QUIC/H3 control-stream hello exchange

These notes describe the execution details chosen for this baseline.

## H3 Request-Template Execution

The frozen carrier profile already defines `origin_host`, `origin_port`, `control_template`, `relay_template`, `headers`, `connect_backoff`, and `zero_rtt_policy`.
Milestone 4 applies those fields with the following implementation rules:

- `:scheme` is synthesized as `https`
- `:authority` is synthesized as `origin_host:origin_port`
- `control_template.path` is used for the unique control-stream request
- `relay_template.path` is reserved for future relay-stream request creation
- signed shared headers are applied to both control and relay request templates
- manifest-supplied headers must be ordinary lowercase header names
- pseudo-headers are not accepted from the manifest
- invalid header names or header values fail request-template construction before transport use

This behavior is implemented in `crates/ns-carrier-h3`.

## `zero_rtt_policy` Handling

The manifest schema includes `zero_rtt_policy`, but the v0.1 implementation still keeps early data disabled.
Milestone 4 handling is:

- parse and preserve the signed policy value through client launch planning and H3 transport config
- do not enable TLS early data or QUIC 0-RTT behavior
- treat the field as signed policy metadata until a future milestone or ADR defines a complete compatibility and replay model

This preserves signed configuration visibility without widening the live attack surface.

## `connect_backoff` Handling

The signed `connect_backoff` object is now preserved through launch planning and H3 transport config.
Milestone 4 does not yet freeze a retry algorithm beyond carrying the signed bounds and jitter inputs forward for runtime use.

## Durable Bridge Store Boundary

Milestone 4 adds `ns_storage::FileBackedBridgeStore` as the first durable bridge-store implementation.
Its current scope is intentionally narrow:

- local file-backed JSON persistence
- persisted bootstrap-redemption replay markers
- persisted device records
- persisted refresh-credential records keyed by digest
- persisted verified-webhook replay fingerprints
- persisted bridge metadata values

Security-relevant implementation rules:

- stored lookup keys are digests, not raw refresh credentials or raw bootstrap values
- in-memory storage remains available for tests and isolated local scenarios
- the bridge demo app now uses the file-backed store by default

This is a single-process, single-node durability path.
It is not a substitute for the multi-instance/shared-database bridge architecture anticipated by the broader bridge spec.

## Live Carrier Milestone Boundary

Milestone 4 achieves:

- real QUIC connection establishment
- real HTTP/3 extended CONNECT request creation from signed transport config
- one control-stream hello request on localhost
- gateway admission over the live control path
- `SERVER_HELLO` success and auth-failure rejection cases over that live path

Milestone 4 does not yet implement:

- relay payload forwarding
- datagram live traffic
- multi-stream session orchestration
- production listener/runtime composition for operators

Those remain follow-on milestones.
