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

stop_background_process() {
  local pid_file="$1"

  if [[ -f "${pid_file}" ]]; then
    kill "$(cat "${pid_file}")" >/dev/null 2>&1 || true
    rm -f "${pid_file}"
  fi
}

run_web_sentry_smoke() {
  local workspace="$1"
  local surface="$2"
  local port="$3"
  local release="$4"
  local secret="$5"
  local public_dsn="$6"
  local server_dsn="$7"
  local python_bin
  local pid_file
  local log_file

  require_command python3
  python_bin="$(python_runner)"
  pid_file="/tmp/${workspace}-sentry-smoke.pid"
  log_file="/tmp/${workspace}-sentry-smoke.log"
  trap 'stop_background_process "'"${pid_file}"'"' RETURN

  info "Validating ${surface} Sentry contract variables..."
  (
    cd "${REPO_ROOT}"
    APP_ENV="staging" \
    SENTRY_RELEASE="${release}" \
    SENTRY_DSN="${server_dsn}" \
    "${python_bin}" scripts/validate-sentry-contract.py \
      --surface "${surface}" \
      --environment-var APP_ENV \
      --release-var SENTRY_RELEASE \
      --dsn-var SENTRY_DSN \
      --expected-environment staging \
      --expected-release "${release}" \
      --require-dsn \
      --summary-label "${surface} Sentry contract"
  )

  info "Starting ${workspace} for Sentry smoke validation..."
  stop_background_process "${pid_file}"
  (
    cd "${REPO_ROOT}"
    APP_ENV="staging" \
    NEXT_PUBLIC_APP_ENV="staging" \
    SENTRY_RELEASE="${release}" \
    NEXT_PUBLIC_SENTRY_RELEASE="${release}" \
    SENTRY_DSN="${server_dsn}" \
    NEXT_PUBLIC_SENTRY_DSN="${public_dsn}" \
    FRONTEND_OBSERVABILITY_INTERNAL_SECRET="${secret}" \
    NEXT_TELEMETRY_DISABLED=1 \
    nohup npm run start -w "${workspace}" -- --hostname 127.0.0.1 --port "${port}" \
      > "${log_file}" 2>&1 &
    echo $! > "${pid_file}"
  )

  info "Running ${workspace} HTTP Sentry smoke checks..."
  (
    cd "${REPO_ROOT}"
    "${python_bin}" scripts/http-smoke-check.py \
      --url "http://127.0.0.1:${port}/api/observability/sentry-contract" \
      --header "x-observability-secret: ${secret}" \
      --expect-status 200 \
      --expect-json-field "runtimeSurface=${surface}" \
      --expect-json-field "environment=staging" \
      --expect-json-field "release=${release}" \
      --expect-json-field "dsnConfigured=true" \
      --expect-json-field "publicDsnConfigured=true" \
      --summary-label "${surface} Sentry runtime smoke"
  )

  stop_background_process "${pid_file}"
  trap - RETURN
  ok "${surface} Sentry smoke passed."
}

run_backend() {
  local python_bin
  local openapi_snapshot
  python_bin="$(python_runner)"
  openapi_snapshot="$(snapshot_file "${BACKEND_DIR}/docs/api/openapi.json")"

  info "Exporting backend OpenAPI spec for observability conformance..."
  (
    cd "${REPO_ROOT}"
    REMNAWAVE_TOKEN="${REMNAWAVE_TOKEN:-dummy_token_for_spec_generation_only}" \
    JWT_SECRET="${JWT_SECRET:-partner_observability_conformance_dummy_secret_that_is_at_least_32_chars_long}" \
    CRYPTOBOT_TOKEN="${CRYPTOBOT_TOKEN:-dummy_cryptobot_token}" \
    SWAGGER_ENABLED="${SWAGGER_ENABLED:-true}" \
    DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://x:x@localhost:5432/x}" \
    REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}" \
    "${python_bin}" backend/scripts/export_openapi.py
  )

  info "Checking backend OpenAPI artifact is in sync..."
  assert_file_unchanged "${openapi_snapshot}" "${BACKEND_DIR}/docs/api/openapi.json" "Backend OpenAPI artifact"

  info "Running backend observability integration packs..."
  (
    cd "${BACKEND_DIR}"
    SKIP_TEST_DB_BOOTSTRAP="${SKIP_TEST_DB_BOOTSTRAP:-1}" \
    "${python_bin}" -m pytest --no-cov \
      tests/integration/test_partner_runtime_observability.py \
      tests/integration/test_partner_operational_observability.py \
      -q
  )
  ok "Backend observability packs passed."
}

run_partner() {
  require_command npm

  info "Running partner frontend observability tests..."
  (
    cd "${REPO_ROOT}"
    npm run test:run -w partner -- \
      src/app/api/observability/sentry-contract/route.test.ts \
      src/app/api/analytics/frontend-runtime/route.test.ts \
      src/app/api/analytics/web-vitals/route.test.ts \
      src/shared/lib/__tests__/frontend-observability.test.ts \
      src/shared/lib/__tests__/web-vitals.test.ts
  )

  info "Running partner lint..."
  (
    cd "${REPO_ROOT}"
    npm run lint:partner
  )

  info "Building partner workspace..."
  (
    cd "${REPO_ROOT}"
    APP_ENV="staging" \
    NEXT_PUBLIC_APP_ENV="staging" \
    SENTRY_RELEASE="partner@observability-smoke" \
    NEXT_PUBLIC_SENTRY_RELEASE="partner@observability-smoke" \
    SENTRY_DSN="https://partner@example.com/1" \
    NEXT_PUBLIC_SENTRY_DSN="https://partner-public@example.com/1" \
    FRONTEND_OBSERVABILITY_INTERNAL_SECRET="partner-sentry-smoke-secret" \
    NEXT_TELEMETRY_DISABLED=1 \
    npm run build -w partner
  )

  run_web_sentry_smoke \
    "partner" \
    "partner" \
    "3201" \
    "partner@observability-smoke" \
    "partner-sentry-smoke-secret" \
    "https://partner-public@example.com/1" \
    "https://partner@example.com/1"
  ok "Partner observability surface passed."
}

run_admin() {
  require_command npm

  info "Running admin frontend observability tests..."
  (
    cd "${REPO_ROOT}"
    npm run test:run -w admin -- \
      src/app/api/observability/sentry-contract/route.test.ts \
      src/app/api/analytics/frontend-runtime/route.test.ts \
      src/app/api/analytics/web-vitals/route.test.ts \
      src/shared/lib/__tests__/frontend-observability.test.ts \
      src/shared/lib/__tests__/web-vitals.test.ts
  )

  info "Running admin lint..."
  (
    cd "${REPO_ROOT}"
    npm run lint:admin
  )

  info "Building admin workspace..."
  (
    cd "${REPO_ROOT}"
    APP_ENV="staging" \
    NEXT_PUBLIC_APP_ENV="staging" \
    SENTRY_RELEASE="admin@observability-smoke" \
    NEXT_PUBLIC_SENTRY_RELEASE="admin@observability-smoke" \
    SENTRY_DSN="https://admin@example.com/1" \
    NEXT_PUBLIC_SENTRY_DSN="https://admin-public@example.com/1" \
    FRONTEND_OBSERVABILITY_INTERNAL_SECRET="admin-sentry-smoke-secret" \
    NEXT_TELEMETRY_DISABLED=1 \
    npm run build -w admin
  )

  run_web_sentry_smoke \
    "admin" \
    "admin" \
    "3200" \
    "admin@observability-smoke" \
    "admin-sentry-smoke-secret" \
    "https://admin-public@example.com/1" \
    "https://admin@example.com/1"
  ok "Admin observability surface passed."
}

run_assets() {
  require_command bash
  require_command jq
  require_command python3

  local python_bin
  python_bin="$(python_runner)"

  info "Checking observability staging smoke script syntax..."
  (
    cd "${REPO_ROOT}"
    bash -n scripts/run-partner-observability-staging-smoke.sh
    bash -n scripts/ensure-observability-cli-tools.sh
    bash -n scripts/validate-observability-tooling.sh
  )

  info "Validating Prometheus and Alertmanager tooling with promtool/amtool..."
  (
    cd "${REPO_ROOT}"
    bash scripts/validate-observability-tooling.sh
  )

  info "Running observability asset contract tests..."
  (
    cd "${BACKEND_DIR}"
    SKIP_TEST_DB_BOOTSTRAP="${SKIP_TEST_DB_BOOTSTRAP:-1}" \
    "${python_bin}" -m pytest --no-cov \
      tests/contract/test_partner_observability_assets_contract.py \
      -q
  )

  info "Validating Grafana dashboards..."
  (
    cd "${REPO_ROOT}"
    bash infra/tests/validate_dashboards.sh
  )

  info "Checking required observability assets and rule names..."
  (
    cd "${REPO_ROOT}"
    jq -e '.panels[] | select(.title=="LCP P75 (30m)")' infra/grafana/dashboards/partner-platform-frontend-ux-dashboard.json >/dev/null
    jq -e '.panels[] | select(.title=="INP P75 (30m)")' infra/grafana/dashboards/partner-platform-frontend-ux-dashboard.json >/dev/null
    jq -e '.paths["/api/v1/monitoring/frontend-web-vitals"]' backend/docs/api/openapi.json >/dev/null
    rg -q 'PartnerPlatformFrontendLCPHigh' infra/prometheus/rules/partner_platform_alerts.yml
    rg -q 'PartnerPlatformFrontendINPHigh' infra/prometheus/rules/partner_platform_alerts.yml
    rg -q 'staging:partner-observability:smoke' package.json
    rg -q 'evidence:partner-observability:init' package.json
    test -f docs/evidence/partner-platform/templates/partner-observability-evidence-template.md
    test -f scripts/bootstrap-partner-observability-evidence.sh
    test -f docs/runbooks/PARTNER_OBSERVABILITY_GITHUB_PROTECTION_HANDOFF.md
    test -f .github/rulesets/partner-observability-main-gate.disabled.json
    test -f scripts/sync-partner-observability-ruleset.sh
    rg -q 'All Partner Observability Checks Passed' docs/runbooks/PARTNER_OBSERVABILITY_GITHUB_PROTECTION_HANDOFF.md
  )
  ok "Observability assets passed."
}

case "${mode}" in
  all)
    run_backend
    run_partner
    run_admin
    run_assets
    ;;
  --backend)
    run_backend
    ;;
  --partner)
    run_partner
    ;;
  --admin)
    run_admin
    ;;
  --assets)
    run_assets
    ;;
  *)
    fail "Unknown mode '${mode}'. Use --backend, --partner, --admin, --assets, or no argument."
    exit 1
    ;;
esac

ok "Partner observability conformance run finished successfully."
