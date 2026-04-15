# Milestone 40 Implementation Notes

Milestone 40 extends the datagram rollout toolchain from release-candidate consolidation toward release-candidate hardening with broader deployment-grade evidence, while keeping Remnawave non-fork, bridge contracts unchanged, the session core transport-agnostic, and `0-RTT` disabled.

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
- strengthen release-facing operator verdicts around exact compatible-host interop-catalog provenance and fail-closed summary-contract handling
- project fallback-flow rejection evidence from maintained live UDP checks into rollout-validation and downstream release-facing summaries
- grow the maintained reviewed UDP corpus around non-canonical flow-close and stream-close outer frame lengths without widening parser behavior

## Implemented

- Added a workflow-backed Linux `release_candidate_hardening` lane to `.github/workflows/udp-optional-gates.yml` plus `scripts/udp-release-candidate-hardening.ps1` and `scripts/udp-release-candidate-hardening.sh`.
- Added `crates/ns-testkit/examples/udp_release_candidate_hardening.rs`, which consumes `release_candidate_consolidation` plus Linux, macOS, and Windows rollout-validation evidence and emits a fail-closed machine-readable operator verdict.
- Advanced the shared operator-verdict schema to version `19` across the release-facing verdict stack.
- Tightened `udp_release_gate` and `udp_release_candidate_consolidation` so compatible-host interop catalogs must carry the exact `source_lane = compatible_host_interop_lab` contract instead of only a non-empty provenance string.
- Synchronized rollout-validation summary version `16` and projected `fallback_flow_guard_rejection_stable` into `transport_fallback_integrity_surface_passed` and downstream release-facing decisions.
- Added reviewed malformed outer frame-length fixtures `WC-UDP-FLOW-CLOSE-NONCANONFRAMELEN-077` and `WC-UDP-STREAM-CLOSE-NONCANONFRAMELEN-078`, then synchronized them into the maintained corpora and conformance suite.
- Kept wire behavior fail closed for non-canonical close-frame outer lengths and aligned the reviewed fixture expectations to the actual decoder result (`NonCanonicalVarint`) instead of widening parser behavior.
- Preserved bridge-domain, adapter, and bridge-app boundaries; milestone 40 does not widen Remnawave or bridge contracts.

## Verification Notes

- The maintained fixture generator, corpus sync, and wire conformance suite all pass with the `077-078` reviewed malformed-input set included.
- The release-facing example chain through `udp_release_candidate_hardening` now passes targeted tests on shared operator-verdict schema version `19`.
- The maintained live evidence surfaces `loopback_h3_datagrams_accept_payload_at_effective_mtu_ceiling` and `loopback_udp_fallback_rejects_wrong_flow_id_with_protocol_violation_close` both pass and now back maintained rollout-validation and release-candidate-hardening evidence instead of remaining stand-alone checks.
- The Windows-first `udp-release-candidate-hardening.ps1` wrapper remains intentionally fail closed when required release-candidate-consolidation or compatible-host rollout-validation evidence is missing, partial, stale, or schema-drifted.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, and release-facing workflow lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, summary, and compatible-host catalog surfaces
