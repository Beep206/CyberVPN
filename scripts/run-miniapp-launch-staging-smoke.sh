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

prom_query() {
  local target_path="$1"
  local query="$2"
  local headers=()
  local body_file
  local status
  if [[ -n "${CYBERVPN_PROMETHEUS_BEARER_TOKEN:-}" ]]; then
    headers+=(-H "Authorization: Bearer ${CYBERVPN_PROMETHEUS_BEARER_TOKEN}")
  fi
  body_file="$(mktemp)"
  status="$(
    curl -sS -o "${body_file}" -w '%{http_code}' \
      "${headers[@]}" \
      --get \
      --data-urlencode "query=${query}" \
      "${CYBERVPN_PROMETHEUS_BASE%/}/api/v1/query"
  )"
  write_json "${target_path}" "$(cat "${body_file}")"
  write_status "${target_path%.json}.status" "${status}"
  rm -f "${body_file}"
  printf '%s' "${status}"
}

require_command curl
require_command jq

require_env CYBERVPN_API_BASE
require_env CYBERVPN_ADMIN_SMOKE_EMAIL
require_env CYBERVPN_ADMIN_SMOKE_PASSWORD
require_env CYBERVPN_MINIAPP_CUSTOMER_SMOKE_EMAIL
require_env CYBERVPN_MINIAPP_CUSTOMER_SMOKE_PASSWORD

EVIDENCE_DIR="${EVIDENCE_DIR:-$(mktemp -d)}"
MINIAPP_LOCALE="${CYBERVPN_MINIAPP_LOCALE:-en-EN}"
MINIAPP_START_PARAM="${CYBERVPN_MINIAPP_START_PARAM:-staging-launch-smoke}"
EXPECT_CONFIG="${CYBERVPN_MINIAPP_EXPECT_CONFIG:-false}"
ENABLE_TRIAL_SMOKE="${CYBERVPN_MINIAPP_ENABLE_TRIAL_SMOKE:-false}"
TRIAL_EXPECT_SUCCESS="${CYBERVPN_MINIAPP_TRIAL_EXPECT_SUCCESS:-false}"
PAYMENT_ID="${CYBERVPN_MINIAPP_PAYMENT_ID:-}"

CUSTOMER_DEVICE_ID="${CYBERVPN_MINIAPP_CUSTOMER_DEVICE_ID:-00000000-0000-4000-8000-000000000099}"
CUSTOMER_DEVICE_PLATFORM="${CYBERVPN_MINIAPP_CUSTOMER_DEVICE_PLATFORM:-android}"
CUSTOMER_PLATFORM_ID="${CYBERVPN_MINIAPP_CUSTOMER_PLATFORM_ID:-miniapp-launch-smoke}"
CUSTOMER_OS_VERSION="${CYBERVPN_MINIAPP_CUSTOMER_OS_VERSION:-14}"
CUSTOMER_APP_VERSION="${CYBERVPN_MINIAPP_CUSTOMER_APP_VERSION:-1.0.99}"
CUSTOMER_DEVICE_MODEL="${CYBERVPN_MINIAPP_CUSTOMER_DEVICE_MODEL:-miniapp-smoke-device}"

mkdir -p "${EVIDENCE_DIR}/admin" "${EVIDENCE_DIR}/miniapp" "${EVIDENCE_DIR}/monitoring" "${EVIDENCE_DIR}/notes"

admin_login_payload="$(jq -cn \
  --arg login_or_email "${CYBERVPN_ADMIN_SMOKE_EMAIL}" \
  --arg password "${CYBERVPN_ADMIN_SMOKE_PASSWORD}" \
  '{login_or_email: $login_or_email, password: $password}')"

admin_login_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/admin/admin-login.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/auth/login" \
    "${admin_login_payload}" \
    -H 'X-Auth-Realm: admin'
)"
[[ "${admin_login_status}" == "200" ]]

admin_token="$(jq -r '.access_token' "${EVIDENCE_DIR}/admin/admin-login.json")"
[[ -n "${admin_token}" && "${admin_token}" != "null" ]]

runtime_status="$(
  api_get \
    "${EVIDENCE_DIR}/admin/runtime.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/system-config/miniapp-runtime" \
    -H "Authorization: Bearer ${admin_token}"
)"
[[ "${runtime_status}" == "200" ]]

readiness_status="$(
  api_get \
    "${EVIDENCE_DIR}/admin/launch-readiness.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/system-config/miniapp-launch-readiness" \
    -H "Authorization: Bearer ${admin_token}"
)"
[[ "${readiness_status}" == "200" ]]

summary_status="$(
  api_get \
    "${EVIDENCE_DIR}/admin/launch-summary.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/system-config/miniapp-launch-summary" \
    -H "Authorization: Bearer ${admin_token}"
)"
[[ "${summary_status}" == "200" ]]

timeline_status="$(
  api_get \
    "${EVIDENCE_DIR}/admin/launch-timeline.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/system-config/miniapp-launch-timeline?limit=10" \
    -H "Authorization: Bearer ${admin_token}"
)"
[[ "${timeline_status}" == "200" ]]

customer_login_payload="$(jq -cn \
  --arg email "${CYBERVPN_MINIAPP_CUSTOMER_SMOKE_EMAIL}" \
  --arg password "${CYBERVPN_MINIAPP_CUSTOMER_SMOKE_PASSWORD}" \
  --arg device_id "${CUSTOMER_DEVICE_ID}" \
  --arg platform "${CUSTOMER_DEVICE_PLATFORM}" \
  --arg platform_id "${CUSTOMER_PLATFORM_ID}" \
  --arg os_version "${CUSTOMER_OS_VERSION}" \
  --arg app_version "${CUSTOMER_APP_VERSION}" \
  --arg device_model "${CUSTOMER_DEVICE_MODEL}" \
  '{
    email: $email,
    password: $password,
    remember_me: true,
    device: {
      device_id: $device_id,
      platform: $platform,
      platform_id: $platform_id,
      os_version: $os_version,
      app_version: $app_version,
      device_model: $device_model
    }
  }')"

customer_login_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/miniapp/customer-login.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/mobile/auth/login" \
    "${customer_login_payload}"
)"
[[ "${customer_login_status}" == "200" ]]

customer_token="$(jq -r '.tokens.access_token' "${EVIDENCE_DIR}/miniapp/customer-login.json")"
[[ -n "${customer_token}" && "${customer_token}" != "null" ]]

bootstrap_status="$(
  api_get \
    "${EVIDENCE_DIR}/miniapp/bootstrap.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/miniapp/bootstrap?locale=${MINIAPP_LOCALE}&startParam=${MINIAPP_START_PARAM}" \
    -H "Authorization: Bearer ${customer_token}"
)"
[[ "${bootstrap_status}" == "200" ]]

jq -e '.session.authenticated == true' "${EVIDENCE_DIR}/miniapp/bootstrap.json" >/dev/null
jq -e '.rollout.accessGranted == true' "${EVIDENCE_DIR}/miniapp/bootstrap.json" >/dev/null

offers_status="$(
  api_get \
    "${EVIDENCE_DIR}/miniapp/offers.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/miniapp/offers" \
    -H "Authorization: Bearer ${customer_token}"
)"
[[ "${offers_status}" == "200" ]]

config_status="$(
  api_get \
    "${EVIDENCE_DIR}/miniapp/config.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/miniapp/config" \
    -H "Authorization: Bearer ${customer_token}"
)"
if [[ "${EXPECT_CONFIG}" == "true" ]]; then
  [[ "${config_status}" == "200" ]]
else
  [[ "${config_status}" == "200" || "${config_status}" == "404" ]]
fi

if [[ "${ENABLE_TRIAL_SMOKE}" == "true" ]]; then
  trial_status="$(
    api_post_json \
      "${EVIDENCE_DIR}/miniapp/trial-activate.json" \
      "${CYBERVPN_API_BASE%/}/api/v1/miniapp/trial/activate" \
      '{}' \
      -H "Authorization: Bearer ${customer_token}"
  )"
  if [[ "${TRIAL_EXPECT_SUCCESS}" == "true" ]]; then
    [[ "${trial_status}" == "200" ]]
  else
    [[ "${trial_status}" == "200" || "${trial_status}" == "400" || "${trial_status}" == "503" ]]
  fi
fi

if [[ -n "${PAYMENT_ID}" ]]; then
  payment_status="$(
    api_get \
      "${EVIDENCE_DIR}/miniapp/payment-status.json" \
      "${CYBERVPN_API_BASE%/}/api/v1/miniapp/payments/${PAYMENT_ID}" \
      -H "Authorization: Bearer ${customer_token}"
  )"
  [[ "${payment_status}" == "200" ]]
fi

if [[ -n "${CYBERVPN_PROMETHEUS_BASE:-}" ]]; then
  launch_state_status="$(
    prom_query \
      "${EVIDENCE_DIR}/monitoring/launch-state.json" \
      'max(miniapp_launch_state_current)'
  )"
  [[ "${launch_state_status}" == "200" ]]

  blockers_status="$(
    prom_query \
      "${EVIDENCE_DIR}/monitoring/launch-blockers.json" \
      'max(miniapp_launch_blockers_current)'
  )"
  [[ "${blockers_status}" == "200" ]]

  request_rate_status="$(
    prom_query \
      "${EVIDENCE_DIR}/monitoring/runtime-request-rate.json" \
      'sum(rate(miniapp_runtime_requests_total[5m]))'
  )"
  [[ "${request_rate_status}" == "200" ]]

  config_failures_status="$(
    prom_query \
      "${EVIDENCE_DIR}/monitoring/config-failures.json" \
      'sum(rate(miniapp_config_delivery_total{status!="success"}[15m]))'
  )"
  [[ "${config_failures_status}" == "200" ]]
fi

printf '[OK] Mini App launch staging smoke passed. Evidence written to %s\n' "${EVIDENCE_DIR}"
