# Milestone 43 Implementation Notes

Milestone 43 extends the datagram rollout toolchain from release-candidate signoff closure toward release-candidate stabilization with broader deployment-grade evidence, while keeping Remnawave non-fork, bridge contracts unchanged, the session core transport-agnostic, and `0-RTT` disabled.

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
- strengthen release-facing operator verdicts around exact compatible-host interop-catalog `source_lane`, host-label-set, failed-profile-count, readiness-set, and summary-contract handling
- project maintained datagram-unavailable rejection evidence from live UDP coverage into rollout-validation and downstream release-facing summaries
- grow the maintained reviewed UDP corpus around malformed fallback close-frame lengths without widening parser behavior

## Implemented

- Added a workflow-backed Linux `release_candidate_stabilization` lane to `.github/workflows/udp-optional-gates.yml` plus `scripts/udp-release-candidate-stabilization.ps1` and `scripts/udp-release-candidate-stabilization.sh`.
- Added `crates/ns-testkit/examples/udp_release_candidate_stabilization.rs`, which consumes `release_candidate_signoff_closure` plus Linux, macOS, and Windows compatible-host interop catalogs and emits a fail-closed machine-readable operator verdict.
- Kept the shared operator-verdict schema on version `20` while extending release-facing consumers with exact compatible-host interop-catalog `source_lane`, host-label-set, failed-profile-count, and release-candidate-evidence-freeze/readiness contract checks.
- Synchronized rollout-validation summary version `19` and projected `datagram_only_unavailable_rejection_stable` so transport-fallback-integrity evidence now carries the maintained datagram-only-unavailable rejection signal through downstream release-facing summaries.
- Tightened release-candidate stabilization so `release_candidate_signoff_closure` must remain contract-valid, `release_candidate_evidence_freeze` must be present and passed for a ready verdict, readiness labels and readiness host labels must stay exact, a passed compatible-host interop contract cannot carry failed profiles, and exact Linux/macOS/Windows compatible-host catalog provenance must remain stable.
- Added reviewed malformed fallback close-frame outer-frame-length fixtures `WC-UDP-STREAM-CLOSE-BADFRAMELEN-083` and `WC-UDP-FLOW-CLOSE-BADFRAMELEN-084`, then synchronized them only into the maintained fallback-frame and control-frame corpus/regression buckets.
- Kept wire behavior fail closed for malformed fallback close-frame lengths and aligned the reviewed fixture expectations to the actual decoder result (`LengthMismatch`) instead of widening parser behavior.
- Preserved bridge-domain, adapter, and bridge-app boundaries; milestone 43 does not widen Remnawave or bridge contracts.

## Verification Notes

- The maintained fixture generator, corpus sync, and wire conformance suite all pass with the `083-084` reviewed malformed-input set included.
- The release-facing example chain through `udp_release_candidate_stabilization` now passes targeted tests on the shared operator-verdict schema version `20`.
- The maintained datagram-only-unavailable rejection live evidence now backs rollout-validation and downstream release-facing consumers instead of remaining a stand-alone signal.
- The Windows-first `udp-release-candidate-stabilization.ps1` wrapper remains intentionally fail closed when required release-candidate-signoff-closure or compatible-host interop-catalog evidence is missing, partial, stale, or schema-drifted.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, and release-facing workflow lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, summary, and compatible-host catalog surfaces
