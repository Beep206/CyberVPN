#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
EVIDENCE_DIR="${ROOT_DIR}/.tmp/stage1-secrets"
SNAPSHOT_DIR="${TMPDIR:-/tmp}/cybervpn-s1-gitleaks-current-tree"
BASELINE_PATH="${ROOT_DIR}/.gitleaks.s1.current-tree.baseline.json"
REPORT_PATH="${EVIDENCE_DIR}/gitleaks-s1-current-tree-redacted.json"
GITLEAKS_EXIT_CODE="${GITLEAKS_EXIT_CODE:-1}"

mkdir -p "${EVIDENCE_DIR}"
rm -rf "${SNAPSHOT_DIR}"
mkdir -p "${SNAPSHOT_DIR}"

cd "${ROOT_DIR}"

git ls-files -z | rsync -a --files-from=- --from0 ./ "${SNAPSHOT_DIR}/"

if git ls-files --others --exclude-standard -z docs/cybervpn_stage1_launch_docs | grep -qz .; then
  git ls-files --others --exclude-standard -z docs/cybervpn_stage1_launch_docs \
    | rsync -a --files-from=- --from0 ./ "${SNAPSHOT_DIR}/"
fi

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

jq -r 'group_by(.RuleID)[] | [.[0].RuleID, length] | @tsv' "${REPORT_PATH}" \
  > "${EVIDENCE_DIR}/gitleaks-s1-current-tree-by-rule.tsv"
jq -r 'group_by(.File)[] | [.[0].File, length] | @tsv' "${REPORT_PATH}" \
  > "${EVIDENCE_DIR}/gitleaks-s1-current-tree-by-file.tsv"
