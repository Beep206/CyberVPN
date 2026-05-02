#!/usr/bin/env bash

set -euo pipefail

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    printf '[FAIL] Required command %s is not available on PATH.\n' "${command_name}" >&2
    exit 1
  fi
}

require_file() {
  local file_path="$1"
  if [[ ! -f "${file_path}" ]]; then
    printf '[FAIL] Required evidence file %s does not exist.\n' "${file_path}" >&2
    exit 1
  fi
}

read_status() {
  local file_path="$1"
  require_file "${file_path}"
  tr -d '\n' < "${file_path}"
}

check_status() {
  local label="$1"
  local file_path="$2"
  local expected_status="$3"
  local actual_status

  actual_status="$(read_status "${file_path}")"
  if [[ "${actual_status}" != "${expected_status}" ]]; then
    blocking_items+=("${label}: expected HTTP ${expected_status}, got ${actual_status}")
  fi
}

check_jq() {
  local label="$1"
  local jq_program="$2"
  local file_path="$3"

  require_file "${file_path}"
  if ! jq -e "${jq_program}" "${file_path}" >/dev/null 2>&1; then
    blocking_items+=("${label}: expected jq assertion '${jq_program}' to pass for ${file_path}")
  fi
}

check_jq_with_arg() {
  local label="$1"
  local arg_name="$2"
  local arg_value="$3"
  local jq_program="$4"
  local file_path="$5"

  require_file "${file_path}"
  if ! jq -e --arg "${arg_name}" "${arg_value}" "${jq_program}" "${file_path}" >/dev/null 2>&1; then
    blocking_items+=("${label}: expected jq assertion '${jq_program}' to pass for ${file_path}")
  fi
}

json_string_array() {
  local values=("$@")
  if [[ ${#values[@]} -eq 0 ]]; then
    printf '[]'
    return
  fi
  printf '%s\n' "${values[@]}" | jq -R . | jq -s .
}

markdown_bullets() {
  local values=("$@")
  if [[ ${#values[@]} -eq 0 ]]; then
    printf '%s\n' '- none'
    return
  fi

  local value
  for value in "${values[@]}"; do
    printf -- '- %s\n' "${value}"
  done
}

require_command jq

EVIDENCE_DIR="${1:-${EVIDENCE_DIR:-}}"
if [[ -z "${EVIDENCE_DIR}" ]]; then
  printf '[FAIL] Usage: bash scripts/assess-customer-growth-reporting-governance-gate-readiness.sh <evidence-dir>\n' >&2
  exit 1
fi

if [[ ! -d "${EVIDENCE_DIR}" ]]; then
  printf '[FAIL] Evidence directory %s does not exist.\n' "${EVIDENCE_DIR}" >&2
  exit 1
fi

APPROVALS_DIR="${EVIDENCE_DIR}/approvals"
mkdir -p "${APPROVALS_DIR}"

monitoring_required="${CYBERVPN_GROWTH_REPORTING_GOVERNANCE_REQUIRE_MONITORING:-false}"
checked_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

blocking_items=()
notes=()

check_status "admin login" "${EVIDENCE_DIR}/auth/admin-login.status" "200"
check_status "growth reporting refresh" "${EVIDENCE_DIR}/api/refresh.status" "200"
check_status "suppressed subscription create" "${EVIDENCE_DIR}/api/grg-001/subscription-created.status" "201"
check_status "blocked subscription create" "${EVIDENCE_DIR}/api/grg-002/subscription-created.status" "201"
check_status "claim deliveries" "${EVIDENCE_DIR}/api/claim.status" "200"
check_status "governance overview" "${EVIDENCE_DIR}/api/grg-003/governance-overview.status" "200"
check_status "governance export" "${EVIDENCE_DIR}/exports/grg-003-governance-export.status" "200"
check_status "deliveries export" "${EVIDENCE_DIR}/api/grg-004/deliveries.status" "200"
check_status "healthy delivery completion" "${EVIDENCE_DIR}/notes/healthy-delivery-complete.status" "200"

check_jq "governance coverage gap count" '.coverage_gap_count >= 2' "${EVIDENCE_DIR}/api/grg-003/governance-overview.json"
check_jq "suppressed coverage present" '.coverage_counts[] | select(.coverage_state == "delivery_suppressed" and .count >= 1)' "${EVIDENCE_DIR}/api/grg-003/governance-overview.json"
check_jq "blocked coverage present" '.coverage_counts[] | select(.coverage_state == "recipient_domain_blocked" and .count >= 1)' "${EVIDENCE_DIR}/api/grg-003/governance-overview.json"
check_jq "suppressed decision present" '.recent_decisions[] | select(.status_reason == "delivery_suppressed")' "${EVIDENCE_DIR}/api/grg-003/governance-overview.json"
check_jq "blocked decision present" '.recent_decisions[] | select(.status_reason == "recipient_domain_blocked")' "${EVIDENCE_DIR}/api/grg-003/governance-overview.json"
check_jq "audit evidence present" '.recent_audit_events | length >= 3' "${EVIDENCE_DIR}/api/grg-003/governance-overview.json"
check_jq "governance export kind" '.export_kind == "growth_reporting_governance_snapshot"' "${EVIDENCE_DIR}/exports/grg-003-governance-export.json"
check_jq "governance export subscription count" '.payload.subscriptions | length >= 3' "${EVIDENCE_DIR}/exports/grg-003-governance-export.json"

healthy_email="$(
  jq -r '.recipient_email // .subscription.recipient_email // empty' \
    "${EVIDENCE_DIR}/notes/healthy-subscription-created.json" 2>/dev/null
)"
if [[ -z "${healthy_email}" ]]; then
  blocking_items+=("healthy delivery claim: unable to determine healthy recipient email from evidence")
else
  check_jq_with_arg \
    "healthy delivery claim" \
    "recipient_email" \
    "${healthy_email}" \
    '.deliveries[]? | select(.recipient_email == $recipient_email)' \
    "${EVIDENCE_DIR}/api/claim.json"
fi

monitoring_present="false"
if [[ -f "${EVIDENCE_DIR}/monitoring/governance-gap-metric.status" ]]; then
  monitoring_present="true"
  check_status "governance gap metric" "${EVIDENCE_DIR}/monitoring/governance-gap-metric.status" "200"
  check_status "recipient-domain-blocked metric" "${EVIDENCE_DIR}/monitoring/recipient-domain-blocked-metric.status" "200"
  check_jq "governance gap metric payload" '.status == "success"' "${EVIDENCE_DIR}/monitoring/governance-gap-metric.json"
  check_jq "recipient-domain-blocked metric payload" '.status == "success"' "${EVIDENCE_DIR}/monitoring/recipient-domain-blocked-metric.json"
else
  notes+=("monitoring proof not attached in evidence directory")
  if [[ "${monitoring_required}" == "true" ]]; then
    blocking_items+=("monitoring proof required but governance metric artifacts are missing")
  fi
fi

decision="enable"
result="passed"
summary="Evidence is sufficient to recommend protected gate activation."
if [[ ${#blocking_items[@]} -gt 0 ]]; then
  decision="hold"
  result="failed"
  summary="Evidence is incomplete or inconsistent; hold protected gate activation until blockers are resolved."
fi

blocking_items_json="$(json_string_array "${blocking_items[@]}")"
notes_json="$(json_string_array "${notes[@]}")"

jq -n \
  --arg checked_at "${checked_at}" \
  --arg evidence_dir "${EVIDENCE_DIR}" \
  --arg result "${result}" \
  --arg decision "${decision}" \
  --arg summary "${summary}" \
  --argjson protected_gate_ready "$([[ "${decision}" == "enable" ]] && printf 'true' || printf 'false')" \
  --argjson monitoring_proof_required "$([[ "${monitoring_required}" == "true" ]] && printf 'true' || printf 'false')" \
  --argjson monitoring_proof_present "$([[ "${monitoring_present}" == "true" ]] && printf 'true' || printf 'false')" \
  --argjson blocking_items "${blocking_items_json}" \
  --argjson notes "${notes_json}" \
  '{
    checked_at: $checked_at,
    evidence_dir: $evidence_dir,
    result: $result,
    decision: $decision,
    protected_gate_ready: $protected_gate_ready,
    monitoring_proof_required: $monitoring_proof_required,
    monitoring_proof_present: $monitoring_proof_present,
    summary: $summary,
    blocking_items: $blocking_items,
    notes: $notes
  }' > "${APPROVALS_DIR}/gate-readiness.json"

cat > "${APPROVALS_DIR}/gate-readiness.md" <<EOF
# Customer Growth Reporting Governance Gate Readiness

**Checked At:** ${checked_at}
**Evidence Directory:** \`${EVIDENCE_DIR}\`
**Result:** ${result}
**Decision:** ${decision}
**Protected Gate Ready:** $([[ "${decision}" == "enable" ]] && printf 'yes' || printf 'no')
**Monitoring Proof Required:** ${monitoring_required}
**Monitoring Proof Present:** ${monitoring_present}

## Summary

${summary}

## Blocking Items

$(markdown_bullets "${blocking_items[@]}")

## Notes

$(markdown_bullets "${notes[@]}")
EOF

printf '[OK] Gate readiness assessment completed. Decision: %s. Evidence: %s\n' "${decision}" "${APPROVALS_DIR}/gate-readiness.json"
