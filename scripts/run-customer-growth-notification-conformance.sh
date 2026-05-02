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

  info "Exporting backend OpenAPI spec for customer growth notification conformance..."
  (
    cd "${REPO_ROOT}"
    REMNAWAVE_TOKEN="${REMNAWAVE_TOKEN:-dummy_token_for_spec_generation_only}" \
    JWT_SECRET="${JWT_SECRET:-customer_growth_notification_conformance_dummy_secret_that_is_at_least_32_chars_long}" \
    CRYPTOBOT_TOKEN="${CRYPTOBOT_TOKEN:-dummy_cryptobot_token}" \
    SWAGGER_ENABLED="${SWAGGER_ENABLED:-true}" \
    DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://x:x@localhost:5432/x}" \
    REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}" \
    "${python_bin}" backend/scripts/export_openapi.py
  )

  info "Checking backend OpenAPI artifact is in sync..."
  assert_file_unchanged "${openapi_snapshot}" "${BACKEND_DIR}/docs/api/openapi.json" "Backend OpenAPI artifact"

  info "Running backend growth-notification conformance packs..."
  (
    cd "${BACKEND_DIR}"
    SKIP_TEST_DB_BOOTSTRAP="${SKIP_TEST_DB_BOOTSTRAP:-1}" \
    "${python_bin}" -m pytest --no-cov \
      tests/contract/test_growth_notification_delivery_conformance_pack.py \
      tests/e2e/test_growth_notification_delivery_conformance.py \
      tests/integration/test_customer_growth_notification_delivery.py \
      -q
  )
  ok "Backend growth-notification conformance packs passed."
}

run_frontend() {
  local types_snapshot
  require_command npm
  types_snapshot="$(snapshot_file "${REPO_ROOT}/frontend/src/lib/api/generated/types.ts")"

  info "Regenerating frontend API types..."
  (
    cd "${REPO_ROOT}"
    npm run generate:api-types -w frontend
  )

  info "Checking frontend generated types are in sync..."
  assert_file_unchanged "${types_snapshot}" "${REPO_ROOT}/frontend/src/lib/api/generated/types.ts" "Frontend generated API type artifact"

  info "Running frontend growth-notification tests..."
  (
    cd "${REPO_ROOT}"
    npm run test:run -w frontend -- \
      src/lib/api/__tests__/growth-notifications.test.ts \
      'src/app/[locale]/(dashboard)/referral/components/__tests__/ReferralClient.test.tsx' \
      'src/app/[locale]/miniapp/referral/__tests__/page.test.tsx'
  )

  info "Running frontend lint..."
  (
    cd "${REPO_ROOT}"
    npm run lint
  )

  info "Building frontend workspace..."
  (
    cd "${REPO_ROOT}"
    NEXT_TELEMETRY_DISABLED=1 npm run build
  )
  ok "Frontend growth-notification surface passed."
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

  info "Running admin growth-notification tests..."
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
  ok "Admin growth-notification surface passed."
}

run_assets() {
  require_command bash
  require_command jq

  local python_bin
  local evidence_dir
  python_bin="$(python_runner)"
  evidence_dir="${REPO_ROOT}/docs/evidence/customer-growth/2099-01-01/staging/growth-notification-rollout/conformance-assets-check"

  info "Checking growth notification conformance script syntax..."
  (
    cd "${REPO_ROOT}"
    bash -n scripts/run-customer-growth-notification-conformance.sh
    bash -n scripts/bootstrap-customer-growth-notification-evidence.sh
    bash -n scripts/run-customer-growth-notification-staging-smoke.sh
    bash -n scripts/sync-customer-growth-notification-ruleset.sh
  )

  info "Validating Prometheus and Alertmanager tooling with promtool/amtool..."
  (
    cd "${REPO_ROOT}"
    bash scripts/validate-observability-tooling.sh
  )

  info "Running growth notification asset contract tests..."
  (
    cd "${BACKEND_DIR}"
    SKIP_TEST_DB_BOOTSTRAP="${SKIP_TEST_DB_BOOTSTRAP:-1}" \
    "${python_bin}" -m pytest --no-cov \
      tests/contract/test_growth_notification_rollout_assets_contract.py \
      -q
  )

  info "Validating Grafana dashboards..."
  (
    cd "${REPO_ROOT}"
    bash infra/tests/validate_dashboards.sh
  )

  info "Bootstrapping temporary evidence pack..."
  (
    cd "${REPO_ROOT}"
    rm -rf "${evidence_dir}"
    bash scripts/bootstrap-customer-growth-notification-evidence.sh 2099-01-01 staging conformance-assets-check R2 "asset checker"
    test -f "${evidence_dir}/README.md"
    rm -rf "${evidence_dir}"
  )

  info "Checking required rollout-hardening assets..."
  (
    cd "${REPO_ROOT}"
    jq -e '.panels[] | select(.title=="Unresolved Backlog Delta (24h)")' infra/grafana/dashboards/customer-growth-notification-delivery-dashboard.json >/dev/null
    jq -e '.panels[] | select(.title=="Recovery Ratio (24h)")' infra/grafana/dashboards/customer-growth-notification-delivery-dashboard.json >/dev/null
    rg -q 'CustomerGrowthNotificationUnresolvedBacklogHigh' infra/prometheus/rules/customer_growth_notification_alerts.yml
    rg -q 'CustomerGrowthNotificationRecoveryRatioLow' infra/prometheus/rules/customer_growth_notification_alerts.yml
    rg -q 'conformance:customer-growth-notifications' package.json
    rg -q 'evidence:customer-growth-notifications:init' package.json
    rg -q 'staging:customer-growth-notifications:smoke' package.json
    test -f docs/evidence/customer-growth/templates/customer-growth-notification-rollout-evidence-template.md
    test -f docs/runbooks/CUSTOMER_GROWTH_NOTIFICATION_DELIVERY_RUNBOOK.md
    test -f docs/runbooks/CUSTOMER_GROWTH_NOTIFICATION_STAGING_ROLLOUT_RUNBOOK.md
    test -f docs/runbooks/CUSTOMER_GROWTH_NOTIFICATION_GITHUB_PROTECTION_HANDOFF.md
    test -f .github/workflows/customer-growth-notification-conformance.yml
    test -f .github/rulesets/customer-growth-notification-main-gate.disabled.json
    rg -q 'All Customer Growth Notification Checks Passed' docs/runbooks/CUSTOMER_GROWTH_NOTIFICATION_GITHUB_PROTECTION_HANDOFF.md
  )
  ok "Growth-notification rollout assets passed."
}

case "${mode}" in
  all)
    run_backend
    run_frontend
    run_admin
    run_assets
    ;;
  --backend)
    run_backend
    ;;
  --frontend)
    run_frontend
    ;;
  --admin)
    run_admin
    ;;
  --assets)
    run_assets
    ;;
  *)
    fail "Unknown mode '${mode}'. Use --backend, --frontend, --admin, --assets, or no argument."
    exit 1
    ;;
esac

ok "Customer growth notification conformance run finished successfully."
