# Milestone 15 Implementation Notes

## Scope

Milestone 15 closes the first post-`SERVER_HELLO` datagram validation gap and moves the UDP verification slice from ad-hoc local checks toward safer operator-grade rollout gates.

Normative behavior still comes from:

- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/northstar_protocol_rfc_draft_v0_1.md`
- `docs/spec/northstar_blueprint_v0.md`
- `docs/spec/northstar_threat_model_v0_1.md`
- `docs/spec/northstar_security_test_and_interop_plan_v0_1.md`

This note records implementation choices and verification scope only.

## Decisions Recorded Here

### 1. `SERVER_HELLO` is now treated as a strict contract, not a hint

Milestone 15 keeps the session core transport-agnostic but strengthens what the client and session layer must reject after hello:

- `policy_epoch` must match the effective local policy
- negotiated `datagram_mode` must remain compatible with local rollout posture and signed intent
- `max_udp_flows` must not exceed the local effective flow budget
- `effective_max_udp_payload` must not exceed the local effective payload ceiling
- unusable zero-valued runtime limits must reject immediately

This follows the frozen rule that the hello response commits the active session contract.

### 2. Active UDP flows now remain transport-mode aware until close

`ns-session` now keeps active UDP flow state keyed by both `flow_id` and the selected transport mode.

That keeps these cases fail closed and transport-neutral:

- datagram input after `UDP_FLOW_CLOSE`
- datagram input for unknown `flow_id`
- fallback stream open for the wrong `flow_id`
- datagram or fallback traffic on the wrong transport mode for the active flow

These conditions now stay typed as protocol violations instead of becoming carrier-specific surprises.

### 3. Datagram burst budgets are now explicit alongside the existing byte ceiling

The first H3 datagram runtime slice already had a byte-bound queue budget.
Milestone 15 adds count-based burst budgets on top of that:

- `max_buffered_datagrams = 8`
- `max_buffered_datagrams_per_flow = 4`
- existing byte ceiling remains `8 KiB`

This keeps burst abuse bounded even when payload sizes stay small.

### 4. UDP compatibility coverage now includes post-close and malformed fallback cases

Milestone 15 adds and exercises these wire fixtures:

- `NS-FX-UDP-FLOW-CLOSE-PROTOVIOL-003`
- `WC-UDP-STREAM-PACKET-TRUNCATED-014`

Live H3 integration coverage now also proves:

- unknown-flow datagram rejection after close
- wrong fallback `flow_id` rejection with frozen `ProtocolViolation`

### 5. UDP smoke replay is now an opt-in workspace gate

The Windows-first smoke path still exists:

- `.\scripts\fuzz-udp-smoke.ps1`
- `./scripts/fuzz-udp-smoke.sh`

Milestone 15 additionally makes it easy to opt into the same verification through the normal repo wrapper:

- `NORTHSTAR_ENABLE_UDP_FUZZ_SMOKE=1`
- `NORTHSTAR_ENABLE_UDP_PERF_GATE=1`

`scripts/check.*` now keeps those gates off by default and available for local or CI-style opt-in runs.

### 6. UDP perf validation now has an explicit threshold harness

Milestone 15 adds:

- `cargo run -p ns-testkit --example udp_perf_gate`

The gate intentionally uses wide ratio-based thresholds rather than machine-specific absolute timings.
It currently checks:

- wrapped send-path cost versus baseline encode at `64`, `512`, and `1200` bytes
- wrapped receive-path cost versus baseline decode at `64`, `512`, and `1200` bytes
- oversize reject-path cost at `1201` bytes

This is a stability gate, not a throughput benchmark.

### 7. Bridge topology and Remnawave boundaries remain unchanged

Milestone 15 deliberately does not widen:

- public `/v0/*` bridge API behavior
- bridge-domain contracts
- Remnawave adapter contracts
- bridge topology or store-service contracts

The milestone stays inside datagram validation, carrier/runtime budgets, local verification gates, and doc sync.

## No New ADR

Milestone 15 does not add a new ADR.

The milestone changes:

- strict post-hello validation
- datagram flow-state validation
- datagram burst budgets
- opt-in fuzz and perf gates
- datagram coverage and observability details

but do not change bridge contracts, signed manifest meaning, or ADR 0001.

## Deferred On Purpose

These items remain follow-on work:

- WAN-like or cross-network datagram interoperability
- sustained fuzz execution in CI by default rather than as an opt-in gate
- larger reviewed UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflows beyond local staged runtime controls
- `0-RTT`

## Verification Scope

Milestone 15 is considered complete only after:

- the new UDP fixtures were generated and exercised
- post-`SERVER_HELLO` drift validation tests passed
- live localhost H3 tests for unknown-flow-after-close and wrong fallback-flow rejection passed
- UDP smoke replay passed both directly and through the Windows-first wrapper
- the UDP performance threshold harness passed
- full-workspace formatting, clippy, and tests passed
- implementation docs were synchronized with the new validation, guard, fuzz, and perf behavior
