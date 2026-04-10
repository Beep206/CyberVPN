# Control-Plane DR Drill

This runbook covers the Phase 7 disaster-recovery rehearsal for the
CyberVPN control plane.

## Preconditions

1. A recent successful backup exists.
2. The operator reviewed `CONTROL_PLANE_BACKUP_RESTORE_RUNBOOK.md`.
3. The drill is scheduled in a maintenance window.
4. The restore target database name does not collide with production traffic.

## Recommended drill sequence

1. Capture a fresh backup:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-control-plane-backup-staging
```

2. Run a non-destructive restore verification first:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-control-plane-restore-drill-staging
```

3. Only if that passes, run the destructive drill with explicit extra vars:

```bash
cd /home/beep/projects/VPNBussiness/infra/ansible
ansible-playbook -i inventories/staging playbooks/control-plane-restore-drill.yml \
  -e control_plane_target_group=control_plane_staging \
  -e backup_restore_run_destructive_restore_drill=true
```

## Expected result

- a temporary restore database is created;
- the latest dump is restored into it;
- `SELECT 1` succeeds against the restored database;
- the temporary restore database is dropped afterwards.

If any step fails, stop widening the rollout and inspect the latest backup
artifact before retrying.
