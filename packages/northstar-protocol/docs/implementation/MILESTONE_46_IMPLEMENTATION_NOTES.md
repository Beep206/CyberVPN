# Milestone 46 Implementation Notes

Milestone 46 extends the datagram rollout toolchain from release-candidate acceptance toward release-candidate certification with stronger deployment-grade evidence, while keeping Remnawave non-fork, bridge contracts unchanged, the session core transport-agnostic, and `0-RTT` disabled.

## Governing Inputs

- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/northstar_security_test_and_interop_plan_v0_1.md`
- `docs/spec/northstar_threat_model_v0_1.md`
- `docs/spec/northstar_remnawave_bridge_spec_v0_1.md`

## Scope

- keep Remnawave on the external bridge boundary
- keep bridge deployment topology unchanged
- keep transport selection, fallback, and rollout rules spec-driven and fail closed
- add one more workflow-backed datagram verification surface without changing Windows-first wrapper expectations
- strengthen release-facing operator verdicts around exact compatible-host interop-catalog `source_lane`, failed-profile-count, host-label-set, blocked-fallback, policy-disabled-fallback, and transport-fallback-integrity handling
- grow the maintained reviewed UDP corpus around malformed datagram-unavailable close-frame outer lengths without widening parser behavior

## Implemented

- Added a workflow-backed Linux `release_candidate_certification` lane to `.github/workflows/udp-optional-gates.yml` plus `scripts/udp-release-candidate-certification.ps1` and `scripts/udp-release-candidate-certification.sh`.
- Added `crates/ns-testkit/examples/udp_release_candidate_certification.rs`, which consumes `release_candidate_acceptance` plus Linux, macOS, and Windows compatible-host interop-profile catalogs and emits a fail-closed machine-readable operator verdict on the shared schema version `20`.
- Kept the shared operator-verdict schema on version `20` while extending release-facing consumers with exact compatible-host interop-catalog `source_lane`, failed-profile-count, host-label-set, blocked-fallback, policy-disabled-fallback round-trip, and transport-fallback-integrity certification handling.
- Tightened release-candidate certification so carried `release_candidate_acceptance` evidence must remain contract-valid and ready, Linux/macOS/Windows compatible-host interop catalogs must stay exact, a passed compatible-host interop contract cannot carry failed profiles, and `udp_blocked_fallback_surface_passed`, `policy_disabled_fallback_round_trip_stable`, and `transport_fallback_integrity_surface_passed` must remain resolved for a ready verdict.
- Added reviewed malformed control-frame outer-frame-length fixture `WC-UDP-FLOW-CLOSE-DGRAMUNAVAIL-BADFRAMELEN-087`, then synchronized it only into the maintained control-frame corpus and regression buckets.
- Preserved bridge-domain, adapter, bridge-app, wire, and session-core boundaries; milestone 46 does not widen Remnawave, bridge, or transport contracts.

## Verification Notes

- The maintained fixture generator, corpus sync, and wire conformance suite all pass with the `087` reviewed malformed-input seed included.
- The release-facing example chain through `udp_release_candidate_certification` now passes targeted tests on the shared operator-verdict schema version `20`, and the maintained live UDP fallback, datagram-unavailable, reordering, impairment, MTU, and queue-pressure checks remain green.
- The Windows-first `udp-release-candidate-certification.ps1` wrapper remains intentionally fail closed when required release-candidate-acceptance or compatible-host interop-catalog evidence is missing, partial, stale, or schema-drifted.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, and release-facing workflow lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, summary, and compatible-host catalog surfaces
