> CyberVPN Launch Program
> Версия: 0.1-draft
> Дата evidence: 2026-05-03
> Backlog ID: `S1-INFRA-009`
> Статус: PASS for local Docker/Compose core stack. This is local/dev evidence only.

# S1-INFRA-009 Local Docker / Compose Evidence

## Purpose

Этот документ закрывает `S1-INFRA-009`: verify local Docker/Compose stack. Цель — подтвердить, что локальный Docker доступен, `infra/docker-compose.yml` валиден, default local core stack поднимается, а базовые локальные сервисы отвечают.

Это не production/staging evidence и не заменяет будущие gates по production Remnawave, managed PostgreSQL, private Valkey/Redis, DNS/TLS, backups or rollback.

## Commands Executed

```bash
docker --version
docker compose version
test -f infra/.env
test -f infra/.env.example
docker compose -f infra/docker-compose.yml config --quiet
docker compose -f infra/docker-compose.yml config --services
docker compose -f infra/docker-compose.yml config --profiles
docker compose -f infra/docker-compose.yml up -d
docker compose -f infra/docker-compose.yml ps --format json
docker inspect --format '{{.Name}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' remnawave-db remnawave-redis remnawave db-backup
curl -fsS http://127.0.0.1:3001/health
docker exec remnawave-redis valkey-cli ping
docker exec remnawave-db sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker compose -f infra/docker-compose.yml port remnawave 3000
docker compose -f infra/docker-compose.yml port remnawave 3001
docker compose -f infra/docker-compose.yml port remnawave-db 5432
docker compose -f infra/docker-compose.yml port remnawave-redis 6379
docker compose -f infra/docker-compose.yml images remnawave remnawave-db remnawave-redis db-backup
docker compose -f infra/docker-compose.yml ps --services --status running
```

`infra/.env` exists but its contents were not printed to avoid exposing secrets.

## Tooling Result

| Check | Result |
|---|---|
| Docker version | `Docker version 29.4.0, build 9d7ad9f` |
| Docker Compose version | `Docker Compose version v5.1.2` |
| `infra/.env` | Exists |
| `infra/.env.example` | Exists |
| Compose config validation | PASS: `docker compose -f infra/docker-compose.yml config --quiet` exited `0` |

## Compose Inventory

Default services:

```text
remnawave-db
db-backup
remnawave-redis
remnawave
```

Available profiles:

```text
bot
email-test
helix
helix-lab
monitoring
proxy
subscription
worker
```

## Local Core Stack Result

The default local core stack was started with:

```bash
docker compose -f infra/docker-compose.yml up -d
```

Running services after startup:

```text
db-backup
remnawave
remnawave-db
remnawave-redis
```

Docker health:

```text
/remnawave-db running healthy
/remnawave-redis running healthy
/remnawave running healthy
/db-backup running healthy
```

Core images:

| Container | Image | Image digest / ID |
|---|---|---|
| `remnawave-db` | `postgres:17.7` | `sha256:7352e0c4d62bbac8aa69d95e40220a60967c4a19f9c4f65b4d118175f7ce9e3b` |
| `remnawave-redis` | `valkey/valkey:8.1-alpine` | `sha256:3c3ccc8571d4866ec5ac5ffb2519b6b6a1fdbf6b5ff5fdab075413026fbff273` |
| `remnawave` | `remnawave/backend:2.7.4` | `sha256:a0e9a3d52e898b894965baed38ee45245b2cdb59ba19e198ab6371319e2968fc` |
| `db-backup` | `prodrigestivill/postgres-backup-local:17` | `sha256:e803bd9eb4bfb42e9b3e74ba411227f3d55da292905800395659cc579b6641e8` |

Local port bindings:

```text
remnawave app:      127.0.0.1:3005 -> 3000/tcp
remnawave metrics:  127.0.0.1:3001 -> 3001/tcp
postgres:           127.0.0.1:6767 -> 5432/tcp
valkey:             127.0.0.1:6379 -> 6379/tcp
```

Networks present:

```text
cybervpn-backend bridge local
cybervpn-data bridge local
cybervpn-frontend bridge local
cybervpn-monitoring bridge local
```

Volume present:

```text
remnawave-db-data local
```

## Local Health Checks

Remnawave health endpoint:

```json
{"status":"ok","info":{"database":{"status":"up"}},"error":{},"details":{"database":{"status":"up"}}}
```

Valkey ping:

```text
PONG
```

PostgreSQL readiness:

```text
/var/run/postgresql:5432 - accepting connections
```

## Observation

The scoped core image inventory command passed:

```bash
docker compose -f infra/docker-compose.yml images remnawave remnawave-db remnawave-redis db-backup
```

An unscoped `docker compose -f infra/docker-compose.yml images` command returned a missing image SHA error for a non-core/profile-related image. This does not block `S1-INFRA-009` because:

- default core services are running and healthy;
- scoped core service image inventory is available;
- profile services are not part of this task;
- profile-specific images should be checked when their own work packages start.

## Result

`S1-INFRA-009` result: **PASS**.

Acceptance met:

- Docker and Docker Compose are available.
- `infra/docker-compose.yml` validates.
- Default local core stack starts.
- Remnawave, PostgreSQL, Valkey and local backup container are running and healthy.
- Local service inventory is captured.

The local stack was left running intentionally for the next task, `S1-VPN-012`.

## Next Work Item

Next ID to execute: `S1-VPN-012` — run local Remnawave smoke.

