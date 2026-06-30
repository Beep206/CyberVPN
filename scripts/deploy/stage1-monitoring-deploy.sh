#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

REMOTE_HOST="${STAGE1_PROD_HOST:-45.87.41.146}"
REMOTE_USER="${STAGE1_PROD_USER:-root}"
SSH_KEY_FILE="${STAGE1_PROD_SSH_KEY_FILE:-${HOME}/.ssh/MainKey2_private_fixed.pem}"
REMOTE_DIR="${STAGE1_MONITORING_REMOTE_DIR:-/srv/cybervpn/compose/monitoring}"
REMOTE_APP_DIR="${STAGE1_APP_REMOTE_DIR:-/srv/cybervpn/compose/app}"

fail() {
  echo "ERROR: $*" >&2
  exit 2
}

validate_remote_path() {
  local name="$1"
  local path="$2"
  if [[ ! "$path" =~ ^/[A-Za-z0-9._/-]+$ || "$path" == *"//"* ]]; then
    fail "${name} must be an absolute Linux path containing only A-Z, a-z, 0-9, '.', '_', '-' and '/': ${path}"
  fi
}

validate_remote_path STAGE1_MONITORING_REMOTE_DIR "${REMOTE_DIR}"
validate_remote_path STAGE1_APP_REMOTE_DIR "${REMOTE_APP_DIR}"

known_hosts_file=""
SSH_OPTS=(
  -i "${SSH_KEY_FILE}"
  -o BatchMode=yes
  -o StrictHostKeyChecking=yes
  -o ConnectTimeout=10
)

if [[ ! -r "${SSH_KEY_FILE}" ]]; then
  fail "SSH key is not readable: ${SSH_KEY_FILE}"
fi

tmp_dir="$(mktemp -d)"
payload_archive="$(mktemp)"
cleanup() {
  rm -rf "${tmp_dir}"
  rm -f "${payload_archive}"
  if [[ -n "${known_hosts_file}" && -f "${known_hosts_file}" ]]; then
    rm -f "${known_hosts_file}"
  fi
}
trap cleanup EXIT

if [[ -n "${STAGE1_PROD_KNOWN_HOSTS:-}" ]]; then
  known_hosts_file="$(mktemp)"
  printf '%s\n' "${STAGE1_PROD_KNOWN_HOSTS}" >"${known_hosts_file}"
  SSH_OPTS+=(-o "UserKnownHostsFile=${known_hosts_file}")
elif [[ -n "${STAGE1_PROD_KNOWN_HOSTS_FILE:-}" ]]; then
  SSH_OPTS+=(-o "UserKnownHostsFile=${STAGE1_PROD_KNOWN_HOSTS_FILE}")
else
  SSH_OPTS+=(-o "UserKnownHostsFile=${HOME}/.ssh/known_hosts")
fi

mkdir -p \
  "${tmp_dir}/prometheus/rules" \
  "${tmp_dir}/grafana/provisioning" \
  "${tmp_dir}/grafana/dashboards" \
  "${tmp_dir}/alertmanager"

cp "${ROOT_DIR}/infra/deploy/stage1/monitoring/docker-compose.stage1-monitoring.yml" "${tmp_dir}/docker-compose.yml"
cp "${ROOT_DIR}/infra/deploy/stage1/monitoring/prometheus.stage1-production.yml.template" "${tmp_dir}/prometheus/prometheus.yml.template"
cp "${ROOT_DIR}/infra/deploy/stage1/monitoring/alertmanager.stage1-production.yml" "${tmp_dir}/alertmanager/alertmanager.yml"
cp "${ROOT_DIR}/infra/prometheus/rules/stage1_dashboard_recording_rules.yml" "${tmp_dir}/prometheus/rules/"
cp "${ROOT_DIR}/infra/prometheus/rules/stage1_alerts.yml" "${tmp_dir}/prometheus/rules/"
cp -R "${ROOT_DIR}/infra/grafana/provisioning/." "${tmp_dir}/grafana/provisioning/"
cp "${ROOT_DIR}/infra/grafana/dashboards/remnawave-node-metrics-dashboard.json" "${tmp_dir}/grafana/dashboards/"

tar -C "${tmp_dir}" -czf "${payload_archive}" .
remote_archive="/tmp/cybervpn-stage1-monitoring-$(date +%s)-$$.tgz"
scp "${SSH_OPTS[@]}" "${payload_archive}" "${REMOTE_USER}@${REMOTE_HOST}:${remote_archive}"

# Remote arguments are strict-validated absolute paths before this call.
# shellcheck disable=SC2029
ssh "${SSH_OPTS[@]}" "${REMOTE_USER}@${REMOTE_HOST}" \
  "bash -s --" "${REMOTE_DIR}" "${REMOTE_APP_DIR}" "${remote_archive}" <<'REMOTE'
set -euo pipefail
REMOTE_DIR="$1"
REMOTE_APP_DIR="$2"
REMOTE_ARCHIVE="$3"
mkdir -p -- "${REMOTE_DIR}"
tar -C "${REMOTE_DIR}" -xzf "${REMOTE_ARCHIVE}"
rm -f -- "${REMOTE_ARCHIVE}"
cd "${REMOTE_DIR}"

remnawave_container="$(cd "${REMOTE_APP_DIR}" && docker compose ps -q cybervpn-remnawave)"
if [[ -z "${remnawave_container}" ]]; then
  echo "Remnawave container was not found in ${REMOTE_APP_DIR}" >&2
  exit 3
fi

export REMNAWAVE_METRICS_USER
export REMNAWAVE_METRICS_PASS
REMNAWAVE_METRICS_USER="$(docker exec "${remnawave_container}" sh -lc 'printf %s "${METRICS_USER:?missing METRICS_USER}"')"
REMNAWAVE_METRICS_PASS="$(docker exec "${remnawave_container}" sh -lc 'printf %s "${METRICS_PASS:?missing METRICS_PASS}"')"

umask 077
if [[ ! -f .env ]]; then
  grafana_password="$(openssl rand -base64 36 | tr -d '\n')"
  cat > .env <<EOF
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=${grafana_password}
STAGE1_PROMETHEUS_PORT=9090
STAGE1_GRAFANA_PORT=3002
STAGE1_ALERTMANAGER_PORT=9093
EOF
fi
chmod 0600 .env

python3 - <<'PY'
import os
from pathlib import Path

template_path = Path("prometheus/prometheus.yml.template")
output_path = Path("prometheus/prometheus.yml")
text = template_path.read_text()
text = text.replace("${REMNAWAVE_METRICS_USER}", os.environ["REMNAWAVE_METRICS_USER"])
text = text.replace("${REMNAWAVE_METRICS_PASS}", os.environ["REMNAWAVE_METRICS_PASS"])
output_path.write_text(text)
PY
chown 65534:65534 prometheus/prometheus.yml
chmod 0400 prometheus/prometheus.yml

docker compose --env-file .env -f docker-compose.yml config >/dev/null
docker compose --env-file .env -f docker-compose.yml up -d --wait --force-recreate prometheus grafana alertmanager

printf 'PROMETHEUS_HEALTH='
curl -fsS http://127.0.0.1:9090/-/healthy
printf '\nGRAFANA_HEALTH='
curl -fsS http://127.0.0.1:3002/api/health | python3 -c 'import json,sys; data=json.load(sys.stdin); print(data.get("database"), data.get("version"))'
printf 'ALERTMANAGER_HEALTH='
curl -fsS http://127.0.0.1:9093/-/healthy
printf '\nREMNAWAVE_UP='
prometheus_query_json="$(
  curl -fsS --get http://127.0.0.1:9090/api/v1/query --data-urlencode 'query=up{job="remnawave"}'
)"
PROMETHEUS_QUERY_JSON="${prometheus_query_json}" python3 - <<'PY'
import json
import os

data = json.loads(os.environ["PROMETHEUS_QUERY_JSON"])
result = data.get("data", {}).get("result", [])
value = result[0].get("value", [None, "none"])[1] if result else "none"
print(len(result), value)
raise SystemExit(0 if result and value == "1" else 1)
PY
REMOTE
