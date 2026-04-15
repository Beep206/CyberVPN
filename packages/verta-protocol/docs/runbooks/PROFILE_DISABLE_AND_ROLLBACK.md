# Profile Disable And Rollback

## Trigger

Use this runbook when a profile must be disabled or when an active rollout must be rolled back to a safer transport posture, including:

- upstream lifecycle transition to `disabled`, `revoked`, or equivalent denial state
- emergency need to force the maintained stream-fallback path
- transport behavior that requires datagram rollback before broader release work continues

## Safe State

- Prefer explicit deny or explicit stream fallback over silent datagram degradation.
- Keep release promotion blocked until the disable or rollback drill is green again.
- Preserve interop, chaos, and release evidence artifacts for diagnosis.

## Immediate Actions

1. Run the profile-disable drill against the supported upstream environment:
   - `bash scripts/operator-profile-disable-drill.sh`
2. Run the maintained rollback drill:
   - `bash scripts/operator-rollout-rollback-drill.sh`
3. Confirm that:
   - bootstrap, refresh, and token issuance deny correctly after lifecycle disable
   - explicit `udp-blocked` fallback still round-trips without silent fallback drift
4. Keep the deployment in the safer posture until the blocking reason is understood and documented.
5. Re-enable broader rollout only after both drill surfaces return `ready`.

## Validation

- `bash scripts/operator-profile-disable-drill.sh`
- `bash scripts/operator-rollout-rollback-drill.sh`
- `bash scripts/phase-l-operator-readiness.sh`

## Recoverability

- Recoverable artifacts: operator runbooks, release evidence, shared durable bridge state, packet captures from rollback drill artifacts.
- Non-recoverable artifacts: disabled or revoked device grants that must be re-bootstraped, rollout state that was advanced without preserved evidence.
- Rotation required: no.
- Re-registration required: yes for affected disabled or revoked device grants.

## Escalation

Escalate if either condition holds:

- lifecycle disable denies do not stay consistent across bootstrap, refresh, and token exchange
- rollback drill cannot prove explicit fallback with retained artifacts
