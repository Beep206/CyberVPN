#!/usr/bin/env bash
set -Eeuo pipefail

evidence_root="${EVIDENCE_ROOT:-/srv/storage/evidence}"
apply=false

if [[ "${1:-}" == "--apply" ]]; then
  apply=true
elif [[ -n "${1:-}" ]]; then
  evidence_root="$1"
fi

if [[ "${2:-}" == "--apply" ]]; then
  apply=true
fi

if [[ ! -d "${evidence_root}" ]]; then
  echo "ERROR: missing evidence root: ${evidence_root}" >&2
  exit 1
fi

report_candidates() {
  local label="$1"
  local path="$2"
  local days="$3"

  echo "## ${label}: ${path}, older than ${days} days"
  if [[ -d "${path}" ]]; then
    find "${path}" -mindepth 1 -maxdepth 1 -type d -mtime "+${days}" -print | sort
  else
    echo "missing"
  fi
  echo
}

delete_candidates() {
  local path="$1"
  local days="$2"

  if [[ -d "${path}" ]]; then
    find "${path}" -mindepth 1 -maxdepth 1 -type d -mtime "+${days}" -print0 | xargs -0r rm -rf --
  fi
}

cat <<EOF
# CyberVPN Evidence Retention Report

created_at_utc=$(date -u --iso-8601=seconds)
evidence_root=${evidence_root}
mode=$([[ "${apply}" == true ]] && echo apply || echo dry-run)

Policy summary:
- releases: keep indefinitely unless a release owner explicitly archives/removes a failed rehearsal.
- incidents: keep indefinitely.
- restores: keep at least 24 months; keep first successful restore evidence for each major service indefinitely.
- backups: keep backup evidence logs at least 12 months; restic snapshot retention is managed separately.
- security-scans: keep at least 12 months; scans tied to releases are also referenced from the release pack.

EOF

report_candidates "backup evidence cleanup candidates" "${evidence_root}/backups" 365
report_candidates "security scan cleanup candidates" "${evidence_root}/security-scans" 365
report_candidates "restore evidence review candidates" "${evidence_root}/restores" 730

if [[ "${apply}" == true ]]; then
  delete_candidates "${evidence_root}/backups" 365
  delete_candidates "${evidence_root}/security-scans" 365
  echo "apply_status=completed"
else
  echo "apply_status=dry_run_only"
fi
