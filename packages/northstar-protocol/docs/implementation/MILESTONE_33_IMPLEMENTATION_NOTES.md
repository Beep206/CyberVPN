# Milestone 33 Implementation Notes

Milestone 33 extends the datagram rollout toolchain from release-gating operator workflow toward release-readiness signoff discipline with stronger sustained compatible-host evidence, while keeping Remnawave non-fork, bridge contracts unchanged, the session core transport-agnostic, and `0-RTT` disabled.

## Governing Inputs

- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/northstar_security_test_and_interop_plan_v0_1.md`
- `docs/spec/northstar_threat_model_v0_1.md`

## Scope

- keep Remnawave on the external bridge boundary
- keep bridge deployment topology unchanged
- keep transport selection and fallback rules spec-driven and fail closed
- strengthen release-facing operator verdicts without inventing new bridge or session semantics
- add one more compatible-host interoperability surface while preserving Windows-first wrapper flows
- grow the maintained reviewed UDP corpus and active-fuzz inputs

## Implemented

- Added a compatible-host Windows interop-lab lane to `.github/workflows/udp-optional-gates.yml` and wired `udp_release_candidate_signoff` plus `scripts/udp-release-candidate-signoff.*` to consume the uploaded Windows interop artifact alongside Windows rollout-readiness and macOS interop evidence.
- Advanced the shared operator-verdict schema to version `12` across `udp_rollout_compare`, `udp_rollout_matrix`, `udp_release_workflow`, `udp_deployment_signoff`, `udp_release_prep`, and `udp_release_candidate_signoff`.
- Tightened interop summary contracts so downstream rollout consumers now fail closed on profile-set drift, required-no-silent-fallback subset drift, queue-pressure drift, transport-fallback-integrity drift, or unsupported upstream summary versions instead of accepting arithmetic-only agreement.
- Extended the maintained WAN-lab profile catalog with `queue-pressure-sticky`, promoted the repeated queue-pressure sticky-selection proof into the interop surface, and projected `queue_pressure_surface_passed`, `required_no_silent_fallback_profile_*`, and `transport_fallback_integrity_surface_passed` into rollout-validation and downstream release-facing summaries.
- Kept rollout-validation fail closed when machine-readable surface facts fail even if the underlying commands returned successfully, so wrapper and workflow callers can reuse one stable non-zero contract.
- Added reviewed malformed UDP fixtures `WC-UDP-OPEN-NONCANONTARGETTYPE-043`, `WC-UDP-OPEN-NONCANONPORT-044`, `WC-UDP-FLOW-CLOSE-NONCANONMSGLEN-045`, and `WC-UDP-STREAM-CLOSE-NONCANONMSGLEN-046`, then synchronized them into the maintained corpora and conformance suite.
- Preserved bridge-domain, adapter, and bridge-app boundaries; milestone 33 does not widen Remnawave or bridge contracts.

## Verification Notes

- Targeted `ns-testkit` example tests passed after updating the shared schema, interop contracts, and release-facing tests to the milestone-33 summary shapes.
- `crates/ns-wire/tests/conformance_fixtures.rs` initially failed only because new fixture generation and conformance were launched in parallel before the JSON fixtures existed on disk; the sequential rerun passed once `generate_milestone2_fixtures` completed.
- The maintained rollout and release-facing wrappers remain intentionally fail closed when required compatible-host artifacts are missing or drifted.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, and release-facing workflow lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, and summary surfaces
