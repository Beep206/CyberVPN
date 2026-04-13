# Milestone 27 Implementation Notes

## Scope

Milestone 27 keeps the bridge topology and Remnawave-facing bridge-domain contracts unchanged.
The work stays inside the existing datagram transport, validation, conformance, fuzz, workflow, and rollout-decision seams.

## Normative anchors

- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
  - Sections 10, 11, 12, 15, and 18.3
- `docs/spec/northstar_security_test_and_interop_plan_v0_1.md`
  - Compatible-host interoperability evidence, malformed-input expectations, and staged rollout evidence
- `docs/spec/northstar_threat_model_v0_1.md`
  - Fail closed, avoid silent fallback after negotiated datagram selection, and keep rollout evidence explicit

## What changed

- the reusable operator-verdict schema now advances in a comparison-friendly way across host-level and matrix-level consumers:
  - `comparison_schema = "udp_rollout_operator_verdict"`
  - `comparison_schema_version = 6`
  - fail-closed summary-version checks now gate consumed smoke, perf, interop, rollout-validation, and active-fuzz artifacts
  - stable `required_input_count`, `required_input_present_count`, `required_input_passed_count`, `blocking_reason_count`, and `advisory_reason_count` fields now exist alongside the existing required-summary state
  - stable `blocking_reason_key_counts` now exists alongside host-specific `blocking_reasons` and `blocking_reason_family_counts`
- `udp_rollout_matrix` now consumes the same operator-verdict shape that `udp_rollout_compare` emits for both `readiness` and `staged_rollout` profiles instead of inferring host readiness from older summary-local fields.
- rollout readiness now blocks on maintained longer-impairment recovery and shutdown-sequence stability instead of only checking a narrower sticky-selection surface.
- `.github/workflows/udp-optional-gates.yml` now adds another workflow-backed release-candidate evidence surface:
  - a Linux staged-rollout matrix lane that consumes Linux and macOS staged-rollout comparison artifacts and emits a machine-readable cross-host staged-rollout verdict
- Windows-first local ergonomics stay intact while the workflow-backed matrix path becomes reusable through:
  - `scripts/udp-rollout-matrix.ps1`
  - `scripts/udp-rollout-matrix.sh`
- reviewed malformed-input coverage now grows with:
  - `WC-UDP-OK-NONCANONFLOW-030`
  - `WC-UDP-STREAM-PACKET-NONCANONLEN-031`
  Those fixtures now flow through conformance, corpus sync, and fuzz-regression directories.
- maintained public validation commands in `ns-clientd`, `nsctl`, and `ns-gatewayd` were re-audited against the shared comparison constants in `ns-core`; milestone 27 does not add new CLI semantics because the maintained schema/version and scope/profile outputs were already aligned.

## Verification lane notes

Milestone 27 keeps the existing Windows-first wrappers intact and broadens the release-candidate staged-rollout recipe with:

- `target/northstar/udp-fuzz-smoke-summary.json`
- `target/northstar/udp-perf-gate-summary.json`
- `target/northstar/udp-interop-lab-summary.json`
- `target/northstar/udp-rollout-validation-summary.json`
- `target/northstar/udp-active-fuzz-summary.json`
- `target/northstar/udp-rollout-comparison-summary.json`
- `target/northstar/udp-rollout-matrix-summary.json`

The rollout-validation summary now also records:

- `passed_command_count`
- `failed_command_count`
- `shutdown_sequence_stable`

The maintained release-candidate staged-rollout recipe is now:

1. reviewed corpus sync
2. UDP smoke replay
3. UDP perf gate
4. UDP interop lab
5. UDP rollout-validation lab
6. UDP active fuzz on a compatible host when staged evidence is required
7. UDP rollout comparison
8. UDP rollout matrix for cross-host host-level review
9. UDP staged-rollout matrix when multiple staged compatible-host summaries are present

That recipe remains opt-in.
It is not a default required PR gate.

## Explicit non-changes

- No bridge-domain contract changes
- No bridge topology changes
- No Remnawave fork or panel-internal coupling
- No new datagram backend choice beyond the existing H3-associated datagram path
- No `0-RTT`

## ADR status

No new ADR was required for milestone 27.

This milestone tightens release-candidate operator-verdict consistency, adds another workflow-backed cross-host staged-rollout surface, and closes the maintained malformed-input coverage gap around existing datagram behavior.
