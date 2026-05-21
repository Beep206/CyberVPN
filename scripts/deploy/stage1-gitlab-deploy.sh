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
  all, frontend, admin, backend, telegram-bot, task-worker

Required CI variables:
  STAGE1_PROD_HOST
  STAGE1_PROD_SSH_PRIVATE_KEY or STAGE1_PROD_SSH_KEY_FILE

Recommended protected CI variables:
  STAGE1_PROD_USER=deploy
  STAGE1_PROD_PORT=22
  STAGE1_PROD_KNOWN_HOSTS=<ssh-keyscan output>
USAGE
}

services_input="${1:-${STAGE1_DEPLOY_SERVICES:-}}"
[[ -n "$services_input" ]] || {
  usage
  fail "service list is required"
}

host="${STAGE1_PROD_HOST:-}"
[[ -n "$host" ]] || fail "STAGE1_PROD_HOST is required"

user="${STAGE1_PROD_USER:-deploy}"
port="${STAGE1_PROD_PORT:-22}"
compose_dir="${STAGE1_PROD_COMPOSE_DIR:-/srv/cybervpn/compose/app}"
release_root="${STAGE1_PROD_RELEASE_ROOT:-/srv/cybervpn/releases}"
image_registry="${STAGE1_IMAGE_REGISTRY:-cybervpn}"
remote_sudo="${STAGE1_REMOTE_SUDO:-sudo}"
release_tag="${STAGE1_RELEASE_TAG:-stage1-ci-${CI_PIPELINE_IID:-0}-${CI_COMMIT_SHORT_SHA:-local}}"
evidence_dir="${STAGE1_DEPLOY_EVIDENCE_DIR:-docs/evidence/releases/ci-stage1}"
public_smoke_urls="${STAGE1_PUBLIC_SMOKE_URLS:-https://cyber-vpn.net/ru-RU/miniapp/home https://admin.cyber-vpn.net/ru-RU/login https://api.cyber-vpn.net/healthz}"

case "$release_tag" in
  *[!A-Za-z0-9_.-]*)
    fail "release tag contains unsupported characters: $release_tag"
    ;;
esac

IFS=',' read -r -a requested_services <<<"$services_input"

declare -A requested=()
for raw_service in "${requested_services[@]}"; do
  service="$(printf '%s' "$raw_service" | xargs)"
  [[ -n "$service" ]] || continue
  case "$service" in
    all|frontend|admin|backend|telegram-bot|task-worker)
      requested["$service"]=1
      ;;
    *)
      fail "unsupported service: $service"
      ;;
  esac
done

[[ ${#requested[@]} -gt 0 ]] || fail "no valid services requested"

if [[ -n "${requested[all]:-}" ]]; then
  requested=(
    [frontend]=1
    [admin]=1
    [backend]=1
    [telegram-bot]=1
    [task-worker]=1
  )
fi

mkdir -p "$evidence_dir"
evidence_file="$evidence_dir/stage1-gitlab-deploy-${release_tag}.md"

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

log "syncing source without secrets/heavy build artifacts"
rsync -az --delete \
  --exclude='.git/' \
  --exclude='.private/' \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='*.pem' \
  --exclude='*.key' \
  --exclude='node_modules/' \
  --exclude='**/node_modules/' \
  --exclude='.next/' \
  --exclude='**/.next/' \
  --exclude='.cache/' \
  --exclude='.pytest_cache/' \
  --exclude='.ruff_cache/' \
  --exclude='.tmp/' \
  --exclude='htmlcov/' \
  --exclude='.coverage' \
  --exclude='.coverage.*' \
  -e "${ssh_base[*]}" \
  ./ "$user@$host:$remote_src/"

services_csv="$(IFS=,; echo "${!requested[*]}")"

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
  "RELEASE_TAG='$release_tag' REMOTE_SRC='$remote_src' COMPOSE_DIR='$compose_dir' IMAGE_REGISTRY='$image_registry' REMOTE_SUDO='$remote_sudo' SERVICES_CSV='$services_csv' bash -s" <<'REMOTE_SCRIPT' | tee -a "$evidence_file"
set -Eeuo pipefail

log() {
  printf '[remote-stage1-deploy] %s\n' "$*"
}

is_requested() {
  case ",${SERVICES_CSV}," in
    *",$1,"*) return 0 ;;
    *) return 1 ;;
  esac
}

image_for() {
  case "$1" in
    backend) echo "${IMAGE_REGISTRY}/cybervpn-backend" ;;
    frontend) echo "${IMAGE_REGISTRY}/cybervpn-frontend" ;;
    admin) echo "${IMAGE_REGISTRY}/cybervpn-admin" ;;
    telegram-bot) echo "${IMAGE_REGISTRY}/cybervpn-telegram-bot" ;;
    task-worker) echo "${IMAGE_REGISTRY}/cybervpn-task-worker" ;;
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
    telegram-bot)
      log "building telegram-bot image"
      $REMOTE_SUDO docker build --pull -t "${repo}:${RELEASE_TAG}" services/telegram-bot
      ;;
    task-worker)
      log "building task-worker image"
      $REMOTE_SUDO docker build --pull -t "${repo}:${RELEASE_TAG}" services/task-worker
      ;;
  esac
}

for service in backend frontend admin telegram-bot task-worker; do
  repo="$(image_for "$service")"
  if is_requested "$service"; then
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

cd "$COMPOSE_DIR"
$REMOTE_SUDO sed -i "s/^CYBERVPN_IMAGE_TAG=.*/CYBERVPN_IMAGE_TAG=${RELEASE_TAG}/" .env

compose_services=()
is_requested backend && compose_services+=(cybervpn-backend)
is_requested frontend && compose_services+=(cybervpn-frontend)
is_requested admin && compose_services+=(cybervpn-admin)
is_requested telegram-bot && compose_services+=(cybervpn-telegram-bot)
if is_requested task-worker; then
  compose_services+=(cybervpn-worker cybervpn-scheduler)
fi

log "recreating compose services: ${compose_services[*]}"
$REMOTE_SUDO docker compose up -d "${compose_services[@]}"

log "compose status"
$REMOTE_SUDO docker compose ps "${compose_services[@]}"

if is_requested backend; then
  curl -fsS http://127.0.0.1:18080/health
  printf '\n'
fi
if is_requested frontend; then
  curl -fsSI http://127.0.0.1:13000/ru-RU/miniapp/home | sed -n '1,8p'
fi
if is_requested admin; then
  curl -fsSI http://127.0.0.1:13001/ru-RU/login | sed -n '1,8p'
fi
if is_requested telegram-bot; then
  curl -fsS http://127.0.0.1:18088/health || true
  printf '\n'
fi

log "deployment complete"
REMOTE_SCRIPT

{
  echo
  echo "## Public Smoke"
  echo
  echo '```text'
} >>"$evidence_file"

for url in $public_smoke_urls; do
  curl -fsS -o /dev/null -w "%{http_code} %{time_total} ${url}\n" "$url" | tee -a "$evidence_file"
done

{
  echo '```'
  echo
  echo "Completed at: \`$(date -u +%Y-%m-%dT%H:%M:%SZ)\`"
} >>"$evidence_file"

log "evidence written to $evidence_file"
