#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
package_root="$(cd "$script_dir/.." && pwd)"
workspace_root="$(cd "$package_root/../.." && pwd)"
infra_env_path="$workspace_root/infra/.env"
source "$script_dir/verta-compat.sh"

verta_sync_phase_i_envs

[[ "$#" -gt 0 ]] || fail "Usage: $0 <command> [args...]"
command -v docker >/dev/null 2>&1 || fail "docker was not found. Install Docker before deriving local supported-upstream env."
[[ -f "$infra_env_path" ]] || fail "Local infra env file is missing at $infra_env_path."

read_env_value() {
  local key="$1"
  awk -F= -v pattern="^${key}=" '$0 ~ pattern {print substr($0, index($0, "=") + 1); exit}' "$infra_env_path"
}

query_first_user() {
  docker exec remnawave-db \
    psql -U postgres -d postgres -t -A \
    -c "select uuid || '|' || short_uuid from users order by created_at asc limit 1;"
}

query_source_version() {
  docker inspect remnawave --format '{{range .Config.Env}}{{println .}}{{end}}' \
    | awk -F= '/^__RW_METADATA_VERSION=/{print $2; exit}'
}

if [[ -z "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN:-}" ]]; then
  derived_api_token="$(read_env_value HELIX_REMNAWAVE_TOKEN)"
  [[ -n "$derived_api_token" ]] || fail "HELIX_REMNAWAVE_TOKEN is missing in $infra_env_path."
  export VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN="$derived_api_token"
fi

if [[ -z "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT:-}" ]] || [[ -z "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID:-}" ]]; then
  first_user="$(query_first_user | tr -d '[:space:]')"
  [[ -n "$first_user" ]] || fail "No local Remnawave user was found in remnawave-db."
  IFS='|' read -r derived_account_id derived_bootstrap_subject <<<"$first_user"
  [[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID:-}" ]] || export VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID="$derived_account_id"
  [[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT:-}" ]] || export VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT="$derived_bootstrap_subject"
fi

[[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL:-}" ]] || export VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL="http://localhost"
[[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_SIGNATURE:-}" ]] || export VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_SIGNATURE="verta-local-webhook"
[[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_STORE_AUTH_TOKEN:-}" ]] || export VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_STORE_AUTH_TOKEN="verta-local-store-auth"
[[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_LABEL:-}" ]] || export VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_LABEL="remnawave-local-docker"
[[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_LIFECYCLE:-}" ]] || export VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_LIFECYCLE="disabled"

if [[ -z "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_SOURCE_VERSION:-}" ]]; then
  derived_source_version="$(query_source_version | tr -d '[:space:]')"
  [[ -n "$derived_source_version" ]] || fail "Could not derive __RW_METADATA_VERSION from the remnawave container."
  export VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_SOURCE_VERSION="$derived_source_version"
fi

verta_sync_phase_i_envs

exec "$@"
