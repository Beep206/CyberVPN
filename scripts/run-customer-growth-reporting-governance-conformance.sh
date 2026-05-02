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

  info "Exporting backend OpenAPI spec for growth reporting governance conformance..."
  (
    cd "${REPO_ROOT}"
    REMNAWAVE_TOKEN="${REMNAWAVE_TOKEN:-dummy_token_for_spec_generation_only}" \
    JWT_SECRET="${JWT_SECRET:-customer_growth_reporting_governance_dummy_secret_that_is_at_least_32_chars_long}" \
    CRYPTOBOT_TOKEN="${CRYPTOBOT_TOKEN:-dummy_cryptobot_token}" \
    SWAGGER_ENABLED="${SWAGGER_ENABLED:-true}" \
    DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://x:x@localhost:5432/x}" \
    REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}" \
    "${python_bin}" backend/scripts/export_openapi.py
  )

  info "Checking backend OpenAPI artifact is in sync..."
  assert_file_unchanged "${openapi_snapshot}" "${BACKEND_DIR}/docs/api/openapi.json" "Backend OpenAPI artifact"

  info "Running backend growth-reporting governance conformance packs..."
  (
    cd "${BACKEND_DIR}"
    SKIP_TEST_DB_BOOTSTRAP="${SKIP_TEST_DB_BOOTSTRAP:-1}" \
    "${python_bin}" -m pytest --no-cov \
      tests/contract/test_growth_reporting_governance_conformance_pack.py \
      tests/integration/test_growth_reporting_distribution.py \
      -q
  )
  ok "Backend growth-reporting governance conformance packs passed."
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

  info "Running admin growth-reporting governance tests..."
  (
    cd "${REPO_ROOT}"
    npm run test:run -w admin -- \
      src/lib/api/__tests__/growth-admin.test.ts
  )

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
  ok "Admin growth-reporting governance surface passed."
}

run_assets() {
  require_command bash
  require_command npm

  local python_bin
  local evidence_dir
  local frontend_types_snapshot
  local partner_types_snapshot

  python_bin="$(python_runner)"
  evidence_dir="${REPO_ROOT}/docs/evidence/customer-growth/2099-01-01/staging/growth-reporting-governance/conformance-assets-check"
  frontend_types_snapshot="$(snapshot_file "${REPO_ROOT}/frontend/src/lib/api/generated/types.ts")"
  partner_types_snapshot="$(snapshot_file "${REPO_ROOT}/partner/src/lib/api/generated/types.ts")"

  info "Checking growth-reporting governance scripts syntax..."
  (
    cd "${REPO_ROOT}"
    bash -n scripts/run-customer-growth-reporting-governance-conformance.sh
    bash -n scripts/bootstrap-customer-growth-reporting-governance-evidence.sh
    bash -n scripts/assess-customer-growth-reporting-governance-gate-readiness.sh
    bash -n scripts/run-customer-growth-reporting-governance-staging-smoke.sh
    bash -n scripts/sync-customer-growth-reporting-governance-ruleset.sh
  )

  info "Checking workflow YAML parses cleanly..."
  (
    cd "${REPO_ROOT}"
    "${python_bin}" - <<'PY'
from pathlib import Path
import yaml

for workflow_path in (
    ".github/workflows/customer-growth-reporting-governance-conformance.yml",
    ".github/workflows/customer-growth-reporting-governance-staging-smoke.yml",
):
    path = Path(workflow_path)
    yaml.safe_load(path.read_text(encoding="utf-8"))
PY
  )

  info "Validating Prometheus and Alertmanager tooling with promtool/amtool..."
  (
    cd "${REPO_ROOT}"
    bash scripts/validate-observability-tooling.sh
  )

  info "Regenerating frontend and partner API types..."
  (
    cd "${REPO_ROOT}"
    npm run generate:api-types -w frontend
    npm run generate:api-types -w partner
  )

  info "Checking frontend and partner generated types are in sync..."
  assert_file_unchanged "${frontend_types_snapshot}" "${REPO_ROOT}/frontend/src/lib/api/generated/types.ts" "Frontend generated API type artifact"
  assert_file_unchanged "${partner_types_snapshot}" "${REPO_ROOT}/partner/src/lib/api/generated/types.ts" "Partner generated API type artifact"

  info "Running growth-reporting governance asset contract tests..."
  (
    cd "${BACKEND_DIR}"
    SKIP_TEST_DB_BOOTSTRAP="${SKIP_TEST_DB_BOOTSTRAP:-1}" \
    "${python_bin}" -m pytest --no-cov \
      tests/contract/test_growth_reporting_governance_assets_contract.py \
      -q
  )

  info "Bootstrapping temporary governance evidence pack..."
  (
    cd "${REPO_ROOT}"
    rm -rf "${evidence_dir}"
    bash scripts/bootstrap-customer-growth-reporting-governance-evidence.sh 2099-01-01 staging conformance-assets-check R2 "asset checker"
    test -f "${evidence_dir}/README.md"
    mkdir -p "${evidence_dir}/auth" "${evidence_dir}/notes" "${evidence_dir}/api/grg-001" "${evidence_dir}/api/grg-002" "${evidence_dir}/api/grg-003" "${evidence_dir}/api/grg-004" "${evidence_dir}/exports"
    printf '200\n' > "${evidence_dir}/auth/admin-login.status"
    printf '{"access_token":"dummy"}\n' > "${evidence_dir}/auth/admin-login.json"
    printf '200\n' > "${evidence_dir}/api/refresh.status"
    printf '{}\n' > "${evidence_dir}/api/refresh.json"
    printf '201\n' > "${evidence_dir}/api/grg-001/subscription-created.status"
    printf '{"recipient_email":"suppressed@example.com"}\n' > "${evidence_dir}/api/grg-001/subscription-created.json"
    printf '201\n' > "${evidence_dir}/api/grg-002/subscription-created.status"
    printf '{"recipient_email":"blocked@blocked.invalid"}\n' > "${evidence_dir}/api/grg-002/subscription-created.json"
    printf '{"recipient_email":"healthy@example.com"}\n' > "${evidence_dir}/notes/healthy-subscription-created.json"
    printf '200\n' > "${evidence_dir}/api/claim.status"
    printf '{"deliveries":[{"delivery_id":"delivery-1","recipient_email":"healthy@example.com"}]}\n' > "${evidence_dir}/api/claim.json"
    printf '200\n' > "${evidence_dir}/notes/healthy-delivery-complete.status"
    printf '{"delivery_id":"delivery-1","delivery_status":"delivered"}\n' > "${evidence_dir}/notes/healthy-delivery-complete.json"
    printf '200\n' > "${evidence_dir}/api/grg-003/governance-overview.status"
    printf '{"coverage_gap_count":2,"coverage_counts":[{"coverage_state":"delivery_suppressed","count":1},{"coverage_state":"recipient_domain_blocked","count":1}],"recent_decisions":[{"status_reason":"delivery_suppressed"},{"status_reason":"recipient_domain_blocked"}],"recent_audit_events":[{"event":"a"},{"event":"b"},{"event":"c"}]}\n' > "${evidence_dir}/api/grg-003/governance-overview.json"
    printf '200\n' > "${evidence_dir}/exports/grg-003-governance-export.status"
    printf '{"export_kind":"growth_reporting_governance_snapshot","payload":{"subscriptions":[{"id":"1"},{"id":"2"},{"id":"3"}]}}\n' > "${evidence_dir}/exports/grg-003-governance-export.json"
    printf '200\n' > "${evidence_dir}/api/grg-004/deliveries.status"
    printf '{"deliveries":[{"delivery_id":"delivery-1","status_reason":"delivery_suppressed"}]}\n' > "${evidence_dir}/api/grg-004/deliveries.json"
    bash scripts/assess-customer-growth-reporting-governance-gate-readiness.sh "${evidence_dir}"
    jq -e '.decision == "enable" and .protected_gate_ready == true' "${evidence_dir}/approvals/gate-readiness.json" >/dev/null
    rm -rf "${evidence_dir}"
  )

  ok "Growth-reporting governance rollout assets passed."
}

case "${mode}" in
  all)
    run_backend
    run_admin
    run_assets
    ;;
  --backend)
    run_backend
    ;;
  --admin)
    run_admin
    ;;
  --assets)
    run_assets
    ;;
  *)
    fail "Unknown mode '${mode}'. Use: all, --backend, --admin, or --assets."
    exit 1
    ;;
esac
