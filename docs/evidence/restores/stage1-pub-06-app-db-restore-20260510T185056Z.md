# STAGE1-PUB-06 App DB Restore Evidence

Date: 2026-05-10 18:50:56 UTC
Stage: STAGE1-PUB-06
Release candidate: `stage1-beta-rc.1`
Approved snapshot commit: `cb042eb77fbc71bec69f4410149e44b4986960bd`
Server: `10.10.10.34` / `cybervpn-h-ops`
Restore type: disposable DB restore drill

## Result

PASS.

The PostgreSQL backup created during STAGE1-PUB-06 was restored into a disposable database and then dropped after validation.

## Source Backup

| Field | Value |
|---|---|
| Path | `/srv/storage/backups/cybervpn-stage1/postgres/stage1-pub-06-cybervpn-20260510T185056Z.dump` |
| Format | PostgreSQL custom dump |
| SHA-256 | `2b8de41b5a4dae5bc218bfa265e1bb2a2a6bfd27474103ab14b1196268534841` |

## Restore Drill

Disposable database:

```text
cybervpn_restore_20260510T185056Z
```

Restore command type:

```text
pg_restore --no-owner --no-acl
```

Validation result:

```text
RESTORE result=ok restore_db=cybervpn_restore_20260510T185056Z restore_db_dropped=yes alembic_version=20260423_p27_partner_events public_table_count=120
```

The restored database matched the source migration state:

| Check | Source | Restored |
|---|---:|---:|
| Alembic version | `20260423_p27_partner_events` | `20260423_p27_partner_events` |
| Public table count | `120` | `120` |

## Cleanup

The disposable restore database was dropped after validation:

```text
restore_db_dropped=yes
```

## Residual Risk

This restore drill proves the local no-cost beta PostgreSQL path can be backed up and restored. It does not remove the operational risk of running Stage 1 data services on the home server. Managed/private PostgreSQL and Valkey remain the preferred production-grade target.
