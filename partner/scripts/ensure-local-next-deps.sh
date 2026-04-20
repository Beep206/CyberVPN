#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCK_SENTINEL="$APP_DIR/node_modules/.package-lock.json"

if [ -f "$APP_DIR/node_modules/next/package.json" ] \
  && [ -f "$APP_DIR/node_modules/react/package.json" ] \
  && [ -f "$LOCK_SENTINEL" ] \
  && [ "$LOCK_SENTINEL" -nt "$APP_DIR/package.json" ] \
  && [ "$LOCK_SENTINEL" -nt "$APP_DIR/package-lock.json" ]; then
  exit 0
fi

cd "$APP_DIR"

if [ "$APP_DIR/package.json" -nt "$APP_DIR/package-lock.json" ]; then
  echo "Refreshing frontend package-lock for Turbopack bootstrap..." >&2
  npm install --package-lock-only --workspaces=false --ignore-scripts --no-fund --no-audit
fi

echo "Syncing frontend local dependencies for Turbopack..." >&2
npm ci --workspaces=false --no-fund --no-audit
