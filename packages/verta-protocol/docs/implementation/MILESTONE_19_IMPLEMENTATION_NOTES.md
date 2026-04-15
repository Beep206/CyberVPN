# Milestone 19 Implementation Notes

## Scope

Milestone 19 promotes the datagram slice from operator-grade local verification toward broader compatible-host interoperability evidence and rollout-readiness.

Bridge topology, bridge-domain contracts, and the Remnawave integration boundary remain intentionally unchanged in this milestone.

## Normative anchors

- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`
  - Sections 10, 11, 12, 15, and 18.3
- `docs/spec/verta_security_test_and_interop_plan_v0_1.md`
  - Named impairment suites for bounded loss, reordering, delay, MTU pressure, and UDP-blocked fallback
- `docs/spec/verta_threat_model_v0_1.md`
  - Degrade safely, fail closed, and avoid silent downgrade behavior on transport disruption

## What changed

- Added a compatible-host Linux interoperability lane in `.github/workflows/udp-optional-gates.yml` that runs the maintained UDP interop harness and uploads machine-readable summary artifacts.
- Expanded public datagram validation surfaces:
  - `apps/ns-clientd` now exposes negotiated datagram-contract validation through `validate-datagram-contract`
  - `apps/ns-gatewayd` now exposes startup datagram posture validation through `validate-datagram-startup`
- Tightened datagram shutdown and queue-pressure coverage so an established datagram selection remains sticky and does not silently degrade to stream fallback when the frozen spec does not allow it.
- Updated the active UDP fuzz wrappers to sync reviewed corpora before running active fuzz so compatible-host runs consume the maintained seed set.
- Extended the UDP perf gate with a machine-readable summary output for staged rollout review.

## Verification lane notes

The repo-native optional UDP lane now has three distinct operator-usable surfaces:

- Windows-first local wrappers for smoke, perf, and deterministic WAN-lab checks
- Compatible-host Linux workflow execution for the maintained interop harness
- Compatible-host active fuzz execution through the existing opt-in workflow input

These remain opt-in verification paths rather than default required PR gates.

## Explicit non-changes

- No bridge-domain contract changes
- No bridge topology changes
- No Remnawave fork or panel-internal coupling
- No new datagram semantics beyond the frozen spec and existing implementation notes
- No `0-RTT`

## ADR status

No new ADR was required for milestone 19.

This milestone tightens public validation, verification-lane discipline, and operator-facing evidence around existing datagram behavior.
