# Milestone 31 Implementation Notes

Milestone 31 extends the datagram rollout toolchain from release-prep operator workflow toward release-candidate signoff discipline without widening bridge-domain contracts or weakening the transport-agnostic session core.

## Governing Inputs

- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/verta_security_test_and_interop_plan_v0_1.md`
- `docs/spec/verta_threat_model_v0_1.md`

## Scope

- keep Remnawave on the non-fork bridge boundary
- keep the session core transport-agnostic
- keep `0-RTT` disabled
- extend operator-facing rollout evidence with a fail-closed release-candidate signoff surface
- keep maintained CLI validation outputs stable and comparison-friendly across `ns-clientd`, `nsctl`, and `ns-gatewayd`

## Implemented

- Added `udp_release_candidate_signoff` plus PowerShell and Bash wrappers as a workflow-backed release-candidate signoff surface that consumes release-prep plus Windows rollout-readiness evidence.
- Advanced the shared operator-verdict schema to version `10` across `udp_rollout_compare`, `udp_rollout_matrix`, `udp_release_workflow`, `udp_deployment_signoff`, `udp_release_prep`, and `udp_release_candidate_signoff`.
- Added explicit `gate_state_reason`, `gate_state_reason_family`, and `required_input_unready_count` semantics across the shared operator-verdict summaries instead of leaving gate-state interpretation implicit or warning-shaped.
- Extended maintained `ns-clientd`, `nsctl`, and `ns-gatewayd` validation outputs with the same gate-state-reason and required-input-unready accounting fields in both text and JSON modes.
- Added the `policy-disabled-fallback` interoperable datagram profile to `udp_interop_lab`, projected `policy_disabled_fallback_surface_passed` plus explicit fallback-profile counts into the rollout summaries, and made downstream rollout consumers fail closed when that maintained fallback surface is absent or failed.
- Added reviewed malformed wire fixtures `WC-UDP-OPEN-IPV4LEN-038` and `WC-UDP-OPEN-BADTARGETTYPE-039` and synced them into the maintained UDP corpora and regression seeds.
- Added a workflow-backed Linux `release_candidate_signoff` lane that publishes machine-readable summary artifacts while preserving the existing Windows-first local wrappers.

## Verification Notes

- `udp_release_candidate_signoff` is intentionally fail closed when release-prep evidence is missing or not ready, when the Windows rollout-readiness summary is missing, drifted, or not ready, or when the maintained policy-disabled fallback interop surface does not pass.
- The local Windows-first verification path now proves that fail-closed posture by writing a machine-readable release-candidate signoff summary and exiting non-zero when only partial compatible-host evidence exists.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, release-workflow, deployment-signoff, release-prep, or release-candidate-signoff lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, and summary surfaces
