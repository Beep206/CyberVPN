# Milestone 45 Implementation Notes

Milestone 45 extends the datagram rollout toolchain from release-candidate readiness toward release-candidate acceptance with stronger deployment-grade evidence, while keeping Remnawave non-fork, bridge contracts unchanged, the session core transport-agnostic, and `0-RTT` disabled.

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
- strengthen release-facing operator verdicts around exact compatible-host interop-catalog `source_lane`, failed-profile-count, host-label-set, readiness-set, blocked-fallback, policy-disabled-fallback, and transport-fallback-integrity handling
- grow the maintained reviewed UDP corpus around malformed control-frame outer lengths without widening parser behavior

## Implemented

- Added a workflow-backed Linux `release_candidate_acceptance` lane to `.github/workflows/udp-optional-gates.yml` plus `scripts/udp-release-candidate-acceptance.ps1` and `scripts/udp-release-candidate-acceptance.sh`.
- Added `crates/ns-testkit/examples/udp_release_candidate_acceptance.rs`, which consumes `release_candidate_readiness` plus Linux, macOS, and Windows rollout-readiness summaries and emits a fail-closed machine-readable operator verdict on the shared schema version `20`.
- Kept the shared operator-verdict schema on version `20` while extending release-facing consumers with exact compatible-host interop-catalog `source_lane`, failed-profile-count, host-label-set, readiness-set, blocked-fallback, policy-disabled-fallback round-trip, and transport-fallback-integrity acceptance handling.
- Tightened release-candidate acceptance so carried `release_candidate_readiness` evidence must remain contract-valid and ready, Linux/macOS/Windows rollout-readiness evidence must stay exact, a passed compatible-host interop contract cannot carry failed profiles, and `udp_blocked_fallback_surface_passed`, `policy_disabled_fallback_round_trip_stable`, and `transport_fallback_integrity_surface_passed` must remain resolved for a ready verdict.
- Added reviewed malformed control-frame outer-frame-length fixture `WC-UDP-OPEN-BADFRAMELEN-086`, then synchronized it only into the maintained control-frame corpus and regression buckets.
- Preserved bridge-domain, adapter, bridge-app, and session-core boundaries; milestone 45 does not widen Remnawave, bridge, or transport contracts.

## Verification Notes

- The maintained fixture generator, corpus sync, and wire conformance suite all pass with the `086` reviewed malformed-input seed included.
- The release-facing example chain through `udp_release_candidate_acceptance` now passes targeted tests on the shared operator-verdict schema version `20`.
- The Windows-first `udp-release-candidate-acceptance.ps1` wrapper remains intentionally fail closed when required release-candidate-readiness or host-readiness evidence is missing, partial, stale, or schema-drifted.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, and release-facing workflow lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, summary, and compatible-host catalog surfaces
