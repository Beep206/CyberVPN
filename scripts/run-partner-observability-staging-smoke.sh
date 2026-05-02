#!/usr/bin/env bash

set -euo pipefail

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    printf '[FAIL] Required command %s is not available on PATH.\n' "${command_name}" >&2
    exit 1
  fi
}

require_env() {
  local var_name="$1"
  if [[ -z "${!var_name:-}" ]]; then
    printf '[FAIL] Required environment variable %s is not set.\n' "${var_name}" >&2
    exit 1
  fi
}

write_json() {
  local target_path="$1"
  local payload="$2"
  mkdir -p "$(dirname "${target_path}")"
  printf '%s\n' "${payload}" > "${target_path}"
}

write_status() {
  local target_path="$1"
  local status_code="$2"
  mkdir -p "$(dirname "${target_path}")"
  printf '%s\n' "${status_code}" > "${target_path}"
}

api_get() {
  local target_path="$1"
  local url="$2"
  shift 2
  local headers=("$@")
  local body_file
  local status
  body_file="$(mktemp)"
  status="$(
    curl -sS -o "${body_file}" -w '%{http_code}' \
      "${headers[@]}" \
      "${url}"
  )"
  write_json "${target_path}" "$(cat "${body_file}")"
  write_status "${target_path%.json}.status" "${status}"
  rm -f "${body_file}"
  printf '%s' "${status}"
}

api_post_json() {
  local target_path="$1"
  local url="$2"
  local json_payload="$3"
  shift 3
  local headers=("$@")
  local body_file
  local status
  body_file="$(mktemp)"
  status="$(
    curl -sS -o "${body_file}" -w '%{http_code}' \
      -X POST \
      -H 'Content-Type: application/json' \
      "${headers[@]}" \
      -d "${json_payload}" \
      "${url}"
  )"
  write_json "${target_path}" "$(cat "${body_file}")"
  write_status "${target_path%.json}.status" "${status}"
  rm -f "${body_file}"
  printf '%s' "${status}"
}

prometheus_query() {
  local target_path="$1"
  local query="$2"
  api_get "${target_path}" "${PROMETHEUS_URL%/}/api/v1/query?query=$(printf '%s' "${query}" | jq -sRr @uri)"
}

wait_for_prometheus_vector() {
  local target_path="$1"
  local query="$2"
  local description="$3"
  local attempts="${4:-18}"
  local sleep_seconds="${5:-5}"
  local status
  local value

  for _ in $(seq 1 "${attempts}"); do
    status="$(prometheus_query "${target_path}" "${query}")"
    if [[ "${status}" != "200" ]]; then
      sleep "${sleep_seconds}"
      continue
    fi

    value="$(
      jq -r '.data.result[0].value[1] // empty' "${target_path}" 2>/dev/null || true
    )"
    if [[ -n "${value}" && "${value}" != "NaN" ]]; then
      printf '[OK] %s observed with value %s\n' "${description}" "${value}"
      return 0
    fi

    sleep "${sleep_seconds}"
  done

  printf '[FAIL] %s was not observed in Prometheus within the expected window.\n' "${description}" >&2
  exit 1
}

require_command curl
require_command jq

require_env CYBERVPN_PARTNER_HOST
require_env CYBERVPN_ADMIN_HOST

PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9094}"
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3002}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-grafana_local_password}"
ALERTMANAGER_URL="${ALERTMANAGER_URL:-http://localhost:9093}"
EVIDENCE_DIR="${EVIDENCE_DIR:-$(mktemp -d)}"

mkdir -p \
  "${EVIDENCE_DIR}/frontend-runtime" \
  "${EVIDENCE_DIR}/web-vitals" \
  "${EVIDENCE_DIR}/prometheus" \
  "${EVIDENCE_DIR}/grafana" \
  "${EVIDENCE_DIR}/alertmanager"

partner_runtime_payload="$(jq -cn '{
  connectionType: "4g",
  deviceBucket: "desktop",
  durationMs: 380,
  endpointTemplate: "/api/v1/partner-session/bootstrap",
  event: "route_load",
  locale: "ru-RU",
  path: "/ru-RU/dashboard",
  reducedMotion: "no-preference",
  releaseRing: "r2",
  result: "success",
  routeGroup: "dashboard",
  saveData: "off",
  surface: "partner_portal",
  viewportBucket: "desktop",
  workspaceStatus: "approved_probation"
}')"

admin_runtime_payload="$(jq -cn '{
  connectionType: "ethernet",
  deviceBucket: "desktop",
  errorCode: "synthetic_render_error",
  event: "render_error",
  locale: "ru-RU",
  path: "/ru-RU/growth/partners",
  reducedMotion: "no-preference",
  result: "failure",
  routeGroup: "dashboard",
  saveData: "off",
  surface: "admin_portal",
  viewportBucket: "desktop"
}')"

partner_web_vital_payload="$(jq -cn '{
  connectionType: "4g",
  deviceBucket: "desktop",
  locale: "ru-RU",
  metric: "lcp",
  path: "/ru-RU/dashboard",
  rating: "good",
  reducedMotion: "no-preference",
  routeGroup: "dashboard",
  saveData: "off",
  value: 1800,
  viewportBucket: "desktop"
}')"

admin_web_vital_payload="$(jq -cn '{
  connectionType: "ethernet",
  deviceBucket: "desktop",
  locale: "ru-RU",
  metric: "inp",
  path: "/ru-RU/growth/partners",
  rating: "good",
  reducedMotion: "no-preference",
  routeGroup: "dashboard",
  saveData: "off",
  value: 140,
  viewportBucket: "desktop"
}')"

partner_runtime_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/frontend-runtime/partner-route-load.json" \
    "${CYBERVPN_PARTNER_HOST%/}/api/analytics/frontend-runtime" \
    "${partner_runtime_payload}" \
    -H "Origin: ${CYBERVPN_PARTNER_HOST%/}" \
    -H "Referer: ${CYBERVPN_PARTNER_HOST%/}/ru-RU/dashboard"
)"
[[ "${partner_runtime_status}" == "204" ]]

admin_runtime_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/frontend-runtime/admin-render-error.json" \
    "${CYBERVPN_ADMIN_HOST%/}/api/analytics/frontend-runtime" \
    "${admin_runtime_payload}" \
    -H "Origin: ${CYBERVPN_ADMIN_HOST%/}" \
    -H "Referer: ${CYBERVPN_ADMIN_HOST%/}/ru-RU/growth/partners"
)"
[[ "${admin_runtime_status}" == "204" ]]

partner_web_vital_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/web-vitals/partner-lcp.json" \
    "${CYBERVPN_PARTNER_HOST%/}/api/analytics/web-vitals" \
    "${partner_web_vital_payload}" \
    -H "Origin: ${CYBERVPN_PARTNER_HOST%/}" \
    -H "Referer: ${CYBERVPN_PARTNER_HOST%/}/ru-RU/dashboard"
)"
[[ "${partner_web_vital_status}" == "204" ]]

admin_web_vital_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/web-vitals/admin-inp.json" \
    "${CYBERVPN_ADMIN_HOST%/}/api/analytics/web-vitals" \
    "${admin_web_vital_payload}" \
    -H "Origin: ${CYBERVPN_ADMIN_HOST%/}" \
    -H "Referer: ${CYBERVPN_ADMIN_HOST%/}/ru-RU/growth/partners"
)"
[[ "${admin_web_vital_status}" == "204" ]]

wait_for_prometheus_vector \
  "${EVIDENCE_DIR}/prometheus/partner-route-load-count.json" \
  'sum(cybervpn_partner_frontend_route_load_duration_seconds_count{surface="partner_portal"})' \
  'partner route-load metric'

wait_for_prometheus_vector \
  "${EVIDENCE_DIR}/prometheus/admin-render-error-count.json" \
  'sum(cybervpn_partner_frontend_render_errors_total{surface="admin_portal"})' \
  'admin render-error metric'

wait_for_prometheus_vector \
  "${EVIDENCE_DIR}/prometheus/partner-lcp-count.json" \
  'sum(cybervpn_partner_frontend_lcp_seconds_count{surface="partner_portal"})' \
  'partner LCP metric'

wait_for_prometheus_vector \
  "${EVIDENCE_DIR}/prometheus/admin-inp-count.json" \
  'sum(cybervpn_partner_frontend_inp_seconds_count{surface="admin_portal"})' \
  'admin INP metric'

wait_for_prometheus_vector \
  "${EVIDENCE_DIR}/prometheus/frontend-route-load-p95.json" \
  'partner_platform:frontend_route_load_duration_seconds:p95_15m{surface="partner_portal"}' \
  'frontend route-load recording rule'

wait_for_prometheus_vector \
  "${EVIDENCE_DIR}/prometheus/frontend-lcp-p75.json" \
  'partner_platform:frontend_lcp_seconds:p75_30m{surface="partner_portal"}' \
  'frontend LCP recording rule'

wait_for_prometheus_vector \
  "${EVIDENCE_DIR}/prometheus/frontend-inp-p75.json" \
  'partner_platform:frontend_inp_seconds:p75_30m{surface="admin_portal"}' \
  'frontend INP recording rule'

grafana_search_status="$(
  api_get \
    "${EVIDENCE_DIR}/grafana/frontend-ux-dashboard-search.json" \
    "${GRAFANA_URL%/}/api/search?query=partner-platform-frontend-ux&type=dash-db" \
    -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}"
)"
[[ "${grafana_search_status}" == "200" ]]
jq -e 'map(select(.uid == "partner-platform-frontend-ux")) | length > 0' \
  "${EVIDENCE_DIR}/grafana/frontend-ux-dashboard-search.json" >/dev/null

grafana_dashboard_status="$(
  api_get \
    "${EVIDENCE_DIR}/grafana/frontend-ux-dashboard.json" \
    "${GRAFANA_URL%/}/api/dashboards/uid/partner-platform-frontend-ux" \
    -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}"
)"
[[ "${grafana_dashboard_status}" == "200" ]]
jq -e '.dashboard.uid == "partner-platform-frontend-ux"' \
  "${EVIDENCE_DIR}/grafana/frontend-ux-dashboard.json" >/dev/null

prometheus_rules_status="$(
  api_get \
    "${EVIDENCE_DIR}/prometheus/rules.json" \
    "${PROMETHEUS_URL%/}/api/v1/rules" 
)"
[[ "${prometheus_rules_status}" == "200" ]]
jq -e '
  [
    "PartnerPlatformFrontendRouteLoadLatencyHigh",
    "PartnerPlatformFrontendSubmitFailuresHigh",
    "PartnerPlatformFrontendErrorSpike",
    "PartnerPlatformFrontendLCPHigh",
    "PartnerPlatformFrontendINPHigh"
  ] as $required
  | [ .data.groups[].rules[]?.name ] as $present
  | ($required - $present | length) == 0
' "${EVIDENCE_DIR}/prometheus/rules.json" >/dev/null

alertmanager_health_status="$(
  api_get \
    "${EVIDENCE_DIR}/alertmanager/health.txt.json" \
    "${ALERTMANAGER_URL%/}/-/healthy"
)"
[[ "${alertmanager_health_status}" == "200" ]]

alertmanager_status="$(
  api_get \
    "${EVIDENCE_DIR}/alertmanager/status.json" \
    "${ALERTMANAGER_URL%/}/api/v2/status"
)"
[[ "${alertmanager_status}" == "200" ]]

alertmanager_receivers_status="$(
  api_get \
    "${EVIDENCE_DIR}/alertmanager/receivers.json" \
    "${ALERTMANAGER_URL%/}/api/v2/receivers"
)"
[[ "${alertmanager_receivers_status}" == "200" ]]
jq -e 'length > 0' "${EVIDENCE_DIR}/alertmanager/receivers.json" >/dev/null

printf '[OK] Partner observability staging smoke passed. Evidence written to %s\n' "${EVIDENCE_DIR}"
