# Infrastructure

Local Docker Compose stack that mirrors the launch plan in `docs/plans/legacy/vpn-business-deployment-guide.md`.

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

Helix lab profiles are opt-in:

```bash
# Adapter only
docker compose --profile helix up -d

# Adapter + two local lab nodes + monitoring + worker audits
docker compose --profile helix-lab --profile monitoring --profile worker up -d
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
- Prometheus: http://localhost:9094 (monitoring profile)
- Grafana: http://localhost:3002 (monitoring profile)
- Helix adapter: http://localhost:8088/healthz (helix profile)
- Helix lab node: http://localhost:8091/healthz (helix-lab profile)
- Helix lab node 02: http://localhost:8092/healthz (helix-lab profile)

## Helix Lab

The Helix lab keeps `Remnawave` authoritative while adding an adapter and two lab node
daemons around it, so route failover can be exercised against a real secondary path.

1. Copy `infra/.env.example` to `infra/.env` if you have not already.
2. Fill in:
   - `HELIX_INTERNAL_AUTH_TOKEN`
   - `HELIX_MANIFEST_SIGNING_KEY`
   - `HELIX_REMNAWAVE_TOKEN` once you have a real local API token
3. Review reference templates:
   - `infra/helix/adapter.env.example`
   - `infra/helix/node.env.example`
4. Start the core stack and lab services:

```bash
cd infra
docker compose --profile helix-lab --profile monitoring --profile worker up -d
```

5. Bootstrap the local lab assignment state:

```bash
bash infra/tests/bootstrap_helix_lab.sh
```

6. Verify:
   - adapter health: `curl http://localhost:8088/readyz`
   - node health: `curl http://localhost:8091/readyz`
   - node 02 health: `curl http://localhost:8092/readyz`
   - Prometheus targets: `curl http://localhost:9094/api/v1/targets`
   - Grafana dashboard: `CyberVPN Helix`

### Helix Headless Perf Lab

Once the lab stack is healthy, you can drive Helix perf runs directly from the desktop workspace:

```powershell
powershell -ExecutionPolicy Bypass -File apps/desktop-client/scripts/run_helix_lab_bench.ps1 -UseSyntheticLabTarget
powershell -ExecutionPolicy Bypass -File apps/desktop-client/scripts/run_helix_recovery_lab.ps1 -Mode failover -UseSyntheticLabTarget
powershell -ExecutionPolicy Bypass -File apps/desktop-client/scripts/run_helix_target_matrix.ps1 -Preset mixed -UseSyntheticLabTarget
```

Artifacts land under `apps/desktop-client/.artifacts/*` and include runtime config, manifest,
sidecar stdout/stderr, health snapshots, telemetry snapshots, and the JSON report for each run.

The adapter applies SQLx migrations on startup. The lab nodes keep their state in the
`helix_node_state` and `helix_node_state_2` Docker volumes so rollback and last-known-good
behavior survive container restarts.

### Helix Rollback And Hardening Drills

Static rollback verification:

```bash
bash infra/tests/verify_helix_rollback.sh
```

Destructive live rollback verification:

```bash
HELIX_REQUIRE_LIVE=true HELIX_RUN_DESTRUCTIVE_DRILL=true bash infra/tests/verify_helix_rollback.sh
```

Reset lab history before a new destructive drill:

```bash
bash infra/tests/reset_helix_lab_history.sh
```

Helix backend live load scenario lives in:

```text
backend/tests/load/test_helix_load.py
```

Deterministic local canary-evidence budget test:

```text
backend/tests/load/test_helix_canary_evidence_budget.py
```

See [docs/testing/helix-load-test-plan.md](C:/project/CyberVPN/docs/testing/helix-load-test-plan.md) for the required environment and the internal-beta acceptance rules.

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
- Subscription Page requires a Remnawave API token from the panel.
- Helix alerts live in `infra/prometheus/rules/helix_alerts.yml`.
- Run `bash infra/tests/test_helix_stack.sh` after profile changes to verify the lab wiring.
- Run `bash infra/tests/verify_helix_rollback.sh` to verify rollback-drill prerequisites and, optionally, execute a destructive rollback rehearsal with `HELIX_RUN_DESTRUCTIVE_DRILL=true`.
