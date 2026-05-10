#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
ARTIFACT_DIR="${SECURITY_ARTIFACT_DIR:-${ROOT_DIR}/security-artifacts}"
TRIVY_IMAGE="${TRIVY_IMAGE:-aquasec/trivy:0.70.0}"
GRYPE_IMAGE="${GRYPE_IMAGE:-anchore/grype:v0.112.0}"

mkdir -p "${ARTIFACT_DIR}/container"

run_trivy_fs() {
  if command -v trivy >/dev/null 2>&1; then
    trivy fs \
      --scanners vuln,misconfig \
      --skip-dirs '**/.git' \
      --skip-dirs '**/node_modules' \
      --skip-dirs '**/node_modules/**' \
      --skip-dirs '**/.tmp' \
      --skip-dirs '**/.tmp/**' \
      --skip-dirs '**/.cache' \
      --skip-dirs '**/.cache/**' \
      --skip-dirs '**/.terraform' \
      --skip-dirs '**/.terraform/**' \
      --skip-dirs '**/.venv' \
      --skip-dirs '**/.venv/**' \
      --skip-dirs '**/build' \
      --skip-dirs '**/build/**' \
      --skip-dirs '**/dist' \
      --skip-dirs '**/dist/**' \
      --skip-dirs '**/target' \
      --skip-dirs '**/target/**' \
      --skip-dirs '**/coverage' \
      --skip-dirs '**/coverage/**' \
      --skip-dirs '**/.gradle' \
      --skip-dirs '**/.gradle/**' \
      --skip-dirs '**/apps/android-tv/app/build' \
      --skip-dirs '**/cybervpn_mobile/.dart_tool' \
      --skip-dirs '**/frontend/.next' \
      --skip-dirs '**/admin/.next' \
      --skip-dirs '**/partner/.next' \
      --format json \
      --output "${ARTIFACT_DIR}/container/trivy-fs.json" \
      "${ROOT_DIR}"
  else
    docker run --rm \
      -v "${ROOT_DIR}:/repo:ro" \
      -v "${ARTIFACT_DIR}/container:/out" \
      "${TRIVY_IMAGE}" \
      fs \
      --scanners vuln,misconfig \
      --skip-dirs '**/.git' \
      --skip-dirs '**/node_modules' \
      --skip-dirs '**/node_modules/**' \
      --skip-dirs '**/.tmp' \
      --skip-dirs '**/.tmp/**' \
      --skip-dirs '**/.cache' \
      --skip-dirs '**/.cache/**' \
      --skip-dirs '**/.terraform' \
      --skip-dirs '**/.terraform/**' \
      --skip-dirs '**/.venv' \
      --skip-dirs '**/.venv/**' \
      --skip-dirs '**/build' \
      --skip-dirs '**/build/**' \
      --skip-dirs '**/dist' \
      --skip-dirs '**/dist/**' \
      --skip-dirs '**/target' \
      --skip-dirs '**/target/**' \
      --skip-dirs '**/coverage' \
      --skip-dirs '**/coverage/**' \
      --skip-dirs '**/.gradle' \
      --skip-dirs '**/.gradle/**' \
      --skip-dirs '**/apps/android-tv/app/build' \
      --skip-dirs '**/cybervpn_mobile/.dart_tool' \
      --skip-dirs '**/frontend/.next' \
      --skip-dirs '**/admin/.next' \
      --skip-dirs '**/partner/.next' \
      --format json \
      --output /out/trivy-fs.json \
      /repo
  fi
}

run_grype_dir() {
  local output_tmp="${ARTIFACT_DIR}/container/grype-dir.json.tmp"
  rm -f "${output_tmp}"

  if command -v grype >/dev/null 2>&1; then
    for attempt in 1 2 3; do
      if grype dir:"${ROOT_DIR}" \
        --exclude '**/.git/**' \
        --exclude '**/node_modules/**' \
        --exclude '**/.tmp/**' \
        --exclude '**/.cache/**' \
        --exclude '**/.terraform/**' \
        --exclude '**/.venv/**' \
        --exclude '**/build/**' \
        --exclude '**/dist/**' \
        --exclude '**/target/**' \
        --exclude '**/coverage/**' \
        --exclude '**/.gradle/**' \
        --exclude '**/apps/android-tv/app/build/**' \
        --exclude '**/cybervpn_mobile/.dart_tool/**' \
        --exclude '**/frontend/.next/**' \
        --exclude '**/admin/.next/**' \
        --exclude '**/partner/.next/**' \
        -o json > "${output_tmp}"; then
        mv "${output_tmp}" "${ARTIFACT_DIR}/container/grype-dir.json"
        return 0
      fi
      sleep "$((attempt * 5))"
    done
  else
    for attempt in 1 2 3; do
      if docker run --rm \
        -v "${ROOT_DIR}:/repo:ro" \
        "${GRYPE_IMAGE}" \
        dir:/repo \
        --exclude '**/.git/**' \
        --exclude '**/node_modules/**' \
        --exclude '**/.tmp/**' \
        --exclude '**/.cache/**' \
        --exclude '**/.terraform/**' \
        --exclude '**/.venv/**' \
        --exclude '**/build/**' \
        --exclude '**/dist/**' \
        --exclude '**/target/**' \
        --exclude '**/coverage/**' \
        --exclude '**/.gradle/**' \
        --exclude '**/apps/android-tv/app/build/**' \
        --exclude '**/cybervpn_mobile/.dart_tool/**' \
        --exclude '**/frontend/.next/**' \
        --exclude '**/admin/.next/**' \
        --exclude '**/partner/.next/**' \
        -o json > "${output_tmp}"; then
        mv "${output_tmp}" "${ARTIFACT_DIR}/container/grype-dir.json"
        return 0
      fi
      sleep "$((attempt * 5))"
    done
  fi

  rm -f "${output_tmp}"
  cat > "${ARTIFACT_DIR}/container/grype-dir.json" <<'EOF'
{"status":"error","scanner":"grype","message":"grype scan failed after retries; see CI job log"}
EOF
  printf 'status=error\nscanner=grype\nmessage=grype scan failed after retries; see CI job log\n' \
    > "${ARTIFACT_DIR}/container/grype-dir.status.txt"

  if [[ "${PHASE20_GRYPE_REQUIRED:-false}" == "true" ]]; then
    echo "ERROR: grype scan failed after retries" >&2
    return 1
  fi

  echo "WARN: grype scan failed after retries; continuing with trivy evidence" >&2
  return 0
}

run_trivy_fs
run_grype_dir
