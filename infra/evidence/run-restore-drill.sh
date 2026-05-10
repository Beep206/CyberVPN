#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

if [[ ${EUID} -ne 0 ]]; then
  echo "ERROR: run as root" >&2
  exit 1
fi

timestamp="${1:-$(date -u +%Y%m%dT%H%M%SZ)}"
restic_env=/srv/cybervpn-h/secrets/restic.env
evidence_root="${EVIDENCE_ROOT:-/srv/storage/evidence/restores}"
evidence_dir="${evidence_root}/cybervpn-h-restore-drill-${timestamp}"

install -d -m 0700 "${evidence_dir}"
log_file="${evidence_dir}/restore-drill.log"
timings_file="${evidence_dir}/timings.tsv"
: > "${timings_file}"
exec > >(tee -a "${log_file}") 2>&1

record_timing() {
  local name="$1"
  local started="$2"
  local finished
  finished="$(date +%s)"
  printf '%s\t%s\n' "${name}" "$((finished - started))" >> "${timings_file}"
}

printf 'started_at_utc=%s\n' "$(date -u --iso-8601=seconds)" | tee "${evidence_dir}/summary.txt"
printf 'host=%s\n' "$(hostname -f 2>/dev/null || hostname)" | tee -a "${evidence_dir}/summary.txt"
printf 'evidence_dir=%s\n' "${evidence_dir}" | tee -a "${evidence_dir}/summary.txt"

if [[ ! -r ${restic_env} ]]; then
  echo "ERROR: missing ${restic_env}" >&2
  exit 1
fi

set -a
. "${restic_env}"
set +a
export RESTIC_REPOSITORY RESTIC_PASSWORD RESTIC_CACHE_DIR
install -d -m 0700 "${RESTIC_CACHE_DIR}"

step_start="$(date +%s)"
restic_json="${evidence_dir}/restic-config-latest-snapshot.json"
restic snapshots --tag configs --latest 1 --json > "${restic_json}"
config_snapshot="$(jq -r '.[0].short_id // .[0].id // empty' "${restic_json}")"
if [[ -z "${config_snapshot}" ]]; then
  echo "ERROR: no configs restic snapshot found" >&2
  exit 1
fi
config_file=/srv/cybervpn-h/runbooks/security-pipeline.md
restic_target="${evidence_dir}/restic-config-file-restore"
install -d -m 0700 "${restic_target}"
restic restore "${config_snapshot}" --target "${restic_target}" --include "${config_file}"
restored_config="${restic_target}${config_file}"
test -s "${restored_config}"
cmp -s "${config_file}" "${restored_config}"
sha256sum "${config_file}" "${restored_config}" > "${evidence_dir}/restic-config-file-checksums.sha256"
printf 'restic_config_snapshot=%s\n' "${config_snapshot}" | tee -a "${evidence_dir}/summary.txt"
printf 'restic_config_file_status=ok\n' | tee -a "${evidence_dir}/summary.txt"
record_timing "restic_config_file_restore" "${step_start}"

step_start="$(date +%s)"
/srv/cybervpn-h/scripts/backup-observability.sh "${timestamp}"
grafana_backup="/srv/storage/backups/observability/grafana-${timestamp}"
grafana_target="${evidence_dir}/grafana-dashboard-restore"
install -d -m 0700 "${grafana_target}"
tar -xzf "${grafana_backup}/grafana-dashboards.tgz" -C "${grafana_target}"
(
  cd "${grafana_target}"
  sha256sum -c "${grafana_backup}/dashboard-checksums.sha256"
) > "${evidence_dir}/grafana-dashboard-checksum-verify.txt"
find "${grafana_target}/grafana/dashboards" -type f -name '*.json' \
  | sort > "${evidence_dir}/grafana-restored-dashboard-files.txt"
grafana_dashboard_count="$(wc -l < "${evidence_dir}/grafana-restored-dashboard-files.txt")"
printf 'grafana_backup=%s\n' "${grafana_backup}" | tee -a "${evidence_dir}/summary.txt"
printf 'grafana_restored_dashboard_json_count=%s\n' "${grafana_dashboard_count}" | tee -a "${evidence_dir}/summary.txt"
record_timing "grafana_dashboard_restore" "${step_start}"

step_start="$(date +%s)"
gitlab_backup="$(find /srv/storage/backups/gitlab -maxdepth 1 -type f -name '*_gitlab_backup.tar' -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)"
if [[ -z "${gitlab_backup}" ]]; then
  echo "ERROR: no GitLab backup archive found" >&2
  exit 1
fi
gitlab_target="${evidence_dir}/gitlab-backup-archive-restore"
install -d -m 0700 "${gitlab_target}/extracted"
tar -tf "${gitlab_backup}" > "${evidence_dir}/gitlab-backup-tar-list.txt"
tar -xf "${gitlab_backup}" -C "${gitlab_target}/extracted"
test -s "${gitlab_target}/extracted/backup_information.yml"
test -s "${gitlab_target}/extracted/db/database.sql.gz"
gzip -t "${gitlab_target}/extracted/db/database.sql.gz"
bundle_count="$(find "${gitlab_target}/extracted/repositories" -type f -name '*.bundle' | wc -l)"
for archive in uploads.tar.gz builds.tar.gz artifacts.tar.gz pages.tar.gz lfs.tar.gz terraform_state.tar.gz packages.tar.gz ci_secure_files.tar.gz; do
  if [[ -f "${gitlab_target}/extracted/${archive}" ]]; then
    tar -tzf "${gitlab_target}/extracted/${archive}" >/dev/null
  fi
done
sha256sum "${gitlab_backup}" > "${evidence_dir}/gitlab-backup-archive.sha256"
cp "${gitlab_target}/extracted/backup_information.yml" "${evidence_dir}/gitlab-backup-information.yml"
du -sh "${gitlab_target}" > "${evidence_dir}/gitlab-restore-du.txt"
printf 'gitlab_backup=%s\n' "${gitlab_backup}" | tee -a "${evidence_dir}/summary.txt"
printf 'gitlab_repository_bundle_count=%s\n' "${bundle_count}" | tee -a "${evidence_dir}/summary.txt"
printf 'gitlab_archive_restore_status=ok\n' | tee -a "${evidence_dir}/summary.txt"
record_timing "gitlab_archive_restore" "${step_start}"

cat > "${evidence_dir}/missing-pieces.md" <<'EOF'
# Missing Pieces And Follow-Ups

- GitLab was validated by archive extraction, database gzip verification, repository bundle count, and subarchive listing in a non-production directory. A full application restore into a separate GitLab container was not performed in this drill to avoid production port, hostname, and secret conflicts on the home server.
- GitLab registry data is skipped by the current GitLab backup command (`SKIP=registry`). Back up `/srv/storage/gitlab-registry` separately before treating registry images as production source of truth.
- Grafana restore validated provisioned dashboard JSON and provisioning files. UI-only Grafana state must be exported into provisioning JSON or restored from `grafana.db` intentionally.
- Offsite backup is still deferred until an external disk or remote encrypted target is available.
EOF

sha256sum "${log_file}" "${timings_file}" "${evidence_dir}/summary.txt" > "${evidence_dir}/evidence-checksums.sha256"
printf 'finished_at_utc=%s\nstatus=ok\n' "$(date -u --iso-8601=seconds)" | tee -a "${evidence_dir}/summary.txt"
