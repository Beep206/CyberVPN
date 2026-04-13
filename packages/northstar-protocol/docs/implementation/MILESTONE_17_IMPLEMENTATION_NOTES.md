# Milestone 17 Implementation Notes

## Scope

Milestone 17 moves the first datagram slice from deterministic local-lab hardening toward operator-grade interoperability and sustained opt-in verification without widening bridge-domain contracts or weakening the transport-agnostic session core.

Normative behavior still comes from:

- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/northstar_protocol_rfc_draft_v0_1.md`
- `docs/spec/northstar_blueprint_v0.md`
- `docs/spec/northstar_threat_model_v0_1.md`
- `docs/spec/northstar_security_test_and_interop_plan_v0_1.md`

This note records implementation choices and verification scope only.

## Decisions Recorded Here

### 1. The first WAN-like datagram lab stays deterministic and repo-native

Milestone 17 does not add probabilistic traffic shaping or OS-level emulation.

Instead it defines a reusable `ns-testkit` UDP WAN-lab profile catalog plus wrappers for:

- bounded loss
- bounded reordering
- delayed delivery plus short degradation
- MTU pressure
- carrier-unavailable fallback

Each profile maps to stable live-test filters and relevant spec-suite IDs so the path is CI-safe and reproducible on Windows-first developer machines.

### 2. Gateway startup composition now derives datagram posture instead of trusting a raw operator knob

`apps/ns-gatewayd` no longer treats the advertised datagram mode as a direct CLI truth source for validation.

The startup/runtime composition now derives that posture from:

- signed datagram intent
- local rollout stage
- carrier datagram availability

and fails closed if rollout would widen signed transport intent.

### 3. Client launch planning now exposes the expected `SERVER_HELLO` datagram contract explicitly

The client runtime already rejected rollout-enabled planning when the signed carrier profile disabled datagrams.

Milestone 17 additionally makes the expected `SERVER_HELLO.datagram_mode` derivation explicit from the launch plan so startup/runtime behavior does not depend on hidden inference when carrier availability is known.

### 4. Established datagram selection still must not silently fall back

Milestone 17 keeps the milestone-16 interpretation:

- fallback is a selection-time choice
- post-selection degradation must not silently switch to stream fallback unless the frozen specs explicitly authorize it

The reusable WAN-lab coverage now asserts that rule across bounded loss, bounded reordering, and delayed-delivery plus short-degradation paths instead of only one degradation case.

### 5. Optional UDP verification is now a clearer repo-native path

The repo-native optional UDP workflow remains opt-in.

Milestone 17 adds:

- `scripts/udp-wan-lab.ps1`
- `scripts/udp-wan-lab.sh`
- `cargo run -p ns-testkit --example udp_wan_lab`
- `NORTHSTAR_ENABLE_UDP_WAN_LAB=1` support in `scripts/check.*`
- workflow summary output and a `run_wan_lab` input in `.github/workflows/udp-optional-gates.yml`

This keeps the path discoverable without turning it into a default required PR gate.

### 6. UDP perf validation now includes a maintained queue-full regression surface

The existing ratio-based UDP perf gate already covered:

- wrapped send
- wrapped decode
- oversize reject

Milestone 17 adds a maintained queue-full reject threshold using `H3DatagramSocket` so one bounded saturation surface is measured beyond bench buildability.

### 7. Bridge topology and Remnawave boundaries remain unchanged

Milestone 17 intentionally does not widen:

- bridge-domain contracts
- public `/v0/*` bridge surfaces
- Remnawave adapter contracts
- deployment topology or store-service behavior

The milestone stays inside datagram interoperability, startup/runtime validation, opt-in verification plumbing, and doc sync.

## No New ADR

Milestone 17 does not add a new ADR.

The milestone makes rollout/runtime behavior and verification posture more explicit, but it does not change bridge architecture, manifest meaning, or ADR 0001.

## Deferred On Purpose

These items remain follow-on work:

- broader WAN-like or cross-network datagram interoperability beyond the deterministic lab profile set
- default-on CI execution for UDP fuzz, perf, or WAN-lab gates
- larger reviewed UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflows beyond the current local and CLI-stage controls
- `0-RTT`

## Verification Scope

Milestone 17 is considered complete only after:

- the reusable `ns-testkit` UDP WAN-lab profile set and wrappers were added
- gateway startup composition rejected rollout that widened signed datagram intent
- the client launch plan exposed the expected `SERVER_HELLO` datagram contract
- live degradation coverage asserted no silent fallback across the maintained lab profiles
- the optional UDP workflow and local wrappers documented the WAN-lab path clearly
- the UDP perf gate measured at least one maintained queue-full saturation threshold
- full-workspace formatting, clippy, and tests passed
- implementation docs were synchronized with the new WAN-lab, startup-composition, and opt-in verification behavior
