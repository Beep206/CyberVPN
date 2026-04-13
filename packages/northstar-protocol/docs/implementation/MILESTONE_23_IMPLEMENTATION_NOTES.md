# Milestone 23 Implementation Notes

## Scope

Milestone 23 keeps the bridge topology and Remnawave-facing bridge-domain contracts unchanged.
The work stays inside the existing datagram transport, validation, conformance, and rollout-verification seams.

## Implemented

- Added a compatible-host Windows UDP rollout-readiness lane in `.github/workflows/udp-optional-gates.yml` using the existing Windows-first `scripts/udp-rollout-readiness.ps1` wrapper.
- Promoted `crates/ns-testkit/examples/udp_rollout_compare.rs` into the maintained staged-rollout comparison surface.
  - It consumes the existing smoke, perf, interop, and rollout-validation summaries.
  - It emits a single machine-readable verdict at `target/northstar/udp-rollout-comparison-summary.json` by default.
- Extended `crates/ns-testkit/examples/udp_rollout_validation_lab.rs` so staged rollout review now includes:
  - `sticky_selection_surface_passed`
  - `queue_saturation_surface_passed`
  - `queue_saturation_worst_case`
  - `queue_saturation_worst_utilization_pct`
  - `rollout_surface_passed`
- Extended `scripts/udp-rollout-readiness.ps1` and `scripts/udp-rollout-readiness.sh` so the maintained rollout recipe now runs:
  1. corpus sync
  2. UDP smoke replay
  3. UDP perf gate
  4. UDP interop lab
  5. UDP rollout-validation lab
  6. UDP rollout comparison
- Tightened maintained public CLI validation outputs in `apps/ns-clientd`, `apps/nsctl`, and `apps/ns-gatewayd`.
  - Success and mismatch paths now emit consistent `validation_result=valid|invalid` text output.
  - The same surfaces now emit consistent JSON `validation_result` fields plus stable `error_class` and `error_message` fields on fail-closed mismatch paths.
  - Boolean CLI inputs now accept both explicit `=false` or `=true` values and the previous short `--flag` form.
- Grew the maintained reviewed UDP corpus with:
  - `WC-UDP-OK-TRUNCATED-018`
  - `WC-UDP-STREAM-ACCEPT-TRUNCATED-019`
  Those seeds now flow into conformance, corpus sync, and fuzz-regression directories.

## Non-Changes

- No bridge spec, bridge HTTP contract, or Remnawave adapter contract change was made.
- No new ADR was required.
- No new datagram backend choice was introduced.
- `0-RTT` remains disabled.
- Session core remains transport-agnostic.

## Operator-Facing Outcome

Milestone 23 does not claim deployment-grade WAN interoperability yet.
It does make staged datagram rollout review more reusable:

- one more compatible-host readiness lane exists
- the maintained wrappers now produce one comparison verdict per host or lane
- public CLI validation commands now fail clearly in both text and JSON modes
- queue saturation evidence is normalized against maintained thresholds rather than raw host timings
