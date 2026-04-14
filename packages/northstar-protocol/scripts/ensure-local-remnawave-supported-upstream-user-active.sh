#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -z "${NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL:-}" ]] \
  || [[ -z "${NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN:-}" ]] \
  || [[ -z "${NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID:-}" ]]; then
  exec bash "$script_dir/with-local-remnawave-supported-upstream-env.sh" bash "$0" "$@"
fi

response_body="$(mktemp)"
trap 'rm -f "$response_body"' EXIT

status_code="$(
  curl -sS -o "$response_body" -w '%{http_code}' \
    -H "Authorization: Bearer ${NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN}" \
    -X POST \
    "${NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL%/}/api/users/${NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID}/actions/enable"
)"

if [[ "$status_code" == "200" ]] || [[ "$status_code" == "201" ]]; then
  echo "==> Ensured local supported-upstream account is active"
  exit 0
fi

if [[ "$status_code" == "400" ]] && grep -qi 'already enabled' "$response_body"; then
  echo "==> Local supported-upstream account was already active"
  exit 0
fi

echo "Failed to ensure local supported-upstream account is active (HTTP $status_code)" >&2
cat "$response_body" >&2
exit 1
