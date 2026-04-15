# Milestone 24 Implementation Notes

## Scope

Milestone 24 keeps the bridge topology and Remnawave-facing bridge-domain contracts unchanged.
The work stays inside the existing datagram transport, validation, conformance, fuzz, and rollout-verification seams.

## Normative anchors

- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`
  - Sections 10, 11, 12, 15, and 18.3
- `docs/spec/verta_security_test_and_interop_plan_v0_1.md`
  - Named impairment suites, malformed-input expectations, and staged interoperability evidence
- `docs/spec/verta_threat_model_v0_1.md`
  - Fail closed, avoid silent fallback after negotiated datagram selection, and keep rollout evidence explicit

## What changed

- `udp_rollout_compare` now supports two maintained profiles:
  - `readiness`
  - `staged_rollout`
- the `staged_rollout` profile now consumes the maintained smoke, perf, interop, rollout-validation, and active-fuzz summaries and emits stable blocking reasons instead of requiring operators to infer a verdict from wrapper failures.
- `udp_rollout_validation_lab` now projects normalized queue-guard headroom facts from the maintained perf thresholds:
  - `queue_guard_headroom_passed`
  - `queue_guard_headroom_band`
  - `queue_guard_rejection_path_passed`
  - `queue_guard_recovery_path_passed`
  - `queue_guard_burst_path_passed`
- `.github/workflows/udp-optional-gates.yml` now includes a compatible-host Linux staged-rollout lane that runs the maintained rollout-readiness recipe with active fuzz enabled and uploads both the active-fuzz and rollout-comparison summaries.
- maintained public validation commands in `ns-clientd`, `nsctl`, and `ns-gatewayd` now emit comparison-friendly fields in both text and JSON modes:
  - `comparison_family`
  - `comparison_label`
- the maintained live datagram coverage now keeps no-silent-fallback assertions explicit through an additional repeated queue-pressure cycle and through the post-close rogue-datagram path without accepting a silently opened fallback stream.
- reviewed corpus growth now includes:
  - `WC-UDP-OPEN-TRUNCATED-020`
  - `WC-UDP-DGRAM-NONCANONFLOW-021`
  - `WC-UDP-STREAM-CLOSE-BADCODE-022`
  Those fixtures now flow into conformance, corpus sync, and fuzz-regression directories.

## Verification lane notes

Milestone 24 keeps the existing Windows-first wrappers intact and broadens the compatible-host staged-rollout story with:

- `target/verta/udp-fuzz-smoke-summary.json`
- `target/verta/udp-perf-gate-summary.json`
- `target/verta/udp-interop-lab-summary.json`
- `target/verta/udp-rollout-validation-summary.json`
- `target/verta/udp-active-fuzz-summary.json`
- `target/verta/udp-rollout-comparison-summary.json`

The maintained compatible-host staged-rollout recipe is:

1. reviewed corpus sync
2. UDP smoke replay
3. UDP perf gate
4. UDP interop lab
5. UDP rollout-validation lab
6. UDP active fuzz
7. UDP rollout comparison with `--profile staged_rollout`

That recipe remains opt-in.
It is not a default required PR gate.

## Explicit non-changes

- No bridge-domain contract changes
- No bridge topology changes
- No Remnawave fork or panel-internal coupling
- No new datagram backend choice beyond the existing H3-associated datagram path
- No `0-RTT`

## ADR status

No new ADR was required for milestone 24.

This milestone tightens staged-rollout comparison discipline, machine-readable operator-facing validation output, maintained compatible-host evidence, and rollout-facing queue-guard projection around existing behavior.
