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

write_text() {
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

api_patch_json() {
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
      -X PATCH \
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
  local status
  local body_file
  local headers=()
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
require_env CYBERVPN_GROWTH_CUSTOMER_SMOKE_EMAIL
require_env CYBERVPN_GROWTH_CUSTOMER_SMOKE_PASSWORD

EVIDENCE_DIR="${EVIDENCE_DIR:-$(mktemp -d)}"
CUSTOMER_DEVICE_ID="${CYBERVPN_GROWTH_CUSTOMER_DEVICE_ID:-00000000-0000-4000-8000-000000000018}"
CUSTOMER_DEVICE_PLATFORM="${CYBERVPN_GROWTH_CUSTOMER_DEVICE_PLATFORM:-android}"
CUSTOMER_PLATFORM_ID="${CYBERVPN_GROWTH_CUSTOMER_PLATFORM_ID:-gc-wb-18-staging-smoke}"
CUSTOMER_OS_VERSION="${CYBERVPN_GROWTH_CUSTOMER_OS_VERSION:-14}"
CUSTOMER_APP_VERSION="${CYBERVPN_GROWTH_CUSTOMER_APP_VERSION:-1.0.18}"
CUSTOMER_DEVICE_MODEL="${CYBERVPN_GROWTH_CUSTOMER_DEVICE_MODEL:-growth-smoke-device}"
PROMETHEUS_ENABLED="false"

if [[ -n "${CYBERVPN_PROMETHEUS_BASE:-}" ]]; then
  PROMETHEUS_ENABLED="true"
fi

mkdir -p "${EVIDENCE_DIR}/auth" \
  "${EVIDENCE_DIR}/api/gcn-repair-001" \
  "${EVIDENCE_DIR}/api/gcn-repair-004" \
  "${EVIDENCE_DIR}/exports" \
  "${EVIDENCE_DIR}/monitoring" \
  "${EVIDENCE_DIR}/notes"

customer_token=""
admin_token=""
customer_user_id=""
customer_original_email_admin_updates=""
cleanup_attempted="false"

restore_customer_preferences() {
  if [[ "${cleanup_attempted}" == "true" ]]; then
    return 0
  fi
  cleanup_attempted="true"

  if [[ -z "${customer_token}" || -z "${customer_original_email_admin_updates}" ]]; then
    return 0
  fi

  local restore_payload
  restore_payload="$(jq -cn \
    --argjson growth_email_admin_updates "${customer_original_email_admin_updates}" \
    '{growth_email_admin_updates: $growth_email_admin_updates}')"

  api_patch_json \
    "${EVIDENCE_DIR}/notes/preferences-restored.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/growth-notifications/preferences" \
    "${restore_payload}" \
    -H "Authorization: Bearer ${customer_token}" \
    >/dev/null || true
}

trap restore_customer_preferences EXIT

customer_login_payload="$(jq -cn \
  --arg email "${CYBERVPN_GROWTH_CUSTOMER_SMOKE_EMAIL}" \
  --arg password "${CYBERVPN_GROWTH_CUSTOMER_SMOKE_PASSWORD}" \
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
    "${EVIDENCE_DIR}/auth/customer-login.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/mobile/auth/login" \
    "${customer_login_payload}"
)"
[[ "${customer_login_status}" == "200" ]]

customer_token="$(jq -r '.tokens.access_token' "${EVIDENCE_DIR}/auth/customer-login.json")"
customer_user_id="$(jq -r '.user.id' "${EVIDENCE_DIR}/auth/customer-login.json")"
[[ -n "${customer_token}" && "${customer_token}" != "null" ]]
[[ -n "${customer_user_id}" && "${customer_user_id}" != "null" ]]

admin_login_payload="$(jq -cn \
  --arg login_or_email "${CYBERVPN_ADMIN_SMOKE_EMAIL}" \
  --arg password "${CYBERVPN_ADMIN_SMOKE_PASSWORD}" \
  '{login_or_email: $login_or_email, password: $password}')"

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

preferences_before_status="$(
  api_get \
    "${EVIDENCE_DIR}/auth/preferences-before.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/growth-notifications/preferences" \
    -H "Authorization: Bearer ${customer_token}"
)"
[[ "${preferences_before_status}" == "200" ]]
customer_original_email_admin_updates="$(jq -r '.growth_email_admin_updates' "${EVIDENCE_DIR}/auth/preferences-before.json")"
[[ "${customer_original_email_admin_updates}" == "true" || "${customer_original_email_admin_updates}" == "false" ]]

# Scenario GCN-REPAIR-001: preference-disabled email delivery recovers after preference re-enable.
disable_email_pref_payload="$(jq -cn '{growth_email_admin_updates: false}')"
disable_email_pref_status="$(
  api_patch_json \
    "${EVIDENCE_DIR}/api/gcn-repair-001/preferences-disabled.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/growth-notifications/preferences" \
    "${disable_email_pref_payload}" \
    -H "Authorization: Bearer ${customer_token}"
)"
[[ "${disable_email_pref_status}" == "200" ]]
[[ "$(jq -r '.growth_email_admin_updates' "${EVIDENCE_DIR}/api/gcn-repair-001/preferences-disabled.json")" == "false" ]]

manual_pref_disabled_payload="$(jq -cn \
  --arg mobile_user_id "${customer_user_id}" \
  '{
    mobile_user_id: $mobile_user_id,
    title: "GCN staging preference-disabled recovery",
    message: "Verify email delivery recovery after preference re-enable.",
    route_slug: "/referral",
    locale: "en-EN",
    notes: ["GCN-STAGE-001", "preference_disabled_recovery"],
    channels: ["in_app", "email"]
  }')"

manual_pref_disabled_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/api/gcn-repair-001/manual-notification-created.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-notification-deliveries/manual" \
    "${manual_pref_disabled_payload}" \
    -H "Authorization: Bearer ${admin_token}" \
    -H 'X-Auth-Realm: admin'
)"
[[ "${manual_pref_disabled_status}" == "201" ]]

pref_disabled_email_delivery_id="$(jq -r '.deliveries[] | select(.delivery_channel=="email") | .id' "${EVIDENCE_DIR}/api/gcn-repair-001/manual-notification-created.json")"
pref_disabled_notification_key="$(jq -r '.deliveries[] | select(.delivery_channel=="email") | .notification_key' "${EVIDENCE_DIR}/api/gcn-repair-001/manual-notification-created.json")"
[[ -n "${pref_disabled_email_delivery_id}" && "${pref_disabled_email_delivery_id}" != "null" ]]
[[ -n "${pref_disabled_notification_key}" && "${pref_disabled_notification_key}" != "null" ]]
[[ "$(jq -r '.deliveries[] | select(.delivery_channel=="email") | .delivery_status' "${EVIDENCE_DIR}/api/gcn-repair-001/manual-notification-created.json")" == "skipped" ]]
[[ "$(jq -r '.deliveries[] | select(.delivery_channel=="email") | .status_reason' "${EVIDENCE_DIR}/api/gcn-repair-001/manual-notification-created.json")" == "preference_disabled" ]]

pref_disabled_customer_detail_status="$(
  api_get \
    "${EVIDENCE_DIR}/api/gcn-repair-001/customer-detail-pre-disabled.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/growth-notifications/${pref_disabled_notification_key}" \
    -H "Authorization: Bearer ${customer_token}"
)"
[[ "${pref_disabled_customer_detail_status}" == "200" ]]
[[ "$(jq -r '.deliveries[] | select(.delivery_channel=="email") | .troubleshooting_state' "${EVIDENCE_DIR}/api/gcn-repair-001/customer-detail-pre-disabled.json")" == "suppressed" ]]

enable_email_pref_payload="$(jq -cn '{growth_email_admin_updates: true}')"
enable_email_pref_status="$(
  api_patch_json \
    "${EVIDENCE_DIR}/api/gcn-repair-001/preferences-enabled.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/growth-notifications/preferences" \
    "${enable_email_pref_payload}" \
    -H "Authorization: Bearer ${customer_token}"
)"
[[ "${enable_email_pref_status}" == "200" ]]
[[ "$(jq -r '.growth_email_admin_updates' "${EVIDENCE_DIR}/api/gcn-repair-001/preferences-enabled.json")" == "true" ]]

pref_disabled_admin_detail_status="$(
  api_get \
    "${EVIDENCE_DIR}/api/gcn-repair-001/admin-detail-after-recovery.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-notification-deliveries/${pref_disabled_email_delivery_id}" \
    -H "Authorization: Bearer ${admin_token}" \
    -H 'X-Auth-Realm: admin'
)"
[[ "${pref_disabled_admin_detail_status}" == "200" ]]
pref_disabled_recovered_status="$(jq -r '.delivery.delivery_status' "${EVIDENCE_DIR}/api/gcn-repair-001/admin-detail-after-recovery.json")"
[[ "${pref_disabled_recovered_status}" == "planned" || "${pref_disabled_recovered_status}" == "delivered" ]]
jq -e '.events[] | select(.event_type=="repair_completed")' "${EVIDENCE_DIR}/api/gcn-repair-001/admin-detail-after-recovery.json" >/dev/null
jq -e '.events[] | select(.event_type=="delivery_recovered")' "${EVIDENCE_DIR}/api/gcn-repair-001/admin-detail-after-recovery.json" >/dev/null

pref_disabled_export_status="$(
  api_get \
    "${EVIDENCE_DIR}/exports/gcn-repair-001-recovered-export.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-notification-deliveries/${pref_disabled_email_delivery_id}/export" \
    -H "Authorization: Bearer ${admin_token}" \
    -H 'X-Auth-Realm: admin'
)"
[[ "${pref_disabled_export_status}" == "200" ]]

# Scenario GCN-REPAIR-004: paused delivery becomes unresolved, customer escalates, support resolves and emits closure.
manual_support_payload="$(jq -cn \
  --arg mobile_user_id "${customer_user_id}" \
  '{
    mobile_user_id: $mobile_user_id,
    title: "GCN staging support resolution",
    message: "Verify support escalation and closure after operator resolution.",
    route_slug: "/referral",
    locale: "en-EN",
    notes: ["GCN-STAGE-004", "support_resolved"],
    channels: ["in_app", "email"]
  }')"

manual_support_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/api/gcn-repair-004/manual-notification-created.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-notification-deliveries/manual" \
    "${manual_support_payload}" \
    -H "Authorization: Bearer ${admin_token}" \
    -H 'X-Auth-Realm: admin'
)"
[[ "${manual_support_status}" == "201" ]]

support_email_delivery_id="$(jq -r '.deliveries[] | select(.delivery_channel=="email") | .id' "${EVIDENCE_DIR}/api/gcn-repair-004/manual-notification-created.json")"
support_notification_key="$(jq -r '.deliveries[] | select(.delivery_channel=="email") | .notification_key' "${EVIDENCE_DIR}/api/gcn-repair-004/manual-notification-created.json")"
[[ -n "${support_email_delivery_id}" && "${support_email_delivery_id}" != "null" ]]
[[ -n "${support_notification_key}" && "${support_notification_key}" != "null" ]]
[[ "$(jq -r '.deliveries[] | select(.delivery_channel=="email") | .delivery_status' "${EVIDENCE_DIR}/api/gcn-repair-004/manual-notification-created.json")" == "planned" ]]

pause_payload="$(jq -cn '{reason_code: "staging_pause_for_unresolved_snapshot"}')"
pause_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/api/gcn-repair-004/admin-pause.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-notification-deliveries/${support_email_delivery_id}/pause" \
    "${pause_payload}" \
    -H "Authorization: Bearer ${admin_token}" \
    -H 'X-Auth-Realm: admin'
)"
[[ "${pause_status}" == "200" ]]
[[ "$(jq -r '.delivery_status' "${EVIDENCE_DIR}/api/gcn-repair-004/admin-pause.json")" == "paused" ]]

unresolved_export_status="$(
  api_get \
    "${EVIDENCE_DIR}/exports/gcn-repair-004-unresolved-export.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-notification-deliveries/${support_email_delivery_id}/export" \
    -H "Authorization: Bearer ${admin_token}" \
    -H 'X-Auth-Realm: admin'
)"
[[ "${unresolved_export_status}" == "200" ]]
[[ "$(jq -r '.delivery.delivery_status' "${EVIDENCE_DIR}/exports/gcn-repair-004-unresolved-export.json")" == "paused" ]]

support_detail_status="$(
  api_get \
    "${EVIDENCE_DIR}/api/gcn-repair-004/customer-detail-before-escalation.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/growth-notifications/${support_notification_key}" \
    -H "Authorization: Bearer ${customer_token}"
)"
[[ "${support_detail_status}" == "200" ]]
[[ "$(jq -r '.deliveries[] | select(.delivery_channel=="email") | .support_required' "${EVIDENCE_DIR}/api/gcn-repair-004/customer-detail-before-escalation.json")" == "true" ]]

support_escalation_payload="$(jq -cn '{delivery_channel: "email", escalation_channel: "contact_form"}')"
support_escalation_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/api/gcn-repair-004/customer-support-escalation.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/growth-notifications/${support_notification_key}/support-escalation" \
    "${support_escalation_payload}" \
    -H "Authorization: Bearer ${customer_token}"
)"
[[ "${support_escalation_status}" == "200" ]]
[[ "$(jq -r '.support_handoff.reference_code | startswith(\"GCN-\")' "${EVIDENCE_DIR}/api/gcn-repair-004/customer-support-escalation.json")" == "true" ]]

resolve_payload="$(jq -cn '{reason_code: "support_resolved"}')"
resolve_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/api/gcn-repair-004/admin-resolve.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-notification-deliveries/${support_email_delivery_id}/resolve" \
    "${resolve_payload}" \
    -H "Authorization: Bearer ${admin_token}" \
    -H 'X-Auth-Realm: admin'
)"
[[ "${resolve_status}" == "200" ]]
support_resolved_status="$(jq -r '.delivery_status' "${EVIDENCE_DIR}/api/gcn-repair-004/admin-resolve.json")"
[[ "${support_resolved_status}" == "planned" || "${support_resolved_status}" == "delivered" ]]

resolved_detail_status="$(
  api_get \
    "${EVIDENCE_DIR}/api/gcn-repair-004/admin-detail-after-resolve.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-notification-deliveries/${support_email_delivery_id}" \
    -H "Authorization: Bearer ${admin_token}" \
    -H 'X-Auth-Realm: admin'
)"
[[ "${resolved_detail_status}" == "200" ]]
jq -e '.events[] | select(.event_type=="support_resolved")' "${EVIDENCE_DIR}/api/gcn-repair-004/admin-detail-after-resolve.json" >/dev/null
jq -e '.events[] | select(.event_type=="delivery_recovered")' "${EVIDENCE_DIR}/api/gcn-repair-004/admin-detail-after-resolve.json" >/dev/null

resolved_export_status="$(
  api_get \
    "${EVIDENCE_DIR}/exports/gcn-repair-004-support-resolved-export.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-notification-deliveries/${support_email_delivery_id}/export" \
    -H "Authorization: Bearer ${admin_token}" \
    -H 'X-Auth-Realm: admin'
)"
[[ "${resolved_export_status}" == "200" ]]

customer_feed_after_status="$(
  api_get \
    "${EVIDENCE_DIR}/api/gcn-repair-004/customer-feed-after-resolve.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/growth-notifications?include_archived=true" \
    -H "Authorization: Bearer ${customer_token}"
)"
[[ "${customer_feed_after_status}" == "200" ]]
jq -e --arg source_id "${support_email_delivery_id}" '.[] | select(.source_kind=="growth_notification_closure" and .source_id==$source_id)' "${EVIDENCE_DIR}/api/gcn-repair-004/customer-feed-after-resolve.json" >/dev/null

if [[ "${PROMETHEUS_ENABLED}" == "true" ]]; then
  recovery_ratio_status="$(
    prom_query \
      "${EVIDENCE_DIR}/monitoring/recovery-ratio.json" \
      'avg(customer_growth:notification_recovery_ratio:24h)'
  )"
  [[ "${recovery_ratio_status}" == "200" ]]

  unresolved_delta_status="$(
    prom_query \
      "${EVIDENCE_DIR}/monitoring/unresolved-backlog-delta.json" \
      'sum(customer_growth:notification_unresolved_backlog_delta:24h)'
  )"
  [[ "${unresolved_delta_status}" == "200" ]]

  support_resolution_status="$(
    prom_query \
      "${EVIDENCE_DIR}/monitoring/support-resolutions.json" \
      'sum(customer_growth:notification_support_resolutions:increase24h)'
  )"
  [[ "${support_resolution_status}" == "200" ]]
else
  write_text \
    "${EVIDENCE_DIR}/monitoring/prometheus-skipped.txt" \
    "CYBERVPN_PROMETHEUS_BASE is not set. Monitoring proof was skipped for this smoke run."
fi

write_text \
  "${EVIDENCE_DIR}/notes/scenario-summary.txt" \
  "GCN-REPAIR-001 recovered delivery id: ${pref_disabled_email_delivery_id}
GCN-REPAIR-004 unresolved/support-resolved delivery id: ${support_email_delivery_id}
Customer id: ${customer_user_id}
Prometheus checks enabled: ${PROMETHEUS_ENABLED}"

restore_customer_preferences

printf '[OK] Customer growth notification staging smoke passed. Evidence written to %s\n' "${EVIDENCE_DIR}"
