# STAGE1-PUB-14 App And Remnawave Restore Evidence

Date: 2026-05-11T06:46:30Z

Stage: `STAGE1-PUB-14`

Result: PASS.

Server: `10.10.10.34` / `cybervpn-h-ops`

Runtime tag: `stage1-beta-rc.2`

## Scope

This restore drill proves that the fresh Stage 1 backup artifacts can be restored into disposable databases and validated without replacing or stopping the live databases.

## App DB Restore Drill

Source backup:

```text
/srv/storage/backups/cybervpn-stage1/postgres/stage1-pub-14-cybervpn-20260511T064630Z.dump
```

Restore command type:

```text
createdb disposable_db
pg_restore --no-owner --no-acl
psql smoke queries
dropdb disposable_db
```

Disposable database:

```text
cybervpn_restore_20260511T064630Z
```

Validation:

| Check | Source | Restored |
|---|---:|---:|
| Alembic version | `20260423_p27_partner_events` | `20260423_p27_partner_events` |
| Public table count | `120` | `120` |

Cleanup:

```text
app_restore_dropped=yes
app_restore_db_left=0
```

## Remnawave DB Restore Drill

Source backup:

```text
/srv/storage/backups/cybervpn-stage1/remnawave/stage1-pub-14-remnawave-20260511T064630Z.dump
```

Restore command type:

```text
createdb disposable_db
pg_restore --no-owner --no-acl
psql smoke queries
dropdb disposable_db
```

Disposable database:

```text
remnawave_restore_20260511T064630Z
```

Validation:

| Check | Source | Restored |
|---|---:|---:|
| Public table count | `36` | `36` |
| Migration table count | `1` | not required for equality check |

Cleanup:

```text
remnawave_restore_dropped=yes
remnawave_restore_db_left=0
```

## Live Smoke After Restore

Public/runtime checks after restore:

```text
200 https://cyber-vpn.net/en-EN/status
200 https://admin.cyber-vpn.net/ru-RU/login
200 https://api.cyber-vpn.net/healthz
```

All Stage 1 app containers remained `running` and `healthy`.

## Interpretation

The restore drill is acceptable for the controlled beta gate:

- backup files are readable by restore tooling;
- application schema state survives restore;
- Remnawave DB shape survives restore;
- disposable restore databases are cleaned up;
- live runtime remains healthy afterward.

## Residual Risk

The current restore drill validates local no-cost PostgreSQL services on the home server. A future managed PostgreSQL migration must repeat the same drill against the managed provider backup/restore mechanism.
