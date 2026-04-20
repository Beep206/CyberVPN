#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARTNER_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PARTNER_DIR}"

export NEXT_TELEMETRY_DISABLED=1
export NODE_ENV=production
export HOSTNAME="${HOSTNAME:-0.0.0.0}"
export PORT="${PORT:-9004}"

exec node /home/beep/projects/VPNBussiness/node_modules/next/dist/bin/next start -H "${HOSTNAME}" -p "${PORT}"
