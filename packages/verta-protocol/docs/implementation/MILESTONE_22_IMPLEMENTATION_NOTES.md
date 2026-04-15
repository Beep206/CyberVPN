# Milestone 22 Implementation Notes

## Scope

Milestone 22 promotes the datagram slice from deployment-candidate operator validation toward broader compatible-host interoperability evidence and stronger rollout discipline.

Bridge topology, bridge-domain contracts, and the Remnawave integration boundary remain intentionally unchanged in this milestone.

## Normative anchors

- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`
  - Sections 10, 11, 12, 15, and 18.3
- `docs/spec/verta_security_test_and_interop_plan_v0_1.md`
  - Named impairment suites, malformed-input expectations, and staged interoperability evidence
- `docs/spec/verta_threat_model_v0_1.md`
  - Fail closed, avoid silent fallback after negotiated datagram selection, and keep rollout evidence explicit

## What changed

- `ns-clientd`, `nsctl`, and `ns-gatewayd` now all emit consistent human-readable and machine-readable startup or negotiated datagram-contract output from their maintained public validation commands instead of relying on text-only ad hoc prints.
- `ns-clientd`, `nsctl`, and `ns-gatewayd` now keep the same fail-closed mismatch facts across startup and negotiated validation surfaces: signed datagram intent, rollout stage, carrier support, negotiated datagram mode, and UDP limits.
- `ns-carrier-h3` now strengthens repeated queue-pressure validation so the queue-full guard stays low-cardinality and the same datagram-selected flow proves it can recover after multiple drains without silently degrading into stream fallback.
- the maintained delayed-delivery plus short-black-hole live datagram test now covers one more repeated impairment-and-recovery cycle before clean shutdown, keeping the no-silent-fallback rule explicit for longer degradation windows.
- reviewed corpus growth now includes truncated `UDP_FLOW_CLOSE` and truncated `UDP_STREAM_CLOSE` regression fixtures so control-frame and fallback-frame decoding remain aligned with the hardened UDP close and rejection paths.
- `ns-testkit` now exposes rollout-facing summary fields from the existing smoke and perf summaries through `udp_rollout_validation_lab`, including queue-saturation threshold pass/fail facts instead of forcing operators to interpret multiple output files manually.
- the repo now includes `scripts/udp-rollout-readiness.ps1` and `scripts/udp-rollout-readiness.sh`, which combine corpus sync, smoke replay, the UDP perf gate, the interop harness, and the rollout-validation harness into one documented compatible-host readiness recipe with fail-evident summary paths.
- `.github/workflows/udp-optional-gates.yml` now includes a compatible-host macOS rollout-readiness lane alongside the Linux rollout-readiness and Windows rollout-validation lanes while preserving the existing Windows-first local wrappers and machine-readable artifacts.

## Verification lane notes

Milestone 22 keeps the existing optional UDP verification lane intact and broadens the rollout-facing summary story with:

- `target/verta/udp-fuzz-smoke-summary.json`
- `target/verta/udp-perf-gate-summary.json`
- `target/verta/udp-interop-lab-summary.json`
- `target/verta/udp-rollout-validation-summary.json`

The new `udp-rollout-readiness.*` wrappers fail if any requested summary is missing and print the resolved summary paths so operators can archive or compare them during staged rollout.

The compatible-host workflow now has:

- the existing Linux interop lane
- the existing Linux rollout-readiness lane
- a new macOS rollout-readiness lane with the same summary set
- the existing Windows rollout-validation lane
- the existing optional Linux active-fuzz lane

These remain opt-in verification paths rather than default required PR gates.

## Explicit non-changes

- No bridge-domain contract changes
- No bridge topology changes
- No Remnawave fork or panel-internal coupling
- No new datagram semantics beyond the frozen spec and prior implementation notes
- No `0-RTT`

## ADR status

No new ADR was required for milestone 22.

This milestone tightens public validation parity, rollout-readiness ergonomics, maintained compatible-host evidence, and rollout-facing summary discipline around existing behavior.
