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

api_put_json() {
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
      -X PUT \
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
require_env CYBERVPN_GROWTH_REPORTING_INTERNAL_SECRET

EVIDENCE_DIR="${EVIDENCE_DIR:-$(mktemp -d)}"
PROMETHEUS_ENABLED="false"
if [[ -n "${CYBERVPN_PROMETHEUS_BASE:-}" ]]; then
  PROMETHEUS_ENABLED="true"
fi

allowed_domain="${CYBERVPN_GROWTH_REPORTING_ALLOWED_DOMAIN:-}"
if [[ -z "${allowed_domain}" ]]; then
  allowed_domain="${CYBERVPN_ADMIN_SMOKE_EMAIL##*@}"
fi

run_suffix="$(date +%s)"
suppressed_email="growth-reporting-suppressed-${run_suffix}@${allowed_domain}"
healthy_email="growth-reporting-healthy-${run_suffix}@${allowed_domain}"
blocked_email="growth-reporting-blocked-${run_suffix}@blocked.invalid"

mkdir -p \
  "${EVIDENCE_DIR}/auth" \
  "${EVIDENCE_DIR}/api/grg-001" \
  "${EVIDENCE_DIR}/api/grg-002" \
  "${EVIDENCE_DIR}/api/grg-003" \
  "${EVIDENCE_DIR}/api/grg-004" \
  "${EVIDENCE_DIR}/exports" \
  "${EVIDENCE_DIR}/monitoring" \
  "${EVIDENCE_DIR}/notes"

admin_token=""
suppressed_subscription_id=""
healthy_subscription_id=""
blocked_subscription_id=""
cleanup_attempted="false"

pause_subscription_if_exists() {
  local subscription_id="$1"
  local target_path="$2"
  if [[ -z "${subscription_id}" || -z "${admin_token}" ]]; then
    return 0
  fi

  local pause_payload
  pause_payload="$(jq -cn '{reason_code: "staging_smoke_cleanup"}')"

  api_post_json \
    "${target_path}" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-reporting/subscriptions/${subscription_id}/pause" \
    "${pause_payload}" \
    -H "Authorization: Bearer ${admin_token}" \
    >/dev/null || true
}

cleanup_subscriptions() {
  if [[ "${cleanup_attempted}" == "true" ]]; then
    return 0
  fi
  cleanup_attempted="true"

  pause_subscription_if_exists "${suppressed_subscription_id}" "${EVIDENCE_DIR}/notes/suppressed-cleanup.json"
  pause_subscription_if_exists "${healthy_subscription_id}" "${EVIDENCE_DIR}/notes/healthy-cleanup.json"
  pause_subscription_if_exists "${blocked_subscription_id}" "${EVIDENCE_DIR}/notes/blocked-cleanup.json"
}

trap cleanup_subscriptions EXIT

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

refresh_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/api/refresh.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-reporting/refresh?window_days=30" \
    '{}' \
    -H "Authorization: Bearer ${admin_token}"
)"
[[ "${refresh_status}" == "200" ]]

future_suppression="$(date -u -d '+1 day' '+%Y-%m-%dT%H:%M:%SZ')"

suppressed_payload="$(jq -cn \
  --arg email "${suppressed_email}" \
  --arg suppressed_until "${future_suppression}" \
  '{
    recipient_email: $email,
    recipient_name: "Governance Suppressed Smoke",
    audience_key: "ops",
    cadence: "daily",
    report_window_days: 14,
    policy: {
      template_key: "ops_exec",
      template_locale: "en-EN",
      recipient_domain_policy: "allow_any",
      allowed_recipient_domains: [],
      suppressed_until: $suppressed_until,
      suppression_reason_code: "staging_governance_smoke"
    }
  }')"

suppressed_create_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/api/grg-001/subscription-created.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-reporting/subscriptions" \
    "${suppressed_payload}" \
    -H "Authorization: Bearer ${admin_token}"
)"
[[ "${suppressed_create_status}" == "201" ]]
suppressed_subscription_id="$(jq -r '.id' "${EVIDENCE_DIR}/api/grg-001/subscription-created.json")"

healthy_payload="$(jq -cn \
  --arg email "${healthy_email}" \
  --arg domain "${allowed_domain}" \
  '{
    recipient_email: $email,
    recipient_name: "Governance Healthy Smoke",
    audience_key: "product",
    cadence: "daily",
    report_window_days: 14,
    policy: {
      template_key: "product_exec",
      template_locale: "en-EN",
      recipient_domain_policy: "allowlist_only",
      allowed_recipient_domains: [$domain]
    }
  }')"

healthy_create_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/notes/healthy-subscription-created.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-reporting/subscriptions" \
    "${healthy_payload}" \
    -H "Authorization: Bearer ${admin_token}"
)"
[[ "${healthy_create_status}" == "201" ]]
healthy_subscription_id="$(jq -r '.id' "${EVIDENCE_DIR}/notes/healthy-subscription-created.json")"

blocked_payload="$(jq -cn \
  --arg email "${blocked_email}" \
  --arg domain "${allowed_domain}" \
  '{
    recipient_email: $email,
    recipient_name: "Governance Blocked Smoke",
    audience_key: "risk",
    cadence: "daily",
    report_window_days: 14,
    policy: {
      template_key: "risk_exec",
      template_locale: "en-EN",
      recipient_domain_policy: "allowlist_only",
      allowed_recipient_domains: [$domain]
    }
  }')"

blocked_create_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/api/grg-002/subscription-created.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-reporting/subscriptions" \
    "${blocked_payload}" \
    -H "Authorization: Bearer ${admin_token}"
)"
[[ "${blocked_create_status}" == "201" ]]
blocked_subscription_id="$(jq -r '.id' "${EVIDENCE_DIR}/api/grg-002/subscription-created.json")"

claim_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/api/claim.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-reporting/internal/deliveries/claim?limit=20" \
    '{}' \
    -H "X-Telegram-Bot-Secret: ${CYBERVPN_GROWTH_REPORTING_INTERNAL_SECRET}"
)"
[[ "${claim_status}" == "200" ]]

healthy_delivery_id="$(jq -r --arg email "${healthy_email}" '.deliveries[]? | select(.recipient_email == $email) | .delivery_id' "${EVIDENCE_DIR}/api/claim.json" | head -n 1)"
[[ -n "${healthy_delivery_id}" ]]
complete_status="$(
  api_post_json \
    "${EVIDENCE_DIR}/notes/healthy-delivery-complete.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-reporting/internal/deliveries/${healthy_delivery_id}/complete" \
    '{"delivery_status":"delivered","provider_name":"email","provider_message_id":"staging-governance-smoke","failure_message":null}' \
    -H "X-Telegram-Bot-Secret: ${CYBERVPN_GROWTH_REPORTING_INTERNAL_SECRET}"
)"
[[ "${complete_status}" == "200" ]]

governance_overview_status="$(
  api_get \
    "${EVIDENCE_DIR}/api/grg-003/governance-overview.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-reporting/governance" \
    -H "Authorization: Bearer ${admin_token}"
)"
[[ "${governance_overview_status}" == "200" ]]

governance_export_status="$(
  api_get \
    "${EVIDENCE_DIR}/exports/grg-003-governance-export.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-reporting/governance/export" \
    -H "Authorization: Bearer ${admin_token}"
)"
[[ "${governance_export_status}" == "200" ]]

deliveries_status="$(
  api_get \
    "${EVIDENCE_DIR}/api/grg-004/deliveries.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-reporting/deliveries?limit=20" \
    -H "Authorization: Bearer ${admin_token}"
)"
[[ "${deliveries_status}" == "200" ]]

subscriptions_status="$(
  api_get \
    "${EVIDENCE_DIR}/notes/subscriptions.json" \
    "${CYBERVPN_API_BASE%/}/api/v1/admin/growth-reporting/subscriptions" \
    -H "Authorization: Bearer ${admin_token}"
)"
[[ "${subscriptions_status}" == "200" ]]

jq -e '.coverage_gap_count >= 2' "${EVIDENCE_DIR}/api/grg-003/governance-overview.json" >/dev/null
jq -e '.coverage_counts[] | select(.coverage_state == "delivery_suppressed" and .count >= 1)' "${EVIDENCE_DIR}/api/grg-003/governance-overview.json" >/dev/null
jq -e '.coverage_counts[] | select(.coverage_state == "recipient_domain_blocked" and .count >= 1)' "${EVIDENCE_DIR}/api/grg-003/governance-overview.json" >/dev/null
jq -e '.recent_decisions[] | select(.status_reason == "delivery_suppressed")' "${EVIDENCE_DIR}/api/grg-003/governance-overview.json" >/dev/null
jq -e '.recent_decisions[] | select(.status_reason == "recipient_domain_blocked")' "${EVIDENCE_DIR}/api/grg-003/governance-overview.json" >/dev/null
jq -e '.recent_audit_events | length >= 3' "${EVIDENCE_DIR}/api/grg-003/governance-overview.json" >/dev/null
jq -e '.export_kind == "growth_reporting_governance_snapshot"' "${EVIDENCE_DIR}/exports/grg-003-governance-export.json" >/dev/null
jq -e '.payload.subscriptions | length >= 3' "${EVIDENCE_DIR}/exports/grg-003-governance-export.json" >/dev/null

if [[ "${PROMETHEUS_ENABLED}" == "true" ]]; then
  prom_query \
    "${EVIDENCE_DIR}/monitoring/governance-gap-metric.json" \
    'customer_growth:reporting_governance_gap_subscriptions' >/dev/null
  prom_query \
    "${EVIDENCE_DIR}/monitoring/recipient-domain-blocked-metric.json" \
    'customer_growth:reporting_recipient_domain_blocked_subscriptions' >/dev/null
fi

bash "$(dirname "$0")/assess-customer-growth-reporting-governance-gate-readiness.sh" "${EVIDENCE_DIR}"

printf '[OK] Customer growth reporting governance staging smoke completed. Evidence directory: %s\n' "${EVIDENCE_DIR}"
