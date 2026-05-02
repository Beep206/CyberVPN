#!/usr/bin/env bash
set -euo pipefail

BINARY_PATH="${1:-apps/desktop-client/src-tauri/target/release/desktop-client}"
SMOKE_DELAY_MS="${DESKTOP_SMOKE_DELAY_MS:-1500}"
SMOKE_TIMEOUT_SECONDS="${DESKTOP_SMOKE_TIMEOUT_SECONDS:-30}"

if [[ ! -x "${BINARY_PATH}" ]]; then
  echo "desktop smoke binary not found or not executable: ${BINARY_PATH}" >&2
  exit 1
fi

SMOKE_ROOT="$(mktemp -d)"
cleanup() {
  rm -rf "${SMOKE_ROOT}"
}
trap cleanup EXIT

export HOME="${SMOKE_ROOT}/home"
export XDG_CONFIG_HOME="${HOME}/.config"
export XDG_DATA_HOME="${HOME}/.local/share"
mkdir -p "${XDG_CONFIG_HOME}" "${XDG_DATA_HOME}"

export VITE_SENTRY_DSN="${VITE_SENTRY_DSN:-https://desktop-renderer@example.com/1}"
export VITE_SENTRY_ENVIRONMENT="${VITE_SENTRY_ENVIRONMENT:-staging}"
export VITE_SENTRY_RELEASE="${VITE_SENTRY_RELEASE:-desktop@0.1.5+smoke}"
export DESKTOP_SENTRY_DSN="${DESKTOP_SENTRY_DSN:-https://desktop-native@example.com/1}"
export DESKTOP_SENTRY_ENVIRONMENT="${DESKTOP_SENTRY_ENVIRONMENT:-staging}"
export DESKTOP_SENTRY_RELEASE="${DESKTOP_SENTRY_RELEASE:-desktop@0.1.5+smoke}"

RUNNER=()
if [[ -z "${DISPLAY:-}" ]] && command -v xvfb-run >/dev/null 2>&1; then
  RUNNER=(xvfb-run -a)
fi

run_smoke_case() {
  local label="$1"
  shift

  echo "[desktop-smoke] ${label}"
  timeout "${SMOKE_TIMEOUT_SECONDS}s" "${RUNNER[@]}" "${BINARY_PATH}" "$@"
}

run_smoke_case "visible-clean-exit" --smoke-exit-after-ms "${SMOKE_DELAY_MS}"
run_smoke_case "hidden-clean-exit" --hidden --smoke-exit-after-ms "${SMOKE_DELAY_MS}"

echo "[desktop-smoke] passed"
