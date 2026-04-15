# Milestone 21 Implementation Notes

## Scope

Milestone 21 promotes the datagram slice from compatible-host rollout evidence toward deployment-candidate operator validation and broader interoperability signals.

Bridge topology, bridge-domain contracts, and the Remnawave integration boundary remain intentionally unchanged in this milestone.

## Normative anchors

- `docs/spec/verta_wire_format_freeze_candidate_v0_1.md`
  - Sections 10, 11, 12, 15, and 18.3
- `docs/spec/verta_security_test_and_interop_plan_v0_1.md`
  - Named impairment suites, malformed-input expectations, and staged interoperability evidence
- `docs/spec/verta_threat_model_v0_1.md`
  - Fail closed, avoid silent fallback after negotiated datagram selection, and keep rollout evidence explicit

## What changed

- `nsctl` now carries `client_version` through its client planning and datagram validation surfaces instead of hardcoding a local default behind the public CLI surface.
- `ns-gatewayd` and `nsctl` now use explicit boolean `ArgAction::Set` parsing for `signed_datagram_enabled`, so fail-closed startup posture can be exercised consistently with explicit `true` and `false` inputs.
- `ns-clientd`, `nsctl`, and `ns-gatewayd` now all have maintained CLI-level tests for datagram startup or negotiated-contract validation paths, including fail-closed mismatch handling.
- `ns-carrier-h3` now asserts repeated queue-pressure saturation without silent fallback, not only a single queue-full event.
- the maintained delayed-delivery and short-black-hole live datagram test now covers a prolonged degradation cycle with repeated recovery while preserving the no-silent-fallback rule through shutdown.
- `ns-testkit` now provides `udp_rollout_validation_lab`, a machine-readable compatible-host rollout-validation harness that exercises maintained CLI/startup surfaces plus sticky datagram degradation and shutdown checks.
- `.github/workflows/udp-optional-gates.yml` now includes a Windows compatible-host rollout-validation lane that uploads a dedicated JSON summary artifact while keeping the existing Windows-first wrappers and prior summary artifacts intact.
- reviewed UDP corpus growth now includes a valid MTU-boundary datagram fixture plus a truncated datagram regression fixture, and both are synchronized into the maintained fuzz corpus and conformance coverage.

## Verification lane notes

Milestone 21 keeps the existing optional UDP verification lane intact and adds one more machine-readable surface:

- `target/verta/udp-rollout-validation-summary.json`

That summary records whether the maintained CLI/startup surfaces, repeated queue-pressure checks, prolonged impairment checks, post-close rejection checks, and clean shutdown checks all passed on the current host.

The compatible-host workflow now has:

- the existing Linux interop lane
- the existing Linux rollout-readiness lane
- the existing Linux active-fuzz lane
- a Windows rollout-validation lane with a dedicated JSON summary

These remain opt-in verification paths rather than default required PR gates.

## Explicit non-changes

- No bridge-domain contract changes
- No bridge topology changes
- No Remnawave fork or panel-internal coupling
- No new datagram semantics beyond the frozen spec and prior implementation notes
- No `0-RTT`

## ADR status

No new ADR was required for milestone 21.

This milestone tightens public validation parity, compatible-host rollout evidence, and maintained datagram regression coverage around existing behavior.
