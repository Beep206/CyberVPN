#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
FRONTEND_DIR="${REPO_ROOT}/frontend"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SNAPSHOT_DIR="$(mktemp -d)"

info()  { printf "\033[0;34m[INFO]\033[0m  %s\n" "$*"; }
ok()    { printf "\033[0;32m[OK]\033[0m    %s\n" "$*"; }
fail()  { printf "\033[0;31m[FAIL]\033[0m  %s\n" "$*"; }

cleanup() {
    rm -rf "${SNAPSHOT_DIR}"
}

trap cleanup EXIT

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    fail "${PYTHON_BIN} is not available on PATH"
    exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
    fail "npm is not available on PATH"
    exit 1
fi

mkdir -p "${SNAPSHOT_DIR}/backend/docs/api" \
         "${SNAPSHOT_DIR}/frontend/src/lib/api/generated" \
         "${SNAPSHOT_DIR}/frontend/src/i18n/messages"

cp -f "${BACKEND_DIR}/docs/api/openapi.json" "${SNAPSHOT_DIR}/backend/docs/api/openapi.json"
cp -f "${FRONTEND_DIR}/src/lib/api/generated/types.ts" "${SNAPSHOT_DIR}/frontend/src/lib/api/generated/types.ts"
cp -a "${FRONTEND_DIR}/src/i18n/messages/generated" "${SNAPSHOT_DIR}/frontend/src/i18n/messages/generated"

info "Regenerating backend OpenAPI spec..."
export REMNAWAVE_TOKEN="${REMNAWAVE_TOKEN:-dummy_token_for_generated_artifact_check}"
export REMNAWAVE_WEBHOOK_SECRET="${REMNAWAVE_WEBHOOK_SECRET:-dummy_webhook_secret_for_generated_artifact_check}"
export JWT_SECRET="${JWT_SECRET:-generated_artifact_check_dummy_secret_that_is_at_least_32_chars_long}"
export CRYPTOBOT_TOKEN="${CRYPTOBOT_TOKEN:-dummy_cryptobot_token}"
export SWAGGER_ENABLED="${SWAGGER_ENABLED:-true}"
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://x:x@localhost:5432/x}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
"${PYTHON_BIN}" "${BACKEND_DIR}/scripts/export_openapi.py"

info "Regenerating frontend API types..."
(
    cd "${FRONTEND_DIR}"
    npm run generate:api-types
)

info "Regenerating frontend i18n bundles..."
(
    cd "${FRONTEND_DIR}"
    npm run prepare:i18n
)

info "Checking for generated artifact drift..."
if ! diff -u "${SNAPSHOT_DIR}/backend/docs/api/openapi.json" "${BACKEND_DIR}/docs/api/openapi.json" \
    || ! diff -u "${SNAPSHOT_DIR}/frontend/src/lib/api/generated/types.ts" "${FRONTEND_DIR}/src/lib/api/generated/types.ts" \
    || ! diff -ruN "${SNAPSHOT_DIR}/frontend/src/i18n/messages/generated" "${FRONTEND_DIR}/src/i18n/messages/generated"; then
    fail "Generated artifacts are out of date."
    echo "Run these commands and commit the results:"
    echo "  cd ${BACKEND_DIR} && ${PYTHON_BIN} scripts/export_openapi.py"
    echo "  cd ${FRONTEND_DIR} && npm run generate:api-types && npm run prepare:i18n"
    exit 1
fi

ok "Generated artifacts are in sync."
