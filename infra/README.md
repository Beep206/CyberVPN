# Infrastructure

Local Docker Compose stack that mirrors the launch plan in `plan/vpn-business-deployment-guide.md`.

## Quick start
1. Review and edit `infra/.env` (generated for local use) or copy `infra/.env.example`.
2. Start the core services:

```bash
cd infra
docker compose up -d
```

Optional services are enabled via profiles:

```bash
docker compose --profile proxy --profile subscription --profile bot --profile monitoring up -d
```

### Development mode

For hot-reload, debug ports, and verbose logging:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

Adds: DEBUG logging, Python debugger port (5678), Grafana anonymous auth.

## Local endpoints
- Panel: http://localhost:3000 (or http://panel.localhost with the proxy profile)
- Metrics: http://localhost:3001/metrics
- Postgres: localhost:6767
- Subscription page: http://localhost:3010 (subscription profile)
- Prometheus: http://localhost:9090 (monitoring profile)
- Grafana: http://localhost:3002 (monitoring profile)

## PostgreSQL Backups

The `db-backup` service runs daily automated backups using `pg_dump --format=custom`.

- **Storage:** `infra/backups/postgres/` (host-mounted, outside Docker volumes)
- **Schedule:** Daily at midnight UTC (`@daily`)
- **Retention:** 7 days (older backups auto-deleted)
- **Format:** Custom (compressed, supports selective restore via `pg_restore`)

### Manual backup

```bash
docker exec db-backup /backup.sh
```

### List available backups

```bash
ls -lht infra/backups/postgres/
```

### Restore to existing database (full)

```bash
# Stop the app first to avoid active connections
docker compose stop remnawave

# Restore from the most recent backup
docker exec -i remnawave-db pg_restore \
  --clean --if-exists \
  --dbname="${POSTGRES_DB}" \
  -U "${POSTGRES_USER}" \
  < infra/backups/postgres/<db-name>/latest.dump

# Restart
docker compose start remnawave
```

### Restore to a fresh database

```bash
# Drop and recreate the database
docker exec remnawave-db psql -U "${POSTGRES_USER}" -c "DROP DATABASE IF EXISTS ${POSTGRES_DB};"
docker exec remnawave-db psql -U "${POSTGRES_USER}" -c "CREATE DATABASE ${POSTGRES_DB} OWNER ${POSTGRES_USER};"

# Restore
docker exec -i remnawave-db pg_restore \
  --dbname="${POSTGRES_DB}" \
  -U "${POSTGRES_USER}" \
  < infra/backups/postgres/<db-name>/latest.dump
```

### Restore a single table

```bash
docker exec -i remnawave-db pg_restore \
  --dbname="${POSTGRES_DB}" \
  -U "${POSTGRES_USER}" \
  --table=<table_name> \
  --clean --if-exists \
  < infra/backups/postgres/<db-name>/latest.dump
```

### Verify backup integrity

```bash
# List contents without restoring
pg_restore --list infra/backups/postgres/<db-name>/latest.dump
```

## Valkey (Redis) Zero-Persistence

Valkey runs with persistence disabled (`--save "" --appendonly no`). This is intentional:

- **Use case:** Cache and TaskIQ message broker only — no durable data
- **Benefit:** Lower disk I/O, faster writes, simpler operations
- **Trade-off:** All data lost on container restart (cache rebuilds from DB, pending tasks re-enqueue)
- **No backup needed:** There is no state to back up

If you need durable queues in the future, enable AOF: `--appendonly yes --appendfsync everysec`.

## Notes
- If you change `METRICS_PASS` in `infra/.env`, update `infra/prometheus/prometheus.yml`.
- `infra/postgres/init/001-create-remnashop.sql` auto-creates the `remnashop` database.
- Remnashop and Subscription Page require a Remnawave API token from the panel.
