# Milestone 48 Implementation Notes

## Scope

Milestone 48 advances `Phase I` from the first supported-upstream contact harness toward a real lifecycle and reconciliation pass for the maintained non-fork Remnawave path.

This slice intentionally stays inside:

- `crates/ns-testkit`
- `crates/ns-remnawave-adapter`
- existing `ns-bridge-api` and `ns-bridge-domain` behavior
- existing CLI/runtime validation surfaces

This slice intentionally does **not**:

- widen the frozen Bridge `/v0/*` API
- fork Remnawave
- move control-plane logic into panel internals
- couple lifecycle verification to the transport/session core

## What Was Added

- `crates/ns-testkit/examples/remnawave_supported_upstream_lifecycle_verification.rs`
  - primes a real supported-upstream active bridge flow
  - waits for an operator-driven lifecycle transition such as `disabled`, `revoked`, `expired`, or `limited`
  - verifies webhook signature rejection, positive webhook delivery, duplicate webhook replay rejection, and reconcile-hint shape
  - verifies that bootstrap manifest fetch, refresh manifest fetch, and token exchange fail closed after the lifecycle transition with the expected stable Bridge error code
  - emits a machine-readable fail-closed lifecycle summary
- `scripts/remnawave-supported-upstream-lifecycle-verify.ps1`
- `scripts/remnawave-supported-upstream-lifecycle-verify.sh`

## What This Milestone Proves

- the maintained bridge path can start from a real supported upstream account in an active state
- a real operator-driven lifecycle transition can be observed through the maintained adapter path
- verified webhook ingress remains fail closed for bad signatures and duplicate deliveries during the lifecycle pass
- manifest and token issuance can be re-checked after the transition on the same bridge runtime path without widening Bridge contracts
- lifecycle drift, reconcile lag, stale snapshot state, replay-sensitive inconsistency, auth failure, timeout, response-shape drift, and incompatible-contract conditions are surfaced explicitly for operators

## What This Milestone Still Does Not Prove

- a full deployment-grade remote/shared-store bridge reality pass against a supported upstream environment
- every production deployment detail of upstream webhook delivery beyond the current Bridge-side signature and timestamp gate
- broader upstream lifecycle automation such as operator-driven revoke/disable orchestration from inside Verta itself
- WAN-grade transport/runtime evidence; that remains outside `Phase I`

## Phase I Status After Milestone 48

Milestone 48 moves `Phase I` materially closer to exit because it closes the first real lifecycle and reconciliation verification lane over the maintained supported-upstream path.

`Phase I` is still **not complete** after milestone 48.

The main remaining blocker is milestone 49's deployment-grade bridge reality gate over the supported upstream path, especially for remote/shared-store and stronger deployment-shaped failure evidence.
