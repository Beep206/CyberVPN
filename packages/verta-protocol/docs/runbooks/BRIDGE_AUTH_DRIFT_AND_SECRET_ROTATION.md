# Bridge Auth Drift And Secret Rotation

## Trigger

Use this runbook when bridge-to-store or bridge-to-upstream auth no longer matches the expected deployment configuration, including:

- `upstream_auth_failure_detected`
- remote store auth mismatch
- unauthorized primary store access
- operator-confirmed token or secret rotation event

## Safe State

- Fail closed on bridge auth and store auth mismatches.
- Do not bypass store-service auth to keep traffic flowing.
- Do not rewrite deployment secrets on only one side of a shared-durable deployment.

## Immediate Actions

1. Confirm whether the failing credential is upstream API auth, webhook signature material, or store-service auth.
2. Rotate credentials atomically for the relevant boundary instead of patching one node at a time.
3. Re-run the exact maintained verification lane for the affected boundary:
   - supported upstream: `bash scripts/remnawave-supported-upstream-verify.sh`
   - lifecycle/profile-disable: `bash scripts/operator-profile-disable-drill.sh`
4. Confirm that failover or secondary store endpoints did not silently mask the primary auth drift.
5. Record the new secret version and deployment label in operator change notes.

## Validation

- `bash scripts/remnawave-supported-upstream-verify.sh`
- `bash scripts/operator-profile-disable-drill.sh`

## Recoverability

- Recoverable artifacts: durable bridge store contents, release evidence, deployment labels, interop and rollout summaries.
- Non-recoverable artifacts: leaked credentials, webhook signatures or API tokens that were exposed outside the intended trust boundary.
- Rotation required: yes.
- Re-registration required: no.

## Escalation

Escalate if either condition holds:

- rotated credentials still produce auth failures on a clean rerun
- operators cannot determine whether the drift was configuration-only or credential compromise
