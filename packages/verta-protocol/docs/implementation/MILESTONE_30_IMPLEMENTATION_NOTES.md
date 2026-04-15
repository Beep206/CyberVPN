# Milestone 30 Implementation Notes

Milestone 30 extends the datagram rollout toolchain from deployment-candidate signoff toward release-prep operator workflow without widening bridge-domain contracts or weakening the transport-agnostic session core.

## Governing Inputs

- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/verta_security_test_and_interop_plan_v0_1.md`
- `docs/spec/verta_threat_model_v0_1.md`

## Scope

- keep Remnawave on the non-fork bridge boundary
- keep the session core transport-agnostic
- keep `0-RTT` disabled
- extend operator-facing rollout evidence with a fail-closed release-prep surface
- keep maintained CLI validation outputs stable and comparison-friendly across `ns-clientd`, `nsctl`, and `ns-gatewayd`

## Implemented

- Added `udp_release_prep` plus PowerShell and Bash wrappers as a workflow-backed release-prep surface that consumes deployment-signoff plus Linux, macOS, and Windows rollout-validation evidence.
- Advanced the shared operator-verdict schema to version `9` across `udp_rollout_compare`, `udp_rollout_matrix`, `udp_release_workflow`, `udp_deployment_signoff`, and `udp_release_prep`.
- Added explicit required-input missing/failed counts plus blocking-reason key/family counts across the shared operator-verdict summaries.
- Tightened operator-verdict evidence-state handling so comparison, matrix, release-workflow, deployment-signoff, and release-prep all fail closed when consumed upstream evidence is parse-invalid, contract-invalid, stale-versioned, or otherwise incomplete.
- Extended maintained `ns-clientd`, `nsctl`, and `ns-gatewayd` validation outputs with stable required-input accounting fields in both text and JSON modes.
- Added reviewed malformed wire fixtures `WC-UDP-OPEN-NONCANONTIMEOUT-036` and `WC-UDP-OK-NONCANONTIMEOUT-037` and synced them into the maintained UDP corpora and regression seeds.
- Added a workflow-backed Linux `release_prep` lane that publishes machine-readable summary artifacts while preserving the existing Windows-first local wrappers.

## Verification Notes

- `udp_release_prep` is intentionally fail closed when deployment-signoff evidence is missing or not ready, or when Linux, macOS, or Windows rollout-validation artifacts are missing or drifted.
- The local Windows-first verification path now proves that fail-closed posture by writing a machine-readable release-prep summary and exiting non-zero when only partial host evidence exists.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, release-workflow, deployment-signoff, or release-prep lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, and summary surfaces
