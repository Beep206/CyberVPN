# Milestone 41 Implementation Notes

Milestone 41 extends the datagram rollout toolchain from release-candidate hardening toward release-candidate evidence freeze with broader deployment-grade evidence, while keeping Remnawave non-fork, bridge contracts unchanged, the session core transport-agnostic, and `0-RTT` disabled.

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
- strengthen release-facing operator verdicts around exact compatible-host interop-catalog provenance, failed-profile accounting, and summary-contract handling
- project blocked-fallback evidence from maintained live UDP coverage into rollout-validation and downstream release-facing summaries
- grow the maintained reviewed UDP corpus around malformed fallback frame lengths without widening parser behavior

## Implemented

- Added a workflow-backed Linux `release_candidate_evidence_freeze` lane to `.github/workflows/udp-optional-gates.yml` plus `scripts/udp-release-candidate-evidence-freeze.ps1` and `scripts/udp-release-candidate-evidence-freeze.sh`.
- Added `crates/ns-testkit/examples/udp_release_candidate_evidence_freeze.rs`, which consumes `release_candidate_hardening` plus Linux, macOS, and Windows compatible-host interop catalogs and emits a fail-closed machine-readable operator verdict.
- Advanced the shared operator-verdict schema to version `20` across the release-facing verdict stack.
- Synchronized rollout-validation summary version `17` and projected `udp_blocked_fallback_surface_passed` so `transport_fallback_integrity_surface_passed` cannot remain true when the maintained blocked-fallback evidence fails.
- Tightened the release-facing compatible-host interop-catalog contract so `source_lane` must stay exactly `compatible_host_interop_lab`, `interop_failed_profile_count` must match the failed-profile inventory, and a passed profile contract cannot carry failed profiles.
- Added reviewed malformed fallback frame-length fixtures `WC-UDP-STREAM-PACKET-NONCANONFRAMELEN-079` and `WC-UDP-STREAM-PACKET-BADFRAMELEN-080`, then synchronized them only into the maintained fallback-frame corpus and regression buckets.
- Kept wire behavior fail closed for malformed fallback frame lengths and aligned the reviewed fixture expectations to the actual decoder results (`NonCanonicalVarint` and `LengthMismatch`) instead of widening parser behavior.
- Preserved bridge-domain, adapter, and bridge-app boundaries; milestone 41 does not widen Remnawave or bridge contracts.

## Verification Notes

- The maintained fixture generator, corpus sync, and wire conformance suite all pass with the `079-080` reviewed malformed-input set included.
- The release-facing example chain through `udp_release_candidate_evidence_freeze` now passes targeted tests on shared operator-verdict schema version `20`.
- The maintained blocked-fallback live evidence now backs rollout-validation and downstream release-facing consumers instead of remaining a stand-alone signal.
- The Windows-first `udp-release-candidate-evidence-freeze.ps1` wrapper remains intentionally fail closed when required release-candidate-hardening or compatible-host interop-catalog evidence is missing, partial, stale, or schema-drifted.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, and release-facing workflow lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, summary, and compatible-host catalog surfaces
