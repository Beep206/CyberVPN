#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
EVIDENCE_DIR="${SECURITY_ARTIFACT_DIR:-${ROOT_DIR}/.tmp/stage1-secrets}"
SNAPSHOT_DIR="${GITLEAKS_SNAPSHOT_DIR:-/scan}"
BASELINE_PATH="${ROOT_DIR}/.gitleaks.s1.current-tree.baseline.json"
REPORT_PATH="${EVIDENCE_DIR}/gitleaks-s1-current-tree-redacted.json"
GITLEAKS_EXIT_CODE="${GITLEAKS_EXIT_CODE:-1}"

mkdir -p "${EVIDENCE_DIR}"
if ! rm -rf "${SNAPSHOT_DIR}" 2>/dev/null || ! mkdir -p "${SNAPSHOT_DIR}" 2>/dev/null; then
  SNAPSHOT_DIR="${TMPDIR:-/tmp}/cybervpn-s1-gitleaks-current-tree"
  rm -rf "${SNAPSHOT_DIR}"
  mkdir -p "${SNAPSHOT_DIR}"
fi

cd "${ROOT_DIR}"

copy_git_paths() {
  local rel_path
  while IFS= read -r -d '' rel_path; do
    if [[ -e "${rel_path}" || -L "${rel_path}" ]]; then
      mkdir -p "${SNAPSHOT_DIR}/$(dirname "${rel_path}")"
      cp -a "${rel_path}" "${SNAPSHOT_DIR}/${rel_path}"
    fi
  done
}

git ls-files -z | copy_git_paths
git ls-files --others --exclude-standard -z | copy_git_paths

GITLEAKS_ARGS=(
  detect
  --source "${SNAPSHOT_DIR}"
  --no-git
  --redact=100
  --report-format json
  --report-path "${REPORT_PATH}"
  --no-banner
  --no-color
  --exit-code "${GITLEAKS_EXIT_CODE}"
  --timeout 300
)

if [[ -f "${BASELINE_PATH}" ]]; then
  GITLEAKS_ARGS+=(--baseline-path "${BASELINE_PATH}")
fi

if command -v gitleaks >/dev/null 2>&1 && [[ "${SNAPSHOT_DIR}" == "/scan" || ! -f "${BASELINE_PATH}" ]]; then
  gitleaks "${GITLEAKS_ARGS[@]}"
else
  DOCKER_ARGS=(
    run
    --rm
    -v "${SNAPSHOT_DIR}:/scan:ro"
    -v "${EVIDENCE_DIR}:/out"
    -v "${ROOT_DIR}:/repo:ro"
    ghcr.io/gitleaks/gitleaks:latest
    detect
    --source /scan
    --no-git
    --redact=100
    --report-format json
    --report-path /out/gitleaks-s1-current-tree-redacted.json
    --no-banner
    --no-color
    --exit-code "${GITLEAKS_EXIT_CODE}"
    --timeout 300
  )

  if [[ -f "${BASELINE_PATH}" ]]; then
    DOCKER_ARGS+=(--baseline-path /repo/.gitleaks.s1.current-tree.baseline.json)
  fi

  docker "${DOCKER_ARGS[@]}"
fi

if command -v jq >/dev/null 2>&1; then
  jq -r 'group_by(.RuleID)[] | [.[0].RuleID, length] | @tsv' "${REPORT_PATH}" \
    > "${EVIDENCE_DIR}/gitleaks-s1-current-tree-by-rule.tsv"
  jq -r 'group_by(.File)[] | [.[0].File, length] | @tsv' "${REPORT_PATH}" \
    > "${EVIDENCE_DIR}/gitleaks-s1-current-tree-by-file.tsv"
else
  printf 'jq unavailable; see %s\n' "${REPORT_PATH}" > "${EVIDENCE_DIR}/gitleaks-s1-current-tree-summary.txt"
fi
