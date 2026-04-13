# Milestone 37 Implementation Notes

Milestone 37 extends the datagram rollout toolchain from sustained release-gate operator workflow toward release-readiness burn-down discipline with stronger sustained compatible-host evidence, while keeping Remnawave non-fork, bridge contracts unchanged, the session core transport-agnostic, and `0-RTT` disabled.

## Governing Inputs

- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/northstar_security_test_and_interop_plan_v0_1.md`
- `docs/spec/northstar_threat_model_v0_1.md`

## Scope

- keep Remnawave on the external bridge boundary
- keep bridge deployment topology unchanged
- keep transport selection, fallback, and rollout rules spec-driven and fail closed
- add one more workflow-backed datagram verification surface without changing Windows-first local wrapper expectations
- strengthen release-facing operator verdicts around exact summary-contract precedence, host-bound compatible-host interop-catalog semantics, and low-cardinality queue-hold accounting
- grow the maintained reviewed UDP corpus around metadata-length canonicality and truncation behavior

## Implemented

- Added a workflow-backed Linux `release_readiness_burndown` lane to `.github/workflows/udp-optional-gates.yml` plus `scripts/udp-release-readiness-burndown.ps1` and `scripts/udp-release-readiness-burndown.sh`.
- Added `crates/ns-testkit/examples/udp_release_readiness_burndown.rs`, which consumes release-gate plus Linux, macOS, and Windows rollout-readiness evidence and emits a fail-closed machine-readable operator verdict.
- Advanced the shared operator-verdict schema to version `16` in release-facing consumers and carried explicit `summary_contract_invalid_count`, `queue_hold_input_count`, exact interop-profile-catalog host-label accounting, and stable gate-state reasoning into downstream release surfaces.
- Extended `udp_interop_lab -- --list --format json` so compatible-host interop catalogs now carry a stable envelope with `catalog_schema`, `catalog_schema_version`, `host_label`, and `source_lane`, rather than exposing only a raw profile array.
- Synchronized rollout-validation summary version `13` across `udp_rollout_compare`, `udp_deployment_signoff`, and `udp_release_prep`, which restored the Windows-first `udp-rollout-readiness.*` path after the milestone 37 rollout-validation expansion.
- Added reviewed malformed UDP fixtures `WC-UDP-OPEN-NONCANONMETALEN-061`, `WC-UDP-OK-NONCANONMETALEN-062`, `WC-UDP-STREAM-OPEN-NONCANONMETALEN-063`, `WC-UDP-STREAM-ACCEPT-NONCANONMETALEN-064`, `WC-UDP-OPEN-BADMETALEN-065`, `WC-UDP-OK-BADMETALEN-066`, `WC-UDP-STREAM-OPEN-BADMETALEN-067`, and `WC-UDP-STREAM-ACCEPT-BADMETALEN-068`, then synchronized them into the maintained corpora and conformance suite.
- Kept wire behavior fail closed for bad metadata-length truncation and aligned the reviewed fixture expectations to the actual decoder result (`Truncated`) instead of widening parser behavior.
- Preserved bridge-domain, adapter, and bridge-app boundaries; milestone 37 does not widen Remnawave or bridge contracts.

## Verification Notes

- The maintained fixture generator, corpus sync, and wire conformance suite all pass with the `061-068` reviewed malformed-input set included.
- The release-facing example chain through `udp_release_readiness_burndown` now passes targeted tests on shared operator-verdict schema version `16`.
- The Windows-first `udp-rollout-readiness.ps1` wrapper now passes again after the rollout-validation summary-version sync.
- The Windows-first `udp-release-readiness-burndown.ps1` wrapper remains intentionally fail closed when required release-gate or compatible-host rollout-readiness evidence is missing or drifted.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, and release-facing workflow lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, summary, and compatible-host catalog surfaces
