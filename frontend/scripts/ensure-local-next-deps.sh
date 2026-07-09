#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ROOT_DIR="$(cd "$APP_DIR/.." && pwd)"
WORKSPACE_DIR="$(basename "$APP_DIR")"
LOCK_SENTINEL="$ROOT_DIR/node_modules/.package-lock.json"

run_npm() {
  if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
    npm "$@"
    return
  fi

  if command -v cmd.exe >/dev/null 2>&1; then
    cmd.exe /D /C npm.cmd "$@"
    return
  fi

  echo "npm and node are required to sync workspace dependencies." >&2
  exit 127
}

if [ -f "$ROOT_DIR/node_modules/next/package.json" ] \
  && [ -f "$ROOT_DIR/node_modules/react/package.json" ] \
  && [ -f "$LOCK_SENTINEL" ] \
  && [ "$LOCK_SENTINEL" -nt "$ROOT_DIR/package.json" ] \
  && [ "$LOCK_SENTINEL" -nt "$ROOT_DIR/package-lock.json" ] \
  && [ "$LOCK_SENTINEL" -nt "$APP_DIR/package.json" ] \
  && [ ! -f "$APP_DIR/package-lock.json" ]; then
  exit 0
fi

cd "$ROOT_DIR"

echo "Syncing ${WORKSPACE_DIR} dependencies from the root package-lock..." >&2
run_npm ci --no-fund --no-audit
