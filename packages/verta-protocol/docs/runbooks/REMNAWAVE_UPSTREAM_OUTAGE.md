# Remnawave Upstream Outage

## Trigger

Use this runbook when the bridge cannot obtain fresh upstream truth or when supported-upstream evidence surfaces any of these conditions:

- `upstream_unavailable_detected`
- `upstream_timeout_detected`
- `upstream_stale_detected`
- repeated bootstrap, refresh, or token failures that correlate with upstream health loss

## Safe State

- Keep Remnawave external and non-fork.
- Treat bridge truth as stale until the supported upstream path is fresh again.
- Deny new bootstrap, refresh, and token issuance if upstream freshness or auth can no longer be trusted.
- Preserve shared durable store state; do not delete replay or refresh data just to clear symptoms.

## Immediate Actions

1. Inspect the last machine-readable supported-upstream summary in `target/verta/remnawave-supported-upstream-summary.json`.
2. Confirm whether the failure is availability, timeout, or stale-snapshot drift.
3. Stop release promotion if the outage affects a release branch or `rc/**`.
4. Verify bridge health, store-service health, and Remnawave reachability separately before restarting anything.
5. Resume bridge traffic only after a fresh supported-upstream verification pass is green again.

## Validation

- `bash scripts/remnawave-supported-upstream-verify.sh`
- If lifecycle denial behavior also needs confirmation, run `bash scripts/operator-profile-disable-drill.sh`

## Recoverability

- Recoverable artifacts: shared durable store state, previous release evidence, last known valid manifest snapshots, webhook delivery records.
- Non-recoverable artifacts: upstream mutations that never reached Verta before the outage, operator assumptions based on stale panel state.
- Rotation required: no.
- Re-registration required: no.

## Escalation

Escalate if either condition holds:

- supported-upstream verification stays red after upstream health is restored
- stale or partial upstream state creates account-lifecycle ambiguity that operators cannot reconcile from webhook or refresh evidence alone
