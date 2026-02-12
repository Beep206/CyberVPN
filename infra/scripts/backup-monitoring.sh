#!/usr/bin/env bash
set -euo pipefail

# Backup monitoring Docker volumes (Grafana, Prometheus, Loki, Alertmanager)
# Retention: 7 days

BACKUP_DIR="${BACKUP_DIR:-./backups/monitoring}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
VOLUMES=(grafana_data prometheus_data loki_data alertmanager_data)

mkdir -p "$BACKUP_DIR"

for vol in "${VOLUMES[@]}"; do
  dest="$BACKUP_DIR/${vol}_${TIMESTAMP}.tar.gz"
  echo "Backing up volume $vol → $dest"
  docker run --rm \
    -v "$vol":/source:ro \
    -v "$(cd "$BACKUP_DIR" && pwd)":/backup \
    alpine tar czf "/backup/${vol}_${TIMESTAMP}.tar.gz" -C /source .
  echo "  Done ($(du -h "$dest" | cut -f1))"
done

# Prune backups older than 7 days
echo "Pruning backups older than 7 days..."
find "$BACKUP_DIR" -name '*.tar.gz' -mtime +7 -delete

echo "Backup complete."
