# Phase 12 Backup Foundation Evidence

Date: 2026-05-10
Host: `cybervpn-h-ops`
Server: `10.10.10.34`

## Scope

Phase 12 prepared the local backup foundation before GitLab, Sentry and observability services are deployed.

Remote/offsite backup is deferred until an external disk or remote storage target is available.

## Installed Backup Surface

Local restic repository:

```text
/srv/storage/backups/restic/cybervpn-h-local
```

Root-only secret/config files:

```text
/srv/cybervpn-h/secrets/restic.env
/srv/cybervpn-h/secrets/rclone.conf
```

Backup and restore scripts:

```text
/srv/cybervpn-h/scripts/backup-configs.sh
/srv/cybervpn-h/scripts/backup-gitlab.sh
/srv/cybervpn-h/scripts/backup-sentry.sh
/srv/cybervpn-h/scripts/backup-observability.sh
/srv/cybervpn-h/scripts/restic-check.sh
/srv/cybervpn-h/scripts/restore-configs-smoke.sh
```

Runbook:

```text
/srv/cybervpn-h/runbooks/restore-from-restic.md
```

Systemd timers:

```text
cybervpn-config-backup.timer
cybervpn-restic-check.timer
```

## Verification

Restic repository initialization:

```text
initialized
```

Secret permissions:

```text
-rw------- root:root /srv/cybervpn-h/secrets/restic.env
-rw------- root:root /srv/cybervpn-h/secrets/rclone.conf
drwx------ root:root /srv/storage/backups/restic/cybervpn-h-local
```

First config snapshot:

```text
snapshot c8a5feff saved
status=ok
```

Snapshot metadata:

```text
ID        Time                 Host            Tags
c8a5feff  2026-05-10 05:09:50  cybervpn-h-ops  cybervpn-h,configs,phase12
```

Restore smoke test:

```text
snapshot=c8a5feff
target=/srv/storage/backups/restore-tests/configs-20260510T050954Z
test_file=/srv/cybervpn-h/runbooks/restore-from-restic.md
status=ok
```

Restic check:

```text
no errors were found
status=ok
```

Timer status:

```text
cybervpn-config-backup.timer active
cybervpn-restic-check.timer active
```

Next scheduled runs at verification time:

```text
Mon 2026-05-11 02:49:57 UTC    cybervpn-config-backup.timer
Sun 2026-05-17 03:44:19 UTC    cybervpn-restic-check.timer
```

Storage target:

```text
Filesystem  Type  Size  Used  Avail  Use%  Mounted on
/dev/sda1   ext4  1.8T  49M   1.8T   1%    /srv/storage
```

Secret exclusion check:

```text
restic_env_excluded=ok
rclone_conf_excluded=ok
```

## Evidence Paths On Server

```text
/srv/cybervpn-h/evidence/backups/restic-init.status
/srv/cybervpn-h/evidence/backups/phase12-secret-perms.txt
/srv/cybervpn-h/evidence/backups/phase12-systemd-timers.txt
/srv/cybervpn-h/evidence/backups/config-backup-20260510T050950Z/
/srv/cybervpn-h/evidence/backups/restore-smoke-20260510T050954Z/
/srv/cybervpn-h/evidence/backups/restic-check-20260510T050955Z/
```

## Current Limitations

GitLab, Sentry, Prometheus, Loki and Grafana data are not backed up yet because those services are not deployed in Phase 12.

`backup-gitlab.sh`, `backup-sentry.sh` and `backup-observability.sh` are explicit placeholders until their services exist and restore drills can be validated.

The server currently reports `46 GiB` RAM available again after earlier seeing `62 GiB`; hardware/RAM stability remains a blocker before heavy service load.
