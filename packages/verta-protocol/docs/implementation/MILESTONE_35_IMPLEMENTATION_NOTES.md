# Milestone 35 Implementation Notes

Milestone 35 extends the datagram rollout toolchain from release-burn-in operator workflow toward release-soak signoff discipline with stronger sustained compatible-host evidence, while keeping Remnawave non-fork, bridge contracts unchanged, the session core transport-agnostic, and `0-RTT` disabled.

## Governing Inputs

- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/verta_security_test_and_interop_plan_v0_1.md`
- `docs/spec/verta_threat_model_v0_1.md`

## Scope

- keep Remnawave on the external bridge boundary
- keep bridge deployment topology unchanged
- keep transport selection, fallback, and rollout rules spec-driven and fail closed
- add one more workflow-backed datagram verification surface without changing Windows-first local wrapper expectations
- strengthen release-facing operator verdicts around exact interop profile contracts, queue-pressure hold accounting, and transport-fallback integrity
- grow the maintained reviewed UDP corpus and active-fuzz inputs

## Implemented

- Added a workflow-backed Linux `release_soak` lane to `.github/workflows/udp-optional-gates.yml` plus `scripts/udp-release-soak.ps1` and `scripts/udp-release-soak.sh`.
- Added `crates/ns-testkit/examples/udp_release_soak.rs`, which consumes release-burn-in plus Linux, macOS, and Windows interop artifacts and emits a fail-closed machine-readable operator verdict.
- Advanced the shared operator-verdict schema to version `14` in release-facing consumers and carried explicit `queue_pressure_hold_count`, exact interop-profile-contract, and transport-fallback-integrity semantics into the new release-soak surface.
- Extended the maintained compatible-host interop catalog with the `associated-stream-guard-recovery` profile so downstream consumers can require explicit no-silent-fallback proof for wrong-associated-stream recovery.
- Added a maintained interop profile catalog capture path through `cargo run -p ns-testkit --example udp_interop_lab -- --list --format json`.
- Added reviewed malformed UDP fixtures `WC-UDP-OK-ZEROIDLETIMEOUT-051`, `WC-UDP-FLOW-CLOSE-BADUTF8-052`, `WC-UDP-STREAM-OPEN-BADMETACOUNT-053`, `WC-UDP-STREAM-ACCEPT-BADMETACOUNT-054`, and `WC-UDP-OK-BADMETACOUNT-055`, then synchronized them into the maintained corpora and conformance suite.
- Preserved bridge-domain, adapter, and bridge-app boundaries; milestone 35 does not widen Remnawave or bridge contracts.

## Verification Notes

- The new `udp_release_soak` example tests pass with both a fully ready operator-verdict path and a fail-closed missing-Windows-interop path.
- The maintained fixture generator, corpus sync, and wire conformance suite now all include the `051-055` reviewed malformed-input set.
- The maintained rollout and release-facing wrappers remain intentionally fail closed when required compatible-host artifacts are missing or drifted.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, and release-facing workflow lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, and summary surfaces
