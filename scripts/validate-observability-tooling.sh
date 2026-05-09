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
  local secret_dir="$2"
  local smtp_password_file="${secret_dir}/smtp_password"

  printf '%s' "${ALERTMANAGER_SMTP_PASSWORD:-}" >"${smtp_password_file}"

  ALERTMANAGER_TELEGRAM_BOT_TOKEN_RENDER="${ALERTMANAGER_TELEGRAM_BOT_TOKEN:-000000000:stage1-local-placeholder}" \
  ALERTMANAGER_TELEGRAM_CHAT_ID_RENDER="${ALERTMANAGER_TELEGRAM_CHAT_ID:--5173727789}" \
  ALERTMANAGER_SMTP_PASSWORD_FILE_RENDER="${smtp_password_file}" \
  ALERTMANAGER_SMTP_FROM_RENDER="${ALERTMANAGER_SMTP_FROM:-alerts@cyber-vpn.net}" \
  ALERTMANAGER_SMTP_SMARTHOST_RENDER="${ALERTMANAGER_SMTP_SMARTHOST:-mailpit-1:1025}" \
  ALERTMANAGER_SMTP_HELLO_RENDER="${ALERTMANAGER_SMTP_HELLO:-cyber-vpn.net}" \
  ALERTMANAGER_SMTP_AUTH_USERNAME_RENDER="${ALERTMANAGER_SMTP_AUTH_USERNAME:-}" \
  ALERTMANAGER_SMTP_REQUIRE_TLS_RENDER="${ALERTMANAGER_SMTP_REQUIRE_TLS:-false}" \
  ALERTMANAGER_BACKUP_EMAIL_RENDER="${ALERTMANAGER_BACKUP_EMAIL:-backup@cyber-vpn.net}" \
  ALERTMANAGER_TEMPLATES_DIR_RENDER="${REPO_ROOT}/infra/alertmanager/templates" \
  python3 - <<'PY' >"${output_file}"
import os
from pathlib import Path

template = Path("infra/alertmanager/alertmanager.yml.template").read_text(encoding="utf-8")
replacements = {
    "${ALERTMANAGER_TELEGRAM_BOT_TOKEN}": os.environ["ALERTMANAGER_TELEGRAM_BOT_TOKEN_RENDER"],
    "${ALERTMANAGER_TELEGRAM_CHAT_ID}": os.environ["ALERTMANAGER_TELEGRAM_CHAT_ID_RENDER"],
    "${ALERTMANAGER_SMTP_PASSWORD_FILE}": os.environ["ALERTMANAGER_SMTP_PASSWORD_FILE_RENDER"],
    "${ALERTMANAGER_SMTP_FROM}": os.environ["ALERTMANAGER_SMTP_FROM_RENDER"],
    "${ALERTMANAGER_SMTP_SMARTHOST}": os.environ["ALERTMANAGER_SMTP_SMARTHOST_RENDER"],
    "${ALERTMANAGER_SMTP_HELLO}": os.environ["ALERTMANAGER_SMTP_HELLO_RENDER"],
    "${ALERTMANAGER_SMTP_AUTH_USERNAME}": os.environ["ALERTMANAGER_SMTP_AUTH_USERNAME_RENDER"],
    "${ALERTMANAGER_SMTP_REQUIRE_TLS}": os.environ["ALERTMANAGER_SMTP_REQUIRE_TLS_RENDER"],
    "${ALERTMANAGER_BACKUP_EMAIL}": os.environ["ALERTMANAGER_BACKUP_EMAIL_RENDER"],
    "/etc/alertmanager/templates": os.environ["ALERTMANAGER_TEMPLATES_DIR_RENDER"],
}
for needle, value in replacements.items():
    template = template.replace(needle, value)
print(template, end="")
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
  local rendered_alertmanager_secret_dir
  local rendered_prometheus_config
  local rendered_prometheus_targets_dir

  cd "${REPO_ROOT}"
  require_command promtool
  require_command amtool
  require_command python3

  rendered_prometheus_config="$(mktemp)"
  rendered_alertmanager_config="$(mktemp)"
  rendered_alertmanager_secret_dir="$(mktemp -d)"
  rendered_prometheus_targets_dir="$(mktemp -d)"
  trap "rm -f '${rendered_prometheus_config}' '${rendered_alertmanager_config}'; rm -rf '${rendered_prometheus_targets_dir}' '${rendered_alertmanager_secret_dir}'" EXIT

  if compgen -G "${PROMETHEUS_TARGETS_DIR}/*.json" >/dev/null; then
    cp "${PROMETHEUS_TARGETS_DIR}"/*.json "${rendered_prometheus_targets_dir}/"
  else
    printf '[]\n' >"${rendered_prometheus_targets_dir}/placeholder.json"
  fi

  render_prometheus_config "${rendered_prometheus_config}" "${rendered_prometheus_targets_dir}"
  render_alertmanager_config "${rendered_alertmanager_config}" "${rendered_alertmanager_secret_dir}"

  info "Checking Prometheus config with promtool..."
  promtool check config "${rendered_prometheus_config}" --lint=all --lint-fatal

  info "Checking Prometheus rules with promtool..."
  promtool check rules "${PROMETHEUS_RULES_DIR}"/*.yml --lint=all --lint-fatal

  info "Checking rendered Alertmanager config with amtool..."
  amtool check-config "${rendered_alertmanager_config}"

  ok "promtool/amtool validation passed."
}

main "$@"
