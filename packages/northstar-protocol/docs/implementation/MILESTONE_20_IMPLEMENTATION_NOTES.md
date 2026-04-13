# Milestone 20 Implementation Notes

## Scope

Milestone 20 promotes the datagram slice from compatible-host verification toward broader rollout-readiness evidence and more consistent public startup-validation surfaces.

Bridge topology, bridge-domain contracts, and the Remnawave integration boundary remain intentionally unchanged in this milestone.

## Normative anchors

- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
  - Sections 10, 11, 12, 15, and 18.3
- `docs/spec/northstar_security_test_and_interop_plan_v0_1.md`
  - Named impairment suites for bounded loss, reordering, delay, MTU pressure, and UDP-blocked fallback
- `docs/spec/northstar_threat_model_v0_1.md`
  - Degrade safely, fail closed, avoid silent fallback after negotiated datagram selection, and keep rollout evidence explicit

## What changed

- Added a shared H3 startup-contract resolver so client and gateway validation surfaces derive datagram posture from signed intent, rollout stage, and carrier availability through the same transport helper instead of separate CLI-only logic.
- Expanded public validation surfaces:
  - `ns-clientd` now has an explicit `validate-datagram-startup` surface in addition to manifest planning and negotiated-contract validation
  - `nsctl` now mirrors both client and gateway startup validation surfaces
  - `ns-gatewayd validate-hello` now supports UDP-shaped validation and labels manual readiness facts as `simulated_inputs=true`
- Added a broader compatible-host UDP rollout-readiness lane in `.github/workflows/udp-optional-gates.yml` that combines reviewed-corpus sync, UDP smoke replay, the maintained interop harness, the UDP perf gate, queue-pressure coverage, and post-close rejection coverage.
- Tightened verification discipline so enabled WAN-lab, perf, and active-fuzz lanes fail when their expected machine-readable summary artifacts are missing.
- Grew the maintained reviewed UDP corpus used by `control_frame_decoder` with hello, ping, and UDP control seeds, and updated active-fuzz wrappers to replay smoke before fuzzing and to include `control_frame_decoder`.
- Extended the maintained rollout-facing perf surface with `H3DatagramSocket.queue_recovery_send`, which keeps short saturation recovery observable without adding a new event family.

## Verification lane notes

The repo-native optional UDP lane now has four operator-usable surfaces:

- Windows-first local wrappers for smoke, perf, and deterministic WAN-lab checks
- Compatible-host Linux interop execution with uploaded machine-readable summaries
- Compatible-host Linux rollout-readiness execution that combines maintained smoke, perf, interop, queue-pressure, and shutdown checks
- Compatible-host active fuzz execution with reviewed-corpus sync, smoke replay, and a machine-readable summary artifact

These remain opt-in verification paths rather than default required PR gates.

## Explicit non-changes

- No bridge-domain contract changes
- No bridge topology changes
- No Remnawave fork or panel-internal coupling
- No new datagram semantics beyond the frozen spec and existing implementation notes
- No `0-RTT`

## ADR status

No new ADR was required for milestone 20.

This milestone tightens public validation consistency, compatible-host rollout evidence, and opt-in verification discipline around existing datagram behavior.
