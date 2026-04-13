# Milestone 14 Implementation Notes

## Scope

Milestone 14 hardens the first datagram slice for bounded operator rollout and broader interoperability while keeping session core transport-agnostic and the bridge deployment topology unchanged.

Normative behavior still comes from:

- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/northstar_protocol_rfc_draft_v0_1.md`
- `docs/spec/northstar_blueprint_v0.md`
- `docs/spec/northstar_threat_model_v0_1.md`

This note records implementation choices and verification scope only.

## Decisions Recorded Here

### 1. Datagram rollout is now staged, not merely enabled or disabled

The signed carrier profile still carries transport intent through `datagram_enabled`.

Milestone 14 extends the local rollout control to:

- `H3DatagramRollout::Disabled`
- `H3DatagramRollout::Canary`
- `H3DatagramRollout::Automatic`

The stages stay local runtime policy rather than becoming signed manifest semantics.

### 2. Canary rollout is intentionally narrow and fail closed

Milestone 14 keeps `Canary` conservative:

- carrier datagrams stay visible as available in negotiated metadata when support exists
- only flows that explicitly set `prefer_datagram` may use datagrams under canary
- flows that allow fallback but do not prefer datagrams stay on stream fallback
- if carrier support is absent or the runtime says datagrams are unavailable, the flow must not silently attempt datagrams

This gives operators a reversible, low-risk rollout step without widening bridge or manifest contracts.

### 3. Live datagram hardening now covers deterministic edge behavior

The live localhost H3 harness now proves:

- repeated bounded datagram loss without forced fallback
- bounded reordering without corrupting flow state
- successful round-trip at the effective MTU ceiling
- queue-pressure overflow plus successful recovery after the queue drains
- stream fallback when rollout disables datagrams
- stream fallback when the session-level carrier availability signal is unavailable

These tests stay deterministic by asserting bounded, reviewed behaviors instead of transport-library timing quirks.

### 4. Wire compatibility coverage now includes additional UDP close and fallback cases

Fixture-backed wire coverage now includes:

- `NS-FX-UDP-FLOW-CLOSE-DGRAMUNAVAIL-002`
- `NS-FX-UDP-STREAM-CLOSE-IDLE-002`
- `WC-UDP-FLOW-CLOSE-BADCODE-012`
- `WC-UDP-STREAM-OPEN-TRUNCATED-013`

This keeps emitted rejection and close semantics pinned to the frozen wire spec as the datagram slice expands.

### 5. UDP fuzzing is now runnable locally without requiring cargo-fuzz

Milestone 14 keeps the deeper `cargo fuzz` targets, but adds a Windows-first active local verification path:

- `cargo run -p ns-testkit --example sync_udp_fuzz_corpus`
- `cargo run -p ns-testkit --example udp_fuzz_smoke`
- `.\scripts\fuzz-udp-smoke.ps1`
- `./scripts/fuzz-udp-smoke.sh`

The corpus sync step derives seeds from reviewed fixtures.
The smoke step replays those seeds and expects regression inputs to keep failing.

### 6. Datagram perf validation now has an explicit microbenchmark

Milestone 14 adds a crate-local H3 datagram benchmark:

- `cargo bench -p ns-carrier-h3 --bench datagram_runtime`

The benchmark measures:

- datagram send-path preparation at `64`, `512`, and `1200` bytes
- received datagram decode at `64`, `512`, and `1200` bytes
- oversize rejection at `1201` bytes

This keeps the first UDP performance pass focused on codec and guard cost rather than WAN throughput claims.

### 7. Bridge topology and Remnawave boundaries remain unchanged

Milestone 14 deliberately does not widen:

- the public `/v0/*` bridge API
- bridge-domain contracts
- Remnawave adapter contracts
- bridge-store schemas for carrier or datagram state

Datagram rollout remains a carrier/runtime concern only.

## No New ADR

Milestone 14 does not add a new ADR.

The milestone changes:

- local rollout staging
- datagram hardening and conformance coverage
- runnable local fuzz verification
- microbenchmark availability
- datagram observability details

but do not widen bridge contracts, change signed manifest meaning, or replace ADR 0001.

## Deferred On Purpose

These items remain follow-on work:

- broader WAN or non-localhost datagram interop
- active long-running fuzz execution in CI
- larger UDP corpus growth beyond the current reviewed fixture-derived seeds
- richer operator rollout workflows beyond explicit local runtime stages
- `0-RTT`

## Verification Scope

Milestone 14 is considered complete only after:

- the new UDP fixtures were generated and exercised
- UDP fuzz corpora and regression seeds were synchronized from reviewed fixtures
- the UDP smoke replay path passed locally
- the H3 datagram microbenchmark built successfully
- live localhost H3 datagram tests for repeated loss, reordering, MTU ceiling, fallback, oversize rejection, and associated-stream mismatch passed
- full-workspace formatting, clippy, and tests passed
- implementation docs were synchronized with the new rollout, fuzz, and perf behavior
