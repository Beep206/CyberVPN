# Recovery Boundaries

Verta recovery is intentionally bounded. `Phase L` does not promise “fix everything in place”; it documents which artifacts are safe to preserve, which actions require credential rotation, and which failures require re-registration or a new bootstrap.

## Recoverable Without Rotation

- shared durable bridge store state
- rollout, chaos, and release evidence artifacts
- compatible-host interop catalogs
- packet captures and qlog artifacts retained by maintained drills

## Recoverable Only After Rotation

- upstream API auth tokens after compromise or confirmed drift
- webhook signature material after compromise or mismatched rotation
- store-service auth credentials after auth mismatch or credential leak

## Recoverable Only After Re-Registration Or Re-Bootstrap

- disabled or revoked device grants
- identity or lifecycle state that was intentionally invalidated upstream
- device bindings that cannot be trusted after profile-disable or compromise recovery

## Non-Recoverable By Runbook Alone

- missing upstream mutations that never reached Verta before an outage
- leaked secrets that have already escaped the intended trust boundary
- duplicate side effects already accepted by external systems before replay protection was restored

## Operator Rule

If an incident crosses one of these boundaries, do not improvise a silent in-place fix. Rotate, re-register, or re-bootstrap explicitly and preserve the evidence bundle that led to the decision.
