# Milestone 18 Implementation Notes

## Scope

Milestone 18 promotes the first UDP/datagram slice from deterministic local-lab verification toward operator-grade interoperability evidence and sustained optional verification without widening bridge-domain contracts or weakening the transport-agnostic session core.

Normative behavior still comes from:

- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/northstar_protocol_rfc_draft_v0_1.md`
- `docs/spec/northstar_blueprint_v0.md`
- `docs/spec/northstar_threat_model_v0_1.md`
- `docs/spec/northstar_security_test_and_interop_plan_v0_1.md`

This note records implementation choices and verification scope only.

## Decisions Recorded Here

### 1. The deterministic WAN-like profile set now has a machine-readable interoperability harness

Milestone 17 introduced the reusable UDP WAN-lab catalog.
Milestone 18 keeps the same named impairment profiles and adds `udp_interop_lab` as the execution harness.

That harness:

- runs selected or all named profiles
- reuses the maintained live localhost QUIC/H3 UDP tests
- emits machine-readable JSON summaries by default under `target/northstar/udp-interop-lab-summary.json`
- stays CI-safe and deterministic instead of introducing probabilistic host-level network emulation

### 2. Public client tooling now exposes startup and negotiated datagram contracts explicitly

Milestone 18 keeps the lower-level `ns-session` contract checks unchanged and surfaces them more clearly through public runtime/config paths:

- `ns-client-runtime` now exposes a public startup contract from signed intent, rollout stage, and carrier availability
- `ns-client-runtime` now exposes a reusable negotiated datagram-contract validation helper for `policy_epoch`, negotiated datagram mode, `max_udp_flows`, and `effective_max_udp_payload`
- `ns-clientd` and `nsctl` now surface that contract explicitly instead of relying on library-only tests

This keeps the user-facing tools aligned with the same session-core rules rather than inventing a second policy model.

### 3. Gateway startup output now stays explicit about the advertised datagram posture

The gateway-side composition already derived advertised `DatagramMode` from:

- signed transport intent
- rollout posture
- carrier support

Milestone 18 keeps that behavior and makes the resulting posture visible in the public validation output so operator review is not forced to infer it from the code path alone.

### 4. No-silent-fallback assertions now stay visible on degradation and shutdown paths too

Milestone 17 already required deterministic impairment profiles to keep an established datagram selection sticky.

Milestone 18 extends the same evidence to additional post-establishment surfaces:

- wrong associated-stream recovery
- post-close rogue datagram handling

The maintained interpretation remains:

- fallback is a selection-time choice
- once datagrams are selected, later degradation must not silently switch to stream fallback unless the frozen specs explicitly authorize that behavior

### 5. The optional UDP verification lane is now more complete but still opt-in

Milestone 18 keeps the verification lane opt-in and adds:

- `scripts/fuzz-udp-active.ps1`
- `scripts/fuzz-udp-active.sh`
- `NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ=1` support in `scripts/check.*`
- `run_active_fuzz` support in `.github/workflows/udp-optional-gates.yml`
- explicit machine-readable UDP interop summary output in the wrapper and workflow path

This improves sustained optional verification without turning fuzz or WAN-lab work into a default required PR gate.

### 6. Perf gating now tracks additional bounded datagram saturation surfaces

Milestone 18 keeps the ratio-based UDP perf gate and extends its maintained surfaces to include:

- `decode_received_udp_datagram[1201-reject]`
- `H3DatagramSocket.session_burst_reject`
- `H3DatagramSocket.flow_burst_reject`

These remain bounded regression signals for rollout discipline rather than deployment-wide throughput claims.

### 7. Bridge topology and Remnawave boundaries remain unchanged

Milestone 18 intentionally does not widen:

- bridge-domain contracts
- public `/v0/*` bridge surfaces
- Remnawave adapter contracts
- deployment topology or store-service semantics

This milestone stays inside datagram interoperability evidence, public runtime/config validation, optional verification plumbing, and doc sync.

## No New ADR

Milestone 18 does not add a new ADR.

The milestone strengthens verification posture and public runtime/config surfaces, but it does not change bridge architecture, manifest meaning, or ADR 0001.

## Deferred On Purpose

These items remain follow-on work:

- broader WAN-like or real cross-network datagram interoperability beyond the deterministic local lab
- default-on CI execution for UDP smoke, perf, WAN-lab, or active-fuzz paths
- larger reviewed UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflows beyond the current local and CLI-stage controls
- `0-RTT`

## Verification Scope

Milestone 18 is considered complete only after:

- the deterministic UDP WAN-lab profile set gained a machine-readable interoperability harness
- public client tooling surfaced the startup datagram contract explicitly
- public client tooling could validate negotiated datagram contract drift through the shared runtime helper
- gateway validation output surfaced the derived datagram posture clearly
- post-establishment degradation and shutdown coverage asserted no silent fallback on the maintained live UDP paths
- the optional UDP workflow documented and supported the active-fuzz path while keeping it opt-in
- the UDP perf gate measured maintained burst and reject thresholds in addition to the earlier send, receive, oversize, and queue-full surfaces
- full-workspace formatting, clippy, and tests passed
- implementation docs were synchronized with the new interop harness, public contract surfaces, and optional verification lane
