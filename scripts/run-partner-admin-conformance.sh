#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"

mode="all"
if [[ $# -gt 0 ]]; then
  mode="$1"
fi

info() {
  printf "\033[0;34m[INFO]\033[0m  %s\n" "$*"
}

ok() {
  printf "\033[0;32m[OK]\033[0m    %s\n" "$*"
}

fail() {
  printf "\033[0;31m[FAIL]\033[0m  %s\n" "$*"
}

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    fail "Required command '${command_name}' is not available on PATH."
    exit 1
  fi
}

snapshot_file() {
  local file_path="$1"
  local snapshot_path

  if [[ ! -f "${file_path}" ]]; then
    fail "Expected file '${file_path}' does not exist."
    exit 1
  fi

  snapshot_path="$(mktemp)"
  cp "${file_path}" "${snapshot_path}"
  printf "%s" "${snapshot_path}"
}

assert_file_unchanged() {
  local snapshot_path="$1"
  local file_path="$2"
  local label="$3"

  if ! cmp -s "${snapshot_path}" "${file_path}"; then
    fail "${label} drift detected after regeneration."
    diff -u "${snapshot_path}" "${file_path}" || true
    rm -f "${snapshot_path}"
    exit 1
  fi

  rm -f "${snapshot_path}"
  ok "${label} is in sync."
}

python_runner() {
  if [[ -x "${BACKEND_DIR}/.venv/bin/python" ]]; then
    printf "%s" "${BACKEND_DIR}/.venv/bin/python"
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    printf "%s" "python3"
    return
  fi

  if command -v python >/dev/null 2>&1; then
    printf "%s" "python"
    return
  fi

  fail "Python interpreter not found."
  exit 1
}

run_backend() {
  local python_bin
  local openapi_snapshot
  python_bin="$(python_runner)"
  openapi_snapshot="$(snapshot_file "${BACKEND_DIR}/docs/api/openapi.json")"

  info "Exporting backend OpenAPI spec for partner/admin conformance..."
  (
    cd "${REPO_ROOT}"
    REMNAWAVE_TOKEN="${REMNAWAVE_TOKEN:-dummy_token_for_spec_generation_only}" \
    JWT_SECRET="${JWT_SECRET:-partner_admin_conformance_dummy_secret_that_is_at_least_32_chars_long}" \
    CRYPTOBOT_TOKEN="${CRYPTOBOT_TOKEN:-dummy_cryptobot_token}" \
    SWAGGER_ENABLED="${SWAGGER_ENABLED:-true}" \
    DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://x:x@localhost:5432/x}" \
    REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}" \
    "${python_bin}" backend/scripts/export_openapi.py
  )

  info "Checking backend OpenAPI artifact is in sync..."
  assert_file_unchanged "${openapi_snapshot}" "${BACKEND_DIR}/docs/api/openapi.json" "Backend OpenAPI artifact"

  info "Running backend partner/admin conformance contract and e2e packs..."
  (
    cd "${BACKEND_DIR}"
    SKIP_TEST_DB_BOOTSTRAP="${SKIP_TEST_DB_BOOTSTRAP:-1}" \
    "${python_bin}" -m pytest --no-cov \
      tests/contract/test_partner_admin_e2e_conformance_pack.py \
      tests/e2e/test_partner_admin_conformance.py \
      -q
  )
  ok "Backend partner/admin conformance packs passed."
}

run_admin() {
  local types_snapshot
  require_command npm
  types_snapshot="$(snapshot_file "${REPO_ROOT}/admin/src/lib/api/generated/types.ts")"

  info "Regenerating admin API types..."
  (
    cd "${REPO_ROOT}"
    npm run generate:api-types -w admin
  )

  info "Checking admin generated types are in sync..."
  assert_file_unchanged "${types_snapshot}" "${REPO_ROOT}/admin/src/lib/api/generated/types.ts" "Admin generated API type artifact"

  info "Running admin lint..."
  (
    cd "${REPO_ROOT}"
    npm run lint:admin
  )

  info "Building admin workspace..."
  (
    cd "${REPO_ROOT}"
    NEXT_TELEMETRY_DISABLED=1 npm run build:admin
  )
  ok "Admin conformance surface passed."
}

run_partner() {
  local types_snapshot
  require_command npm
  types_snapshot="$(snapshot_file "${REPO_ROOT}/partner/src/lib/api/generated/types.ts")"

  info "Regenerating partner API types..."
  (
    cd "${REPO_ROOT}"
    npm run generate:api-types -w partner
  )

  info "Checking partner generated types are in sync..."
  assert_file_unchanged "${types_snapshot}" "${REPO_ROOT}/partner/src/lib/api/generated/types.ts" "Partner generated API type artifact"

  info "Running partner lint..."
  (
    cd "${REPO_ROOT}"
    npm run lint:partner
  )

  info "Building partner workspace..."
  (
    cd "${REPO_ROOT}"
    NEXT_TELEMETRY_DISABLED=1 npm run build:partner
  )
  ok "Partner conformance surface passed."
}

case "${mode}" in
  all)
    run_backend
    run_admin
    run_partner
    ;;
  --backend)
    run_backend
    ;;
  --admin)
    run_admin
    ;;
  --partner)
    run_partner
    ;;
  *)
    fail "Unknown mode '${mode}'. Use --backend, --admin, --partner, or no argument."
    exit 1
    ;;
esac

ok "Partner/admin conformance run finished successfully."
