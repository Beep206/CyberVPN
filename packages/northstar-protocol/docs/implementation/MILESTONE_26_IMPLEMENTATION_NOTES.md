# Milestone 26 Implementation Notes

## Scope

Milestone 26 keeps the bridge topology and Remnawave-facing bridge-domain contracts unchanged.
The work stays inside the existing datagram transport, validation, conformance, fuzz, workflow, and rollout-decision seams.

## Normative anchors

- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
  - Sections 10, 11, 12, 15, and 18.3
- `docs/spec/northstar_security_test_and_interop_plan_v0_1.md`
  - Compatible-host interoperability evidence, malformed-input expectations, and staged rollout evidence
- `docs/spec/northstar_threat_model_v0_1.md`
  - Fail closed, avoid silent fallback after negotiated datagram selection, and keep rollout evidence explicit

## What changed

- the reusable operator-verdict schema is now shared across host-level rollout comparison and cross-host rollout-matrix summaries through:
  - `comparison_schema = "udp_rollout_operator_verdict"`
  - `comparison_schema_version = 4`
  - `verdict_family = "udp_rollout_operator_decision"`
  - explicit `decision_scope`, `decision_label`, `required_inputs`, `considered_inputs`, and stable blocking-reason details
- `udp_rollout_validation_lab` now records stronger lifecycle evidence for operator review:
  - `summary_version = 4`
  - `longer_impairment_recovery_stable`
  - `clean_shutdown_stable` now reuses the repeated bounded-loss degradation path instead of a simple happy-path round trip
- maintained public validation commands in `ns-clientd`, `nsctl`, and `ns-gatewayd` now emit the same comparison-friendly metadata in both text and JSON modes:
  - `comparison_schema = "udp_rollout_validation_surface"`
  - `comparison_schema_version = 1`
  - `comparison_scope = "surface"`
  - `comparison_profile = "validation_surface"`
- reviewed malformed-input coverage now grows with:
  - `WC-UDP-DGRAM-NONCANONFLAGS-027`
  - `WC-UDP-STREAM-CLOSE-NONCANONCODE-028`
  - `WC-UDP-OK-NONCANONPAYLOAD-029`
  Those fixtures now flow into conformance, corpus sync, and fuzz-regression directories.
- `.github/workflows/udp-optional-gates.yml` now adds another compatible-host staged-rollout surface:
  - a macOS staged-rollout lane with active fuzz, machine-readable comparison output, and fail-evident summary artifact checks

## Verification lane notes

Milestone 26 keeps the existing Windows-first wrappers intact and broadens the compatible-host beta-candidate rollout story with:

- `target/northstar/udp-fuzz-smoke-summary.json`
- `target/northstar/udp-perf-gate-summary.json`
- `target/northstar/udp-interop-lab-summary.json`
- `target/northstar/udp-rollout-validation-summary.json`
- `target/northstar/udp-active-fuzz-summary.json`
- `target/northstar/udp-rollout-comparison-summary.json`
- `target/northstar/udp-rollout-matrix-summary.json`

The maintained beta-candidate rollout recipe is now:

1. reviewed corpus sync
2. UDP smoke replay
3. UDP perf gate
4. UDP interop lab
5. UDP rollout-validation lab
6. UDP active fuzz on a compatible host when staged evidence is required
7. UDP rollout comparison
8. UDP rollout matrix summary for cross-host operator review

That recipe remains opt-in.
It is not a default required PR gate.

## Explicit non-changes

- No bridge-domain contract changes
- No bridge topology changes
- No Remnawave fork or panel-internal coupling
- No new datagram backend choice beyond the existing H3-associated datagram path
- No `0-RTT`

## ADR status

No new ADR was required for milestone 26.

This milestone tightens reusable operator-verdict schema discipline, summary-layer lifecycle evidence, compatible-host staged-rollout coverage, and reviewed malformed-input coverage around the existing datagram behavior.
