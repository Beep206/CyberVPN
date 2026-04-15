# Milestone 25 Implementation Notes

## Scope

Milestone 25 keeps the bridge topology and Remnawave-facing bridge-domain contracts unchanged.
The work stays inside the existing datagram transport, validation, conformance, fuzz, and rollout-verification seams.

## Normative anchors

- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`
  - Sections 10, 11, 12, 15, and 18.3
- `docs/spec/verta_security_test_and_interop_plan_v0_1.md`
  - Named impairment suites, malformed-input expectations, and staged interoperability evidence
- `docs/spec/verta_threat_model_v0_1.md`
  - Fail closed, avoid silent fallback after negotiated datagram selection, and keep rollout evidence explicit

## What changed

- `udp_rollout_compare` now emits one stable reusable operator-verdict schema across maintained profiles:
  - `comparison_schema = "udp_rollout_operator_verdict"`
  - `comparison_schema_version = 1`
  - `verdict_family = "udp_rollout_operator_decision"`
  - explicit `evidence_state`, `gate_state`, `required_summaries`, `considered_summaries`, `blocking_reason_details`, and `advisory_reasons`
- `udp_rollout_validation_lab` now projects additional sticky-selection and queue-path facts into its machine-readable summary:
  - `selected_datagram_lifecycle_passed`
  - `queue_guard_limiting_path`
- maintained public validation commands in `ns-clientd`, `nsctl`, and `ns-gatewayd` now emit comparison-friendly schema fields in both text and JSON modes:
  - `comparison_schema = "udp_rollout_validation_surface"`
  - `comparison_schema_version = 1`
- the maintained live datagram coverage now keeps no-silent-fallback assertions explicit through longer delayed-delivery plus short-black-hole shutdown and through repeated queue-pressure recovery on the same selected datagram flow.
- reviewed corpus growth now includes:
  - `WC-UDP-FLOW-CLOSE-NONCANONCODE-024`
  - `WC-UDP-STREAM-OPEN-NONCANONFLOW-025`
  - `WC-UDP-STREAM-ACCEPT-NONCANONFLOW-026`
  Those fixtures now flow into conformance, corpus sync, and fuzz-regression directories.
- `.github/workflows/udp-optional-gates.yml` now includes a workflow-backed Linux rollout-matrix lane that consumes compatible-host rollout-comparison artifacts and emits a machine-readable cross-host summary through `udp_rollout_matrix`.

## Verification lane notes

Milestone 25 keeps the existing Windows-first wrappers intact and broadens the compatible-host staged-rollout story with:

- `target/verta/udp-fuzz-smoke-summary.json`
- `target/verta/udp-perf-gate-summary.json`
- `target/verta/udp-interop-lab-summary.json`
- `target/verta/udp-rollout-validation-summary.json`
- `target/verta/udp-active-fuzz-summary.json`
- `target/verta/udp-rollout-comparison-summary.json`
- `target/verta/udp-rollout-matrix-summary.json`

The maintained staged-rollout recipe is now:

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

No new ADR was required for milestone 25.

This milestone tightens reusable operator-verdict schema discipline, public validation schema consistency, maintained cross-host rollout evidence, and reviewed malformed-input coverage around existing behavior.
