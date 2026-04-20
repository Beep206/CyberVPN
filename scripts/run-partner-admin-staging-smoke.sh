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

require_command curl
require_command jq

require_env CYBERVPN_API_BASE
require_env CYBERVPN_PARTNER_SMOKE_EMAIL
require_env CYBERVPN_PARTNER_SMOKE_PASSWORD
require_env CYBERVPN_ADMIN_SMOKE_EMAIL
require_env CYBERVPN_ADMIN_SMOKE_PASSWORD

EVIDENCE_DIR="${EVIDENCE_DIR:-$(mktemp -d)}"
PARTNER_WORKSPACE_ID="${CYBERVPN_PARTNER_WORKSPACE_ID:-}"
ENABLE_LOGOUT_ALL="${CYBERVPN_ENABLE_LOGOUT_ALL_CHECK:-false}"

mkdir -p "${EVIDENCE_DIR}/auth"

partner_login_payload="$(jq -cn \
  --arg login_or_email "${CYBERVPN_PARTNER_SMOKE_EMAIL}" \
  --arg password "${CYBERVPN_PARTNER_SMOKE_PASSWORD}" \
  '{login_or_email: $login_or_email, password: $password}')"

admin_login_payload="$(jq -cn \
  --arg login_or_email "${CYBERVPN_ADMIN_SMOKE_EMAIL}" \
  --arg password "${CYBERVPN_ADMIN_SMOKE_PASSWORD}" \
  '{login_or_email: $login_or_email, password: $password}')"

partner_login_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/auth/partner-login.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/auth/login" \
    "${partner_login_payload}" \
    -H 'X-Auth-Realm: partner'
)"
[[ "${partner_login_status}" == "200" ]]

partner_token="$(jq -r '.access_token' "${EVIDENCE_DIR}/auth/partner-login.json")"
partner_realm_key="$(jq -r '.auth_realm_key // empty' "${EVIDENCE_DIR}/auth/partner-login.json")"
partner_principal_type="$(jq -r '.principal_type // empty' "${EVIDENCE_DIR}/auth/partner-login.json")"
[[ -n "${partner_token}" && "${partner_token}" != "null" ]]
[[ "${partner_realm_key}" == "partner" ]]
[[ "${partner_principal_type}" == "partner_operator" ]]

admin_login_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/auth/admin-login.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/auth/login" \
    "${admin_login_payload}" \
    -H 'X-Auth-Realm: admin'
)"
[[ "${admin_login_status}" == "200" ]]

admin_token="$(jq -r '.access_token' "${EVIDENCE_DIR}/auth/admin-login.json")"
[[ -n "${admin_token}" && "${admin_token}" != "null" ]]

bootstrap_query=""
if [[ -n "${PARTNER_WORKSPACE_ID}" ]]; then
  bootstrap_query="?workspace_id=${PARTNER_WORKSPACE_ID}"
fi

partner_bootstrap_status="$(
  api_get \
    "${EVIDENCE_DIR}/auth/partner-bootstrap.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/partner-session/bootstrap${bootstrap_query}" \
    -H "Authorization: Bearer ${partner_token}" \
    -H 'X-Auth-Realm: partner'
)"
[[ "${partner_bootstrap_status}" == "200" ]]
[[ "$(jq -r '.principal.auth_realm_key // empty' "${EVIDENCE_DIR}/auth/partner-bootstrap.json")" == "partner" ]]
[[ "$(jq -r '.principal.principal_type // empty' "${EVIDENCE_DIR}/auth/partner-bootstrap.json")" == "partner_operator" ]]

admin_on_partner_status="$(
  api_get \
    "${EVIDENCE_DIR}/auth/admin-on-partner-bootstrap.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/partner-session/bootstrap${bootstrap_query}" \
    -H "Authorization: Bearer ${admin_token}" \
    -H 'X-Auth-Realm: admin'
)"
[[ "${admin_on_partner_status}" == "403" ]]

partner_on_admin_status="$(
  api_get \
    "${EVIDENCE_DIR}/auth/partner-on-admin.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/partner-session/bootstrap${bootstrap_query}" \
    -H "Authorization: Bearer ${partner_token}" \
    -H 'X-Auth-Realm: admin'
)"
[[ "${partner_on_admin_status}" == "401" ]]

admin_on_partner_realm_status="$(
  api_get \
    "${EVIDENCE_DIR}/auth/admin-token-on-partner-realm.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/partner-session/bootstrap${bootstrap_query}" \
    -H "Authorization: Bearer ${admin_token}" \
    -H 'X-Auth-Realm: partner'
)"
[[ "${admin_on_partner_realm_status}" == "401" ]]

if [[ "${ENABLE_LOGOUT_ALL}" == "true" ]]; then
  logout_all_status="$(
    api_post_json \
      "${EVIDENCE_DIR}/auth/logout-all-revocation.json" \
      "${CYBERVPN_API_BASE%/}/api/v1/auth/logout-all" \
      '{}' \
      -H "Authorization: Bearer ${partner_token}" \
      -H 'X-Auth-Realm: partner'
  )"
  [[ "${logout_all_status}" == "200" ]]

  revoked_bootstrap_status="$(
    api_get \
      "${EVIDENCE_DIR}/auth/revoked-partner-bootstrap.json" \
      "${CYBERVPN_API_BASE%/}/api/v1/partner-session/bootstrap${bootstrap_query}" \
      -H "Authorization: Bearer ${partner_token}" \
      -H 'X-Auth-Realm: partner'
  )"
  [[ "${revoked_bootstrap_status}" == "401" ]]
fi

printf '[OK] Partner/admin staging smoke passed. Evidence written to %s\n' "${EVIDENCE_DIR}"
