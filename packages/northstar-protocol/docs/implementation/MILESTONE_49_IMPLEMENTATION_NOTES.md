# Milestone 49 Implementation Notes

## Summary

Milestone 49 adds the `Phase I` deployment-reality decision gate for the non-fork Remnawave path.

The new lane lives in:

- `crates/ns-testkit/examples/remnawave_supported_upstream_deployment_reality_verification.rs`
- `scripts/remnawave-supported-upstream-deployment-reality-verify.ps1`
- `scripts/remnawave-supported-upstream-deployment-reality-verify.sh`

It consumes milestone-47 and milestone-48 summaries as required inputs, re-checks the configured supported upstream account through the maintained HTTP adapter, validates the deployment-shaped bridge runtime over the shared-durable service-backed store path, and emits one fail-closed operator-facing summary.

## What The New Gate Proves

- The maintained deployment-shaped bridge runtime can sit over the shared-durable service-backed store path while using the maintained `HttpRemnawaveAdapter`.
- Internal store-service health remains authenticated and must report `SharedDurable`.
- Remote-store auth mismatch fails closed.
- Unauthorized primary store endpoints do not silently fail over to secondary endpoints.
- Public Bridge control-plane issuance still works over the maintained deployment-shaped runtime.

## What It Does Not Prove

- Transport or datagram readiness.
- WAN-grade interoperability.
- That a real supported deployment has already passed the gate in repository history.
- Every remote/shared backend variant beyond the maintained shared-durable service-backed topology path.

The deployment-reality summary is intentionally `control_plane_issuance_only = true`.

## Fail-Closed Taxonomy

The milestone-49 summary is designed to fail closed on:

- missing environment
- unsupported upstream version
- upstream auth failure
- timeout
- response-shape drift
- webhook-signature failure
- lifecycle drift
- reconcile lag
- stale snapshot state
- replay-sensitive inconsistency
- remote-store auth mismatch
- remote backend unavailability
- health-check drift
- startup ordering failure
- partial failover
- incompatible contract conditions

## Boundary Notes

- No public `/v0/*` Bridge API behavior was widened.
- Remnawave remains external and non-fork.
- Session core remains transport-agnostic.
- `0-RTT` remains disabled.

## Phase I Status

Milestone 49 gives `Phase I` its planned deployment-reality decision gate.

`Phase I` is only honestly complete after a real supported deployment actually passes this lane.
Until that operator-run evidence exists, `Phase I` remains blocked by missing real deployment proof rather than missing harness code.
