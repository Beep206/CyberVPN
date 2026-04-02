# Helix Rollback Drill

## Goal

Подтвердить, что `Helix` можно быстро и безопасно откатить на уровне:

- rollout channel;
- desktop manifest issuance;
- node runtime state;
- lab history and evidence state.

## Drill Types

### 1. Control-Plane Pause Drill

Use when the active Helix profile becomes unsafe for new sessions.

Operator actions:

1. Confirm current canary evidence on the affected rollout.
2. Verify applied or recommended action:
   - `pause-channel`
   - `rotate-profile-now`
3. Pause rollout through backend admin surface.
4. Confirm new manifest issuance stops for the affected rollout.
5. Watch worker control alerts until the rollout posture stabilizes.

Success:

- new Helix sessions stop on the affected channel;
- worker and canary snapshot both show the same reaction state.

### 2. Runtime Rollback Drill

Use when Helix node or desktop runtime becomes unhealthy after config change.

Operator actions:

1. Confirm node daemon reports unhealthy bundle or rollback counter increase.
2. Verify node restores last-known-good bundle.
3. Confirm desktop falls back to `sing-box` or `xray` when runtime health gate fails.
4. Export support bundle and attach to incident record.

Success:

- last-known-good bundle becomes active again;
- desktop stable core fallback succeeds without manual user repair.

### 3. Lab History Reset Drill

Use before destructive Helix lab retest or rollback rehearsal.

Scripts:

- [reset_helix_lab_history.sh](/C:/project/CyberVPN/infra/tests/reset_helix_lab_history.sh)
- [verify_helix_rollback.sh](/C:/project/CyberVPN/infra/tests/verify_helix_rollback.sh)

Static verification:

```bash
bash infra/tests/verify_helix_rollback.sh
```

Destructive live verification:

```bash
HELIX_REQUIRE_LIVE=true HELIX_ALLOW_DESTRUCTIVE=true bash infra/tests/verify_helix_rollback.sh
```

Success:

- both Helix lab node containers are cleared;
- both Helix node state volumes are cleared;
- Helix evidence tables are truncated in PostgreSQL.

## Evidence To Save

- current canary evidence snapshot
- worker canary-control alert
- worker actuation alert
- Desktop support bundle
- rollback verification output

## Internal Beta Requirement

At least one full rollback drill must pass before widening Helix beyond the initial internal beta cohort.
