#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS_BIN="$(bash "${REPO_ROOT}/scripts/ensure-observability-cli-tools.sh" --print-bin-dir)"
PROMETHEUS_RULES_DIR="${REPO_ROOT}/infra/prometheus/rules"
PROMETHEUS_TARGETS_DIR="${REPO_ROOT}/infra/prometheus/targets"

export PATH="${TOOLS_BIN}:${PATH}"

info() {
  printf "\033[0;34m[INFO]\033[0m  %s\n" "$*"
}

ok() {
  printf "\033[0;32m[OK]\033[0m    %s\n" "$*"
}

fail() {
  printf "\033[0;31m[FAIL]\033[0m  %s\n" "$*" >&2
}

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    fail "Required command '${command_name}' is not available on PATH."
    exit 1
  fi
}

render_alertmanager_config() {
  local output_file="$1"
  local webhook_url
  webhook_url="${ALERTMANAGER_WEBHOOK_URL:-https://your-telegram-relay.example.com/alert}"

  ALERTMANAGER_WEBHOOK_URL_RENDER="${webhook_url}" \
  ALERTMANAGER_TEMPLATES_DIR_RENDER="${REPO_ROOT}/infra/alertmanager/templates" \
  python3 - <<'PY' >"${output_file}"
import os
from pathlib import Path

template = Path("infra/alertmanager/alertmanager.yml.template").read_text(encoding="utf-8")
webhook_url = os.environ["ALERTMANAGER_WEBHOOK_URL_RENDER"]
template = template.replace("/etc/alertmanager/templates", os.environ["ALERTMANAGER_TEMPLATES_DIR_RENDER"])
print(template.replace("${ALERTMANAGER_WEBHOOK_URL}", webhook_url), end="")
PY
}

render_prometheus_config() {
  local output_file="$1"
  local targets_dir="$2"

  PROMETHEUS_RULES_DIR_RENDER="${PROMETHEUS_RULES_DIR}" \
  PROMETHEUS_TARGETS_DIR_RENDER="${targets_dir}" \
  python3 - <<'PY' >"${output_file}"
import os
from pathlib import Path

config = Path("infra/prometheus/prometheus.yml").read_text(encoding="utf-8")
config = config.replace("/etc/prometheus/rules", os.environ["PROMETHEUS_RULES_DIR_RENDER"])
config = config.replace("/etc/prometheus/targets", os.environ["PROMETHEUS_TARGETS_DIR_RENDER"])
print(config, end="")
PY
}

main() {
  local rendered_alertmanager_config
  local rendered_prometheus_config
  local rendered_prometheus_targets_dir

  cd "${REPO_ROOT}"
  require_command promtool
  require_command amtool
  require_command python3

  rendered_prometheus_config="$(mktemp)"
  rendered_alertmanager_config="$(mktemp)"
  rendered_prometheus_targets_dir="$(mktemp -d)"
  trap "rm -f '${rendered_prometheus_config}' '${rendered_alertmanager_config}'; rm -rf '${rendered_prometheus_targets_dir}'" EXIT

  if compgen -G "${PROMETHEUS_TARGETS_DIR}/*.json" >/dev/null; then
    cp "${PROMETHEUS_TARGETS_DIR}"/*.json "${rendered_prometheus_targets_dir}/"
  else
    printf '[]\n' >"${rendered_prometheus_targets_dir}/placeholder.json"
  fi

  render_prometheus_config "${rendered_prometheus_config}" "${rendered_prometheus_targets_dir}"
  render_alertmanager_config "${rendered_alertmanager_config}"

  info "Checking Prometheus config with promtool..."
  promtool check config "${rendered_prometheus_config}" --lint=all --lint-fatal

  info "Checking Prometheus rules with promtool..."
  promtool check rules "${PROMETHEUS_RULES_DIR}"/*.yml --lint=all --lint-fatal

  info "Checking rendered Alertmanager config with amtool..."
  amtool check-config "${rendered_alertmanager_config}"

  ok "promtool/amtool validation passed."
}

main "$@"
