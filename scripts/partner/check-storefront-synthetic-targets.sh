#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGETS_FILE="${1:-${ROOT_DIR}/infra/prometheus/targets/stage3-storefront-endpoints.json}"

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required" >&2
  exit 1
fi

jq -r '.[].targets[]' "${TARGETS_FILE}" | while read -r url; do
  host="$(printf '%s\n' "${url}" | sed -E 's#^https?://([^/]+)/?.*#\1#')"
  if ! getent hosts "${host}" >/dev/null 2>&1; then
    printf 'blocked\tdns_missing\t%s\n' "${url}"
    continue
  fi
  if curl -fsS --max-time 10 "${url}" >/dev/null; then
    printf 'ok\thttp_2xx\t%s\n' "${url}"
  else
    printf 'blocked\thttp_failed\t%s\n' "${url}"
  fi
done
