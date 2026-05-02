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

run_backend() {
  if command -v uv >/dev/null 2>&1; then
    info "Running backend Mini App launch-control tests via uv..."
    (
      cd "${BACKEND_DIR}"
      PYTHONPATH=. uv run python -m pytest --noconftest --no-cov \
        tests/unit/presentation/api/v1/miniapp/test_routes.py \
        tests/unit/presentation/api/v1/admin/test_system_config.py \
        -q
    )
  else
    fail "uv is required for backend Mini App conformance in this workspace."
    exit 1
  fi
  ok "Backend Mini App launch-control tests passed."
}

run_frontend() {
  require_command npm

  info "Running frontend Mini App runtime tests..."
  (
    cd "${REPO_ROOT}"
    npm run test:run -w frontend -- \
      src/lib/api/__tests__/miniapp.test.ts \
      'src/app/[locale]/miniapp/home/__tests__/page.test.tsx' \
      'src/app/[locale]/miniapp/plans/__tests__/checkout-code-box.test.tsx' \
      'src/app/[locale]/miniapp/components/__tests__/VpnConfigCard.test.tsx' \
      src/app/api/analytics/miniapp-runtime/route.test.ts
  )
  ok "Frontend Mini App runtime tests passed."
}

run_admin() {
  require_command npm

  info "Running admin Mini App governance tests..."
  (
    cd "${REPO_ROOT}"
    npm run test:run -w admin -- \
      src/lib/api/__tests__/governance-miniapp-runtime.test.ts \
      src/features/governance/components/__tests__/policy-console.test.tsx
  )
  ok "Admin Mini App governance tests passed."
}

run_assets() {
  require_command bash
  require_command jq

  local evidence_dir
  evidence_dir="${REPO_ROOT}/docs/evidence/miniapp/2099-01-01/staging/launch/conformance-assets-check"

  info "Checking Mini App launch script syntax..."
  (
    cd "${REPO_ROOT}"
    bash -n scripts/run-miniapp-launch-conformance.sh
    bash -n scripts/bootstrap-miniapp-launch-evidence.sh
    bash -n scripts/run-miniapp-launch-staging-smoke.sh
  )

  info "Bootstrapping temporary Mini App evidence pack..."
  (
    cd "${REPO_ROOT}"
    rm -rf "${evidence_dir}"
    bash scripts/bootstrap-miniapp-launch-evidence.sh 2099-01-01 staging conformance-assets-check R2 "asset checker"
    test -f "${evidence_dir}/README.md"
    rm -rf "${evidence_dir}"
  )

  info "Checking required Mini App launch assets..."
  (
    cd "${REPO_ROOT}"
    rg -q 'conformance:miniapp-launch' package.json
    rg -q 'evidence:miniapp-launch:init' package.json
    rg -q 'staging:miniapp-launch:smoke' package.json
    test -f docs/evidence/miniapp/templates/miniapp-launch-rollout-evidence-template.md
    test -f docs/runbooks/MINIAPP_RUNTIME_OBSERVABILITY_RUNBOOK.md
    test -f docs/runbooks/MINIAPP_LAUNCH_CONTROL_RUNBOOK.md
    test -f docs/runbooks/MINIAPP_STAGING_ROLLOUT_RUNBOOK.md
    test -f scripts/bootstrap-miniapp-launch-evidence.sh
    test -f scripts/run-miniapp-launch-staging-smoke.sh
    test -f infra/prometheus/rules/miniapp_runtime_alerts.yml
    test -f infra/grafana/dashboards/miniapp-runtime-dashboard.json
  )
  ok "Mini App launch assets passed."
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

ok "Mini App launch conformance run finished successfully."
