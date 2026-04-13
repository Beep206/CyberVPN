# Milestone 13 Implementation Notes

## Scope

Milestone 13 hardens the new datagram slice for real interoperability and bounded operator rollout while keeping session core transport-agnostic and the bridge topology unchanged.

Normative behavior still comes from:

- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/northstar_protocol_rfc_draft_v0_1.md`
- `docs/spec/northstar_blueprint_v0.md`
- `docs/spec/northstar_threat_model_v0_1.md`

This note records implementation choices and verification scope only.

## Decisions Recorded Here

### 1. Datagram rollout is now an explicit local runtime control

The signed carrier profile still carries transport intent through `datagram_enabled`.

Milestone 13 adds a separate local rollout control:

- `H3DatagramRollout::Disabled`
- `H3DatagramRollout::Automatic`

This keeps operator rollout separate from signed manifest intent.
The current app-facing default is deliberately conservative:

- `ns-clientd` defaults datagram rollout to `disabled`
- `nsctl plan-client` defaults datagram rollout to `disabled`
- `ns-gatewayd validate-hello` exposes explicit `DatagramMode` selection for validation and bounded rollout checks

### 2. Effective datagram availability now derives from three inputs

The live H3 carrier now chooses its effective datagram posture from:

- signed carrier-profile intent
- local rollout policy
- actual carrier support at runtime

This keeps selection fail-closed.
If rollout is disabled or carrier support is absent, the implementation must not advertise or opportunistically use datagrams.

### 3. Per-flow selection is now strict and explicit

Milestone 13 keeps the transport-neutral selection rule in `ns-session` narrow and reviewable:

- if datagrams are negotiated and effectively available, select `TransportMode::Datagram`
- otherwise, choose `TransportMode::StreamFallback` only when fallback was explicitly allowed
- otherwise, reject with frozen `UDP_DATAGRAM_UNAVAILABLE`

This closes the downgrade-sensitive case where fallback could silently win even when datagrams were available.

### 4. Datagram negative-path coverage is now part of the live baseline

The live localhost H3 harness now proves:

- continued progress after bounded datagram loss
- payload-oversize rejection without corrupting flow state
- wrong-associated-stream rejection as a protocol violation
- forced stream fallback when local rollout disables datagrams

Fixture-backed wire coverage now also includes:

- `UDP_FLOW_OK(stream_fallback)`
- `UDP_FLOW_CLOSE`
- `UDP_STREAM_OPEN`
- `UDP_STREAM_ACCEPT`
- `UDP_STREAM_PACKET`
- `UDP_STREAM_CLOSE`
- malformed UDP fallback packet and close cases

### 5. Datagram observability is now explicit on both success and guard paths

Milestone 13 keeps low-cardinality observability around the datagram slice by asserting:

- mode-selection events
- guard events for payload oversize, queue overflow, and associated-stream mismatch
- success events for inbound and outbound datagram I/O

This stays inside `ns-observability`, `ns-carrier-h3`, and runtime tests.
It does not widen bridge-domain or session-core contracts.

### 6. Bridge topology and Remnawave boundaries remain unchanged

Milestone 13 deliberately does not widen:

- the public `/v0/*` bridge API
- bridge-domain contracts
- Remnawave adapter contracts
- bridge-store schemas for transport-specific state

Datagram rollout remains a carrier/runtime concern only.

## No New ADR

Milestone 13 does not add a new ADR.

The milestone changes:

- local rollout posture
- transport-runtime hardening
- fixture and fuzz coverage
- datagram observability assertions

but do not change the frozen bridge contract, widen session-core transport ownership, or replace the manifest-signing decision already recorded in ADR 0001.

## Deferred On Purpose

These items remain follow-on work:

- broader WAN or non-localhost datagram interop
- datagram-loss tuning and fallback heuristics beyond the first bounded rollout baseline
- active fuzz execution and larger UDP corpus growth
- operator-facing datagram rollout policy beyond the current explicit enable or disable knobs
- `0-RTT`

## Verification Scope

Milestone 13 is considered complete only after:

- UDP fallback fixtures were generated and exercised
- UDP-specific fuzz targets and regression seeds were added to the existing scaffold
- live localhost H3 datagram success, forced-fallback, bounded-loss, payload-oversize, and wrong-associated-stream tests passed
- full-workspace formatting, clippy, and tests passed
- implementation docs were synchronized with the new rollout and interoperability behavior
