#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(cd "${ROOT_DIR}/.." && pwd)"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
OUTPUT_DIR="${HELIX_EVIDENCE_OUTPUT_DIR:-${PROJECT_ROOT}/.artifacts/helix-internal-beta/${TIMESTAMP}}"
ROLLBACK_SCRIPT="${ROOT_DIR}/tests/verify_helix_rollback.sh"
BACKEND_BUDGET_TEST="${PROJECT_ROOT}/backend/tests/load/test_helix_canary_evidence_budget.py"
COMPOSE_ENV_FILE="${ROOT_DIR}/.env"
HELIX_API_BASE_URL="${HELIX_API_BASE_URL:-}"
HELIX_ADMIN_BEARER_TOKEN="${HELIX_ADMIN_BEARER_TOKEN:-}"
HELIX_INTERNAL_AUTH_TOKEN="${HELIX_INTERNAL_AUTH_TOKEN:-}"
HELIX_ADAPTER_URL="${HELIX_ADAPTER_URL:-http://127.0.0.1:8088}"
HELIX_ROLLOUT_ID="${HELIX_ROLLOUT_ID:-rollout-helix-lab}"

load_env_file() {
  local env_file="$1"
  if [[ -f "$env_file" ]]; then
    set -a
    # shellcheck disable=SC1090
    source <(tr -d '\r' < "$env_file")
    set +a
  fi
}

copy_latest_artifact() {
  local source_dir="$1"
  local destination_name="$2"

  if [[ ! -d "$source_dir" ]]; then
    return 0
  fi

  local latest_path
  latest_path="$(find "$source_dir" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' | sort -nr | head -n1 | cut -d' ' -f2-)"
  if [[ -z "$latest_path" ]]; then
    return 0
  fi

  cp -R "$latest_path" "${OUTPUT_DIR}/${destination_name}"
}

load_env_file "$COMPOSE_ENV_FILE"

mkdir -p "${OUTPUT_DIR}"

echo "Collecting Helix internal beta evidence into ${OUTPUT_DIR}"

{
  echo "== Helix Rollback Verification =="
  bash "${ROLLBACK_SCRIPT}"
} | tee "${OUTPUT_DIR}/rollback-verification.txt"

if [[ -n "${REMNAWAVE_TOKEN:-}" && -n "${JWT_SECRET:-}" && -n "${CRYPTOBOT_TOKEN:-}" ]]; then
  {
    echo "== Helix Deterministic Canary Evidence Budget =="
    (
      cd "${PROJECT_ROOT}/backend"
      HELIX_ENABLED=true HELIX_ADMIN_ENABLED=true python -m pytest \
        "${BACKEND_BUDGET_TEST}" -q --no-cov
    )
  } | tee "${OUTPUT_DIR}/backend-canary-evidence-budget.txt"
else
  cat <<'EOF' | tee "${OUTPUT_DIR}/backend-canary-evidence-budget.txt"
Skipped deterministic backend canary-evidence budget test.
Set REMNAWAVE_TOKEN, JWT_SECRET, and CRYPTOBOT_TOKEN to run it.
EOF
fi

if [[ -n "${HELIX_API_BASE_URL}" && -n "${HELIX_ADMIN_BEARER_TOKEN}" ]]; then
  {
    echo "== Helix Current Canary Evidence Snapshot =="
    curl -fsS \
      -H "Authorization: Bearer ${HELIX_ADMIN_BEARER_TOKEN}" \
      "${HELIX_API_BASE_URL%/}/api/v1/helix/admin/rollouts/${HELIX_ROLLOUT_ID}/canary-evidence"
  } | tee "${OUTPUT_DIR}/canary-evidence.json"
elif [[ -n "${HELIX_INTERNAL_AUTH_TOKEN}" ]]; then
  {
    echo "== Helix Current Canary Evidence Snapshot (internal) =="
    curl -fsS \
      -H "x-internal-token: ${HELIX_INTERNAL_AUTH_TOKEN}" \
      "${HELIX_ADAPTER_URL%/}/internal/rollouts/${HELIX_ROLLOUT_ID}/canary-evidence"
  } | tee "${OUTPUT_DIR}/canary-evidence.json"
else
  cat <<'EOF' | tee "${OUTPUT_DIR}/canary-evidence.json"
Skipped live canary evidence fetch.
Set HELIX_API_BASE_URL and HELIX_ADMIN_BEARER_TOKEN, or HELIX_INTERNAL_AUTH_TOKEN, to collect it automatically.
EOF
fi

copy_latest_artifact "${PROJECT_ROOT}/apps/desktop-client/.artifacts/helix-live-comparison" "latest-live-comparison"
copy_latest_artifact "${PROJECT_ROOT}/apps/desktop-client/.artifacts/helix-recovery-lab" "latest-recovery-lab"
copy_latest_artifact "${PROJECT_ROOT}/apps/desktop-client/.artifacts/helix-soak" "latest-soak"

cat <<EOF > "${OUTPUT_DIR}/README.txt"
Helix internal beta evidence pack
=================================

Included:
- rollback-verification.txt
- backend-canary-evidence-budget.txt
- canary-evidence.json
- latest-live-comparison/
- latest-recovery-lab/
- latest-soak/

Still collect manually for a full beta gate:
- live Locust report from backend/tests/load/test_helix_load.py
- Desktop support bundle from the beta build
- worker alert timeline for canary gate / canary control / actuations
EOF

echo "Helix internal beta evidence collection complete."
