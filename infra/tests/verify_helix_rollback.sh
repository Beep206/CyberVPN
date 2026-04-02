#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.yml"
RESET_SCRIPT="${ROOT_DIR}/tests/reset_helix_lab_history.sh"
BOOTSTRAP_SCRIPT="${ROOT_DIR}/tests/bootstrap_helix_lab.sh"
STACK_TEST_SCRIPT="${ROOT_DIR}/tests/test_helix_stack.sh"
RUNBOOK_FILE="${ROOT_DIR}/../backend/docs/INCIDENT_RESPONSE_RUNBOOK.md"
ROTATION_FILE="${ROOT_DIR}/../docs/secret-rotation.md"

STRICT_LIVE_CHECKS="${HELIX_REQUIRE_LIVE:-false}"
RUN_DESTRUCTIVE_DRILL="${HELIX_RUN_DESTRUCTIVE_DRILL:-false}"
ADAPTER_URL="${HELIX_ADAPTER_URL:-http://localhost:8088}"
NODE_URL="${HELIX_NODE_URL:-http://localhost:8091}"
NODE_2_URL="${HELIX_NODE_2_URL:-http://localhost:8092}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

passed=0
failed=0
warnings=0

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

require_file() {
  local path="$1"
  local message="$2"
  if [[ -f "$path" ]]; then
    pass "$message"
  else
    fail "$message"
  fi
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
  if curl -fsS -o /dev/null "$url" 2>/dev/null; then
    pass "$name is reachable at $url"
    return 0
  fi

  if [[ "$STRICT_LIVE_CHECKS" == "true" ]]; then
    fail "$name is not reachable at $url"
    return 1
  fi

  warn "$name is not reachable at $url (live check skipped because HELIX_REQUIRE_LIVE=false)"
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

echo "Verifying Helix rollback and failure-drill artifacts..."

require_file "$RESET_SCRIPT" "reset_helix_lab_history.sh exists"
require_file "$BOOTSTRAP_SCRIPT" "bootstrap_helix_lab.sh exists"
require_file "$STACK_TEST_SCRIPT" "test_helix_stack.sh exists"
require_file "$RUNBOOK_FILE" "backend incident runbook exists"
require_file "$ROTATION_FILE" "secret rotation guide exists"

if command -v docker >/dev/null 2>&1 && docker version >/dev/null 2>&1; then
  docker compose -f "$COMPOSE_FILE" config >/dev/null
  pass "docker compose configuration is valid"
else
  warn "docker is not available from this shell; skipped compose runtime validation"
fi

require_pattern "$COMPOSE_FILE" "STATE_DIR=/var/lib/helix-node" "compose configures Helix node state directory"
require_pattern "$COMPOSE_FILE" "helix_node_state:/var/lib/helix-node" "compose persists primary node state volume"
require_pattern "$COMPOSE_FILE" "helix_node_state_2:/var/lib/helix-node" "compose persists secondary node state volume"
require_pattern "$COMPOSE_FILE" "helix-node-lab-02" "compose defines secondary Helix lab node"

require_pattern "$RESET_SCRIPT" "docker volume rm -f" "reset script removes Helix node state volume"
require_pattern "$RESET_SCRIPT" "TRUNCATE TABLE" "reset script clears Helix adapter database state"
require_pattern "$RESET_SCRIPT" "helix.desktop_runtime_events" "reset script clears desktop runtime evidence"
require_pattern "$BOOTSTRAP_SCRIPT" "target_node_ids" "bootstrap script republishes a rollout batch"
require_pattern "$BOOTSTRAP_SCRIPT" "helix-node-lab-02" "bootstrap script waits for both lab nodes"
require_pattern "$STACK_TEST_SCRIPT" "helix-node-lab-02" "stack test validates dual-node Helix lab wiring"

require_pattern "$RUNBOOK_FILE" "Helix" "incident runbook contains Helix sections"
require_pattern "$ROTATION_FILE" "HELIX_" "secret rotation guide includes Helix secrets"

check_live_endpoint "Helix adapter" "${ADAPTER_URL}/healthz"
check_live_endpoint "Helix node" "${NODE_URL}/healthz"
check_live_endpoint "Helix node 02" "${NODE_2_URL}/healthz"
check_metric "Helix node" "${NODE_URL}/metrics" "helix_node_rollback_total"
check_metric "Helix node 02" "${NODE_2_URL}/metrics" "helix_node_runtime_healthy"

if [[ "$RUN_DESTRUCTIVE_DRILL" == "true" ]]; then
  if ! command -v docker >/dev/null 2>&1 || ! docker version >/dev/null 2>&1; then
    fail "destructive rollback drill requested but docker is unavailable"
  else
    bash "$RESET_SCRIPT"
    docker compose -f "$COMPOSE_FILE" --profile helix-lab up -d --build
    bash "$BOOTSTRAP_SCRIPT"
    HELIX_REQUIRE_LIVE=true bash "$STACK_TEST_SCRIPT"
    pass "destructive Helix rollback drill completed"
  fi
else
  warn "destructive rollback drill skipped (set HELIX_RUN_DESTRUCTIVE_DRILL=true to execute it)"
fi

echo
echo "Passed: ${passed}"
echo "Warnings: ${warnings}"
echo "Failed: ${failed}"

if [[ "$failed" -gt 0 ]]; then
  exit 1
fi

exit 0
