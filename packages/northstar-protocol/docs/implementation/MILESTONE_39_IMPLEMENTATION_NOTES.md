# Milestone 39 Implementation Notes

Milestone 39 extends the datagram rollout toolchain from release-stability signoff toward release-candidate consolidation with broader deployment-grade evidence, while keeping Remnawave non-fork, bridge contracts unchanged, the session core transport-agnostic, and `0-RTT` disabled.

## Governing Inputs

- `docs/spec/northstar_wire_format_freeze_candidate_v0_1.md`
- `docs/spec/northstar_security_test_and_interop_plan_v0_1.md`
- `docs/spec/northstar_threat_model_v0_1.md`

## Scope

- keep Remnawave on the external bridge boundary
- keep bridge deployment topology unchanged
- keep transport selection, fallback, and rollout rules spec-driven and fail closed
- add one more workflow-backed datagram verification surface without changing Windows-first local wrapper expectations
- strengthen release-facing operator verdicts around exact compatible-host interop-catalog host-label accounting and release-candidate consolidation fail-closed behavior
- project MTU-ceiling negotiated-limit evidence into rollout-validation and downstream release-facing summaries
- grow the maintained reviewed UDP corpus around non-canonical outer frame-length varints without widening parser behavior

## Implemented

- Added a workflow-backed Linux `release_candidate_consolidation` lane to `.github/workflows/udp-optional-gates.yml` plus `scripts/udp-release-candidate-consolidation.ps1` and `scripts/udp-release-candidate-consolidation.sh`.
- Added `crates/ns-testkit/examples/udp_release_candidate_consolidation.rs`, which consumes `release_stability_signoff` plus Linux, macOS, and Windows compatible-host interop catalogs and emits a fail-closed machine-readable operator verdict.
- Advanced the shared operator-verdict schema to version `18` across the release-facing verdict stack and carried explicit exact compatible-host interop-catalog host-label accounting into release-candidate consolidation.
- Synchronized rollout-validation summary version `15` and projected `mtu_ceiling_delivery_stable` into negotiated-limit validation and downstream release-facing decisions.
- Extended the maintained compatible-host interop profile set with `fallback-flow-guard-rejection`, backed by the existing live UDP wrong-fallback-flow rejection test instead of inventing new transport behavior.
- Added reviewed malformed outer frame-length fixtures `WC-UDP-OPEN-NONCANONFRAMELEN-073`, `WC-UDP-OK-NONCANONFRAMELEN-074`, `WC-UDP-STREAM-OPEN-NONCANONFRAMELEN-075`, and `WC-UDP-STREAM-ACCEPT-NONCANONFRAMELEN-076`, then synchronized them into the maintained corpora and conformance suite.
- Kept wire behavior fail closed for non-canonical outer frame-length varints and aligned the reviewed fixture expectations to the actual decoder result (`NonCanonicalVarint`) instead of widening parser behavior.
- Preserved bridge-domain, adapter, and bridge-app boundaries; milestone 39 does not widen Remnawave or bridge contracts.

## Verification Notes

- The maintained fixture generator, corpus sync, and wire conformance suite all pass with the `073-076` reviewed malformed-input set included.
- The release-facing example chain through `udp_release_candidate_consolidation` now passes targeted tests on shared operator-verdict schema version `18`.
- The promoted live evidence surfaces `loopback_h3_datagrams_accept_payload_at_effective_mtu_ceiling` and `loopback_udp_fallback_rejects_wrong_flow_id_with_protocol_violation_close` both pass and now back maintained rollout or interop evidence instead of remaining stand-alone checks.
- The Windows-first `udp-release-candidate-consolidation.ps1` wrapper remains intentionally fail closed when required release-stability or compatible-host interop-catalog evidence is missing, partial, or schema-drifted.

## Deferred

- broader WAN or real cross-network datagram interoperability beyond deterministic lab and compatible-host lanes
- default-on CI enforcement for UDP fuzz, perf, interop, and release-facing workflow lanes
- larger maintained UDP corpora and longer-running fuzz campaigns
- richer operator rollout workflow beyond the current CLI, wrapper, summary, and compatible-host catalog surfaces
