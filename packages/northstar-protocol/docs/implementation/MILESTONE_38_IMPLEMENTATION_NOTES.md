# Milestone 38 Implementation Notes

Milestone 38 extends the datagram rollout toolchain from release-readiness burn-down discipline toward release-stability signoff with stronger sustained compatible-host evidence, while keeping Remnawave non-fork, bridge contracts unchanged, the session core transport-agnostic, and `0-RTT` disabled.

## Governing Inputs

- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/northstar_security_test_and_interop_plan_v0_1.md`
- `docs/spec/northstar_threat_model_v0_1.md`

## Scope

- keep Remnawave on the external bridge boundary
- keep bridge deployment topology unchanged
- keep transport selection, fallback, and rollout rules spec-driven and fail closed
- add one more workflow-backed datagram verification surface without changing Windows-first local wrapper expectations
- strengthen release-facing operator verdicts around queue-hold-host accounting, exact compatible-host interop-catalog host coverage, and stable summary-contract precedence
- project oversized-payload guard recovery into rollout-validation and downstream release-facing summaries
- grow the maintained reviewed UDP corpus around metadata-type canonicality without widening parser behavior

## Implemented

- Added a workflow-backed Linux `release_stability_signoff` lane to `.github/workflows/udp-optional-gates.yml` plus `scripts/udp-release-stability-signoff.ps1` and `scripts/udp-release-stability-signoff.sh`.
- Added `crates/ns-testkit/examples/udp_release_stability_signoff.rs`, which consumes release-readiness-burndown plus Linux, macOS, and Windows compatible-host interop evidence and emits a fail-closed machine-readable operator verdict.
- Advanced the shared operator-verdict schema to version `17` in release-facing consumers and carried explicit `queue_hold_host_count`, exact compatible-host interop-catalog host coverage, and stable `summary_contract_invalid` precedence into downstream release surfaces.
- Extended the maintained compatible-host interop profile set with `oversized-payload-guard-recovery`, backed by the existing live UDP oversized-payload guard recovery test instead of inventing a new transport behavior.
- Synchronized rollout-validation summary version `14` and projected `oversized_payload_guard_recovery_stable` into sticky-selection, degradation, and downstream release-facing decisions.
- Added reviewed malformed UDP fixtures `WC-UDP-OPEN-NONCANONMETATYPE-069`, `WC-UDP-OK-NONCANONMETATYPE-070`, `WC-UDP-STREAM-OPEN-NONCANONMETATYPE-071`, and `WC-UDP-STREAM-ACCEPT-NONCANONMETATYPE-072`, then synchronized them into the maintained corpora and conformance suite.
- Kept wire behavior fail closed for non-canonical metadata-type varints and aligned the reviewed fixture expectations to the actual decoder result (`NonCanonicalVarint`) instead of widening parser behavior.
- Preserved bridge-domain, adapter, and bridge-app boundaries; milestone 38 does not widen Remnawave or bridge contracts.

## Verification Notes

- The maintained fixture generator, corpus sync, and wire conformance suite all pass with the `069-072` reviewed malformed-input set included.
- The release-facing example chain through `udp_release_stability_signoff` now passes targeted tests on shared operator-verdict schema version `17`.
- The Windows-first `udp-release-stability-signoff.ps1` wrapper remains intentionally fail closed when required release-readiness-burndown or compatible-host interop evidence is missing or drifted.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, and release-facing workflow lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, summary, and compatible-host catalog surfaces
