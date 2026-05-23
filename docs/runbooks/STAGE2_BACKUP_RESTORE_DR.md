# Stage 2 Backup, Restore, And Disaster Recovery Runbook

**Scope:** CyberVPN S2 Public Release 1.0
**Primary owner:** `@Sasha_Beep`
**Last verified:** 2026-05-23

---

## 1. Emergency Rules

1. Do not overwrite production data before taking a snapshot of the broken state.
2. Do not paste secrets, raw subscription URLs, payment payloads, Telegram init data or VPN configs into public tickets, chats or evidence.
3. Pause risky flows before a destructive restore:
   - registration;
   - checkout/payment;
   - trial activation;
   - invite activation;
   - provisioning workers.
4. Restore PostgreSQL before trying to repair derived cache/queue state.
5. Treat Valkey/Redis as rebuildable for S2. PostgreSQL and Remnawave DB are the durable sources.

---

## 2. Production App Backup

Host:

```text
prod-app-1
```

Script:

```text
/srv/cybervpn/scripts/backup-prod-app.sh
```

Timer:

```bash
systemctl list-timers --all cybervpn-prod-app-backup.timer
systemctl status cybervpn-prod-app-backup.service
```

Run a manual backup:

```bash
sudo /srv/cybervpn/scripts/backup-prod-app.sh
```

Expected result:

```text
cybervpn_table_count=<number>
remnawave_table_count=<number>
status=ok
```

Backup root:

```text
/srv/cybervpn/backups
```

Do not commit files from this directory. They may include restricted config/secret archives.

---

## 3. Production Disposable Restore Test

Use this only as a restore drill. It creates a temporary database, restores into it, compares table counts and drops the temporary database.

Expected pattern:

```bash
docker exec cybervpn-stage1-cybervpn-postgres-1 sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker exec cybervpn-stage1-cybervpn-postgres-1 sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-acl' > cybervpn.dump
docker exec cybervpn-stage1-cybervpn-postgres-1 sh -lc 'createdb -U "$POSTGRES_USER" cybervpn_restore_test'
cat cybervpn.dump | docker exec -i cybervpn-stage1-cybervpn-postgres-1 sh -lc 'pg_restore -U "$POSTGRES_USER" -d cybervpn_restore_test --no-owner --no-acl'
docker exec cybervpn-stage1-cybervpn-postgres-1 sh -lc 'dropdb -U "$POSTGRES_USER" cybervpn_restore_test'
```

Run the same pattern for:

```text
cybervpn-stage1-cybervpn-remnawave-postgres-1
```

Never restore directly over live production without a maintenance window and owner approval.

---

## 4. Off-Host Copy

Current S2 off-host path:

```text
prod-app-1:/srv/cybervpn/backups/<backup-dir>
cybervpn-h-ops:/srv/storage/backups/prod-app-1/<backup-dir>
```

Preferred direction:

```text
home pulls from prod-app-1
```

Reason: do not place the operator's general deployment private key onto production just to push backups.

Before expanding public traffic materially, add one of:

1. a dedicated read-only backup pull key restricted to backup paths;
2. encrypted restic/rclone target;
3. managed provider snapshot plus restore drill evidence.

---

## 5. App Database Restore During Incident

High-level order:

1. Announce internal incident and pause risky flows.
2. Create a broken-state snapshot under `/srv/cybervpn/backups/incident-*`.
3. Stop backend/worker/scheduler if they can write inconsistent data.
4. Restore CyberVPN app PostgreSQL from the selected dump.
5. Restore Remnawave PostgreSQL from the matching dump.
6. Start Remnawave, backend, worker and scheduler.
7. Verify:
   - `/health`;
   - login;
   - active subscription lookup;
   - subscription URL retrieval;
   - one trial/provisioning smoke if safe;
   - one owner VPN client connection.
8. Re-enable paused flows only after verification.

Do not run a live production restore by copying commands from chat. Use a maintenance terminal, selected backup ID and current incident notes.

---

## 6. GitLab Restore

Runbook:

```text
docs/runbooks/restore-gitlab.md
```

S2 validated level:

```text
archive extraction
backup_information.yml exists
database.sql.gz passes gzip test
repository bundle count exists
```

Controlled gap:

```text
Full GitLab app restore into a separate container was not performed in S2-STAGE-12.
```

This is acceptable for S2 because GitHub remains a mirror fallback and Git source can be recovered by clone/push even if the GitLab application needs a longer restore window.

---

## 7. Grafana / Sentry / Restic Restore

Runbooks:

```text
docs/runbooks/restore-grafana.md
docs/runbooks/restore-sentry.md
docs/runbooks/restore-from-restic.md
```

S2 validated level:

- restic repository check passes;
- one config file restore from latest restic config snapshot passes;
- Grafana provisioned dashboard backup restores to a test directory;
- GitLab archive extraction passes;
- Sentry backup is fresh and stored under `/srv/storage/backups/sentry/latest`.

Sentry full historical event restore is not required for S2 customer runtime. Sentry loss reduces error-history visibility, not billing/subscription truth.

---

## 8. Rollback

Current rollback dry-run artifacts are stored on `prod-app-1`:

```text
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback.override.yml
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback-command.txt
```

Before a risky deploy:

```bash
docker compose --env-file .env -f docker-compose.yml -f <rollback.override.yml> config --quiet
```

After a failed deploy:

1. Pause registration/payments/trial/provisioning if data integrity is uncertain.
2. Apply the rollback override only to affected services.
3. Wait for health checks.
4. Verify frontend, API, bot, admin and subscription URL retrieval.
5. Keep the failed release logs and pre/post image inventory.

Rollback must use immutable image tags. Do not rollback by deploying a floating `main`.

---

## 9. RPO / RTO Quick Reference

| Surface | S2 RPO | S2 RTO |
|---|---:|---:|
| CyberVPN app PostgreSQL | `<=24h` | `<=4h` |
| Remnawave PostgreSQL | `<=24h` | `<=4h` |
| app config/secrets archive | `<=24h` plus pre-change archive | `<=2h` |
| Git source | near-zero through GitLab + GitHub mirror | `<=1h` clone/fallback |
| GitLab application | `<=24h` | `<=8h` |
| Grafana dashboards | `<=24h` | `<=2h` |
| Sentry config/project backup | `<=24h` | `<=8h` |
| VPN node rebuild | no durable node data | `<=2h` after provider access |
| Valkey/Redis | no durable source of truth | rebuildable |

---

## 10. Recovery Decision Matrix

| Incident | First action | Restore/rollback path |
|---|---|---|
| Bad frontend release | Disable expansion; rollback frontend image | Compose image rollback |
| Bad backend release, no DB corruption | Pause write flows; rollback backend/worker | Compose image rollback |
| Bad migration or DB corruption | Pause writes; snapshot broken state | PostgreSQL restore |
| Remnawave DB issue | Pause provisioning; snapshot broken state | Remnawave DB restore |
| VPN node failure | Keep app up; mark node degraded | Rebuild node from Remnawave/node config |
| GitLab down | Use GitHub mirror for source fallback | Restore GitLab from archive |
| Home observability down | Customer runtime stays live | Restore Grafana/Sentry/Prometheus configs |
| Secret exposure | Pause affected flows | Rotate affected secret and invalidate sessions/webhooks where needed |

---

## 11. Stage 2 Controlled Gaps

The following are known and accepted for early S2:

1. Automated off-host production backup transfer is not installed.
2. Full GitLab app restore into a second live container was not performed.
3. GitLab registry backup is skipped by current GitLab backup command.
4. Full Sentry historical event restore was not performed.
5. Managed PostgreSQL HA is not enabled yet.

These gaps become harder blockers before S3 partner/reseller scale or before CyberVPN depends on GitLab registry as source of truth.
