# Control-Plane Backup And Restore Runbook

This runbook covers the Phase 7 backup and restore evidence flow for the
CyberVPN control plane.

## Preconditions

1. The control-plane rollout is already healthy on the target host.
2. `db-backup` is part of the deployed compose project.
3. The host has enough free disk space under `/var/backups/cybervpn/`.

## Backup flow

1. Capture a control-plane config snapshot and trigger an on-demand PostgreSQL dump:

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-control-plane-backup-staging
```

2. Verify the new artifacts on the target host:

- config snapshot under `/var/backups/cybervpn/control-plane/config/<timestamp>/`
- PostgreSQL dump under `/var/backups/cybervpn/postgres/.../*.dump`

3. Keep the following evidence with the rollout record:

- host name
- release path from `current`
- snapshot timestamp
- dump file path
- image tags for backend, worker, and helix-adapter

## Restore helper

The default restore helper is non-destructive: it only checks that the latest
dump can be read by `pg_restore --list`.

```bash
cd /home/beep/projects/VPNBussiness/infra
make ansible-control-plane-restore-drill-staging
```

If you need a destructive drill, set
`backup_restore_run_destructive_restore_drill=true` via extra vars and use the
dedicated DR runbook first.
