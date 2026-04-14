# Operator Runbooks

This directory is the maintained operator surface for Northstar.
It is intentionally narrow: these runbooks cover the `Phase L` incidents and recovery boundaries plus the bounded `Phase M` soak/canary discipline already required by the specs and by `docs/implementation/PHASED_EXECUTION_PLAN.md`.

## Runbook Set

- [REMNAWAVE_UPSTREAM_OUTAGE.md](REMNAWAVE_UPSTREAM_OUTAGE.md) for upstream outage, timeout, stale snapshot, and partial availability recovery.
- [BRIDGE_AUTH_DRIFT_AND_SECRET_ROTATION.md](BRIDGE_AUTH_DRIFT_AND_SECRET_ROTATION.md) for bridge auth drift, store auth mismatch, and credential rotation.
- [REPLAY_CACHE_AND_WEBHOOK_RECOVERY.md](REPLAY_CACHE_AND_WEBHOOK_RECOVERY.md) for replay cache inconsistencies, duplicate webhook handling, and reconcile-lag recovery.
- [PROFILE_DISABLE_AND_ROLLBACK.md](PROFILE_DISABLE_AND_ROLLBACK.md) for profile disable, rollout rollback, and emergency stream-fallback safe state.
- [RECOVERY_BOUNDARIES.md](RECOVERY_BOUNDARIES.md) for recoverable vs non-recoverable artifacts, rotation boundaries, and re-registration expectations.
- [PHASE_M_SOAK_AND_CANARY.md](PHASE_M_SOAK_AND_CANARY.md) for the bounded canary stage contract, rollback triggers, and agreed local soak environment.

## Operator Drill Commands

- profile-disable drill: `bash scripts/operator-profile-disable-drill.sh`
- rollback drill: `bash scripts/operator-rollout-rollback-drill.sh`
- Phase L signoff: `bash scripts/phase-l-operator-readiness.sh`
- Phase M soak/canary signoff: `bash scripts/phase-m-soak-canary.sh`

## Required Evidence Inputs

- `target/northstar/remnawave-supported-upstream-lifecycle-summary.json`
- `target/northstar/operator-rollout-rollback-drill-summary.json`
- `docs/runbooks/phase-m-canary-plan.json`
- `docs/development/phase-m-regression-ledger.json`
- `target/northstar/phase-m-soak-canary-signoff-summary.json`

If the supported-upstream lifecycle summary is missing, `Phase L` signoff fails closed instead of guessing that profile-disable recovery is still valid.
If the canary plan, regression ledger, or stage-local soak artifacts drift or go missing, `Phase M` signoff fails closed instead of guessing that prior stability evidence is still valid.
