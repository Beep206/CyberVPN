#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_ENV_FILE="${ROOT_DIR}/.env"

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
HELIX_STATE_VOLUME="${HELIX_STATE_VOLUME:-helix_node_state}"
HELIX_STATE_VOLUME_2="${HELIX_STATE_VOLUME_2:-helix_node_state_2}"

echo "Resetting Helix lab history..."

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 1
fi

docker rm -f helix-node-lab >/dev/null 2>&1 || true
docker rm -f helix-node-lab-02 >/dev/null 2>&1 || true

if docker volume inspect "${HELIX_STATE_VOLUME}" >/dev/null 2>&1; then
  docker volume rm -f "${HELIX_STATE_VOLUME}" >/dev/null
fi

if docker volume inspect "${HELIX_STATE_VOLUME_2}" >/dev/null 2>&1; then
  docker volume rm -f "${HELIX_STATE_VOLUME_2}" >/dev/null
fi

docker exec -i remnawave-db psql \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  -v ON_ERROR_STOP=1 <<'SQL'
TRUNCATE TABLE
    helix.desktop_runtime_events,
    helix.node_heartbeat_snapshots,
    helix.manifest_versions,
    helix.last_known_good_bundles,
    helix.rollout_batches,
    helix.nodes
RESTART IDENTITY;
SQL

echo "Helix lab history reset complete."
