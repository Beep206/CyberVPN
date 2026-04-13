#!/usr/bin/env bash
set -euo pipefail

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "[error] Required command not found: $command_name" >&2
    exit 1
  fi
}

require_env() {
  local var_name="$1"
  if [[ -z "${!var_name:-}" ]]; then
    echo "[error] Required environment variable is missing: $var_name" >&2
    exit 1
  fi
}

print_step() {
  local message="$1"
  echo
  echo "[step] $message"
}

print_ok() {
  local message="$1"
  echo "[ok] $message"
}

require_command curl
require_command jq

require_env REMNAWAVE_BASE_URL
require_env REMNAWAVE_API_TOKEN
require_env API_BASE_URL
require_env EXPECTED_NODE_NAME
require_env ADMIN_LOGIN
require_env ADMIN_PASSWORD
require_env SMOKE_USER_LOGIN
require_env SMOKE_USER_PASSWORD

SMOKE_ALLOW_CANCEL="${SMOKE_ALLOW_CANCEL:-false}"

json_post() {
  local url="$1"
  local payload="$2"
  local auth_header="${3:-}"

  if [[ -n "$auth_header" ]]; then
    curl -fsS -X POST "$url" \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $auth_header" \
      -d "$payload"
    return
  fi

  curl -fsS -X POST "$url" \
    -H "Content-Type: application/json" \
    -d "$payload"
}

json_get() {
  local url="$1"
  local auth_header="${2:-}"

  if [[ -n "$auth_header" ]]; then
    curl -fsS "$url" -H "Authorization: Bearer $auth_header"
    return
  fi

  curl -fsS "$url"
}

issue_token() {
  local login="$1"
  local password="$2"

  local payload
  payload="$(jq -n --arg login "$login" --arg password "$password" '{login_or_email: $login, password: $password}')"

  json_post "$API_BASE_URL/auth/login" "$payload" | jq -er '.access_token'
}

print_step "Verify Remnawave node registration"
nodes_response="$(
  curl -fsS "$REMNAWAVE_BASE_URL/api/nodes" \
    -H "Authorization: Bearer $REMNAWAVE_API_TOKEN"
)"
echo "$nodes_response" | jq .
echo "$nodes_response" \
  | jq -er --arg node "$EXPECTED_NODE_NAME" 'first(.response[]? | select(.name == $node))' >/tmp/remnawave-staging-node.json
echo "$nodes_response" \
  | jq -er --arg node "$EXPECTED_NODE_NAME" 'first(.response[]? | select(.name == $node and .isConnected == true))' >/dev/null
print_ok "Expected node is present and connected"

print_step "Issue backend admin token"
ADMIN_TOKEN="$(issue_token "$ADMIN_LOGIN" "$ADMIN_PASSWORD")"
print_ok "Admin token issued"

print_step "Check backend monitoring health"
health_response="$(json_get "$API_BASE_URL/monitoring/health" "$ADMIN_TOKEN")"
echo "$health_response" | jq .
echo "$health_response" | jq -er '.status == "healthy"' >/dev/null
echo "$health_response" | jq -er '.components.database.status == "healthy"' >/dev/null
echo "$health_response" | jq -er '.components.redis.status == "healthy"' >/dev/null
echo "$health_response" | jq -er '.components.remnawave.status == "healthy"' >/dev/null
print_ok "Monitoring health is healthy across database, redis, and remnawave"

print_step "Check backend monitoring stats"
stats_response="$(json_get "$API_BASE_URL/monitoring/stats" "$ADMIN_TOKEN")"
echo "$stats_response" | jq .
echo "$stats_response" | jq -er '.timestamp | type == "string"' >/dev/null
echo "$stats_response" | jq -er '.total_servers >= 1' >/dev/null
echo "$stats_response" | jq -er '.online_servers >= 1' >/dev/null
print_ok "Monitoring stats report non-zero server inventory"

print_step "Check node plugins facade"
node_plugins_response="$(json_get "$API_BASE_URL/node-plugins/" "$ADMIN_TOKEN")"
echo "$node_plugins_response" | jq .
echo "$node_plugins_response" | jq -er '.total >= 0' >/dev/null
echo "$node_plugins_response" | jq -er '.nodePlugins | type == "array"' >/dev/null
print_ok "Node plugins facade responds with expected shape"

print_step "Issue disposable smoke user token"
SMOKE_USER_TOKEN="$(issue_token "$SMOKE_USER_LOGIN" "$SMOKE_USER_PASSWORD")"
print_ok "Smoke user token issued"

print_step "Check subscription read path"
subscription_active_response="$(json_get "$API_BASE_URL/subscriptions/active" "$SMOKE_USER_TOKEN")"
echo "$subscription_active_response" | jq .
echo "$subscription_active_response" | jq -er '.status | type == "string"' >/dev/null
print_ok "Subscription read path responds with expected shape"

if [[ "$SMOKE_ALLOW_CANCEL" == "true" ]]; then
  print_step "Check subscription cancel path"
  subscription_cancel_response="$(
    curl -fsS -X POST "$API_BASE_URL/subscriptions/cancel" \
      -H "Authorization: Bearer $SMOKE_USER_TOKEN"
  )"
  echo "$subscription_cancel_response" | jq .
  echo "$subscription_cancel_response" | jq -er '.canceled_at | type == "string"' >/dev/null
  print_ok "Subscription cancel path responds with expected shape"
else
  echo
  echo "[warn] Skipping subscription cancel path because SMOKE_ALLOW_CANCEL is not true"
  echo "[warn] Set SMOKE_ALLOW_CANCEL=true only for a disposable staging smoke user"
fi

echo
print_ok "Remnawave staging smoke completed"
