#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

if [[ ${EUID} -ne 0 ]]; then
  echo "ERROR: run as root" >&2
  exit 1
fi

timestamp="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"
backup_root="${OBSERVABILITY_BACKUP_ROOT:-/srv/storage/backups/observability}"
evidence_root="${BACKUP_EVIDENCE_DIR:-/srv/cybervpn-h/evidence/backups}"
backup_dir="${backup_root}/grafana-${timestamp}"
evidence_dir="${evidence_root}/observability-backup-${timestamp}"

install -d -m 0700 "${backup_dir}" "${evidence_dir}"
log_file="${evidence_dir}/backup.log"
exec > >(tee -a "${log_file}") 2>&1

printf 'started_at_utc=%s\n' "$(date -u --iso-8601=seconds)" | tee "${evidence_dir}/summary.txt"
printf 'backup_dir=%s\n' "${backup_dir}" | tee -a "${evidence_dir}/summary.txt"

if [[ ! -d /srv/cybervpn-h/configs/grafana/dashboards ]]; then
  echo "ERROR: missing /srv/cybervpn-h/configs/grafana/dashboards" >&2
  exit 1
fi

tar -C /srv/cybervpn-h/configs \
  -czf "${backup_dir}/grafana-dashboards.tgz" \
  grafana/dashboards \
  grafana/provisioning

find /srv/cybervpn-h/configs/grafana/dashboards -type f -name '*.json' \
  -printf '%f\t%s\t%TY-%Tm-%TdT%TH:%TM:%TS\t%p\n' \
  | sort > "${backup_dir}/dashboard-manifest.tsv"

(
  cd /srv/cybervpn-h/configs
  find grafana/dashboards grafana/provisioning -type f -print0 \
    | sort -z \
    | xargs -0 sha256sum
) > "${backup_dir}/dashboard-checksums.sha256"

if command -v sqlite3 >/dev/null 2>&1 && [[ -f /srv/observability/grafana/grafana.db ]]; then
  sqlite3 /srv/observability/grafana/grafana.db \
    "select count(*) from dashboard;" > "${backup_dir}/grafana-sqlite-dashboard-count.txt"
  sqlite3 /srv/observability/grafana/grafana.db \
    ".backup '${backup_dir}/grafana.db'"
fi

docker ps --filter name=cybervpn-grafana \
  --format '{{.Names}}\t{{.Image}}\t{{.Status}}' > "${backup_dir}/grafana-container.txt" || true

dashboard_count="$(find /srv/cybervpn-h/configs/grafana/dashboards -type f -name '*.json' | wc -l)"
printf 'dashboard_json_count=%s\n' "${dashboard_count}" | tee -a "${evidence_dir}/summary.txt"
du -sh "${backup_dir}" > "${backup_dir}/du-summary.txt"
sha256sum "${backup_dir}"/* > "${backup_dir}/checksums.sha256"
printf 'finished_at_utc=%s\nstatus=ok\n' "$(date -u --iso-8601=seconds)" | tee -a "${evidence_dir}/summary.txt"
