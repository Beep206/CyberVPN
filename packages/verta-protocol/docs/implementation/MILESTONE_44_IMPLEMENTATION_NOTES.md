# Milestone 44 Implementation Notes

Milestone 44 extends the datagram rollout toolchain from release-candidate stabilization toward release-candidate readiness with broader deployment-grade evidence, while keeping Remnawave non-fork, bridge contracts unchanged, the session core transport-agnostic, and `0-RTT` disabled.

## Governing Inputs

- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/verta_security_test_and_interop_plan_v0_1.md`
- `docs/spec/verta_threat_model_v0_1.md`
- `docs/spec/verta_remnawave_bridge_spec_v0_1.md`

## Scope

- keep Remnawave on the external bridge boundary
- keep bridge deployment topology unchanged
- keep transport selection, fallback, and rollout rules spec-driven and fail closed
- add one more workflow-backed datagram verification surface without changing Windows-first wrapper expectations
- strengthen release-facing operator verdicts around exact compatible-host interop-catalog `source_lane`, failed-profile-count, host-label-set, readiness-set, and blocked-fallback contract handling
- project maintained blocked-fallback evidence from compatible-host interop through rollout-validation, rollout-comparison, and downstream release-facing summaries
- grow the maintained reviewed UDP corpus around malformed control-frame outer lengths without widening parser behavior

## Implemented

- Added a workflow-backed Linux `release_candidate_readiness` lane to `.github/workflows/udp-optional-gates.yml` plus `scripts/udp-release-candidate-readiness.ps1` and `scripts/udp-release-candidate-readiness.sh`.
- Added `crates/ns-testkit/examples/udp_release_candidate_readiness.rs`, which consumes `release_candidate_stabilization` plus Linux, macOS, and Windows rollout-readiness summaries and emits a fail-closed machine-readable operator verdict.
- Kept the shared operator-verdict schema on version `20` while extending release-facing consumers with exact compatible-host interop-catalog `source_lane`, failed-profile-count, host-label-set, readiness-set, blocked-fallback, and summary-contract handling.
- Synchronized `udp_interop_lab` summary version `5`, `udp_rollout_validation_lab` summary version `20`, and `udp_rollout_compare` contracts so `udp_blocked_fallback_surface_passed` now remains explicit and fail closed through compatible-host interop, rollout-validation, rollout-comparison, and release-facing consumers.
- Tightened release-candidate readiness so `release_candidate_stabilization` must remain contract-valid, Linux/macOS/Windows rollout-readiness evidence must stay exact, a passed compatible-host interop contract cannot carry failed profiles, and `udp_blocked_fallback_surface_passed`, `policy_disabled_fallback_round_trip_stable`, and `transport_fallback_integrity_surface_passed` must remain resolved for a ready verdict.
- Added reviewed malformed control-frame outer-frame-length fixture `WC-UDP-OK-BADFRAMELEN-085`, then synchronized it only into the maintained control-frame corpus and regression buckets.
- Kept wire behavior fail closed for malformed `UDP_OK` outer-frame lengths and aligned the reviewed fixture expectation to the actual decoder result (`LengthMismatch`) instead of widening parser behavior.
- Preserved bridge-domain, adapter, bridge-app, and session-core boundaries; milestone 44 does not widen Remnawave, bridge, or transport contracts.

## Verification Notes

- The maintained fixture generator, corpus sync, and wire conformance suite all pass with the `085` reviewed malformed-input seed included.
- The release-facing example chain through `udp_release_candidate_readiness` now passes targeted tests on the shared operator-verdict schema version `20`.
- The maintained blocked-fallback compatible-host evidence now backs rollout-validation, rollout-comparison, and downstream release-facing consumers instead of remaining an interop-only signal.
- The Windows-first `udp-release-candidate-readiness.ps1` wrapper remains intentionally fail closed when required release-candidate-stabilization or host-readiness evidence is missing, partial, stale, or schema-drifted.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, and release-facing workflow lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, summary, and compatible-host catalog surfaces
