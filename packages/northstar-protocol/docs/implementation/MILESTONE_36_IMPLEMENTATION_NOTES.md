# Milestone 36 Implementation Notes

Milestone 36 extends the datagram rollout toolchain from release-soak signoff discipline toward a sustained release-gate operator workflow with stronger compatible-host burn-in evidence, while keeping Remnawave non-fork, bridge contracts unchanged, the session core transport-agnostic, and `0-RTT` disabled.

## Governing Inputs

- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/northstar_security_test_and_interop_plan_v0_1.md`
- `docs/spec/northstar_threat_model_v0_1.md`

## Scope

- keep Remnawave on the external bridge boundary
- keep bridge deployment topology unchanged
- keep transport selection, fallback, and rollout rules spec-driven and fail closed
- add one more workflow-backed datagram verification surface without changing Windows-first local wrapper expectations
- strengthen release-facing operator verdicts around exact compatible-host interop-catalog contracts, queue-pressure hold accounting, and transport-fallback integrity
- grow the maintained reviewed UDP corpus and compatible-host catalog artifacts

## Implemented

- Added a workflow-backed Linux `release_gate` lane to `.github/workflows/udp-optional-gates.yml` plus `scripts/udp-release-gate.ps1` and `scripts/udp-release-gate.sh`.
- Added `crates/ns-testkit/examples/udp_release_gate.rs`, which consumes release-soak plus Linux, macOS, and Windows compatible-host interop catalogs and emits a fail-closed machine-readable operator verdict.
- Advanced the shared operator-verdict schema to version `15` in release-facing consumers and carried exact interop-profile-catalog contract validation into the new release-gate surface.
- Extended `udp_rollout_validation_lab` to project `reordered_after_close_rejection_stable`, and fed that signal into `shutdown_sequence_stable`, `degradation_surface_passed`, and `transport_fallback_integrity_surface_passed`.
- Added `loopback_h3_datagrams_reject_reordered_after_close_without_fallback` to the maintained live UDP suite and promoted `reordered-after-close-rejection` into the maintained compatible-host interop profile inventory.
- Added reviewed malformed UDP fixtures `WC-UDP-OPEN-BADMETACOUNT-056`, `WC-UDP-OPEN-NONCANONMETACOUNT-057`, `WC-UDP-OK-NONCANONMETACOUNT-058`, `WC-UDP-STREAM-OPEN-NONCANONMETACOUNT-059`, and `WC-UDP-STREAM-ACCEPT-NONCANONMETACOUNT-060`, then synchronized them into the maintained corpora and conformance suite.
- Preserved bridge-domain, adapter, and bridge-app boundaries; milestone 36 does not widen Remnawave or bridge contracts.

## Verification Notes

- The maintained fixture generator, corpus sync, wire conformance suite, and the new reordered-after-close live UDP test all pass with the `056-060` reviewed malformed-input set included.
- The release-facing example chain through `udp_release_gate` now passes targeted tests on the shared operator-verdict schema after the milestone 36 contract updates.
- The Windows-first `udp-release-gate.ps1` wrapper remains intentionally fail closed when required release-soak or host-catalog evidence is missing or drifted.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, and release-facing workflow lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, summary, and compatible-host catalog surfaces
