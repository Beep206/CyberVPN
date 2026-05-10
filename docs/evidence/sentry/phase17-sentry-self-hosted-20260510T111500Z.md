# Phase 17 Sentry Self-Hosted Evidence

Date: 2026-05-10
Host: `cybervpn-h-ops` / `10.10.10.34`
Service URL: `https://sentry.h.cyber-vpn.net`

## Deployment

- Source: official `getsentry/self-hosted` release `26.4.2`.
- Compose directory: `/srv/cybervpn-h/compose/sentry`.
- Secret env: `/srv/cybervpn-h/secrets/sentry.env` (`0600`, root only).
- Public route: Caddy `sentry.h.cyber-vpn.net` -> `http://127.0.0.1:9000`.
- Caddy reload status: `active`.

## Configuration

- `COMPOSE_PROFILES=errors-only`.
- `SENTRY_EVENT_RETENTION_DAYS=30`.
- `SENTRY_BIND=127.0.0.1:9000`.
- `SENTRY_TASKWORKER_CONCURRENCY=2`.
- Public signup disabled with `SENTRY_FEATURES["auth:register"] = False`.
- Organization-level `require_2fa` enabled for the `sentry` organization.
- Sentry beacon disabled with `SENTRY_BEACON = False`.
- Secure proxy headers and CSRF origin configured for `https://sentry.h.cyber-vpn.net`.

## Storage

- `/srv/storage` is `/dev/sda1`, `ext4`, mounted with `noatime`.
- `sentry-data` Docker volume is a bind volume to `/srv/storage/sentry-attachments`.
- Latest backup directory: `/srv/storage/backups/sentry/sentry-20260510T111907Z`.
- Latest backup symlink: `/srv/storage/backups/sentry/latest`.

## Resource Limits

All Sentry containers have explicit Docker CPU and memory limits in:

```text
/srv/cybervpn-h/compose/sentry/docker-compose.override.yml
```

Post-limit sample from `docker stats`:

```text
sentry-self-hosted-web-1 1.32GiB / 3GiB
sentry-self-hosted-taskworker-1 720.3MiB / 3GiB
sentry-self-hosted-clickhouse-1 163.4MiB / 4GiB
sentry-self-hosted-kafka-1 406.3MiB / 3GiB
sentry-self-hosted-postgres-1 25.6MiB / 2GiB
sentry-self-hosted-attachments-consumer-1 687.5MiB / 1GiB
```

## Health And Smoke

Health check:

```text
curl -k https://sentry.h.cyber-vpn.net/_health/ -> HTTP 200
```

Smoke project:

```text
cybervpn-phase17-smoke
```

Smoke events:

```text
CyberVPN Phase 17 Sentry smoke event
CyberVPN Phase 17 Sentry smoke event after resource limits
```

Post-ingestion query:

```text
project_id=2
group_count=2
latest=[
  (2, "CyberVPN Phase 17 Sentry smoke event after resource limits", "2026-05-10T11:10:17+00:00"),
  (1, "CyberVPN Phase 17 Sentry smoke event", "2026-05-10T11:05:56+00:00")
]
```

## Backup

Backup script:

```text
/srv/cybervpn-h/scripts/backup-sentry.sh
```

Runbooks:

```text
/srv/cybervpn-h/runbooks/sentry-ops.md
/srv/cybervpn-h/runbooks/sentry-restore.md
```

Backup contents:

- `sentry-config-export.json`
- `postgres-dumpall.sql`
- rendered Compose config
- Compose source bundle
- Docker volume inspect output
- storage mount evidence

Backup evidence:

```text
/srv/cybervpn-h/evidence/backups/sentry-backup-20260510T111907Z
status=ok
restic snapshot=0dc4f761
```

## Remote Evidence

Detailed remote logs are stored under:

```text
/srv/cybervpn-h/evidence/sentry/phase17-sentry-20260510T103842Z
```

Important files:

```text
install-rerun3.log
compose-up-wait.log
compose-up-after-limits.log
caddy-sentry-block.out
smoke-group-query-after-limits.out
docker-stats-after-limits.out
```
