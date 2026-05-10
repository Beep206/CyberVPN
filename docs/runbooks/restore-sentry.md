# Sentry Restore Runbook

Host: `cybervpn-h-ops`

Sentry compose directory:

```text
/srv/cybervpn-h/compose/sentry
```

Backup locations:

```text
/srv/storage/backups/sentry/latest
/srv/storage/backups/sentry/sentry-<UTC timestamp>
restic tag: sentry
```

## Restore Levels

1. Config-only restore: `sentry-config-export.json`.
2. Operational restore: config export plus PostgreSQL dump and attachments.
3. Full historical event restore: cold volume restore of ClickHouse/Kafka/Symbolicator/PostgreSQL/Redis. This needs a maintenance window and version matching.

## Config-Only Restore To A Clean Sentry

```bash
cd /srv/cybervpn-h/compose/sentry
sudo docker compose --env-file .env --env-file .env.custom up -d --wait
sudo install -d -m 0700 /srv/storage/sentry-attachments/restore
sudo cp /srv/storage/backups/sentry/latest/sentry-config-export.json /srv/storage/sentry-attachments/restore/
sudo docker compose --env-file .env --env-file .env.custom run --rm -T web sentry import /data/restore/sentry-config-export.json
```

## PostgreSQL Dump Restore

Use only on a clean or intentionally reset Sentry database.

```bash
cd /srv/cybervpn-h/compose/sentry
sudo docker compose --env-file .env --env-file .env.custom down
# Recreate or restore PostgreSQL volume intentionally here.
sudo docker compose --env-file .env --env-file .env.custom up -d postgres pgbouncer
sudo docker compose --env-file .env --env-file .env.custom exec -T postgres psql -U postgres < /srv/storage/backups/sentry/latest/postgres-dumpall.sql
sudo docker compose --env-file .env --env-file .env.custom up -d --wait
```

## Attachments Restore

Attachments are HDD-backed:

```text
/srv/storage/sentry-attachments
```

Restore only after stopping services that can write attachments:

```bash
sudo rsync -aH --delete /path/to/restored/sentry-attachments/ /srv/storage/sentry-attachments/
sudo chown -R root:root /srv/storage/sentry-attachments
```

## Restic Restore Example

```bash
sudo -i
set -a
. /srv/cybervpn-h/secrets/restic.env
set +a
restic snapshots --tag sentry
TARGET=/srv/storage/evidence/restores/sentry-restore-test-$(date -u +%Y%m%dT%H%M%SZ)
install -d -m 0700 "$TARGET"
restic restore <snapshot-id> --target "$TARGET" --tag sentry
```

## Verification

```bash
curl -k -fsS https://sentry.h.cyber-vpn.net/_health/
cd /srv/cybervpn-h/compose/sentry
sudo docker compose --env-file .env --env-file .env.custom ps
```

After a real restore, send a smoke event and confirm that a new issue appears in Sentry.
