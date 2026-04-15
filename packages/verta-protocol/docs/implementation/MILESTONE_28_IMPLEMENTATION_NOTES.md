# Milestone 28 Implementation Notes

## Scope

Milestone 28 keeps the bridge topology and Remnawave-facing bridge-domain contracts unchanged.
The work stays inside the existing datagram transport, validation, conformance, workflow, and staged-rollout evidence seams.

## Normative anchors

- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`
  - Sections 10, 11, 12, 15, and 18.3
- `docs/spec/verta_security_test_and_interop_plan_v0_1.md`
  - Compatible-host interoperability evidence, malformed-input expectations, and staged rollout evidence
- `docs/spec/verta_threat_model_v0_1.md`
  - Fail closed, avoid silent fallback after negotiated datagram selection, and keep rollout evidence explicit

## What changed

- the reusable operator-verdict schema now advances to version `7` across host-level comparison, cross-host matrix, and release-workflow consumers:
  - `comparison_schema = "udp_rollout_operator_verdict"`
  - `comparison_schema_version = 7`
  - host comparison and matrix consumers now fail closed on upstream summary-version or schema drift instead of accepting stale rollout artifacts
  - rollout-validation evidence now projects stable degradation and surface-accounting fields:
    - `degradation_surface_passed`
    - `surface_count_total`
    - `surface_count_passed`
    - `surface_count_failed`
    - `failed_surface_keys`
- `udp_rollout_compare` now treats degradation and shutdown evidence as decision-bearing rollout inputs instead of only checking required-summary presence.
- `udp_rollout_matrix` now fails closed unless every host summary matches the shared operator-verdict schema, carries the expected required-input set, and keeps degradation evidence green.
- a new release-workflow summary consumer now exists:
  - `crates/ns-testkit/examples/udp_release_workflow.rs`
  - `scripts/udp-release-workflow.ps1`
  - `scripts/udp-release-workflow.sh`
  It consumes readiness and staged-rollout matrix summaries and emits one fail-closed release-workflow verdict on the same operator-verdict schema vocabulary.
- `.github/workflows/udp-optional-gates.yml` now adds another workflow-backed release surface:
  - a Linux release-workflow lane that downloads readiness and staged-rollout matrix artifacts and emits `udp-release-workflow-summary.json`
- maintained workflow summaries now surface reusable release-review facts instead of leaning on noisier per-host timing-style details:
  - `missing_required_inputs`
  - `hosts_with_degradation_hold`
  - `queue_guard_limiting_path_counts`
  - `affected_host_count_by_reason_family`
  - release-workflow matrix verdict and gate-state counts
- reviewed malformed-input coverage now grows with:
  - `WC-UDP-FLOW-CLOSE-NONCANONFLOW-032`
  - `WC-UDP-STREAM-CLOSE-NONCANONFLOW-033`
  Those fixtures now flow through conformance, corpus sync, and fuzz-regression directories.
- maintained public validation commands in `ns-clientd`, `nsctl`, and `ns-gatewayd` were re-audited against the shared comparison constants and now keep the same comparison-oriented schema/version and scope/profile semantics while milestone 28 adds explicit `ns-clientd validate-manifest` coverage for those fields.

## Verification lane notes

Milestone 28 keeps the existing Windows-first wrappers intact and broadens the release-workflow recipe with:

- `target/verta/udp-fuzz-smoke-summary.json`
- `target/verta/udp-perf-gate-summary.json`
- `target/verta/udp-interop-lab-summary.json`
- `target/verta/udp-rollout-validation-summary.json`
- `target/verta/udp-active-fuzz-summary.json`
- `target/verta/udp-rollout-comparison-summary.json`
- `target/verta/udp-rollout-matrix-summary.json`
- `target/verta/udp-release-workflow-summary.json`

The rollout-validation summary now also records:

- `degradation_surface_passed`
- `surface_count_total`
- `surface_count_passed`
- `surface_count_failed`
- `failed_surface_keys`

The maintained release-workflow recipe is now:

1. reviewed corpus sync
2. UDP smoke replay
3. UDP perf gate
4. UDP interop lab
5. UDP rollout-validation lab
6. UDP active fuzz on a compatible host when staged evidence is required
7. UDP rollout comparison
8. UDP rollout matrix for cross-host host-level review
9. UDP staged-rollout matrix when multiple staged compatible-host summaries are present
10. UDP release-workflow aggregation over readiness and staged-rollout matrices

That recipe remains opt-in.
It is not a default required PR gate.

## Explicit non-changes

- No bridge-domain contract changes
- No bridge topology changes
- No Remnawave fork or panel-internal coupling
- No new datagram backend choice beyond the existing H3-associated datagram path
- No `0-RTT`

## ADR status

No new ADR was required for milestone 28.

This milestone tightens release-workflow operator-verdict consistency, adds another workflow-backed release surface, and closes the maintained malformed-input coverage gap around non-canonical UDP close flow identifiers.
