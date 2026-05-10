#!/usr/bin/env bash
set -euo pipefail

SERVER_RESTORE_DRILL_SCRIPT="${SERVER_RESTORE_DRILL_SCRIPT:-/srv/cybervpn-h/scripts/run-restore-drill.sh}"
EVIDENCE_ROOT="${RESTORE_DRILL_EVIDENCE_ROOT:-/srv/storage/evidence/restores}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="${EVIDENCE_ROOT}/scheduled-restore-drill-${STAMP}"

mkdir -p "${LOG_DIR}"

{
  printf 'scheduled_restore_drill_started=%s\n' "${STAMP}"
  printf 'script=%s\n' "${SERVER_RESTORE_DRILL_SCRIPT}"
  if [[ ! -x "${SERVER_RESTORE_DRILL_SCRIPT}" ]]; then
    printf 'status=blocked\n'
    printf 'reason=restore_drill_script_missing_or_not_executable\n'
    exit 1
  fi
  "${SERVER_RESTORE_DRILL_SCRIPT}"
  printf 'status=completed\n'
  printf 'scheduled_restore_drill_finished=%s\n' "$(date -u +%Y%m%dT%H%M%SZ)"
} | tee "${LOG_DIR}/scheduled-restore-drill.log"
