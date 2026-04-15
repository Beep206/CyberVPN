# Milestone 29 Implementation Notes

Milestone 29 extends the datagram rollout toolchain from release-workflow evidence to deployment-candidate signoff discipline without widening bridge-domain contracts or weakening the transport-agnostic session core.

## Governing Inputs

- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/verta_security_test_and_interop_plan_v0_1.md`
- `docs/spec/verta_threat_model_v0_1.md`

## Scope

- keep Remnawave on the non-fork bridge boundary
- keep the session core transport-agnostic
- keep `0-RTT` disabled
- extend operator-facing rollout evidence with a fail-closed deployment-signoff surface
- keep maintained CLI validation outputs stable and comparison-friendly across `ns-clientd`, `nsctl`, and `ns-gatewayd`

## Implemented

- Added `udp_deployment_signoff` plus PowerShell and Bash wrappers as a workflow-backed deployment-candidate signoff surface.
- Advanced the shared operator-verdict schema to version `8` across `udp_rollout_compare`, `udp_rollout_matrix`, `udp_release_workflow`, and deployment-signoff consumers.
- Made comparison, matrix, release-workflow, and deployment-signoff decisions fail closed on missing-input, degradation-hold, summary-version drift, schema-version drift, and blocking-reason accounting mismatches.
- Corrected rollout-validation evidence mapping so `clean_shutdown_stable` and `selected_datagram_lifecycle_stable` are projected from the maintained live datagram round-trip path instead of a mismatched degradation check.
- Extended maintained CLI validation outputs with stable `evidence_state`, `gate_state`, `verdict`, `missing_required_input_count`, `degradation_hold_count`, `blocking_reason_count`, `blocking_reason_key`, and `blocking_reason_family` fields in both text and JSON modes.
- Added reviewed malformed wire fixtures `WC-UDP-OPEN-NONCANONFLOW-034` and `WC-UDP-OPEN-NONCANONFLAGS-035` and synced them into the maintained UDP corpora.

## Verification Notes

- Deployment-signoff is intentionally fail closed when release-workflow evidence is missing or not ready, or when the compatible-host rollout-validation artifact is missing, drifted, or degraded.
- The local Windows-first verification path can prove that fail-closed posture even when compatible-host staged evidence is not present yet.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, release-workflow, or deployment-signoff lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, and summary surfaces
