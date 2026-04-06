#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_DIR="${ROOT_DIR}"
COMPOSE_ENV_FILE="${COMPOSE_DIR}/.env"

load_env_file() {
  local env_file="$1"
  if [[ -f "$env_file" ]]; then
    set -a
    # shellcheck disable=SC1090
    source <(tr -d '\r' < "$env_file")
    set +a
  fi
}

load_env_file "$COMPOSE_ENV_FILE"

POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_DB="${POSTGRES_DB:-postgres}"
HELIX_INTERNAL_AUTH_TOKEN="${HELIX_INTERNAL_AUTH_TOKEN:-replace-me-too}"
HELIX_ADAPTER_URL="${HELIX_ADAPTER_URL:-http://localhost:8088}"
HELIX_NODE_URL="${HELIX_NODE_URL:-http://localhost:8091}"
HELIX_NODE_2_URL="${HELIX_NODE_2_URL:-http://localhost:8092}"
HELIX_LAB_NODE_ID="${HELIX_LAB_NODE_ID:-node-lab-01}"
HELIX_LAB_NODE_2_ID="${HELIX_LAB_NODE_2_ID:-node-lab-02}"
HELIX_LAB_ROLLOUT_ID="${HELIX_LAB_ROLLOUT_ID:-rollout-helix-lab}"
HELIX_LAB_BATCH_ID="${HELIX_LAB_BATCH_ID:-batch-helix-lab-001}"
HELIX_LAB_MANIFEST_VERSION="${HELIX_LAB_MANIFEST_VERSION:-helix-lab-manifest-v1}"
HELIX_LAB_NODE_UUID="${HELIX_LAB_NODE_UUID:-00000000-0000-0000-0000-000000000001}"
HELIX_LAB_NODE_2_UUID="${HELIX_LAB_NODE_2_UUID:-00000000-0000-0000-0000-000000000002}"
HELIX_LAB_NODE_NAME="${HELIX_LAB_NODE_NAME:-Helix Lab Node}"
HELIX_LAB_NODE_2_NAME="${HELIX_LAB_NODE_2_NAME:-Helix Lab Node 02}"
HELIX_LAB_ROUTE_HOST="${HELIX_LAB_ROUTE_HOST:-${HELIX_LAB_NODE_HOSTNAME:-127.0.0.1}}"
HELIX_LAB_ROUTE_HOST_2="${HELIX_LAB_ROUTE_HOST_2:-${HELIX_LAB_NODE_2_HOSTNAME:-127.0.0.1}}"
HELIX_LAB_NODE_GROUP="${HELIX_LAB_NODE_GROUP:-lab}"
HELIX_LAB_NODE_LABEL="${HELIX_LAB_NODE_LABEL:-helix-node-lab}"
HELIX_LAB_NODE_2_LABEL="${HELIX_LAB_NODE_2_LABEL:-helix-node-lab-02}"
HELIX_LAB_DATA_PORT="${HELIX_LAB_DATA_PORT:-9443}"
HELIX_LAB_NODE_2_DATA_PORT="${HELIX_LAB_NODE_2_DATA_PORT:-9444}"

echo "Bootstrapping Helix lab state..."

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required" >&2
  exit 1
fi

echo "Ensuring Helix lab services are up..."
docker compose -f "${COMPOSE_DIR}/docker-compose.yml" --profile helix-lab up -d \
  helix-adapter \
  helix-node-lab \
  helix-node-lab-02 \
  helix-bench-target \
  helix-stable-http-proxy >/dev/null

docker exec -i remnawave-db psql \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -v ON_ERROR_STOP=1 <<SQL
INSERT INTO helix.nodes (
    service_node_id,
    remnawave_node_id,
    node_name,
    hostname,
    transport_port,
    transport_enabled,
    rollout_channel,
    node_group,
    adapter_node_label,
    last_synced_at,
    created_at,
    updated_at
)
VALUES (
    '${HELIX_LAB_NODE_UUID}',
    '${HELIX_LAB_NODE_ID}',
    '${HELIX_LAB_NODE_NAME}',
    '${HELIX_LAB_ROUTE_HOST}',
    ${HELIX_LAB_DATA_PORT},
    TRUE,
    'lab',
    '${HELIX_LAB_NODE_GROUP}',
    '${HELIX_LAB_NODE_LABEL}',
    NOW(),
    NOW(),
    NOW()
), (
    '${HELIX_LAB_NODE_2_UUID}',
    '${HELIX_LAB_NODE_2_ID}',
    '${HELIX_LAB_NODE_2_NAME}',
    '${HELIX_LAB_ROUTE_HOST_2}',
    ${HELIX_LAB_NODE_2_DATA_PORT},
    TRUE,
    'lab',
    '${HELIX_LAB_NODE_GROUP}',
    '${HELIX_LAB_NODE_2_LABEL}',
    NOW(),
    NOW(),
    NOW()
)
ON CONFLICT (remnawave_node_id) DO UPDATE
SET
    node_name = EXCLUDED.node_name,
    hostname = EXCLUDED.hostname,
    transport_port = EXCLUDED.transport_port,
    transport_enabled = TRUE,
    rollout_channel = 'lab',
    node_group = EXCLUDED.node_group,
    adapter_node_label = EXCLUDED.adapter_node_label,
    last_synced_at = NOW(),
    updated_at = NOW();
SQL

profiles_json="$(curl -fsS \
  -H "x-internal-token: ${HELIX_INTERNAL_AUTH_TOKEN}" \
  "${HELIX_ADAPTER_URL}/admin/transport-profiles")"

if ! jq -e '.[] | select(.channel == "lab" and .status == "active")' >/dev/null <<<"${profiles_json}"; then
  echo "no active lab transport profile found in adapter" >&2
  exit 1
fi

curl -fsS \
  -X POST \
  -H "x-internal-token: ${HELIX_INTERNAL_AUTH_TOKEN}" \
  -H "content-type: application/json" \
  "${HELIX_ADAPTER_URL}/admin/rollouts" \
  --data @- >/dev/null <<JSON
{
  "rollout_id": "${HELIX_LAB_ROLLOUT_ID}",
  "batch_id": "${HELIX_LAB_BATCH_ID}",
  "channel": "lab",
  "manifest_version": "${HELIX_LAB_MANIFEST_VERSION}",
  "target_node_ids": ["${HELIX_LAB_NODE_ID}", "${HELIX_LAB_NODE_2_ID}"],
  "pause_on_rollback_spike": true,
  "revoke_on_manifest_error": true
}
JSON

echo "Waiting for Helix nodes readiness..."
for _ in $(seq 1 30); do
  if curl -fsS "${HELIX_NODE_URL}/readyz" >/dev/null 2>&1 \
    && curl -fsS "${HELIX_NODE_2_URL}/readyz" >/dev/null 2>&1; then
    echo "Helix lab nodes are ready."
    exit 0
  fi

  sleep 2
done

echo "Helix lab nodes did not become ready in time." >&2
docker logs helix-node-lab --tail 80 >&2 || true
docker logs helix-node-lab-02 --tail 80 >&2 || true
exit 1
