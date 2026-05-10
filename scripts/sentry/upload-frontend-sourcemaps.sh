#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SENTRY_URL="${SENTRY_URL:-https://sentry.h.cyber-vpn.net}"
SENTRY_RELEASE="${SENTRY_RELEASE:-${CI_COMMIT_SHA:-}}"
SOURCEMAP_DIR="${FRONTEND_SOURCEMAPS_DIR:-${ROOT_DIR}/frontend/.next/static}"

required_env=(SENTRY_AUTH_TOKEN SENTRY_ORG SENTRY_PROJECT SENTRY_RELEASE)
for name in "${required_env[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    printf 'ERROR: %s is required\n' "${name}" >&2
    exit 1
  fi
done

if [[ ! -d "${SOURCEMAP_DIR}" ]]; then
  printf 'ERROR: sourcemap directory does not exist: %s\n' "${SOURCEMAP_DIR}" >&2
  exit 1
fi

if command -v sentry-cli >/dev/null 2>&1; then
  SENTRY_CLI=(sentry-cli)
elif command -v npx >/dev/null 2>&1; then
  SENTRY_CLI=(npx --yes @sentry/cli)
else
  printf 'ERROR: sentry-cli or npx is required\n' >&2
  exit 1
fi

export SENTRY_URL SENTRY_AUTH_TOKEN SENTRY_ORG SENTRY_PROJECT

"${SENTRY_CLI[@]}" releases new "${SENTRY_RELEASE}" || true
"${SENTRY_CLI[@]}" releases set-commits "${SENTRY_RELEASE}" --auto || true

upload_args=(
  sourcemaps upload
  --org "${SENTRY_ORG}"
  --project "${SENTRY_PROJECT}"
  --release "${SENTRY_RELEASE}"
)

if [[ -n "${SENTRY_DIST:-}" ]]; then
  upload_args+=(--dist "${SENTRY_DIST}")
fi

upload_args+=("${SOURCEMAP_DIR}")

"${SENTRY_CLI[@]}" "${upload_args[@]}"
"${SENTRY_CLI[@]}" releases finalize "${SENTRY_RELEASE}"

printf 'Uploaded frontend sourcemaps for release %s from %s\n' "${SENTRY_RELEASE}" "${SOURCEMAP_DIR}"
