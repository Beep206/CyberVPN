# Phase 21 Restore Drill Evidence

Date: 2026-05-10

Host: `cybervpn-h-ops`

Server evidence:

```text
/srv/storage/evidence/restores/cybervpn-h-restore-drill-20260510T134712Z
```

Post-drill config backup:

```text
restic snapshot 359f7c44
```

## Installed Runbooks

```text
/srv/cybervpn-h/runbooks/restore-from-restic.md
/srv/cybervpn-h/runbooks/restore-gitlab.md
/srv/cybervpn-h/runbooks/restore-grafana.md
/srv/cybervpn-h/runbooks/restore-sentry.md
```

## Installed Scripts

```text
/srv/cybervpn-h/scripts/backup-observability.sh
/srv/cybervpn-h/scripts/run-restore-drill.sh
```

## Drill Results

Summary from the server:

```text
started_at_utc=2026-05-10T13:47:12+00:00
host=cybervpn-h-ops
evidence_dir=/srv/storage/evidence/restores/cybervpn-h-restore-drill-20260510T134712Z
restic_config_snapshot=01811b41
restic_config_file_status=ok
grafana_backup=/srv/storage/backups/observability/grafana-20260510T134712Z
grafana_restored_dashboard_json_count=22
gitlab_backup=/srv/storage/backups/gitlab/1778408068_2026_05_10_18.11.2_gitlab_backup.tar
gitlab_repository_bundle_count=3
gitlab_archive_restore_status=ok
finished_at_utc=2026-05-10T13:47:15+00:00
status=ok
```

Timings:

```text
restic_config_file_restore  2 seconds
grafana_dashboard_restore   0 seconds
gitlab_archive_restore      1 second
```

## Restic Config File Restore

Restored file:

```text
/srv/cybervpn-h/runbooks/security-pipeline.md
```

Validation:

```text
cmp against live file: ok
```

## Grafana Dashboard Restore

Backup bundle:

```text
/srv/storage/backups/observability/grafana-20260510T134712Z/grafana-dashboards.tgz
```

Validation:

```text
restored dashboard JSON files: 22
checksum verification lines: 24
```

The drill restored provisioned Grafana dashboard JSON and provisioning files to a non-production evidence directory. Production Grafana was not modified.

## GitLab Backup Restore

Backup archive:

```text
/srv/storage/backups/gitlab/1778408068_2026_05_10_18.11.2_gitlab_backup.tar
```

Validation:

```text
backup archive extracted in non-production directory: ok
backup_information.yml exists: ok
db/database.sql.gz gzip test: ok
repository bundle count: 3
backup tar entries: 71
```

Production GitLab was not modified.

## Missing Pieces And Follow-Ups

- Full GitLab application restore into a separate GitLab container was not performed in this drill to avoid production port, hostname, and secret conflicts on the home server.
- GitLab registry data is skipped by the current GitLab backup command using `SKIP=registry`; `/srv/storage/gitlab-registry` needs separate backup before registry images are treated as production source of truth.
- Grafana restore validated provisioned dashboard JSON and provisioning files. UI-only Grafana state must be exported into provisioning JSON or restored intentionally from `grafana.db`.
- Offsite backup is still deferred until an external disk or remote encrypted target is available.

## Acceptance Status

```text
Restore evidence exists: yes
Runbooks accurate enough to follow under pressure: yes
Backup success proven by restore proof: yes
```
