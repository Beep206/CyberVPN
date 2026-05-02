#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO_SLUG="${GITHUB_REPO_SLUG:-Beep206/CyberVPN}"
RULESET_NAME="customer-growth-notification-main-gate"
PAYLOAD_FILE="${REPO_ROOT}/.github/rulesets/customer-growth-notification-main-gate.disabled.json"
API_VERSION_HEADER="X-GitHub-Api-Version: 2026-03-10"
ACCEPT_HEADER="Accept: application/vnd.github+json"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/sync-customer-growth-notification-ruleset.sh --show-current
  bash scripts/sync-customer-growth-notification-ruleset.sh --create-disabled
  bash scripts/sync-customer-growth-notification-ruleset.sh --disable
  bash scripts/sync-customer-growth-notification-ruleset.sh --enable

Default repository:
  Beep206/CyberVPN

Override with:
  GITHUB_REPO_SLUG=owner/repo
EOF
}

fail() {
  printf "\033[0;31m[FAIL]\033[0m  %s\n" "$*" >&2
}

info() {
  printf "\033[0;34m[INFO]\033[0m  %s\n" "$*"
}

ok() {
  printf "\033[0;32m[OK]\033[0m    %s\n" "$*"
}

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    fail "Required command '${command_name}' is not available."
    exit 1
  fi
}

gh_api() {
  gh api -H "${ACCEPT_HEADER}" -H "${API_VERSION_HEADER}" "$@"
}

ruleset_id_by_name() {
  gh_api "repos/${REPO_SLUG}/rulesets" --jq ".[] | select(.name == \"${RULESET_NAME}\") | .id" | head -n 1
}

payload_with_enforcement() {
  local enforcement="$1"
  jq --arg enforcement "${enforcement}" '.enforcement = $enforcement' "${PAYLOAD_FILE}"
}

show_current() {
  local ruleset_id
  ruleset_id="$(ruleset_id_by_name || true)"

  if [[ -z "${ruleset_id}" ]]; then
    info "Ruleset '${RULESET_NAME}' does not exist in ${REPO_SLUG}."
    return 0
  fi

  gh_api "repos/${REPO_SLUG}/rulesets/${ruleset_id}" \
    --jq '{id, name, enforcement, target, html_url: ._links.html.href, required_status_checks: (.rules[]?.parameters.required_status_checks // [])}'
}

create_disabled() {
  local existing_id
  existing_id="$(ruleset_id_by_name || true)"

  if [[ -n "${existing_id}" ]]; then
    info "Ruleset '${RULESET_NAME}' already exists with id ${existing_id}."
    show_current
    return 0
  fi

  gh_api -X POST "repos/${REPO_SLUG}/rulesets" --input "${PAYLOAD_FILE}" \
    --jq '{id, name, enforcement, html_url: ._links.html.href}'
  ok "Disabled ruleset created."
}

update_enforcement() {
  local target_enforcement="$1"
  local ruleset_id
  local temp_payload

  ruleset_id="$(ruleset_id_by_name || true)"
  if [[ -z "${ruleset_id}" ]]; then
    fail "Ruleset '${RULESET_NAME}' does not exist in ${REPO_SLUG}."
    exit 1
  fi

  temp_payload="$(mktemp)"
  trap 'rm -f "${temp_payload}"' EXIT
  payload_with_enforcement "${target_enforcement}" > "${temp_payload}"

  gh_api -X PUT "repos/${REPO_SLUG}/rulesets/${ruleset_id}" --input "${temp_payload}" \
    --jq '{id, name, enforcement, html_url: ._links.html.href}'
  ok "Ruleset '${RULESET_NAME}' updated to enforcement=${target_enforcement}."

  rm -f "${temp_payload}"
  trap - EXIT
}

main() {
  require_command gh
  require_command jq

  case "${1:-}" in
    --show-current)
      show_current
      ;;
    --create-disabled)
      create_disabled
      ;;
    --disable)
      update_enforcement "disabled"
      ;;
    --enable)
      update_enforcement "active"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
