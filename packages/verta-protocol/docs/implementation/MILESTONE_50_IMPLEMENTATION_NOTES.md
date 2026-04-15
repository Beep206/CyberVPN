# Milestone 50 Implementation Notes

## Summary

Milestone 50 adds the `Phase I` operator signoff lane for the non-fork Remnawave path.

The new lane lives in:

- `crates/ns-testkit/examples/remnawave_supported_upstream_phase_i_signoff.rs`
- `scripts/remnawave-supported-upstream-phase-i-signoff.ps1`
- `scripts/remnawave-supported-upstream-phase-i-signoff.sh`

It consumes the milestone-47 supported-upstream summary, the milestone-48 lifecycle summary, and the milestone-49 deployment-reality summary, checks that the three lanes still agree on deployment identity and scope, and emits one fail-closed `Phase I` signoff summary.

## What Was Added

- a machine-readable `Phase I` operator signoff summary
- a Windows-first plus Bash wrapper that runs the maintained milestone-47, milestone-48, milestone-49, and milestone-50 chain in order and clears stale per-lane summaries before each run
- wrapper behavior that prefers an explicitly provided non-local `VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_*` environment and only falls back to the local helper when that environment is incomplete
- optional `VERTA_SUPPORTED_UPSTREAM_ENABLE_COMMAND` and `VERTA_SUPPORTED_UPSTREAM_DISABLE_COMMAND` hooks so operator-managed external deployments can drive account enable or disable transitions without reintroducing local-only helper assumptions
- consistency checks for:
  - supported deployment label presence
  - prior-lane summary presence
  - prior-lane ready/pass state
  - supported-upstream base URL agreement
  - expected account-id agreement across lifecycle and deployment lanes
  - upstream source-version agreement
  - explicit `control_plane_issuance_only = true` confirmation from the deployment-reality lane

## What It Proves

- `Phase I` now has a single operator-facing closure surface instead of only separate milestone-47/48/49 gates
- the maintained supported-upstream chain can be consumed as one fail-closed signoff decision
- closure is only recommended when all prior supported-upstream lanes pass together and stay deployment-consistent
- the maintained wrapper chain can target either the local supported-staging helper path or a real external supported-upstream deployment without widening bridge or session contracts

## What It Does Not Prove

- that a real supported deployment has already passed the chain in repository history
- transport or datagram readiness
- WAN-grade interoperability
- every remote/shared backend variant beyond the maintained shared-durable service-backed topology path

## Exact Blockers In This Run

No real supported deployment was available in this local run.

The signoff lane therefore remains blocked on missing operator-supplied environment and deployment identity, specifically:

- `VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL`
- `VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN`
- `VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT`
- `VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_SIGNATURE`
- `VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID`
- `VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_STORE_AUTH_TOKEN`
- `VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_LABEL`

## Boundary Notes

- No public `/v0/*` Bridge API behavior was widened.
- Remnawave remains external and non-fork.
- The summary stays control-plane and deployment scoped.
- Session core remains transport-agnostic.
- `0-RTT` remains disabled.

## Phase I Status

Milestone 50 adds the honest `Phase I` signoff surface and the operator-run wrapper chain.

`Phase I` is still only complete after a real supported deployment actually passes milestones 47, 48, 49, and 50 together.
In this repository run, `Phase I` remains blocked by missing real deployment evidence rather than missing harness code.
