#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/infra/docker-compose.yml"
CACHE_ROOT="${REPO_ROOT}/.cache/observability-cli"

print_usage() {
  cat <<'EOF'
Usage:
  bash scripts/ensure-observability-cli-tools.sh [--print-bin-dir]

Downloads promtool and amtool versions that match infra/docker-compose.yml
into a local cache directory and prints the bin directory.
EOF
}

fail() {
  printf "\033[0;31m[FAIL]\033[0m  %s\n" "$*" >&2
}

info() {
  printf "\033[0;34m[INFO]\033[0m  %s\n" "$*" >&2
}

require_command() {
  local command_name="$1"
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    fail "Required command '${command_name}' is not available."
    exit 1
  fi
}

resolve_platform() {
  local uname_s uname_m os arch

  uname_s="$(uname -s | tr '[:upper:]' '[:lower:]')"
  uname_m="$(uname -m | tr '[:upper:]' '[:lower:]')"

  case "${uname_s}" in
    linux) os="linux" ;;
    darwin) os="darwin" ;;
    *)
      fail "Unsupported operating system '${uname_s}'."
      exit 1
      ;;
  esac

  case "${uname_m}" in
    x86_64|amd64) arch="amd64" ;;
    aarch64|arm64) arch="arm64" ;;
    *)
      fail "Unsupported architecture '${uname_m}'."
      exit 1
      ;;
  esac

  printf "%s %s" "${os}" "${arch}"
}

extract_versions() {
  python3 - <<'PY'
import re
from pathlib import Path

compose = Path("infra/docker-compose.yml").read_text(encoding="utf-8")
prometheus = re.search(r"image:\s+prom/prometheus:v([0-9.]+)", compose)
alertmanager = re.search(r"image:\s+prom/alertmanager:v([0-9.]+)", compose)
if not prometheus or not alertmanager:
    raise SystemExit("Could not resolve Prometheus/Alertmanager versions from infra/docker-compose.yml")
print(prometheus.group(1), alertmanager.group(1))
PY
}

download_and_extract() {
  local url="$1"
  local destination_dir="$2"
  local binary_name="$3"
  local strip_dir="$4"
  local tarball

  mkdir -p "${destination_dir}"
  tarball="$(mktemp)"
  trap 'rm -f "${tarball}"' RETURN

  info "Downloading ${binary_name} from ${url}"
  curl -fsSL "${url}" -o "${tarball}"
  tar -xzf "${tarball}" -C "${destination_dir}" "${strip_dir}/${binary_name}" --strip-components=1
  chmod +x "${destination_dir}/${binary_name}"
  rm -f "${tarball}"
  trap - RETURN
}

main() {
  local print_bin_dir=false
  local os arch prometheus_version alertmanager_version
  local versions
  local bin_dir prometheus_dir alertmanager_dir

  case "${1:-}" in
    --print-bin-dir)
      print_bin_dir=true
      ;;
    "")
      ;;
    -h|--help)
      print_usage
      exit 0
      ;;
    *)
      print_usage
      exit 1
      ;;
  esac

  require_command curl
  require_command tar
  require_command python3

  cd "${REPO_ROOT}"
  read -r os arch <<<"$(resolve_platform)"
  read -r prometheus_version alertmanager_version <<<"$(extract_versions)"

  bin_dir="${CACHE_ROOT}/bin"
  prometheus_dir="${CACHE_ROOT}/prometheus-${prometheus_version}-${os}-${arch}"
  alertmanager_dir="${CACHE_ROOT}/alertmanager-${alertmanager_version}-${os}-${arch}"

  mkdir -p "${bin_dir}"

  if [[ ! -x "${bin_dir}/promtool" ]]; then
    download_and_extract \
      "https://github.com/prometheus/prometheus/releases/download/v${prometheus_version}/prometheus-${prometheus_version}.${os}-${arch}.tar.gz" \
      "${prometheus_dir}" \
      "promtool" \
      "prometheus-${prometheus_version}.${os}-${arch}"
    cp "${prometheus_dir}/promtool" "${bin_dir}/promtool"
  fi

  if [[ ! -x "${bin_dir}/amtool" ]]; then
    download_and_extract \
      "https://github.com/prometheus/alertmanager/releases/download/v${alertmanager_version}/alertmanager-${alertmanager_version}.${os}-${arch}.tar.gz" \
      "${alertmanager_dir}" \
      "amtool" \
      "alertmanager-${alertmanager_version}.${os}-${arch}"
    cp "${alertmanager_dir}/amtool" "${bin_dir}/amtool"
  fi

  if [[ "${print_bin_dir}" == "true" ]]; then
    printf "%s\n" "${bin_dir}"
    exit 0
  fi

  info "Observability CLI tools are ready in ${bin_dir}"
  printf "%s\n" "${bin_dir}"
}

main "$@"
