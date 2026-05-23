# Stage 2 Backup, Restore, And Disaster Recovery

**Stage:** `S2-STAGE-12`
**Status:** Passed with controlled gaps
**Date:** 2026-05-23
**Owner:** `@Sasha_Beep`

---

## 1. Purpose

Stage 2 public release must have a practical recovery path before CyberVPN opens beyond the controlled beta cohort.

The goal is not to build enterprise DR in S2. The goal is to prove that the owner can recover from the most likely early-public failures:

- broken deployment;
- bad migration;
- lost or corrupted app PostgreSQL data;
- lost or corrupted Remnawave PostgreSQL data;
- failed Remnawave control-plane rebuild;
- broken GitLab/home observability host;
- missing dashboards/evidence after an incident;
- operator mistake during rollback.

Customer-facing runtime stays on rented servers. Home infrastructure remains GitLab, CI/evidence, Sentry, Grafana, Prometheus, Loki, Alertmanager, backups and restore drills. A home outage must reduce visibility and CI convenience, not break customer VPN access.

---

## 2. Runtime Recovery Scope

| Surface | Stage 2 placement | Backup status | Restore status | S2 decision |
|---|---|---|---|---|
| CyberVPN app PostgreSQL | `prod-app-1` | Daily local timer plus pre-release manual backups | Disposable DB restore proven | Required for S2 |
| Remnawave PostgreSQL | `prod-app-1` | Daily local timer plus pre-release manual backups | Disposable DB restore proven | Required for S2 |
| App compose/config/secrets | `prod-app-1` | Restricted local archive in app backup | Archive checksum proven | Required for rebuild |
| Production Valkey/Redis | `prod-app-1` | No durable backup | Rebuild from PostgreSQL/job source of truth | Acceptable for S2 |
| Remnawave node | Dedicated node host only | Node env/config exists on node; control-plane data is in Remnawave DB | Rebuild from Remnawave + node config | Node must remain node-only |
| GitLab | Home server | Fresh GitLab backup archive | Archive extraction and DB gzip validation proven | Required for GitLab-first workflow |
| GitHub mirror | External mirror | Git remote mirror | Clone/pull fallback | Required fallback |
| Grafana dashboards | Home server | Provisioned JSON backup | Dashboard bundle restore proven | Required for visibility |
| Sentry | Home server | Config export, PostgreSQL dump, compose config, restic snapshot | Backup proven; full historical restore deferred | Required for error triage |
| Prometheus/Loki/Alertmanager | Home server | Config/evidence backup through restic/config snapshots | Config restore covered by restic drill | Required for visibility, not customer runtime |

---

## 3. RPO / RTO Targets

| Area | S2 RPO | S2 RTO | Notes |
|---|---:|---:|---|
| CyberVPN app PostgreSQL | `<=24h` | `<=4h` | Daily backup timer plus pre-deploy backup before risky releases |
| Remnawave PostgreSQL | `<=24h` | `<=4h` | Same cadence as app DB; provisioning and subscriptions depend on this |
| App config/secrets archive | `<=24h` plus pre-change archive | `<=2h` | Secrets are backed up as restricted archives; never committed |
| Git source | Near-zero logical RPO | `<=1h` for clone/mirror use | GitLab is first, GitHub remains fallback mirror |
| GitLab application restore | `<=24h` | `<=8h` | Full app restore requires maintenance window and matching GitLab version |
| Grafana dashboards | `<=24h` | `<=2h` | Provisioned JSON is source of truth |
| Sentry config and project setup | `<=24h` | `<=8h` | Full historical event restore is not S2-critical |
| VPN node | No durable user data on node | `<=2h` per node after provider access | Node must remain node-only; no app/observability workloads |
| Valkey/Redis | No durable RPO target | `<=1h` | Cache/queue state is not source of truth for S2 |

If the owner wants stricter RPO/RTO later, S2 should add managed PostgreSQL HA, external encrypted restic/rclone target and automated off-host pull. That is useful, but not required to open S2 with the current cost constraints.

---

## 4. Backup Schedule

### 4.1 Production App Server

Production app backups are created by:

```text
/srv/cybervpn/scripts/backup-prod-app.sh
```

Systemd timer:

```text
cybervpn-prod-app-backup.timer
```

Timer policy:

```text
OnCalendar=*-*-* 02:35:00 UTC
RandomizedDelaySec=15m
Retention=14 days for daily-* local backup directories
```

Backup content:

- CyberVPN app PostgreSQL custom-format dump;
- Remnawave PostgreSQL custom-format dump;
- table-count sanity files;
- restricted app compose/edge/secrets archive;
- Docker container/image inventory.

### 4.2 Home Operations Server

Home backup/restore timers:

```text
cybervpn-config-backup.timer
cybervpn-restic-check.timer
cybervpn-restore-drill.timer
```

Service-specific backup scripts:

```text
/srv/cybervpn-h/scripts/backup-configs.sh
/srv/cybervpn-h/scripts/backup-gitlab.sh
/srv/cybervpn-h/scripts/backup-sentry.sh
/srv/cybervpn-h/scripts/backup-observability.sh
/srv/cybervpn-h/scripts/run-restore-drill.sh
```

---

## 5. Off-Host Storage

S2 has a proven off-host copy path:

```text
prod-app-1 -> cybervpn-h-ops:/srv/storage/backups/prod-app-1/
```

Evidence:

```text
/srv/storage/backups/prod-app-1/s2-stage12-20260523T050454Z
```

Current policy:

1. Pre-release and incident backups must be copied from rented production servers to the home server before high-risk changes.
2. Do not copy private SSH keys from the operator workstation to production just to automate this.
3. Add a dedicated backup pull key or encrypted remote restic/rclone target before increasing S2 scale materially.

Controlled gap:

```text
Automated off-host production backup transfer is not yet installed.
```

This is acceptable for early S2 only because the owner is running controlled public growth and pre-release backups are manual evidence gates.

---

## 6. Restore Contract

Restore order for a production data incident:

1. Pause registration, checkout, trial activation and provisioning if data integrity is uncertain.
2. Snapshot current broken state before overwriting anything.
3. Restore app PostgreSQL first.
4. Restore Remnawave PostgreSQL second.
5. Start backend, worker/scheduler and Remnawave.
6. Verify auth, subscriptions, payment state, provisioning and subscription URL retrieval.
7. Verify one owner VPN client can connect.
8. Re-enable paused flows.

Disposable restore was proven on 2026-05-23:

```text
CyberVPN app DB table count: 121 -> restored 121
Remnawave DB table count: 36 -> restored 36
```

The restore proof used disposable databases and did not replace live production databases.

---

## 7. Rollback Contract

Rollback must be an immutable image/tag operation, not a floating `main` operation.

Production rollback dry-run evidence exists under:

```text
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback-dry-run.log
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback.override.yml
/srv/cybervpn/backups/s2-stage12-20260523T050454Z/rollback-command.txt
```

Validated rollback image set:

```text
cybervpn/cybervpn-backend:stage1-direct-xhttp-ru-bundle-20260522T081900Z
cybervpn/cybervpn-frontend:stage1-direct-xhttp-ru-bundle-20260522T081900Z
cybervpn/cybervpn-telegram-bot:stage1-direct-xhttp-ru-bundle-20260522T081900Z
cybervpn/cybervpn-admin:stage1-rent04-90f5b4b5
cybervpn/cybervpn-task-worker:stage1-rent10-cryptopay-fiat-20260520t1422z
```

`docker compose config --quiet` passed and all rollback images were present on `prod-app-1`.

Controlled gap:

```text
Live destructive rollback was not executed because S1/S2 beta runtime was active.
```

For S2 this is acceptable if every risky deploy also creates a pre-deploy backup and validates the rollback override before applying changes.

---

## 8. Secrets Backup And Rotation

Secrets are backed up only as restricted server-side archives and restic snapshots. They must never be committed into GitLab/GitHub or copied into release evidence.

S2 policy:

1. No routine secret rotation is required solely because S2-STAGE-12 ran.
2. Rotate immediately after suspected disclosure, unauthorized access, leaked logs, lost operator device or provider compromise.
3. Keep restore evidence redacted: paths, file names, hashes and statuses are allowed; secret values are not.
4. Keep production payment, Telegram, Remnawave and JWT secrets outside the repo.

---

## 9. Known Gaps

| Gap | Impact | S2 recommendation |
|---|---|---|
| Automated off-host pull is not installed | Manual step required before risky changes | Add dedicated backup pull key or encrypted restic/rclone target |
| GitLab registry is skipped by current GitLab backup | Registry images are not restored by GitLab backup archive | Keep GitHub/GitLab source and prod image inventory; add registry backup before registry becomes source of truth |
| Full GitLab app restore into separate container was not run | GitLab archive is validated, but full app restore remains unproven | Run full GitLab restore rehearsal before S3/partner scale |
| Sentry full historical event restore was not run | Sentry config/data backup exists, but full event history restore remains deferred | Accept for S2; Sentry is visibility, not billing/source of truth |
| Managed PostgreSQL HA is not enabled yet | App DB depends on VPS local PostgreSQL | Add managed PostgreSQL/replica when budget allows or growth increases |

---

## 10. Exit Criteria

`S2-STAGE-12` is accepted when:

1. Production app PostgreSQL backup and disposable restore are proven.
2. Remnawave PostgreSQL backup and disposable restore are proven.
3. Production backup schedule is installed and tested.
4. Off-host copy to home server is proven.
5. GitLab backup archive is fresh and archive restore validation passes.
6. Grafana dashboard restore from backup passes.
7. Sentry backup is fresh.
8. Restic config restore and check pass.
9. Rollback dry-run validates immutable images and compose config.
10. Known gaps are documented and accepted as controlled S2 gaps.

Evidence:

```text
docs/evidence/releases/s2-stage-12-backup-restore-dr-20260523.md
```
