#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.yml"
PROM_CONFIG="${ROOT_DIR}/prometheus/prometheus.yml"
PROM_RULES="${ROOT_DIR}/prometheus/rules/helix_alerts.yml"
DASHBOARD_FILE="${ROOT_DIR}/grafana/dashboards/helix-dashboard.json"
COMPOSE_ENV_FILE="${ROOT_DIR}/.env"
TEMP_ENV_CREATED=false

ADAPTER_URL="${HELIX_ADAPTER_URL:-http://localhost:8088}"
NODE_URL="${HELIX_NODE_URL:-http://localhost:8091}"
NODE_2_URL="${HELIX_NODE_2_URL:-http://localhost:8092}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9094}"
STRICT_LIVE_CHECKS="${HELIX_REQUIRE_LIVE:-false}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

passed=0
failed=0
warnings=0

cleanup() {
  if [[ "$TEMP_ENV_CREATED" == "true" ]]; then
    rm -f "$COMPOSE_ENV_FILE"
  fi
}

trap cleanup EXIT

pass() {
  echo -e "${GREEN}✓${NC} $1"
  passed=$((passed + 1))
}

fail() {
  echo -e "${RED}✗${NC} $1"
  failed=$((failed + 1))
}

warn() {
  echo -e "${YELLOW}⚠${NC} $1"
  warnings=$((warnings + 1))
}

require_pattern() {
  local file="$1"
  local pattern="$2"
  local message="$3"

  if grep -qE "$pattern" "$file"; then
    pass "$message"
  else
    fail "$message"
  fi
}

check_live_endpoint() {
  local name="$1"
  local url="$2"
  local expected_status="${3:-200}"

  if curl -fsS -o /dev/null "$url" 2>/dev/null; then
    pass "$name is reachable at $url"
    return 0
  fi

  if [[ "$STRICT_LIVE_CHECKS" == "true" ]]; then
    fail "$name is not reachable at $url"
    return 1
  fi

  warn "$name is not reachable at $url (skipped live failure because HELIX_REQUIRE_LIVE=false)"
  return 0
}

check_metric() {
  local name="$1"
  local url="$2"
  local metric="$3"

  local metrics
  if metrics="$(curl -fsS "$url" 2>/dev/null)"; then
    if grep -q "$metric" <<<"$metrics"; then
      pass "$name exposes $metric"
    else
      fail "$name does not expose $metric"
    fi
    return 0
  fi

  if [[ "$STRICT_LIVE_CHECKS" == "true" ]]; then
    fail "$name metrics are not reachable at $url"
    return 1
  fi

  warn "$name metrics are not reachable at $url (metric check skipped)"
  return 0
}

echo "Validating Helix infra artifacts..."

if command -v docker >/dev/null 2>&1 && docker version >/dev/null 2>&1; then
  if [[ ! -f "$COMPOSE_ENV_FILE" && -f "${ROOT_DIR}/.env.example" ]]; then
    cp "${ROOT_DIR}/.env.example" "$COMPOSE_ENV_FILE"
    TEMP_ENV_CREATED=true
  fi

  docker compose -f "$COMPOSE_FILE" config >/dev/null
  pass "docker compose configuration is valid"
else
  warn "docker is not available from this shell; skipped compose runtime validation"
fi

require_pattern "$COMPOSE_FILE" "helix-adapter:" "compose defines helix-adapter service"
require_pattern "$COMPOSE_FILE" "helix-node-lab:" "compose defines helix-node-lab service"
require_pattern "$COMPOSE_FILE" "helix-node-lab-02:" "compose defines helix-node-lab-02 service"
require_pattern "$COMPOSE_FILE" "helix-stable-http-proxy:" "compose defines helix stable HTTP proxy service"
require_pattern "$COMPOSE_FILE" "profiles: \\[\"helix\", \"helix-lab\"\\]" "adapter is available in both Helix profiles"
require_pattern "$COMPOSE_FILE" "profiles: \\[\"helix-lab\"\\]" "lab node uses the helix-lab profile"

require_pattern "$PROM_CONFIG" "helix_alerts.yml" "Prometheus loads Helix alert rules"
require_pattern "$PROM_CONFIG" "job_name: 'helix-adapter'" "Prometheus scrapes the adapter job"
require_pattern "$PROM_CONFIG" "job_name: 'helix-node'" "Prometheus scrapes the node job"

if command -v promtool >/dev/null 2>&1; then
  promtool check rules "$PROM_RULES" >/dev/null
  pass "Helix alert rules pass promtool validation"
else
  require_pattern "$PROM_RULES" "^groups:" "Helix alert rules file exists"
  require_pattern "$PROM_RULES" "HelixAdapterDown" "Helix alert rules include adapter availability alert"
fi

if jq empty "$DASHBOARD_FILE" >/dev/null 2>&1; then
  pass "Helix dashboard JSON is valid"
else
  fail "Helix dashboard JSON is invalid"
fi

require_pattern "$DASHBOARD_FILE" "\"title\": \"CyberVPN Helix\"" "Grafana dashboard title is present"
require_pattern "$DASHBOARD_FILE" "helix_manifest_issued_total" "dashboard includes manifest issuance telemetry"
require_pattern "$DASHBOARD_FILE" "helix_node_runtime_healthy" "dashboard includes node runtime health telemetry"
require_pattern "$DASHBOARD_FILE" "helix_node_rollback_total" "dashboard includes rollback telemetry"

check_live_endpoint "Helix adapter" "${ADAPTER_URL}/healthz"
check_live_endpoint "Helix node" "${NODE_URL}/healthz"
check_live_endpoint "Helix node 02" "${NODE_2_URL}/healthz"
check_live_endpoint "Helix stable HTTP proxy" "http://localhost:${HELIX_STABLE_PROXY_PORT:-8899}/healthz"
check_metric "Helix node" "${NODE_URL}/metrics" "helix_node_rollback_total"
check_metric "Helix node 02" "${NODE_2_URL}/metrics" "helix_node_runtime_healthy"

targets_json="$(mktemp)"

if curl -fsS "${PROMETHEUS_URL}/api/v1/targets" >"${targets_json}" 2>/dev/null; then
  if jq -e '.data.activeTargets[]?.labels.job | select(. == "helix-adapter")' "${targets_json}" >/dev/null; then
    pass "Prometheus target list includes helix-adapter"
  else
    fail "Prometheus target list does not include helix-adapter"
  fi

  if jq -e '.data.activeTargets[]? | select(.labels.job == "helix-node")' "${targets_json}" >/dev/null; then
    pass "Prometheus target list includes helix-node"
  else
    fail "Prometheus target list does not include helix-node"
  fi

  if jq -e '.data.activeTargets[]? | select(.labels.job == "helix-node" and (.scrapeUrl | contains("helix-node-lab-02:8091")))' "${targets_json}" >/dev/null; then
    pass "Prometheus target list includes helix-node-lab-02"
  else
    fail "Prometheus target list does not include helix-node-lab-02"
  fi
else
  if [[ "$STRICT_LIVE_CHECKS" == "true" ]]; then
    fail "Prometheus target API is not reachable at ${PROMETHEUS_URL}"
  else
    warn "Prometheus target API is not reachable at ${PROMETHEUS_URL} (live target checks skipped)"
  fi
fi

rm -f "${targets_json}"

echo
echo "Passed: ${passed}"
echo "Warnings: ${warnings}"
echo "Failed: ${failed}"

if [[ "$failed" -gt 0 ]]; then
  exit 1
fi

exit 0
