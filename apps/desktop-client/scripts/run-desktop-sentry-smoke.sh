#!/usr/bin/env bash
set -euo pipefail

BINARY_PATH="${1:-apps/desktop-client/src-tauri/target/release/desktop-client}"
SMOKE_DELAY_MS="${DESKTOP_SMOKE_DELAY_MS:-2500}"
SMOKE_TIMEOUT_SECONDS="${DESKTOP_SMOKE_TIMEOUT_SECONDS:-60}"

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

export NO_AT_BRIDGE="${NO_AT_BRIDGE:-1}"
export GDK_BACKEND="${GDK_BACKEND:-x11}"
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
export WEBKIT_DISABLE_DMABUF_RENDERER="${WEBKIT_DISABLE_DMABUF_RENDERER:-1}"

RUNNER=()
if [[ -z "${DISPLAY:-}" ]] && command -v xvfb-run >/dev/null 2>&1; then
  RUNNER=(xvfb-run -a -s "-screen 0 1280x720x24 -ac +extension GLX +render -noreset")
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
