#!/usr/bin/env bash

set -euo pipefail

ALERTMANAGER_URL="${ALERTMANAGER_URL:-http://localhost:9093}"
TOOLS_BIN="$(bash "$(dirname "$0")/ensure-observability-cli-tools.sh" --print-bin-dir)"
export PATH="${TOOLS_BIN}:${PATH}"

if ! command -v amtool >/dev/null 2>&1; then
  echo "amtool is required" >&2
  exit 1
fi

cat <<'EOF'
Sending synthetic Stage 1 alert delivery test.
This proves Alertmanager intake only. Human evidence must still capture:
- Telegram message in channel -5173727789
- backup email delivered to backup@cyber-vpn.net
EOF

amtool \
  --alertmanager.url="${ALERTMANAGER_URL}" \
  alert add Stage1AlertDeliveryTest \
  severity=critical \
  priority=p0 \
  service=observability \
  stage=s1 \
  --annotation=summary="S1 alert delivery test" \
  --annotation=description="Synthetic S1 alert delivery test for Telegram and backup email evidence" \
  --annotation=dashboard_path="/d/stage1-controlled-public-beta/stage-1-controlled-public-beta" \
  --annotation=runbook_path="docs/runbooks/STAGE1_OBSERVABILITY_ALERT_RUNBOOK.md"

amtool --alertmanager.url="${ALERTMANAGER_URL}" alert query Stage1AlertDeliveryTest
