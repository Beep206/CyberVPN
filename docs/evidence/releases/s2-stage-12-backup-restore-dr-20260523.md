# S2-STAGE-12 Backup, Restore, And Disaster Recovery Evidence

**Date:** 2026-05-23
**Stage:** `S2-STAGE-12`
**Result:** `PASS_WITH_CONTROLLED_GAPS`
**Owner:** `@Sasha_Beep`

---

## 1. Scope

This evidence records the Stage 2 backup, restore and disaster recovery gate.

Covered:

- production app PostgreSQL backup and disposable restore;
- production Remnawave PostgreSQL backup and disposable restore;
- production app config/secrets restricted archive;
- production backup timer installation and first successful run;
- off-host copy from `prod-app-1` to home storage;
- GitLab backup archive creation and archive restore validation;
- Sentry backup creation;
- Grafana dashboard backup and restore validation;
- restic repository check and config file restore;
- production rollback dry-run with immutable images;
- VPN node-only verification.

---

## 2. Production App Backup And Restore Drill

Host:

```text
prod-app-1
```

Evidence directory:

```text
/srv/cybervpn/backups/s2-stage12-20260523T050454Z
```

Observed summary:

```text
started_at_utc=2026-05-23T05:04:54+00:00
host=prod-app-1
backup_dir=/srv/cybervpn/backups/s2-stage12-20260523T050454Z
cybervpn_table_count=121
cybervpn_restore_status=ok
remnawave_table_count=36
remnawave_restore_status=ok
finished_at_utc=2026-05-23T05:05:01+00:00
status=ok
```

Interpretation:

1. app PostgreSQL accepted connections;
2. app PostgreSQL custom-format dump was created;
3. app dump restored into a disposable database;
4. restored app table count matched source table count;
5. disposable app restore database was removed;
6. Remnawave PostgreSQL followed the same process;
7. Remnawave restored table count matched source table count;
8. disposable Remnawave restore database was removed.

No live production database was replaced.

---

## 3. Production Backup Schedule

Installed on `prod-app-1`:

```text
/srv/cybervpn/scripts/backup-prod-app.sh
/etc/systemd/system/cybervpn-prod-app-backup.service
/etc/systemd/system/cybervpn-prod-app-backup.timer
```

Timer:

```text
OnCalendar=*-*-* 02:35:00 UTC
RandomizedDelaySec=15m
Persistent=true
```

Timer status after install:

```text
NEXT                        LEFT LAST PASSED UNIT                           ACTIVATES
Sun 2026-05-24 07:35:31 +05  21h -         - cybervpn-prod-app-backup.timer cybervpn-prod-app-backup.service
```

Manual first run:

```text
Process: ExecStart=/srv/cybervpn/scripts/backup-prod-app.sh (code=exited, status=0/SUCCESS)
cybervpn_table_count=121
remnawave_table_count=36
status=ok
```

Fresh daily backup created:

```text
/srv/cybervpn/backups/daily-20260523T050928Z
```

---

## 4. Off-Host Copy

Copied from:

```text
prod-app-1:/srv/cybervpn/backups/s2-stage12-20260523T050454Z
```

Copied to:

```text
cybervpn-h-ops:/srv/storage/backups/prod-app-1/s2-stage12-20260523T050454Z
```

Off-host inventory:

```text
cybervpn-20260523T050454Z.dump
cybervpn-20260523T050454Z.dump.sha256
cybervpn-restored-table-count.txt
cybervpn-source-table-count.txt
docker-ps.tsv
evidence-checksums.sha256
image-inventory.tsv
prod-app-backup-restore.log
prod-app-config-secrets-20260523T050454Z.tgz
prod-app-config-secrets.sha256
remnawave-20260523T050454Z.dump
remnawave-20260523T050454Z.dump.sha256
remnawave-restored-table-count.txt
remnawave-source-table-count.txt
summary.txt
```

The off-host path is proven. Automated off-host transfer remains a controlled S2 gap.

---

## 5. Home Restic / Grafana / GitLab Restore Drill

Home server:

```text
cybervpn-h-ops
```

Restore evidence directory:

```text
/srv/storage/evidence/restores/cybervpn-h-restore-drill-20260523T050620Z
```

Observed summary:

```text
started_at_utc=2026-05-23T05:07:06+00:00
restic_config_snapshot=4355a7ef
restic_config_file_status=ok
grafana_backup=/srv/storage/backups/observability/grafana-20260523T050620Z
grafana_restored_dashboard_json_count=33
gitlab_backup=/srv/storage/backups/gitlab/1779512795_2026_05_23_18.11.2_gitlab_backup.tar
gitlab_repository_bundle_count=3
gitlab_archive_restore_status=ok
finished_at_utc=2026-05-23T05:07:09+00:00
status=ok
```

Timings:

```text
restic_config_file_restore    2s
grafana_dashboard_restore     0s
gitlab_archive_restore        1s
```

GitLab backup archive created during this gate:

```text
/srv/storage/backups/gitlab/1779512795_2026_05_23_18.11.2_gitlab_backup.tar
size: 112M
```

Sentry backup created during this gate:

```text
/srv/storage/backups/sentry/sentry-20260523T050644Z
```

Sentry evidence summary:

```text
started_at_utc=2026-05-23T05:06:44+00:00
backup_dir=/srv/storage/backups/sentry/sentry-20260523T050644Z
finished_at_utc=2026-05-23T05:07:06+00:00
status=ok
```

Restic repository check:

```text
18 / 18 snapshots checked
no errors were found
status=ok
```

---

## 6. Rollback Dry-Run

Host:

```text
prod-app-1
```

Artifacts:

```text
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback-dry-run.log
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback.override.yml
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback-command.txt
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback-image-availability.tsv
```

Observed:

```text
compose_config_status=ok
rollback_dry_run_status=ok
```

Validated images:

```text
cybervpn/cybervpn-backend:stage1-direct-xhttp-ru-bundle-20260522T081900Z
cybervpn/cybervpn-frontend:stage1-direct-xhttp-ru-bundle-20260522T081900Z
cybervpn/cybervpn-telegram-bot:stage1-direct-xhttp-ru-bundle-20260522T081900Z
cybervpn/cybervpn-admin:stage1-rent04-90f5b4b5
cybervpn/cybervpn-task-worker:stage1-rent10-cryptopay-fiat-20260520t1422z
```

This was intentionally non-destructive. It validated command structure and image availability without restarting live services.

---

## 7. VPN Node-Only Verification

Node host:

```text
de-1.cyber-vpn.org
```

Observed containers:

```text
cybervpn-remnawave-node    remnawave/node:2.7.0    Up 2 days
```

Observed listening services:

```text
22/tcp    SSH
443/tcp   VPN/Xray through Remnawave node container
8443/tcp  VPN/XHTTP path through Remnawave node container
22230/tcp Remnawave node path
61000/tcp localhost-only internal listener
```

No app, GitLab, Sentry, Grafana, Prometheus, Loki, backend, frontend or payment services were running on the VPN node.

---

## 8. RPO / RTO Decision

Accepted S2 targets:

| Surface | RPO | RTO |
|---|---:|---:|
| CyberVPN app PostgreSQL | `<=24h` | `<=4h` |
| Remnawave PostgreSQL | `<=24h` | `<=4h` |
| app config/secrets archive | `<=24h` plus pre-change archive | `<=2h` |
| Git source | near-zero through GitLab + GitHub | `<=1h` clone/fallback |
| GitLab application | `<=24h` | `<=8h` |
| Grafana dashboards | `<=24h` | `<=2h` |
| Sentry config/project backup | `<=24h` | `<=8h` |
| VPN node rebuild | no durable node data | `<=2h` after provider access |
| Valkey/Redis | no durable source of truth | rebuildable |

---

## 9. Controlled Gaps

| Gap | Accepted for S2? | Follow-up |
|---|---|---|
| Automated off-host production backup transfer is not yet installed | Yes, early S2 only | Add dedicated backup pull key or encrypted restic/rclone remote |
| Full GitLab app restore into a separate live container was not performed | Yes | Run before S3/partner scale |
| GitLab registry is skipped by current GitLab backup | Yes | Add registry backup before registry becomes source of truth |
| Sentry full historical event restore was not performed | Yes | Run when Sentry history becomes operationally critical |
| Managed PostgreSQL HA is not enabled | Yes | Add when budget/growth requires stricter RPO/RTO |

---

## 10. Security Notes

No secret values are stored in this evidence file.

Allowed evidence:

- backup directory paths;
- file names;
- hashes/checksum file names;
- image tags;
- table counts;
- restore status;
- timer status.

Not allowed in evidence:

- payment provider secrets;
- Telegram bot token;
- JWT/TOTP secrets;
- Remnawave API token;
- raw subscription URLs;
- VPN configs;
- database dumps;
- config/secret archive contents.

---

## 11. Result

`S2-STAGE-12` passes with controlled gaps.

The practical S2 recovery path is now proven for:

1. app DB backup/restore;
2. Remnawave DB backup/restore;
3. production backup timer;
4. off-host backup copy;
5. GitLab archive validation;
6. Sentry backup;
7. Grafana dashboard restore;
8. restic config restore;
9. non-destructive rollback command validation.

Next stage:

```text
S2-STAGE-13: Security, Abuse, And Privacy Gate
```
