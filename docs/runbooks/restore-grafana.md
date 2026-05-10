# Grafana Restore Runbook

Host: `cybervpn-h-ops`

Grafana stores provisioned CyberVPN dashboards here:

```text
/srv/cybervpn-h/configs/grafana/dashboards
/srv/cybervpn-h/configs/grafana/provisioning
```

Grafana runtime data is here:

```text
/srv/observability/grafana/grafana.db
```

Prefer restoring dashboards from provisioned JSON files first. Restore `grafana.db` only when you intentionally need UI-created state that is not present in provisioning.

## Backup Location

Timestamped dashboard backup bundles are stored under:

```text
/srv/storage/backups/observability/grafana-<UTC timestamp>
```

Each backup should contain:

```text
grafana-dashboards.tgz
dashboard-manifest.tsv
dashboard-checksums.sha256
grafana-sqlite-dashboard-count.txt
summary.txt
```

## Restore Dashboards To A Test Directory

```bash
sudo -i
BACKUP=/srv/storage/backups/observability/grafana-YYYYMMDDTHHMMSSZ
TARGET=/srv/storage/evidence/restores/grafana-restore-test-$(date -u +%Y%m%dT%H%M%SZ)

install -d -m 0700 "$TARGET"
tar -xzf "$BACKUP/grafana-dashboards.tgz" -C "$TARGET"
find "$TARGET/grafana/dashboards" -type f -name '*.json' | sort > "$TARGET/restored-dashboard-files.txt"
sha256sum -c "$BACKUP/dashboard-checksums.sha256"
```

Use the test restore to confirm that JSON files, counts, and checksums are usable before touching production.

## Restore Dashboards To Production

Maintenance window recommended.

```bash
sudo -i
BACKUP=/srv/storage/backups/observability/grafana-YYYYMMDDTHHMMSSZ
RESTORE=/srv/storage/backups/restore-tests/grafana-production-restore-preview-$(date -u +%Y%m%dT%H%M%SZ)

install -d -m 0700 "$RESTORE"
tar -xzf "$BACKUP/grafana-dashboards.tgz" -C "$RESTORE"
rsync -a --delete "$RESTORE/grafana/dashboards/" /srv/cybervpn-h/configs/grafana/dashboards/
docker restart cybervpn-grafana
```

Verify:

```bash
docker ps --filter name=cybervpn-grafana
curl -fsS http://127.0.0.1:3000/api/health
```

## Missing Pieces

If dashboards were changed only through the Grafana UI, export them into provisioning JSON before relying on this restore path. Provisioned JSON is the preferred source of truth.
