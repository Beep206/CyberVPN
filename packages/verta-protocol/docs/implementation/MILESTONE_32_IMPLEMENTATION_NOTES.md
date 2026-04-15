# Milestone 32 Implementation Notes

Milestone 32 extends the datagram rollout toolchain from release-candidate signoff discipline toward a release-gating operator workflow without widening bridge-domain contracts or weakening the transport-agnostic session core.

## Governing Inputs

- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/verta_security_test_and_interop_plan_v0_1.md`
- `docs/spec/verta_threat_model_v0_1.md`

## Scope

- keep Remnawave on the non-fork bridge boundary
- keep the session core transport-agnostic
- keep `0-RTT` disabled
- broaden compatible-host datagram evidence with one more workflow-backed interoperable surface
- keep release-facing operator verdicts fail closed and comparison-friendly across maintained workflow consumers
- keep maintained CLI validation outputs stable across `ns-clientd`, `nsctl`, and `ns-gatewayd`

## Implemented

- Added a compatible-host macOS interop-lab lane to `.github/workflows/udp-optional-gates.yml` that runs the maintained `udp_wan_lab` harness, uploads `udp-interop-lab-summary-macos.json`, and preserves the existing Windows-first wrapper flow.
- Advanced the shared operator-verdict schema to version `11` across `udp_rollout_compare`, `udp_rollout_matrix`, `udp_release_workflow`, `udp_deployment_signoff`, `udp_release_prep`, and `udp_release_candidate_signoff`.
- Extended `udp_rollout_validation_lab` with `reordering_no_silent_fallback_passed`, `policy_disabled_fallback_surface_passed`, and `transport_fallback_integrity_surface_passed`, so downstream rollout consumers now gate on explicit post-establishment no-silent-fallback evidence instead of inferring it from older surface totals.
- Added `queue_guard_tight_hold_count` and transport-fallback-integrity propagation across the shared operator-verdict stack so comparison, matrix, release-workflow, deployment-signoff, release-prep, and release-candidate-signoff share one low-cardinality required-input and degradation-hold vocabulary.
- Extended `udp_release_candidate_signoff` plus `scripts/udp-release-candidate-signoff.*` so release-facing signoff now consumes release-prep, Windows rollout-readiness, and macOS interop evidence and fails closed when macOS interop or transport-fallback-integrity evidence is missing, drifted, or failed.
- Added reviewed malformed UDP fixtures `WC-UDP-OPEN-IPV6LEN-040`, `WC-UDP-OPEN-EMPTYDOMAIN-041`, and `WC-UDP-OK-NONCANONMODE-042`, synchronized them into the maintained corpora, and fixed `ns-wire` target decoding so empty-domain `UDP_FLOW_OPEN` frames now reject as validation failures.

## Verification Notes

- `scripts/udp-rollout-readiness.ps1` now proves the maintained rollout-validation path on Windows-first machines with explicit `reordering_no_silent_fallback_passed=true` and `transport_fallback_integrity_surface_passed=true`.
- `scripts/udp-release-candidate-signoff.*` are intentionally fail closed unless release-prep, Windows rollout-readiness, and macOS interop evidence all exist on the shared schema and remain ready.
- The new reviewed empty-domain fixture uncovered a real wire-validation gap; milestone 32 closes that gap in `ns-wire` instead of weakening the maintained fixture set.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, release-workflow, deployment-signoff, release-prep, or release-candidate-signoff lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, and summary surfaces
