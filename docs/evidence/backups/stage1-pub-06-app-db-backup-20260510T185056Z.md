# STAGE1-PUB-06 App DB Backup Evidence

Date: 2026-05-10 18:50:56 UTC
Stage: STAGE1-PUB-06
Release candidate: `stage1-beta-rc.1`
Approved snapshot commit: `cb042eb77fbc71bec69f4410149e44b4986960bd`
Server: `10.10.10.34` / `cybervpn-h-ops`
DB mode: no-cost beta local PostgreSQL/Valkey on `cybervpn-h-ops`

## Result

PASS.

For Stage 1 no-cost beta, local data services were accepted with explicit risk:

- PostgreSQL runs locally on `cybervpn-h-ops`.
- Valkey runs locally on `cybervpn-h-ops`.
- This is not the final managed PostgreSQL/Valkey topology from DEC-S1-004/DEC-S1-005.
- Customer-facing availability remains limited by the home server risk until managed data services are adopted.

## Server Layout

| Path | Purpose | Owner | Mode |
|---|---|---:|---:|
| `/srv/cybervpn-h/compose/app/.env` | root-only compose interpolation secrets | `root:root` | `0600` |
| `/srv/cybervpn-h/compose/app/postgres` | PostgreSQL service config/data support directory | `root:root` | `0755` |
| `/srv/cybervpn-h/compose/app/valkey` | Valkey service config support directory | `root:root` | `0755` |
| `/srv/storage/backups/cybervpn-stage1/postgres` | off-root PostgreSQL backup storage | `root:root` | `0700` |

The compose `.env` contains 18 keys. Secret values are intentionally absent from this evidence.

## Data Service Startup

Server compose validation with the root-only data `.env` passed:

```text
server-compose-with-data-env-ok
```

```text
DATA_SERVICES_UP result=ok
POSTGRES_READY result=ok
VALKEY_READY result=ok
```

Running data containers:

```text
cybervpn-stage1-cybervpn-postgres-1 ports=5432/tcp status=Up ... (healthy)
cybervpn-stage1-cybervpn-valkey-1 ports=6379/tcp status=Up ... (healthy)
```

The ports shown above are container ports only. No host ports were published for PostgreSQL or Valkey.

The data containers were intentionally left running for the next deployment step.

## DB Separation

Separate databases/users were created for CyberVPN and Remnawave:

```text
DB_BOOTSTRAP result=ok app_db=cybervpn app_user=cybervpn_app remnawave_db=remnawave remnawave_user=remnawave_app
```

## Clean Migration

The backend Alembic migration was executed through the loaded immutable backend image:

```text
local/cybervpn-backend:stage1-beta-rc.1
```

Result:

```text
MIGRATIONS result=ok alembic_version=20260423_p27_partner_events public_table_count=120 import_secrets=ephemeral
```

Note: Alembic imports backend settings. Required runtime settings such as `JWT_SECRET`, `REMNAWAVE_TOKEN` and `CRYPTOBOT_TOKEN` were supplied as ephemeral generated process environment values only for the migration container. They were not persisted and are not production secrets.

## Backup Artifact

Backup command type:

```text
pg_dump -Fc --no-owner --no-acl
```

Backup artifact:

| Field | Value |
|---|---|
| Path | `/srv/storage/backups/cybervpn-stage1/postgres/stage1-pub-06-cybervpn-20260510T185056Z.dump` |
| Owner | `root:root` |
| Mode | `0600` |
| Size | `711191` bytes |
| SHA-256 | `2b8de41b5a4dae5bc218bfa265e1bb2a2a6bfd27474103ab14b1196268534841` |

## Valkey Policy

```text
VALKEY_STATE result=ok ping=PONG maxmemory_policy=noeviction appendonly=no durable_source_of_truth=no
```

Valkey is explicitly not a durable source of truth for S1. Critical jobs/payment/provisioning state must be recoverable from PostgreSQL.

## Follow-Up

Before full production-grade launch, move PostgreSQL/Valkey to managed/private services or document renewed owner risk acceptance for running customer data on the home server.
