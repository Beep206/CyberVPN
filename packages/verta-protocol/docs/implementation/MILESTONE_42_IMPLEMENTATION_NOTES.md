# Milestone 42 Implementation Notes

Milestone 42 extends the datagram rollout toolchain from release-candidate evidence freeze toward release-candidate signoff closure with broader deployment-grade evidence, while keeping Remnawave non-fork, bridge contracts unchanged, the session core transport-agnostic, and `0-RTT` disabled.

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
- strengthen release-facing operator verdicts around exact compatible-host interop-catalog provenance, failed-profile accounting, and host-label-set contract handling
- project maintained policy-disabled fallback round-trip evidence from live UDP coverage into rollout-validation and downstream release-facing summaries
- grow the maintained reviewed UDP corpus around malformed fallback stream-open and stream-accept frame lengths without widening parser behavior

## Implemented

- Added a workflow-backed Linux `release_candidate_signoff_closure` lane to `.github/workflows/udp-optional-gates.yml` plus `scripts/udp-release-candidate-signoff-closure.ps1` and `scripts/udp-release-candidate-signoff-closure.sh`.
- Added `crates/ns-testkit/examples/udp_release_candidate_signoff_closure.rs`, which consumes `release_candidate_evidence_freeze` plus Linux, macOS, and Windows rollout-readiness summaries and emits a fail-closed machine-readable operator verdict.
- Kept the shared operator-verdict schema on version `20` while extending release-facing consumers with exact compatible-host interop-catalog `source_lane`, failed-profile-count, and Linux/macOS/Windows host-label-set contract checks.
- Synchronized rollout-validation summary version `18` and projected `policy_disabled_fallback_round_trip_stable` so `transport_fallback_integrity_surface_passed` cannot remain true when the maintained policy-disabled fallback round-trip evidence fails.
- Tightened the release-candidate-signoff-closure contract so `source_lane` must stay exactly `compatible_host_interop_lab`, `interop_failed_profile_count` must match the failed-profile inventory, a passed interop contract cannot carry failed profiles, and the carried compatible-host labels must stay exactly `linux`, `macos`, and `windows`.
- Added reviewed malformed fallback stream-open and stream-accept outer-frame-length fixtures `WC-UDP-STREAM-OPEN-BADFRAMELEN-081` and `WC-UDP-STREAM-ACCEPT-BADFRAMELEN-082`, then synchronized them only into the maintained fallback-frame corpus and regression buckets.
- Kept wire behavior fail closed for malformed fallback frame lengths and aligned the reviewed fixture expectations to the actual decoder result (`LengthMismatch`) instead of widening parser behavior.
- Preserved bridge-domain, adapter, and bridge-app boundaries; milestone 42 does not widen Remnawave or bridge contracts.

## Verification Notes

- The maintained fixture generator, corpus sync, and wire conformance suite all pass with the `081-082` reviewed malformed-input set included.
- The release-facing example chain through `udp_release_candidate_signoff_closure` now passes targeted tests on the shared operator-verdict schema version `20`.
- The maintained policy-disabled fallback round-trip live evidence now backs rollout-validation and downstream release-facing consumers instead of remaining a stand-alone signal.
- The Windows-first `udp-release-candidate-signoff-closure.ps1` wrapper remains intentionally fail closed when required release-candidate-evidence-freeze or compatible-host rollout-readiness evidence is missing, partial, stale, or schema-drifted.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, and release-facing workflow lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, summary, and compatible-host catalog surfaces
