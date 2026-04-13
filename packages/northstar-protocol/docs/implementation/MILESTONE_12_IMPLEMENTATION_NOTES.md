# Milestone 12 Implementation Notes

## Scope

Milestone 12 starts the first real datagram slice for Northstar while preserving the operator-shaped bridge topology and keeping session core transport-agnostic.

Normative behavior still comes from:

- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/northstar_protocol_rfc_draft_v0_1.md`
- `docs/spec/northstar_blueprint_v0.md`
- `docs/spec/northstar_threat_model_v0_1.md`

This note records implementation choices and verification scope only.

## Decisions Recorded Here

### 1. The v0.1 H3 datagram backend is now fixed for the implementation baseline

The frozen spec set requires:

- `h3` as the first carrier
- UDP relay with both datagram and stream-fallback modes
- explicit `DatagramMode` negotiation
- manifest-side `udp_template.mode = "h3-datagram"`

The spec set does not force a separate ADR for the crate-level backend binding used in this milestone.
For the current baseline, `ns-carrier-h3` uses:

- RFC 9297-style associated HTTP datagrams
- `h3-datagram`
- `h3-quinn` datagram support
- the active control request stream id as the associated stream for this first live slice

This choice remains carrier-internal.
`ns-session` does not learn Quinn, `h3`, or HTTP datagram details.

### 2. Session-core now owns transport-neutral UDP flow admission and mode selection

`ns-session` now treats UDP flow-open decisions the same way it already treated transport-neutral relay admission:

- duplicate `flow_id` is rejected
- concurrent UDP flow count is bounded
- datagram-only requests fail closed when datagrams are unavailable and fallback was not allowed
- `UDP_DATAGRAM_UNAVAILABLE` is surfaced through the frozen protocol error mapping
- `UDP_FLOW_OK.transport_mode` is selected centrally, not ad hoc inside the carrier

This keeps datagram-vs-fallback policy transport-neutral even though the live backend is currently H3-specific.

### 3. The first live H3 datagram path is real but intentionally bounded

Milestone 12 now proves live localhost UDP relay after hello in two shapes:

- datagram success via `UDP_FLOW_OK(datagram)` plus `UDP_DATAGRAM`
- stream fallback via `UDP_FLOW_OK(stream_fallback)` plus `UDP_STREAM_*`

The first runtime limits are intentionally explicit:

- effective gateway default `max_udp_flows = 8`
- effective max UDP payload `1200` bytes
- H3 datagram buffered queue limit `8 KiB`
- 0-RTT remains disabled

This is a bounded correctness slice, not a broader WAN datagram rollout.

### 4. Bridge topology and Remnawave boundaries remain unchanged

Milestone 12 deliberately does not widen:

- the public `/v0/*` bridge API
- bridge-domain contracts
- Remnawave adapter contracts
- bridge-store schemas for transport-specific state

Datagram startup remains a carrier/runtime concern only.

## No New ADR

Milestone 12 does not add a new ADR.

The datagram backend choice is recorded here as an implementation note because:

- the frozen docs already point to `h3-datagram` behavior strongly enough for a bounded baseline
- the choice stays behind `ns-carrier-h3`
- the milestone does not widen the frozen public bridge or session-domain contracts

If the project later wants to freeze a different H3 datagram binding or make the current choice a stronger interoperability guarantee for external implementations, that should become an ADR or a spec update.

## Deferred On Purpose

These items remain follow-on work:

- broader WAN or non-localhost datagram interop
- datagram-loss tuning and fallback heuristics beyond the current explicit selection rules
- active datagram fuzz execution and a larger UDP fixture corpus
- live datagram operator rollout posture beyond the current localhost baseline
- 0-RTT enablement

## Verification Scope

Milestone 12 is considered complete only after:

- UDP wire fixtures were generated and exercised
- transport-neutral UDP flow admission and error mapping tests passed
- live localhost H3 datagram, stream-fallback, and datagram-unavailable rejection tests passed
- full-workspace formatting, clippy, and tests passed
- implementation docs were synchronized with the new datagram behavior
