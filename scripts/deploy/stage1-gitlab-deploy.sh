#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  printf '[stage1-deploy] %s\n' "$*" >&2
}

fail() {
  printf '[stage1-deploy] ERROR: %s\n' "$*" >&2
  exit 1
}

usage() {
  cat >&2 <<'USAGE'
Usage:
  scripts/deploy/stage1-gitlab-deploy.sh <services>

Services:
  all, frontend, admin, partner, backend, subscription-page, telegram-bot, task-worker, vpn-test-agent, task2-route-evidence

The legacy GitLab name is historical. The script is also runnable manually;
CI_* variables are optional when STAGE1_RELEASE_TAG and SSH settings are supplied.

Required CI variables:
  STAGE1_PROD_HOST
  STAGE1_PROD_SSH_PRIVATE_KEY or STAGE1_PROD_SSH_KEY_FILE

Recommended protected CI variables:
  STAGE1_PROD_USER=deploy
  STAGE1_PROD_PORT=22
  STAGE1_PROD_KNOWN_HOSTS=<ssh-keyscan output>
  STAGE1_DEPLOY_DRY_RUN=true for no-network CI deploy contract validation
USAGE
}

services_input="${1:-${STAGE1_DEPLOY_SERVICES:-}}"
[[ -n "$services_input" ]] || {
  usage
  fail "service list is required"
}

deploy_dry_run="${STAGE1_DEPLOY_DRY_RUN:-false}"
case "$deploy_dry_run" in
  true|false) ;;
  *) fail "STAGE1_DEPLOY_DRY_RUN must be true or false" ;;
esac

host="${STAGE1_PROD_HOST:-}"
if [[ "$deploy_dry_run" == "true" && -z "$host" ]]; then
  host="dry-run.invalid"
fi
[[ -n "$host" ]] || fail "STAGE1_PROD_HOST is required"

user="${STAGE1_PROD_USER:-deploy}"
port="${STAGE1_PROD_PORT:-22}"
compose_dir="${STAGE1_PROD_COMPOSE_DIR:-/srv/cybervpn/compose/app}"
spb_compose_dir="${STAGE1_SPB_COMPOSE_DIR:-/srv/cybervpn/compose/vpn-test-agent-spb}"
spb_compose_file="${STAGE1_SPB_COMPOSE_FILE:-/srv/cybervpn/compose/vpn-test-agent-spb/docker-compose.yml}"
edge_compose_dir="${STAGE1_EDGE_COMPOSE_DIR:-/srv/cybervpn/compose/edge}"
edge_compose_file="${STAGE1_EDGE_COMPOSE_FILE:-/srv/cybervpn/compose/edge/docker-compose.yml}"
edge_caddy_service="${STAGE1_EDGE_CADDY_SERVICE:-caddy}"
edge_caddyfile_path="${STAGE1_EDGE_CADDYFILE_PATH:-/srv/cybervpn/edge/caddy/Caddyfile}"
release_root="${STAGE1_PROD_RELEASE_ROOT:-/srv/cybervpn/releases}"
image_registry="${STAGE1_IMAGE_REGISTRY:-local}"
remote_sudo="${STAGE1_REMOTE_SUDO:-sudo}"
release_tag="${STAGE1_RELEASE_TAG:-stage1-ci-${CI_PIPELINE_IID:-0}-${CI_COMMIT_SHORT_SHA:-local}}"
evidence_dir="${STAGE1_DEPLOY_EVIDENCE_DIR:-docs/evidence/releases/ci-stage1}"
public_smoke_urls="${STAGE1_PUBLIC_SMOKE_URLS:-https://cyber-vpn.net/ru-RU/miniapp https://cyber-vpn.net/ru-RU/miniapp/home https://cyber-vpn.net/runtime/fingerprint https://api.cyber-vpn.net/api/v1/runtime/fingerprint https://admin.cyber-vpn.net/ru-RU/login https://partner.cyber-vpn.net/ru-RU/login https://api.cyber-vpn.net/healthz}"
customer_rsc_smoke_host="${STAGE1_CUSTOMER_RSC_SMOKE_HOST:-https://my.cyber-vpn.net}"
source_sync_mode="${STAGE1_SOURCE_SYNC_MODE:-rsync}"

case "$source_sync_mode" in
  rsync|git-archive|runtime-archive) ;;
  *) fail "STAGE1_SOURCE_SYNC_MODE must be rsync, git-archive, or runtime-archive" ;;
esac

case "$release_tag" in
  *[!A-Za-z0-9_.-]*)
    fail "release tag contains unsupported characters: $release_tag"
    ;;
esac

validate_optional_absolute_remote_path() {
  name="$1"
  value="$2"

  [[ -n "$value" ]] || return 0
  case "$value" in
    /*) ;;
    *) fail "$name must be an absolute remote path" ;;
  esac
  if [[ "$value" == *"'"* || "$value" == *$'\n'* || "$value" == *$'\r'* ]]; then
    fail "$name contains unsupported characters"
  fi
}

validate_optional_absolute_remote_path STAGE1_CADDYFILE_PATH "${STAGE1_CADDYFILE_PATH:-}"
validate_optional_absolute_remote_path STAGE1_CADDY_CONFIG_DIR "${STAGE1_CADDY_CONFIG_DIR:-}"
validate_optional_absolute_remote_path STAGE1_SPB_AGENT_ENV_FILE "${STAGE1_SPB_AGENT_ENV_FILE:-}"
validate_optional_absolute_remote_path STAGE1_SPB_COMPOSE_DIR "$spb_compose_dir"
validate_optional_absolute_remote_path STAGE1_SPB_COMPOSE_FILE "$spb_compose_file"
validate_optional_absolute_remote_path STAGE1_EDGE_COMPOSE_DIR "$edge_compose_dir"
validate_optional_absolute_remote_path STAGE1_EDGE_COMPOSE_FILE "$edge_compose_file"
validate_optional_absolute_remote_path STAGE1_EDGE_CADDYFILE_PATH "$edge_caddyfile_path"
case "$edge_caddy_service" in
  caddy) ;;
  *) fail "STAGE1_EDGE_CADDY_SERVICE must be caddy for the production edge compose project" ;;
esac

IFS=',' read -r -a requested_services <<<"$services_input"

declare -A requested=()
for raw_service in "${requested_services[@]}"; do
  service="$(printf '%s' "$raw_service" | xargs)"
  [[ -n "$service" ]] || continue
  case "$service" in
    all|frontend|admin|partner|backend|subscription-page|telegram-bot|task-worker|vpn-test-agent|task2-route-evidence)
      requested["$service"]=1
      ;;
    *)
      fail "unsupported service: $service"
      ;;
  esac
done

[[ ${#requested[@]} -gt 0 ]] || fail "no valid services requested"

task2_requested=false
if [[ -n "${requested[task2-route-evidence]:-}" ]]; then
  task2_requested=true
fi

if [[ -n "${requested[all]:-}" ]]; then
  requested=(
    [frontend]=1
    [admin]=1
    [partner]=1
    [backend]=1
    [subscription-page]=1
    [telegram-bot]=1
    [task-worker]=1
    [vpn-test-agent]=1
  )
  if [[ "$task2_requested" == "true" ]]; then
    requested[task2-route-evidence]=1
  fi
fi

services_csv="$(IFS=,; echo "${!requested[*]}")"

task2_runtime_artifacts=(
  infra/deploy/stage1/Caddyfile.edge-stage1.production
  infra/deploy/stage1/docker-compose.vpn-test-agent-spb.yml
  infra/nftables/cybervpn-task2-evidence-ingress.nft
  infra/systemd/cybervpn-task2-evidence-firewall.service
  scripts/deploy/stage1-gitlab-deploy.sh
)

primary_deploy_requested=false
for primary_service in frontend admin partner backend subscription-page telegram-bot task-worker vpn-test-agent; do
  if [[ -n "${requested[$primary_service]:-}" ]]; then
    primary_deploy_requested=true
    break
  fi
done

task2_only=false
if [[ "$task2_requested" == "true" && "$primary_deploy_requested" == "false" ]]; then
  task2_only=true
fi

if [[ "$deploy_dry_run" != "true" && "$task2_requested" == "true" && "$source_sync_mode" == "rsync" ]]; then
  fail "Task2 route evidence deploy requires tracked archive sync; set STAGE1_SOURCE_SYNC_MODE=git-archive or runtime-archive"
fi

if [[ "$deploy_dry_run" != "true" && "$task2_requested" == "true" && ( "$source_sync_mode" == "git-archive" || "$source_sync_mode" == "runtime-archive" ) ]]; then
  for artifact in "${task2_runtime_artifacts[@]}"; do
    git ls-files --error-unmatch "$artifact" >/dev/null 2>&1 ||
      fail "Task2 runtime archive artifact must be tracked: $artifact"
  done
fi

mkdir -p "$evidence_dir"
evidence_file="$evidence_dir/stage1-gitlab-deploy-${release_tag}.md"

if [[ "$deploy_dry_run" == "true" ]]; then
  {
    echo "# Stage 1 GitLab Deploy Dry Run"
    echo
    echo "Release tag: \`$release_tag\`"
    echo "Commit: \`${CI_COMMIT_SHA:-local}\`"
    echo "Pipeline: \`${CI_PIPELINE_URL:-local}\`"
    echo "Services: \`$services_csv\`"
    echo "Host: \`$host\`"
    echo "Compose dir: \`$compose_dir\`"
    echo "SPB compose: \`$spb_compose_file\`"
    echo "Release root: \`$release_root\`"
    echo "Image registry: \`$image_registry\`"
    echo "Edge compose: \`$edge_compose_file\`"
    echo "Edge Caddy service: \`$edge_caddy_service\`"
    echo "Edge Caddyfile: \`$edge_caddyfile_path\`"
    echo "Dry run: \`true\`"
    echo "Checked at: \`$(date -u +%Y-%m-%dT%H:%M:%SZ)\`"
    echo
    echo "No SSH, rsync, Docker build, compose restart or public smoke was executed."
  } >"$evidence_file"
  cat "$evidence_file"
  log "dry-run evidence written to $evidence_file"
  exit 0
fi

ssh_key_file="${STAGE1_PROD_SSH_KEY_FILE:-}"
temporary_key_file=""
if [[ -z "$ssh_key_file" ]]; then
  [[ -n "${STAGE1_PROD_SSH_PRIVATE_KEY:-}" ]] || fail "STAGE1_PROD_SSH_PRIVATE_KEY or STAGE1_PROD_SSH_KEY_FILE is required"
  if [[ -f "$STAGE1_PROD_SSH_PRIVATE_KEY" ]]; then
    ssh_key_file="$STAGE1_PROD_SSH_PRIVATE_KEY"
    chmod 600 "$ssh_key_file" 2>/dev/null || true
  else
    temporary_key_file="$(mktemp)"
    printf '%s\n' "$STAGE1_PROD_SSH_PRIVATE_KEY" >"$temporary_key_file"
    chmod 600 "$temporary_key_file"
    ssh_key_file="$temporary_key_file"
  fi
fi

known_hosts_file="$(mktemp)"
cleanup() {
  [[ -n "$temporary_key_file" && -f "$temporary_key_file" ]] && rm -f "$temporary_key_file"
  rm -f "$known_hosts_file"
}
trap cleanup EXIT

if [[ -n "${STAGE1_PROD_KNOWN_HOSTS:-}" ]]; then
  printf '%s\n' "$STAGE1_PROD_KNOWN_HOSTS" >"$known_hosts_file"
else
  log "STAGE1_PROD_KNOWN_HOSTS is not set; collecting host key with ssh-keyscan"
  ssh-keyscan -t rsa,ecdsa,ed25519 -p "$port" -H "$host" >"$known_hosts_file" 2>/dev/null
fi

ssh_base=(
  ssh
  -i "$ssh_key_file"
  -p "$port"
  -o IdentitiesOnly=yes
  -o StrictHostKeyChecking=yes
  -o UserKnownHostsFile="$known_hosts_file"
)

ssh_cmd() {
  "${ssh_base[@]}" "$user@$host" "$@"
}

remote_src="$release_root/src-$release_tag"

log "creating remote source directory $remote_src"
ssh_cmd "$remote_sudo install -d -o '$user' -g '$user' '$remote_src'"

if [[ "$source_sync_mode" == "git-archive" ]]; then
  log "syncing tracked source with git archive"
  ssh_cmd "$remote_sudo rm -rf '$remote_src' && $remote_sudo install -d -o '$user' -g '$user' '$remote_src'"
  git archive --format=tar HEAD | "${ssh_base[@]}" "$user@$host" "tar -xf - -C '$remote_src'"
elif [[ "$source_sync_mode" == "runtime-archive" ]]; then
  log "syncing tracked runtime source archive"
  ssh_cmd "$remote_sudo rm -rf '$remote_src' && $remote_sudo install -d -o '$user' -g '$user' '$remote_src'"
  git ls-files |
    awk '/^(backend|frontend|admin|partner|services\/telegram-bot|services\/vpn-test-agent|infra\/deploy\/stage1)\// || /^(infra\/nftables\/cybervpn-task2-evidence-ingress\.nft|infra\/systemd\/cybervpn-task2-evidence-firewall\.service|scripts\/deploy\/stage1-gitlab-deploy\.sh|package.json|package-lock.json|\.node-version|tsconfig.base.json|AGENTS.md)$/ {print}' |
    tar -cf - -T - |
    "${ssh_base[@]}" "$user@$host" "tar -xf - -C '$remote_src'"
else
  log "syncing source without secrets/heavy build artifacts"
  rsync -az --delete \
    --exclude='.git/' \
    --exclude='.codex/' \
    --exclude='.private/' \
    --exclude='.env' \
    --exclude='.env.*' \
    --exclude='*.pem' \
    --exclude='*.key' \
    --exclude='node_modules/' \
    --exclude='**/node_modules/' \
    --exclude='.venv/' \
    --exclude='**/.venv/' \
    --exclude='.next/' \
    --exclude='**/.next/' \
    --exclude='.next-*' \
    --exclude='**/.next-*' \
    --exclude='.dart_tool/' \
    --exclude='**/.dart_tool/' \
    --exclude='.gradle/' \
    --exclude='**/.gradle/' \
    --exclude='build/' \
    --exclude='**/build/' \
    --exclude='dist/' \
    --exclude='**/dist/' \
    --exclude='.cache/' \
    --exclude='**/.cache/' \
    --exclude='.pytest_cache/' \
    --exclude='.ruff_cache/' \
    --exclude='.tmp/' \
    --exclude='htmlcov/' \
    --exclude='docs/' \
    --exclude='apps/' \
    --exclude='packages/' \
    --exclude='cybervpn_mobile/' \
    --exclude='SDK/' \
    --exclude='services/helix-adapter/' \
    --exclude='services/helix-node/' \
    --exclude='services/node-fleet-controller/' \
    --exclude='infra/terraform/' \
    --exclude='infra/backups/' \
    --exclude='.coverage' \
    --exclude='.coverage.*' \
    -e "${ssh_base[*]}" \
    ./ "$user@$host:$remote_src/"
fi

{
  echo "# Stage 1 GitLab Deploy"
  echo
  echo "Release tag: \`$release_tag\`"
  echo "Commit: \`${CI_COMMIT_SHA:-local}\`"
  echo "Pipeline: \`${CI_PIPELINE_URL:-local}\`"
  echo "Services: \`$services_csv\`"
  echo "Started at: \`$(date -u +%Y-%m-%dT%H:%M:%SZ)\`"
  echo
} >"$evidence_file"

log "building and deploying services: $services_csv"
"${ssh_base[@]}" "$user@$host" \
  "RELEASE_TAG='$release_tag' REMOTE_SRC='$remote_src' COMPOSE_DIR='$compose_dir' SPB_COMPOSE_DIR='$spb_compose_dir' SPB_COMPOSE_FILE='$spb_compose_file' EDGE_COMPOSE_DIR='$edge_compose_dir' EDGE_COMPOSE_FILE='$edge_compose_file' EDGE_CADDY_SERVICE='$edge_caddy_service' EDGE_CADDYFILE_PATH='$edge_caddyfile_path' IMAGE_REGISTRY='$image_registry' REMOTE_SUDO='$remote_sudo' SERVICES_CSV='$services_csv' TASK2_ROUTE_EVIDENCE_REQUESTED='$task2_requested' TASK2_ONLY='$task2_only' PRIMARY_DEPLOY_REQUESTED='$primary_deploy_requested' STAGE1_SPB_AGENT_ENV_FILE='${STAGE1_SPB_AGENT_ENV_FILE:-}' bash -s" <<'REMOTE_SCRIPT' | tee -a "$evidence_file"
set -Eeuo pipefail

log() {
  printf '[remote-stage1-deploy] %s\n' "$*"
}

remote_fail() {
  log "ERROR: $*"
  exit 1
}

retry_curl() {
  label="$1"
  shift
  max_attempts="${STAGE1_DEPLOY_SMOKE_ATTEMPTS:-30}"
  sleep_seconds="${STAGE1_DEPLOY_SMOKE_SLEEP_SECONDS:-2}"
  attempt=1

  case "$max_attempts" in
    ""|*[!0-9]*) remote_fail "STAGE1_DEPLOY_SMOKE_ATTEMPTS must be an integer" ;;
  esac
  case "$sleep_seconds" in
    ""|*[!0-9]*) remote_fail "STAGE1_DEPLOY_SMOKE_SLEEP_SECONDS must be an integer" ;;
  esac
  if [ "$max_attempts" -lt 1 ] || [ "$max_attempts" -gt 60 ]; then
    remote_fail "STAGE1_DEPLOY_SMOKE_ATTEMPTS must be between 1 and 60"
  fi
  if [ "$sleep_seconds" -lt 1 ] || [ "$sleep_seconds" -gt 10 ]; then
    remote_fail "STAGE1_DEPLOY_SMOKE_SLEEP_SECONDS must be between 1 and 10"
  fi

  while [ "$attempt" -le "$max_attempts" ]; do
    if "$@"; then
      return 0
    fi
    log "${label} not ready yet (${attempt}/${max_attempts})"
    attempt=$((attempt + 1))
    sleep "$sleep_seconds"
  done

  log "${label} did not become ready"
  return 1
}

is_requested() {
  case ",${SERVICES_CSV}," in
    *",$1,"*) return 0 ;;
    *) return 1 ;;
  esac
}

task2_route_evidence_requested() {
  [ "${TASK2_ROUTE_EVIDENCE_REQUESTED:-false}" = "true" ]
}

remote_env_value() {
  file="$1"
  key="$2"
  $REMOTE_SUDO awk -F= -v key="$key" '$1 == key {print substr($0, index($0, "=") + 1)}' "$file" | tail -1
}

remote_env_bool_is_true() {
  file="$1"
  key="$2"
  value="$(remote_env_value "$file" "$key" | tr '[:upper:]' '[:lower:]' || true)"

  case "$value" in
    true|1|yes|on) return 0 ;;
    false|0|no|off|"") return 1 ;;
    *) remote_fail "${key} must be true or false" ;;
  esac
}

ensure_remote_env_value() {
  file="$1"
  key="$2"
  value="$3"

  if $REMOTE_SUDO grep -q "^${key}=" "$file"; then
    $REMOTE_SUDO sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" | $REMOTE_SUDO tee -a "$file" >/dev/null
  fi
}

ensure_remote_env_secret() {
  file="$1"
  key="$2"

  if $REMOTE_SUDO grep -q "^${key}=." "$file"; then
    log "${key} is present"
    return 0
  fi

  value="$(openssl rand -hex 32)"
  if $REMOTE_SUDO grep -q "^${key}=" "$file"; then
    $REMOTE_SUDO sed -i "s|^${key}=.*|${key}=${value}|" "$file"
  else
    printf '\n%s=%s\n' "$key" "$value" | $REMOTE_SUDO tee -a "$file" >/dev/null
  fi
  log "created ${key}"
}

require_remote_env_true() {
  file="$1"
  key="$2"

  if ! remote_env_bool_is_true "$file" "$key"; then
    remote_fail "${key} must be true when Task2 route evidence is enabled"
  fi
}

require_remote_env_present() {
  file="$1"
  key="$2"
  value="$(remote_env_value "$file" "$key" || true)"

  if [ -z "$value" ]; then
    remote_fail "${key} is required when Task2 route evidence is enabled"
  fi
}

require_remote_env_secret_present() {
  file="$1"
  key="$2"
  value="$(remote_env_value "$file" "$key" || true)"

  if [ -z "$value" ]; then
    remote_fail "${key} is required when Task2 route evidence is enabled"
  fi

  secret_lower="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')"
  case "$secret_lower" in
    *replace*|*example*|*test*|*placeholder*|*changeme*|*dummy*|*local*|*development*|*dev-*|*redacted*|*your_*)
      remote_fail "${key} must not use a placeholder value"
      ;;
  esac
  log "${key} is present"
}

require_remnawave_stream_hmac_secret() {
  file="$COMPOSE_DIR/.env"
  stream_secret="$(remote_env_value "$file" REMNAWAVE_STREAM_IP_HMAC_SECRET || true)"
  backend_secret="$(remote_env_value "$file" BACKEND_INTERNAL_SECRET || true)"

  if [ "${#stream_secret}" -lt 32 ]; then
    remote_fail "REMNAWAVE_STREAM_IP_HMAC_SECRET must already be provisioned with at least 32 characters"
  fi
  secret_lower="$(printf '%s' "$stream_secret" | tr '[:upper:]' '[:lower:]')"
  case "$secret_lower" in
    *replace*|*example*|*test*|*placeholder*|*changeme*|*dummy*|*local*|*development*|*dev-*|*redacted*|*your_*)
      remote_fail "REMNAWAVE_STREAM_IP_HMAC_SECRET must not use a placeholder value"
      ;;
  esac
  if [ -n "$backend_secret" ] && [ "$stream_secret" = "$backend_secret" ]; then
    remote_fail "REMNAWAVE_STREAM_IP_HMAC_SECRET must be distinct from BACKEND_INTERNAL_SECRET"
  fi
  log "REMNAWAVE_STREAM_IP_HMAC_SECRET is provisioned and distinct"
}

require_remnawave_connection_drop_hmac_secret() {
  file="$COMPOSE_DIR/.env"
  receipt_secret="$(remote_env_value "$file" REMNAWAVE_CONNECTION_DROP_HMAC_SECRET || true)"
  backend_secret="$(remote_env_value "$file" BACKEND_INTERNAL_SECRET || true)"
  stream_secret="$(remote_env_value "$file" REMNAWAVE_STREAM_IP_HMAC_SECRET || true)"
  fingerprint_secret="$(remote_env_value "$file" WEBHOOK_LOG_FINGERPRINT_SECRET || true)"

  if [ "${#receipt_secret}" -lt 32 ]; then
    remote_fail "REMNAWAVE_CONNECTION_DROP_HMAC_SECRET must already be provisioned with at least 32 characters"
  fi
  secret_lower="$(printf '%s' "$receipt_secret" | tr '[:upper:]' '[:lower:]')"
  case "$secret_lower" in
    *replace*|*example*|*test*|*placeholder*|*changeme*|*dummy*|*local*|*development*|*dev-*|*redacted*|*your_*)
      remote_fail "REMNAWAVE_CONNECTION_DROP_HMAC_SECRET must not use a placeholder value"
      ;;
  esac
  if [ -n "$backend_secret" ] && [ "$receipt_secret" = "$backend_secret" ]; then
    remote_fail "REMNAWAVE_CONNECTION_DROP_HMAC_SECRET must be distinct from BACKEND_INTERNAL_SECRET"
  fi
  if [ -n "$stream_secret" ] && [ "$receipt_secret" = "$stream_secret" ]; then
    remote_fail "REMNAWAVE_CONNECTION_DROP_HMAC_SECRET must be distinct from REMNAWAVE_STREAM_IP_HMAC_SECRET"
  fi
  if [ -n "$fingerprint_secret" ] && [ "$receipt_secret" = "$fingerprint_secret" ]; then
    remote_fail "REMNAWAVE_CONNECTION_DROP_HMAC_SECRET must be distinct from WEBHOOK_LOG_FINGERPRINT_SECRET"
  fi
  log "REMNAWAVE_CONNECTION_DROP_HMAC_SECRET is provisioned, stable, and distinct"
}

require_remnawave_app_secret_continuity() {
  compose_env="$COMPOSE_DIR/.env"
  panel_image="$(remote_env_value "$compose_env" CYBERVPN_REMNAWAVE_BACKEND_IMAGE || true)"
  if ! printf '%s' "$panel_image" | grep -Eq '^.+:3[.]4[.]3-raw-vision-flow[.][0-9]+@sha256:[a-f0-9]{64}$'; then
    remote_fail "CYBERVPN_REMNAWAVE_BACKEND_IMAGE must be the registry digest-pinned 3.4.3 compatibility image"
  fi

  secrets_dir="$(remote_env_value "$compose_env" CYBERVPN_SECRETS_DIR || true)"
  if [ -z "$secrets_dir" ]; then
    secrets_dir="/srv/cybervpn-h/secrets"
  fi
  panel_env="${secrets_dir%/}/remnawave-panel.env"
  if ! $REMOTE_SUDO test -f "$panel_env"; then
    remote_fail "Remnawave panel secret file is missing: ${panel_env}"
  fi

  app_secret="$(remote_env_value "$panel_env" APP_SECRET || true)"
  expected_sha256="$(remote_env_value "$compose_env" REMNAWAVE_PREUPGRADE_AUTH_SECRET_SHA256 || true)"
  if [ "${#app_secret}" -ne 128 ]; then
    remote_fail "APP_SECRET must preserve the 64-byte (128 hex character) pre-upgrade JWT_AUTH_SECRET"
  fi
  case "$app_secret" in
    *[!0-9a-fA-F]*) remote_fail "APP_SECRET must contain exactly 128 hexadecimal characters" ;;
  esac
  if [ "${#expected_sha256}" -ne 64 ]; then
    remote_fail "REMNAWAVE_PREUPGRADE_AUTH_SECRET_SHA256 must be provisioned from the read-only baseline"
  fi
  case "$expected_sha256" in
    *[!0-9a-f]*) remote_fail "REMNAWAVE_PREUPGRADE_AUTH_SECRET_SHA256 must be 64 lowercase hex characters" ;;
  esac

  actual_sha256="$(printf '%s' "$app_secret" | sha256sum | awk '{print $1}')"
  if [ "$actual_sha256" != "$expected_sha256" ]; then
    remote_fail "APP_SECRET fingerprint differs from the pre-upgrade auth secret; refusing an implicit rotation"
  fi
  log "Remnawave 3.4.3 image identity and APP_SECRET continuity attestations passed"
}

require_remnawave_subscription_page_contract() {
  is_requested subscription-page || return 0

  compose_env="$COMPOSE_DIR/.env"
  secrets_dir="$(remote_env_value "$compose_env" CYBERVPN_SECRETS_DIR || true)"
  if [ -z "$secrets_dir" ]; then
    secrets_dir="/srv/cybervpn-h/secrets"
  fi
  subscription_env="${secrets_dir%/}/remnawave-subscription-page.env"
  if ! $REMOTE_SUDO test -f "$subscription_env"; then
    remote_fail "subscription-page secret file is missing: ${subscription_env}"
  fi

  subscription_token="$(remote_env_value "$subscription_env" REMNAWAVE_API_TOKEN || true)"
  if [ "${#subscription_token}" -lt 32 ]; then
    remote_fail "subscription-page REMNAWAVE_API_TOKEN must be a dedicated token of at least 32 characters"
  fi
  token_lower="$(printf '%s' "$subscription_token" | tr '[:upper:]' '[:lower:]')"
  case "$token_lower" in
    *replace*|*example*|*test*|*placeholder*|*changeme*|*dummy*|*local*|*development*|*dev-*|*redacted*|*your_*|*todo*)
      remote_fail "subscription-page REMNAWAVE_API_TOKEN must not use a placeholder value"
      ;;
  esac

  worker_token="$(remote_env_value "${secrets_dir%/}/remnawave.env" REMNAWAVE_API_TOKEN 2>/dev/null || true)"
  backend_token="$(remote_env_value "${secrets_dir%/}/app.env" REMNAWAVE_TOKEN 2>/dev/null || true)"
  panel_secret="$(remote_env_value "${secrets_dir%/}/remnawave-panel.env" APP_SECRET 2>/dev/null || true)"
  for reused_token in "$worker_token" "$backend_token" "$panel_secret"; do
    if [ -n "$reused_token" ] && [ "$subscription_token" = "$reused_token" ]; then
      remote_fail "subscription-page REMNAWAVE_API_TOKEN must not reuse a worker, backend, or panel secret"
    fi
  done

  backend_subnet="$(remote_env_value "$compose_env" CYBERVPN_STAGE1_BACKEND_SUBNET || true)"
  [ -n "$backend_subnet" ] || backend_subnet="172.30.3.0/24"
  trusted_proxy="$(remote_env_value "$compose_env" REMNAWAVE_SUBSCRIPTION_PAGE_TRUST_PROXY || true)"
  [ -n "$trusted_proxy" ] || trusted_proxy="172.30.3.0/24"
  if [ "$trusted_proxy" != "$backend_subnet" ]; then
    remote_fail "REMNAWAVE_SUBSCRIPTION_PAGE_TRUST_PROXY must exactly match CYBERVPN_STAGE1_BACKEND_SUBNET"
  fi

  subscription_image="$(remote_env_value "$compose_env" REMNAWAVE_SUBSCRIPTION_PAGE_IMAGE || true)"
  [ -n "$subscription_image" ] || subscription_image="remnawave/subscription-page:8.0.0@sha256:04e8d479afb3598024e4018e9e15cd7fe879938250090a690ba39f1ee91b79ac"
  if ! printf '%s' "$subscription_image" | grep -Eq '^.+@sha256:[a-f0-9]{64}$'; then
    remote_fail "REMNAWAVE_SUBSCRIPTION_PAGE_IMAGE must be an immutable digest-pinned image"
  fi

  rollback_image="$(remote_env_value "$compose_env" REMNAWAVE_SUBSCRIPTION_PAGE_ROLLBACK_IMAGE || true)"
  [ -n "$rollback_image" ] || rollback_image="remnawave/subscription-page:7.2.6@sha256:da5ee26ec70ecd81e57303993e8bfb74c8e52f2fa74644b84aad53324cde2e8c"
  if ! printf '%s' "$rollback_image" | grep -Eq '^.+:7[.]2[.]6@sha256:[a-f0-9]{64}$'; then
    remote_fail "REMNAWAVE_SUBSCRIPTION_PAGE_ROLLBACK_IMAGE must be the digest-pinned 7.2.6 fallback"
  fi

  log "subscription-page token, proxy CIDR, current image and 7.2.6 rollback contract passed"
}

require_task2_evidence_config_if_enabled() {
  env_file="$COMPOSE_DIR/.env"

  if ! remote_env_bool_is_true "$env_file" VPN_TESTER_TASK2_ROUTE_EVIDENCE_ENABLED; then
    log "Task2 route evidence remains disabled"
    return 0
  fi

  log "Task2 route evidence is enabled; validating fail-closed runtime configuration"
  require_remote_env_true "$env_file" VPN_TESTER_ENABLED
  require_remote_env_true "$env_file" VPN_TESTER_RUNTIME_ENABLED
  require_remote_env_true "$env_file" VPN_TESTER_SYNTHETIC_USERS_ENABLED
  require_remote_env_present "$env_file" VPN_TEST_AGENT_SPB_URL
  require_remote_env_secret_present "$env_file" VPN_TEST_AGENT_SPB_SECRET
  require_remote_env_secret_present "$env_file" VPN_TESTER_TASK2_XRAY_WEBHOOK_SECRET
  require_remote_env_present "$env_file" VPN_TESTER_TASK2_SYNTHETIC_USER
  require_remote_env_present "$env_file" VPN_TESTER_TASK2_SYNTHETIC_XRAY_EMAIL
}

ensure_backend_device_cookie_pepper() {
  is_requested backend || return 0

  secrets_dir="$(remote_env_value "$COMPOSE_DIR/.env" CYBERVPN_SECRETS_DIR || true)"
  if [ -z "$secrets_dir" ]; then
    secrets_dir="/srv/cybervpn/secrets"
  fi
  app_env="${secrets_dir%/}/app.env"

  if ! $REMOTE_SUDO test -f "$app_env"; then
    remote_fail "backend secret file is missing: ${app_env}"
  fi
  if ! $REMOTE_SUDO grep -q '^JWT_SECRET=.' "$app_env"; then
    remote_fail "backend secret file ${app_env} is missing JWT_SECRET; refusing to create a partial app.env"
  fi
  if $REMOTE_SUDO grep -q '^CYBERVPN_DEVICE_COOKIE_PEPPER=.' "$app_env"; then
    log "CYBERVPN_DEVICE_COOKIE_PEPPER is present in backend app.env"
    return 0
  fi

  pepper="$(openssl rand -hex 32)"
  backup="${app_env}.pre-device-cookie-pepper-$(date -u +%Y%m%dT%H%M%SZ)"
  $REMOTE_SUDO cp -p "$app_env" "$backup"
  if $REMOTE_SUDO grep -q '^CYBERVPN_DEVICE_COOKIE_PEPPER=' "$app_env"; then
    $REMOTE_SUDO sed -i "s/^CYBERVPN_DEVICE_COOKIE_PEPPER=.*/CYBERVPN_DEVICE_COOKIE_PEPPER=${pepper}/" "$app_env"
  else
    printf '\nCYBERVPN_DEVICE_COOKIE_PEPPER=%s\n' "$pepper" | $REMOTE_SUDO tee -a "$app_env" >/dev/null
  fi
  $REMOTE_SUDO chmod 0600 "$app_env"
  log "created CYBERVPN_DEVICE_COOKIE_PEPPER in backend app.env; backup: ${backup}"
}

task2_backup_manifest=""
task2_deploy_active=false
task2_deploy_completed=false
task2_firewall_unit="cybervpn-task2-evidence-firewall.service"
task2_firewall_was_enabled=false
task2_firewall_was_active=false
task2_spb_agent_env_file=""
task2_spb_sidecar_started=false
task2_spb_sidecar_existed=false
task2_spb_sidecar_was_running=false
task2_spb_previous_registry=""
task2_spb_previous_tag=""
task2_caddy_touched=false

task2_remote_env_or_default() {
  file="$1"
  key="$2"
  default="$3"
  value="$(remote_env_value "$file" "$key" || true)"
  if [ -n "$value" ]; then
    printf '%s\n' "$value"
  else
    printf '%s\n' "$default"
  fi
}

task2_caddyfile_path() {
  printf '%s\n' "$EDGE_CADDYFILE_PATH"
}

task2_resolve_spb_agent_env_file() {
  if [ -n "${STAGE1_SPB_AGENT_ENV_FILE:-}" ]; then
    printf '%s\n' "$STAGE1_SPB_AGENT_ENV_FILE"
    return 0
  fi

  task2_remote_env_or_default "$COMPOSE_DIR/.env" CYBERVPN_SPB_AGENT_ENV_FILE /srv/cybervpn/secrets/vpn-test-agent-spb.env
}

backup_remote_file() {
  path="$1"
  label="$2"
  backup=""

  $REMOTE_SUDO install -d "$(dirname "$path")"
  if $REMOTE_SUDO test -e "$path"; then
    backup="${path}.pre-${RELEASE_TAG}-$(date -u +%Y%m%dT%H%M%SZ)"
    $REMOTE_SUDO cp -a "$path" "$backup"
    log "${label} backup: ${backup}"
  else
    log "${label} has no existing file; rollback will remove ${path}"
  fi

  printf '%s|%s\n' "$path" "$backup" >>"$task2_backup_manifest"
}

install_remote_file_with_backup() {
  source_path="$1"
  destination_path="$2"
  mode="$3"
  label="$4"

  $REMOTE_SUDO test -f "$source_path" || remote_fail "release artifact is missing: ${source_path}"
  backup_remote_file "$destination_path" "$label"
  $REMOTE_SUDO install -m "$mode" "$source_path" "$destination_path"
}

capture_task2_firewall_state() {
  if $REMOTE_SUDO systemctl is-enabled --quiet "$task2_firewall_unit"; then
    task2_firewall_was_enabled=true
  else
    task2_firewall_was_enabled=false
  fi

  if $REMOTE_SUDO systemctl is-active --quiet "$task2_firewall_unit"; then
    task2_firewall_was_active=true
  else
    task2_firewall_was_active=false
  fi
}

rollback_task2_files() {
  [ -n "$task2_backup_manifest" ] && [ -f "$task2_backup_manifest" ] || return 0

  log "rolling back Task2 route evidence files"
  if [ "$task2_spb_sidecar_started" = "true" ] && [ -n "$task2_spb_agent_env_file" ] && $REMOTE_SUDO test -f "$SPB_COMPOSE_FILE"; then
    log "stopping Task2 SPB sidecar"
    task2_spb_compose stop cybervpn-vpn-test-agent-spb-target || true
    task2_spb_compose rm -f -s cybervpn-vpn-test-agent-spb-target || true
  fi

  while IFS='|' read -r destination backup; do
    [ -n "$destination" ] || continue
    if [ -n "$backup" ] && $REMOTE_SUDO test -e "$backup"; then
      $REMOTE_SUDO cp -a "$backup" "$destination"
    else
      $REMOTE_SUDO rm -f "$destination"
    fi
  done <"$task2_backup_manifest"

  if [ "$task2_spb_sidecar_existed" = "true" ] && $REMOTE_SUDO test -f "$SPB_COMPOSE_FILE"; then
    log "restoring previous Task2 SPB sidecar image"
    task2_spb_compose_with_image "$task2_spb_previous_registry" "$task2_spb_previous_tag" up -d --force-recreate cybervpn-vpn-test-agent-spb-target || true
    if [ "$task2_spb_sidecar_was_running" != "true" ]; then
      task2_spb_compose_with_image "$task2_spb_previous_registry" "$task2_spb_previous_tag" stop cybervpn-vpn-test-agent-spb-target || true
    fi
  fi

  if [ "$task2_caddy_touched" = "true" ]; then
    log "reloading Caddy with restored Task2 route evidence config"
    (cd "$EDGE_COMPOSE_DIR" && $REMOTE_SUDO docker compose -f "$EDGE_COMPOSE_FILE" up -d --no-deps --force-recreate "$EDGE_CADDY_SERVICE") || true
  fi

  $REMOTE_SUDO systemctl daemon-reload || true
  if [ "$task2_firewall_was_active" = "true" ]; then
    $REMOTE_SUDO systemctl restart "$task2_firewall_unit" || true
  else
    $REMOTE_SUDO systemctl stop "$task2_firewall_unit" || true
  fi
  if [ "$task2_firewall_was_enabled" = "true" ]; then
    $REMOTE_SUDO systemctl enable "$task2_firewall_unit" >/dev/null || true
  else
    $REMOTE_SUDO systemctl disable "$task2_firewall_unit" >/dev/null || true
  fi
}

rollback_task2_on_error() {
  status=$?
  if [ "$task2_deploy_active" = "true" ] && [ "$task2_deploy_completed" != "true" ]; then
    log "Task2 route evidence deploy failed; restoring backups"
    rollback_task2_files || log "Task2 rollback encountered an error"
  fi
  exit "$status"
}

trap rollback_task2_on_error ERR

require_stage1_backend_network_contract() {
  env_file="$COMPOSE_DIR/.env"
  stage1_backend_network="$(task2_remote_env_or_default "$env_file" CYBERVPN_STAGE1_BACKEND_NETWORK cybervpn_stage1_backend)"
  expected_subnet="$(task2_remote_env_or_default "$env_file" CYBERVPN_STAGE1_BACKEND_SUBNET 172.30.3.0/24)"
  expected_gateway="$(task2_remote_env_or_default "$env_file" CYBERVPN_STAGE1_BACKEND_GATEWAY 172.30.3.1)"

  if [ "$stage1_backend_network" != "cybervpn_stage1_backend" ]; then
    remote_fail "Task2 route evidence requires cybervpn_stage1_backend network, got ${stage1_backend_network}"
  fi
  if [ "$expected_subnet" != "172.30.3.0/24" ] || [ "$expected_gateway" != "172.30.3.1" ]; then
    remote_fail "Task2 route evidence requires subnet 172.30.3.0/24 and gateway 172.30.3.1"
  fi

  network_contract="$($REMOTE_SUDO docker network inspect "$stage1_backend_network" --format '{{range .IPAM.Config}}{{println .Subnet "|" .Gateway}}{{end}}' || true)"
  if [ -z "$network_contract" ]; then
    remote_fail "existing Docker network ${stage1_backend_network} is missing; refusing unsafe recreation"
  fi
  if ! printf '%s\n' "$network_contract" | grep -Fxq "172.30.3.0/24 | 172.30.3.1"; then
    remote_fail "existing Docker network ${stage1_backend_network} does not match subnet 172.30.3.0/24 gateway 172.30.3.1"
  fi

  log "Docker network ${stage1_backend_network} matches Task2 route evidence contract"
}

task2_spb_compose_with_image() {
  registry="$1"
  tag="$2"
  shift 2
  (
    cd "$SPB_COMPOSE_DIR"
    $REMOTE_SUDO env \
      CYBERVPN_IMAGE_REGISTRY="$registry" \
      CYBERVPN_IMAGE_TAG="$tag" \
      CYBERVPN_SPB_AGENT_ENV_FILE="$task2_spb_agent_env_file" \
      docker compose -f "$SPB_COMPOSE_FILE" "$@"
  )
}

task2_spb_compose() {
  task2_spb_compose_with_image "$IMAGE_REGISTRY" "$RELEASE_TAG" "$@"
}

capture_task2_spb_sidecar_state() {
  container=cybervpn-vpn-test-agent-spb-target
  if ! $REMOTE_SUDO docker inspect "$container" >/dev/null 2>&1; then
    return 0
  fi

  task2_spb_sidecar_existed=true
  previous_image="$($REMOTE_SUDO docker inspect "$container" --format '{{.Config.Image}}')"
  case "$previous_image" in
    */cybervpn-vpn-test-agent:*)
      task2_spb_previous_registry="${previous_image%/cybervpn-vpn-test-agent:*}"
      task2_spb_previous_tag="${previous_image##*:}"
      ;;
    *) remote_fail "existing SPB vpn-test-agent image is outside the expected repository" ;;
  esac
  if [ "$($REMOTE_SUDO docker inspect "$container" --format '{{.State.Running}}')" = "true" ]; then
    task2_spb_sidecar_was_running=true
  fi
}

require_spb_compose_contract() {
  [ "$SPB_COMPOSE_DIR" = "/srv/cybervpn/compose/vpn-test-agent-spb" ] || remote_fail "Task2 route evidence requires production SPB compose dir /srv/cybervpn/compose/vpn-test-agent-spb"
  [ "$SPB_COMPOSE_FILE" = "/srv/cybervpn/compose/vpn-test-agent-spb/docker-compose.yml" ] || remote_fail "Task2 route evidence requires production SPB compose file /srv/cybervpn/compose/vpn-test-agent-spb/docker-compose.yml"
}

edge_compose() {
  (cd "$EDGE_COMPOSE_DIR" && $REMOTE_SUDO docker compose -f "$EDGE_COMPOSE_FILE" "$@")
}

require_edge_caddy_contract() {
  [ "$EDGE_COMPOSE_DIR" = "/srv/cybervpn/compose/edge" ] || remote_fail "Task2 route evidence requires production edge compose dir /srv/cybervpn/compose/edge"
  [ "$EDGE_COMPOSE_FILE" = "/srv/cybervpn/compose/edge/docker-compose.yml" ] || remote_fail "Task2 route evidence requires production edge compose file /srv/cybervpn/compose/edge/docker-compose.yml"
  [ "$EDGE_CADDY_SERVICE" = "caddy" ] || remote_fail "Task2 route evidence requires production edge service caddy"
  [ "$EDGE_CADDYFILE_PATH" = "/srv/cybervpn/edge/caddy/Caddyfile" ] || remote_fail "Task2 route evidence requires production edge Caddyfile /srv/cybervpn/edge/caddy/Caddyfile"

  $REMOTE_SUDO test -f "$EDGE_COMPOSE_FILE" || remote_fail "production edge compose file is missing: ${EDGE_COMPOSE_FILE}"
  $REMOTE_SUDO test -f "$EDGE_CADDYFILE_PATH" || remote_fail "production edge Caddyfile is missing: ${EDGE_CADDYFILE_PATH}"
  $REMOTE_SUDO grep -Fq '"[2a0d:2787:1b:12f5::a]:9445:9445/tcp"' "$EDGE_COMPOSE_FILE" || remote_fail "production edge compose does not publish the dedicated Task2 IPv6 port"
  $REMOTE_SUDO grep -Fq '/srv/cybervpn/edge/caddy/Caddyfile:/etc/caddy/Caddyfile:ro' "$EDGE_COMPOSE_FILE" || remote_fail "production edge compose does not mount the canonical Caddyfile"
  edge_network_contract="$($REMOTE_SUDO docker network inspect cybervpn-edge --format '{{range .IPAM.Config}}{{println .Subnet "|" .Gateway}}{{end}}' 2>/dev/null || true)"
  if ! printf '%s\n' "$edge_network_contract" | grep -Fxq "172.30.0.0/24 | 172.30.0.1"; then
    remote_fail "production edge network must use subnet 172.30.0.0/24 and gateway 172.30.0.1 for the Task2 Caddy source matcher"
  fi
  edge_compose config --quiet
  edge_config_file="$(mktemp)"
  edge_compose config --format json >"$edge_config_file"
  if ! python3 - "$edge_config_file" "$EDGE_CADDY_SERVICE" <<'PY'
import json
import sys

config_path, expected_service = sys.argv[1:]
with open(config_path, encoding="utf-8") as config_file:
    config = json.load(config_file)

services = config.get("services")
if not isinstance(services, dict):
    raise SystemExit("compose services are missing")

task2_publishes = []
for service_name, service in services.items():
    if not isinstance(service, dict):
        continue
    ports = service.get("ports") or []
    if not isinstance(ports, list):
        raise SystemExit(f"compose ports are invalid for {service_name}")
    for port in ports:
        if not isinstance(port, dict):
            raise SystemExit(f"compose port entry is invalid for {service_name}")
        if str(port.get("published") or "") == "9445" or port.get("target") == 9445:
            task2_publishes.append((service_name, port))

if len(task2_publishes) != 1:
    raise SystemExit("Task2 evidence requires exactly one 9445 publish")

service_name, task2_publish = task2_publishes[0]
expected = {
    "host_ip": "2a0d:2787:1b:12f5::a",
    "target": 9445,
    "published": "9445",
    "protocol": "tcp",
}
if service_name != expected_service or any(task2_publish.get(key) != value for key, value in expected.items()):
    raise SystemExit("Task2 evidence 9445 publish is not bound exclusively to the dedicated IPv6")
PY
  then
    rm -f "$edge_config_file"
    remote_fail "production edge compose has an unsafe Task2 9445 publish contract"
  fi
  rm -f "$edge_config_file"
  if edge_compose ps -a cybervpn-caddy >/dev/null 2>&1; then
    remote_fail "refusing to use app Caddy service name cybervpn-caddy in the production edge compose project"
  fi
  edge_container_id="$(edge_compose ps -q "$EDGE_CADDY_SERVICE")"
  [ -n "$edge_container_id" ] || remote_fail "production edge Caddy service is not running: ${EDGE_CADDY_SERVICE}"
}

require_spb_sidecar_secret_env() {
  task2_spb_agent_env_file="$(task2_resolve_spb_agent_env_file)"
  $REMOTE_SUDO test -s "$task2_spb_agent_env_file" || remote_fail "SPB vpn-test-agent env file is missing or empty: ${task2_spb_agent_env_file}"
  sidecar_secret="$(remote_env_value "$task2_spb_agent_env_file" VPN_TEST_AGENT_SECRET || true)"
  if [ -z "$sidecar_secret" ]; then
    remote_fail "SPB vpn-test-agent env file is missing VPN_TEST_AGENT_SECRET"
  fi
  sidecar_secret_lower="$(printf '%s' "$sidecar_secret" | tr '[:upper:]' '[:lower:]')"
  case "$sidecar_secret_lower" in
    *replace*|*example*|*test*|*placeholder*|*changeme*|*dummy*|*local*|*development*|*dev-*|*redacted*|*your_*)
      remote_fail "SPB vpn-test-agent env file contains a placeholder VPN_TEST_AGENT_SECRET"
      ;;
  esac
  if remote_env_bool_is_true "$COMPOSE_DIR/.env" VPN_TESTER_TASK2_ROUTE_EVIDENCE_ENABLED; then
    backend_spb_secret="$(remote_env_value "$COMPOSE_DIR/.env" VPN_TEST_AGENT_SPB_SECRET || true)"
    [ "$backend_spb_secret" = "$sidecar_secret" ] || remote_fail "VPN_TEST_AGENT_SPB_SECRET must match SPB sidecar VPN_TEST_AGENT_SECRET"
  fi
  log "SPB vpn-test-agent env file is present"
}

install_task2_route_evidence_files() {
  caddyfile_path="$(task2_caddyfile_path)"

  install_remote_file_with_backup \
    "$REMOTE_SRC/infra/deploy/stage1/Caddyfile.edge-stage1.production" \
    "$caddyfile_path" \
    0644 \
    "production edge Caddyfile"
  task2_caddy_touched=true
  install_remote_file_with_backup \
    "$REMOTE_SRC/infra/nftables/cybervpn-task2-evidence-ingress.nft" \
    "/etc/nftables.d/cybervpn-task2-evidence-ingress.nft" \
    0644 \
    "Task2 nftables rules"
  install_remote_file_with_backup \
    "$REMOTE_SRC/infra/systemd/cybervpn-task2-evidence-firewall.service" \
    "/etc/systemd/system/${task2_firewall_unit}" \
    0644 \
    "Task2 firewall systemd unit"
  install_remote_file_with_backup \
    "$REMOTE_SRC/infra/deploy/stage1/docker-compose.vpn-test-agent-spb.yml" \
    "$SPB_COMPOSE_FILE" \
    0644 \
    "SPB vpn-test-agent sidecar compose"
}

start_task2_firewall() {
  $REMOTE_SUDO systemctl daemon-reload
  $REMOTE_SUDO systemctl enable --now "$task2_firewall_unit"
  $REMOTE_SUDO systemctl is-active --quiet "$task2_firewall_unit"
  log "Task2 firewall unit is active"
}

start_task2_spb_sidecar() {
  agent_image="$(image_for vpn-test-agent):${RELEASE_TAG}"
  $REMOTE_SUDO docker image inspect "$agent_image" >/dev/null || remote_fail "verified vpn-test-agent image is missing: ${agent_image}"
  task2_spb_compose config --quiet
  task2_spb_compose up -d --force-recreate
  task2_spb_sidecar_started=true
  retry_curl task2-spb-agent-health task2_spb_compose exec -T cybervpn-vpn-test-agent-spb-target python healthcheck.py
  log "Task2 SPB proxy-only sidecar is healthy"
}

recreate_caddy_for_task2_evidence() {
  require_edge_caddy_contract
  edge_compose up -d --no-deps --force-recreate "$EDGE_CADDY_SERVICE"
  retry_curl task2-edge-caddy-validate edge_compose exec -T "$EDGE_CADDY_SERVICE" caddy validate --config /etc/caddy/Caddyfile
  retry_curl task2-edge-caddy-task2-deny edge_compose exec -T "$EDGE_CADDY_SERVICE" sh -lc "wget --quiet --tries=1 --server-response --spider --header='Host: task2-evidence.cyber-vpn.org' http://127.0.0.1:9445/ 2>&1 | grep -q ' 404 '"
  log "Task2 production edge Caddy route is loaded and denies unrelated requests"
}

deploy_task2_route_evidence_surface() {
  task2_backup_manifest="$(mktemp)"
  capture_task2_firewall_state
  task2_deploy_active=true

  require_stage1_backend_network_contract
  require_task2_evidence_config_if_enabled
  require_spb_compose_contract
  require_spb_sidecar_secret_env
  require_edge_caddy_contract
  capture_task2_spb_sidecar_state
  install_task2_route_evidence_files
  start_task2_firewall
  start_task2_spb_sidecar
  recreate_caddy_for_task2_evidence

  log "Task2 route evidence deploy surface is ready"
}

image_for() {
  case "$1" in
    backend) echo "${IMAGE_REGISTRY}/cybervpn-backend" ;;
    frontend) echo "${IMAGE_REGISTRY}/cybervpn-frontend" ;;
    admin) echo "${IMAGE_REGISTRY}/cybervpn-admin" ;;
    partner) echo "${IMAGE_REGISTRY}/cybervpn-partner" ;;
    telegram-bot) echo "${IMAGE_REGISTRY}/cybervpn-telegram-bot" ;;
    task-worker) echo "${IMAGE_REGISTRY}/cybervpn-task-worker" ;;
    vpn-test-agent) echo "${IMAGE_REGISTRY}/cybervpn-vpn-test-agent" ;;
    *) return 1 ;;
  esac
}

current_tag="$($REMOTE_SUDO grep -E '^CYBERVPN_IMAGE_TAG=' "$COMPOSE_DIR/.env" | tail -1 | cut -d= -f2- || true)"
if [ -z "$current_tag" ]; then
  current_tag="stage1-beta-rc.1"
fi

log "current tag: ${current_tag}"
log "new tag: ${RELEASE_TAG}"

cd "$REMOTE_SRC"

build_service() {
  service="$1"
  repo="$(image_for "$service")"
  case "$service" in
    backend)
      log "building backend image"
      $REMOTE_SUDO docker build --pull -t "${repo}:${RELEASE_TAG}" backend
      ;;
    frontend)
      log "building frontend image"
      $REMOTE_SUDO docker build -f infra/deploy/stage1/Dockerfile.next-workspace \
        --build-arg NEXT_WORKSPACE=frontend \
        --build-arg NEXT_PUBLIC_SITE_URL="${STAGE1_FRONTEND_PUBLIC_URL:-https://cyber-vpn.net}" \
        --build-arg NEXT_PUBLIC_API_URL="${STAGE1_FRONTEND_API_URL:-https://cyber-vpn.net}" \
        --build-arg NEXT_PUBLIC_STAGE1_ADDONS_ENABLED="${STAGE1_NEXT_PUBLIC_STAGE1_ADDONS_ENABLED:-${NEXT_PUBLIC_STAGE1_ADDONS_ENABLED:-true}}" \
        --build-arg NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED="${STAGE1_NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED:-${NEXT_PUBLIC_STAGE1_GROWTH_EVIDENCE_APPROVED:-true}}" \
        --build-arg NEXT_PUBLIC_STAGE1_REFERRAL_ENABLED="${STAGE1_NEXT_PUBLIC_STAGE1_REFERRAL_ENABLED:-${NEXT_PUBLIC_STAGE1_REFERRAL_ENABLED:-true}}" \
        --build-arg NEXT_PUBLIC_STAGE1_PROMO_CODES_ENABLED="${STAGE1_NEXT_PUBLIC_STAGE1_PROMO_CODES_ENABLED:-${NEXT_PUBLIC_STAGE1_PROMO_CODES_ENABLED:-true}}" \
        --build-arg NEXT_PUBLIC_STAGE1_GIFT_CODES_ENABLED="${STAGE1_NEXT_PUBLIC_STAGE1_GIFT_CODES_ENABLED:-${NEXT_PUBLIC_STAGE1_GIFT_CODES_ENABLED:-true}}" \
        --build-arg NEXT_PUBLIC_STAGE1_CHECKOUT_CODES_ENABLED="${STAGE1_NEXT_PUBLIC_STAGE1_CHECKOUT_CODES_ENABLED:-${NEXT_PUBLIC_STAGE1_CHECKOUT_CODES_ENABLED:-true}}" \
        --build-arg NEXT_PUBLIC_PARTNER_PORTAL_ENABLED="${STAGE1_NEXT_PUBLIC_PARTNER_PORTAL_ENABLED:-${NEXT_PUBLIC_PARTNER_PORTAL_ENABLED:-true}}" \
        --build-arg NEXT_PUBLIC_PARTNER_STOREFRONTS_ENABLED="${STAGE1_NEXT_PUBLIC_PARTNER_STOREFRONTS_ENABLED:-${NEXT_PUBLIC_PARTNER_STOREFRONTS_ENABLED:-true}}" \
        --build-arg NEXT_PUBLIC_PARTNER_PILOT_ENABLED="${STAGE1_NEXT_PUBLIC_PARTNER_PILOT_ENABLED:-${NEXT_PUBLIC_PARTNER_PILOT_ENABLED:-true}}" \
        --build-arg API_INTERNAL_ORIGIN="${STAGE1_API_INTERNAL_ORIGIN:-http://cybervpn-backend:8000}" \
        -t "${repo}:${RELEASE_TAG}" .
      ;;
    admin)
      log "building admin image"
      $REMOTE_SUDO docker build -f infra/deploy/stage1/Dockerfile.next-workspace \
        --build-arg NEXT_WORKSPACE=admin \
        --build-arg NEXT_PUBLIC_SITE_URL="${STAGE1_ADMIN_PUBLIC_URL:-https://admin.cyber-vpn.net}" \
        --build-arg NEXT_PUBLIC_API_URL="${STAGE1_FRONTEND_API_URL:-https://cyber-vpn.net}" \
        --build-arg API_INTERNAL_ORIGIN="${STAGE1_API_INTERNAL_ORIGIN:-http://cybervpn-backend:8000}" \
        -t "${repo}:${RELEASE_TAG}" .
      ;;
    partner)
      log "building partner image"
      $REMOTE_SUDO docker build -f infra/deploy/stage1/Dockerfile.next-workspace \
        --build-arg NEXT_WORKSPACE=partner \
        --build-arg NEXT_PUBLIC_SITE_URL="${STAGE1_PARTNER_PUBLIC_URL:-https://partner.cyber-vpn.net}" \
        --build-arg NEXT_PUBLIC_API_URL="${STAGE1_FRONTEND_API_URL:-https://api.cyber-vpn.net}" \
        --build-arg NEXT_PUBLIC_PARTNER_PORTAL_ENABLED="${STAGE1_NEXT_PUBLIC_PARTNER_PORTAL_ENABLED:-${NEXT_PUBLIC_PARTNER_PORTAL_ENABLED:-true}}" \
        --build-arg NEXT_PUBLIC_PARTNER_STOREFRONTS_ENABLED="${STAGE1_NEXT_PUBLIC_PARTNER_STOREFRONTS_ENABLED:-${NEXT_PUBLIC_PARTNER_STOREFRONTS_ENABLED:-true}}" \
        --build-arg NEXT_PUBLIC_PARTNER_PILOT_ENABLED="${STAGE1_NEXT_PUBLIC_PARTNER_PILOT_ENABLED:-${NEXT_PUBLIC_PARTNER_PILOT_ENABLED:-true}}" \
        --build-arg NEXT_PUBLIC_PARTNER_PORTAL_HOST="${STAGE1_PARTNER_PORTAL_HOST:-partner.cyber-vpn.net}" \
        --build-arg NEXT_PUBLIC_PARTNER_PORTAL_HOSTS="${STAGE1_PARTNER_PORTAL_HOSTS:-partner.cyber-vpn.net}" \
        --build-arg NEXT_PUBLIC_PARTNER_STOREFRONT_HOSTS="${STAGE1_PARTNER_STOREFRONT_HOSTS:-storefront.cyber-vpn.net}" \
        --build-arg NEXT_PUBLIC_PARTNER_API_AUTH_REALM="${STAGE1_PARTNER_API_AUTH_REALM:-partner}" \
        --build-arg NEXT_PUBLIC_PARTNER_PORTAL_SIMULATION_ENABLED="${STAGE1_NEXT_PUBLIC_PARTNER_PORTAL_SIMULATION_ENABLED:-${NEXT_PUBLIC_PARTNER_PORTAL_SIMULATION_ENABLED:-false}}" \
        --build-arg API_INTERNAL_ORIGIN="${STAGE1_API_INTERNAL_ORIGIN:-http://cybervpn-backend:8000}" \
        -t "${repo}:${RELEASE_TAG}" .
      ;;
    telegram-bot)
      log "building telegram-bot image"
      $REMOTE_SUDO docker build --pull -t "${repo}:${RELEASE_TAG}" services/telegram-bot
      ;;
    task-worker)
      log "building task-worker image"
      $REMOTE_SUDO docker build --pull -t "${repo}:${RELEASE_TAG}" services/task-worker
      ;;
    vpn-test-agent)
      log "building vpn-test-agent image"
      $REMOTE_SUDO docker build --pull -t "${repo}:${RELEASE_TAG}" services/vpn-test-agent
      ;;
  esac
}

if [ "${TASK2_ONLY:-false}" = "true" ]; then
  build_service vpn-test-agent
else
  for service in backend frontend admin partner telegram-bot task-worker vpn-test-agent; do
    repo="$(image_for "$service")"
    if is_requested "$service" || { [ "$service" = "vpn-test-agent" ] && task2_route_evidence_requested; }; then
      build_service "$service"
    else
      log "retagging unchanged ${service} image for compose compatibility"
      if $REMOTE_SUDO docker image inspect "${repo}:${current_tag}" >/dev/null 2>&1; then
        $REMOTE_SUDO docker tag "${repo}:${current_tag}" "${repo}:${RELEASE_TAG}"
      elif $REMOTE_SUDO docker image inspect "${repo}:${RELEASE_TAG}" >/dev/null 2>&1; then
        log "${service} already has ${RELEASE_TAG}"
      else
        log "missing ${repo}:${current_tag}; cannot retag unchanged service"
        exit 1
      fi
    fi
  done
fi

if [ "${PRIMARY_DEPLOY_REQUESTED:-false}" = "true" ]; then
  if [ -f "$REMOTE_SRC/infra/deploy/stage1/docker-compose.stage1.yml" ]; then
    compose_backup="$COMPOSE_DIR/docker-compose.yml.pre-${RELEASE_TAG}"
    log "updating compose file from release source"
    $REMOTE_SUDO cp "$COMPOSE_DIR/docker-compose.yml" "$compose_backup"
    $REMOTE_SUDO install -m 0644 "$REMOTE_SRC/infra/deploy/stage1/docker-compose.stage1.yml" "$COMPOSE_DIR/docker-compose.yml"
    log "compose backup: ${compose_backup}"
  fi
  if [ -f "$REMOTE_SRC/infra/deploy/stage1/docker-compose.subscription-page-rollback.yml" ]; then
    subscription_rollback_compose="$COMPOSE_DIR/docker-compose.subscription-page-rollback.yml"
    if $REMOTE_SUDO test -e "$subscription_rollback_compose"; then
      $REMOTE_SUDO cp -a "$subscription_rollback_compose" "${subscription_rollback_compose}.pre-${RELEASE_TAG}"
    fi
    $REMOTE_SUDO install -m 0644 \
      "$REMOTE_SRC/infra/deploy/stage1/docker-compose.subscription-page-rollback.yml" \
      "$subscription_rollback_compose"
    log "installed component-only subscription-page 7.2.6 rollback override"
  fi

  cd "$COMPOSE_DIR"
  $REMOTE_SUDO sed -i "s/^CYBERVPN_IMAGE_TAG=.*/CYBERVPN_IMAGE_TAG=${RELEASE_TAG}/" .env
  ensure_remote_env_value .env REGISTRATION_ENABLED true
  ensure_remote_env_value .env TELEGRAM_BOT_REGISTRATION_MODE allow_pending_onboarding
  ensure_remote_env_value .env TELEGRAM_BOT_ALLOW_REGISTRATION_WHEN_PUBLIC_CLOSED true
  ensure_remote_env_value .env TELEGRAM_MINIAPP_URL https://cyber-vpn.net/ru-RU/miniapp
  ensure_remote_env_value .env TELEGRAM_MINIAPP_ONBOARDING_URL https://cyber-vpn.net/ru-RU/miniapp/onboarding/code
  ensure_remote_env_value .env VPN_TESTER_ENABLED true
  if remote_env_bool_is_true .env VPN_TESTER_TASK2_ROUTE_EVIDENCE_ENABLED; then
    log "Task2 route evidence is enabled; preserving runtime and synthetic-user switches for validation"
  else
    ensure_remote_env_value .env VPN_TESTER_RUNTIME_ENABLED false
    ensure_remote_env_value .env VPN_TESTER_SYNTHETIC_USERS_ENABLED false
  fi
  ensure_remote_env_value .env VPN_TESTER_SCHEDULED_ENABLED true
  ensure_remote_env_value .env VPN_TESTER_BALANCER_RECOMMENDATIONS_ENABLED true
  ensure_remote_env_value .env VPN_TESTER_RETENTION_DAYS 30
  ensure_remote_env_value .env VPN_TEST_AGENT_URL http://cybervpn-vpn-test-agent:8080
  ensure_remote_env_secret .env VPN_TEST_AGENT_SECRET
  ensure_remote_env_value .env VPN_TEST_AGENT_PROXY_ONLY_ENABLED true
  ensure_remote_env_value .env VPN_TEST_AGENT_TUN_ENABLED false
else
  cd "$COMPOSE_DIR"
  log "skipping primary app compose and .env mutation for Task2-only deploy"
fi

compose_services=()
is_requested backend && compose_services+=(cybervpn-backend)
is_requested subscription-page && compose_services+=(cybervpn-remnawave-subscription-page)
is_requested frontend && compose_services+=(cybervpn-frontend)
is_requested admin && compose_services+=(cybervpn-admin)
is_requested partner && compose_services+=(cybervpn-partner)
is_requested telegram-bot && compose_services+=(cybervpn-telegram-bot)
is_requested vpn-test-agent && compose_services+=(cybervpn-vpn-test-agent)
if is_requested task-worker; then
  compose_services+=(cybervpn-worker cybervpn-scheduler)
fi

if [ "${PRIMARY_DEPLOY_REQUESTED:-false}" = "true" ]; then
  ensure_backend_device_cookie_pepper
  require_remnawave_stream_hmac_secret
  require_remnawave_connection_drop_hmac_secret
  require_remnawave_app_secret_continuity
  require_remnawave_subscription_page_contract
fi

if task2_route_evidence_requested; then
  deploy_task2_route_evidence_surface
fi

if [ "${#compose_services[@]}" -gt 0 ]; then
  log "recreating compose services: ${compose_services[*]}"
  $REMOTE_SUDO docker compose up -d "${compose_services[@]}"
else
  log "no primary compose services requested"
fi

if is_requested backend; then
  log "running backend database migrations"
  $REMOTE_SUDO docker compose exec -T cybervpn-backend alembic upgrade heads
fi
if is_requested subscription-page; then
  retry_curl subscription-page-health $REMOTE_SUDO docker compose exec -T cybervpn-remnawave-subscription-page curl -fsS -o /dev/null --max-time 2 http://127.0.0.1:3010/internal/health
fi

log "compose status"
$REMOTE_SUDO docker compose ps "${compose_services[@]}"

if is_requested backend; then
  retry_curl backend-health curl -fsS http://127.0.0.1:18080/health
  printf '\n'
  retry_curl backend-fingerprint curl -fsS http://127.0.0.1:18080/api/v1/runtime/fingerprint
  printf '\n'
  retry_curl backend-capabilities curl -fsS http://127.0.0.1:18080/api/v1/client/capabilities
  printf '\n'
fi
if is_requested frontend; then
  retry_curl frontend-miniapp curl -fsSI http://127.0.0.1:13000/ru-RU/miniapp/home | sed -n '1,8p'
fi
if is_requested admin; then
  retry_curl admin-login curl -fsSI http://127.0.0.1:13001/ru-RU/login | sed -n '1,8p'
fi
if is_requested partner; then
  retry_curl partner-login curl -fsSI http://127.0.0.1:13002/ru-RU/login | sed -n '1,8p'
fi
if is_requested telegram-bot; then
  retry_curl telegram-bot-health curl -fsS http://127.0.0.1:18088/health
  printf '\n'
  retry_curl telegram-bot-fingerprint curl -fsS http://127.0.0.1:18088/runtime/fingerprint
  printf '\n'
  $REMOTE_SUDO docker compose exec -T cybervpn-telegram-bot python - <<'PY'
import json
import os
import sys
import urllib.parse
import urllib.request

token = (os.environ.get("BOT_TOKEN") or "").strip()
if not token:
    print("BOT_TOKEN is not configured in telegram bot container", file=sys.stderr)
    sys.exit(1)
with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getWebhookInfo", timeout=15) as response:
    payload = json.loads(response.read().decode("utf-8"))
result = payload.get("result") or {}
safe = {
    "ok": bool(payload.get("ok")),
    "pending_update_count": result.get("pending_update_count"),
    "last_error_message": result.get("last_error_message"),
    "url_host": urllib.parse.urlparse(str(result.get("url") or "")).netloc,
}
print(json.dumps(safe, ensure_ascii=False, sort_keys=True))
if safe["last_error_message"] and "401" in str(safe["last_error_message"]):
    sys.exit(1)
PY
fi
if is_requested vpn-test-agent; then
  retry_curl vpn-test-agent-health $REMOTE_SUDO docker compose exec -T cybervpn-vpn-test-agent python healthcheck.py
fi

if task2_route_evidence_requested; then
  task2_deploy_completed=true
  task2_deploy_active=false
fi

log "deployment complete"
REMOTE_SCRIPT

if [[ "$primary_deploy_requested" == "true" ]]; then
  {
    echo
    echo "## Public Smoke"
    echo
    echo '```text'
  } >>"$evidence_file"

  for url in $public_smoke_urls; do
    curl --retry 10 --retry-delay 3 --retry-all-errors -fsS -o /dev/null -w "%{http_code} %{time_total} ${url}\n" "$url" | tee -a "$evidence_file"
  done

  {
    echo '```'
  } >>"$evidence_file"
else
  {
    echo
    echo "## Public Smoke"
    echo
    echo "Skipped for Task2-only deploy; bounded edge and sidecar smoke ran on the remote host."
  } >>"$evidence_file"
fi

if [[ "$primary_deploy_requested" == "true" && ",$services_csv," == *",frontend,"* ]]; then
  {
    echo
    echo "## Customer RSC Smoke"
    echo
    echo '```text'
  } >>"$evidence_file"
  HOST="$customer_rsc_smoke_host" bash scripts/smoke/customer_site_rsc_routes.sh | tee -a "$evidence_file"
  {
    echo '```'
  } >>"$evidence_file"
fi

{
  echo
  echo "Completed at: \`$(date -u +%Y-%m-%dT%H:%M:%SZ)\`"
} >>"$evidence_file"

log "evidence written to $evidence_file"
