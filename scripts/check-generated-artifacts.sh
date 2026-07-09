#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="${REPO_ROOT}/backend"
FRONTEND_DIR="${REPO_ROOT}/frontend"
ADMIN_DIR="${REPO_ROOT}/admin"
PARTNER_DIR="${REPO_ROOT}/partner"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SNAPSHOT_DIR="$(mktemp -d)"

info()  { printf "\033[0;34m[INFO]\033[0m  %s\n" "$*"; }
ok()    { printf "\033[0;32m[OK]\033[0m    %s\n" "$*"; }
fail()  { printf "\033[0;31m[FAIL]\033[0m  %s\n" "$*"; }

is_wsl() {
    [[ -r /proc/version ]] && grep -qi microsoft /proc/version
}

prepend_wsl_windows_node_path() {
    if ! is_wsl; then
        return
    fi

    local windows_node_dir="/mnt/c/Program Files/nodejs"
    if [[ -x "${windows_node_dir}/node.exe" && -x "${windows_node_dir}/npm" ]]; then
        PATH="${windows_node_dir}:${PATH}"
        export PATH
    fi
}

append_wslenv_entries() {
    local entry
    for entry in "$@"; do
        case ":${WSLENV:-}:" in
            *":${entry}:"*) ;;
            *) WSLENV="${WSLENV:+${WSLENV}:}${entry}" ;;
        esac
    done
    export WSLENV
}

cleanup() {
    rm -rf "${SNAPSHOT_DIR}"
}

trap cleanup EXIT

prepend_wsl_windows_node_path

if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    fail "${PYTHON_BIN} is not available on PATH"
    exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
    fail "npm is not available on PATH"
    exit 1
fi

if ! npm --version >/dev/null 2>&1; then
    fail "npm is present but cannot run; ensure Node.js is available on PATH"
    exit 1
fi

mkdir -p "${SNAPSHOT_DIR}/backend/docs/api" \
         "${SNAPSHOT_DIR}/frontend/src/lib/api/generated" \
         "${SNAPSHOT_DIR}/frontend/src/i18n/messages" \
         "${SNAPSHOT_DIR}/admin/src/lib/api/generated" \
         "${SNAPSHOT_DIR}/admin/src/i18n/messages" \
         "${SNAPSHOT_DIR}/partner/src/lib/api/generated" \
         "${SNAPSHOT_DIR}/partner/src/i18n/messages"

cp -f "${BACKEND_DIR}/docs/api/openapi.json" "${SNAPSHOT_DIR}/backend/docs/api/openapi.json"
cp -f "${FRONTEND_DIR}/src/lib/api/generated/types.ts" "${SNAPSHOT_DIR}/frontend/src/lib/api/generated/types.ts"
cp -a "${FRONTEND_DIR}/src/i18n/messages/generated" "${SNAPSHOT_DIR}/frontend/src/i18n/messages/generated"
cp -f "${ADMIN_DIR}/src/lib/api/generated/types.ts" "${SNAPSHOT_DIR}/admin/src/lib/api/generated/types.ts"
cp -a "${ADMIN_DIR}/src/i18n/messages/generated" "${SNAPSHOT_DIR}/admin/src/i18n/messages/generated"
cp -f "${PARTNER_DIR}/src/lib/api/generated/types.ts" "${SNAPSHOT_DIR}/partner/src/lib/api/generated/types.ts"
cp -a "${PARTNER_DIR}/src/i18n/messages/generated" "${SNAPSHOT_DIR}/partner/src/i18n/messages/generated"

info "Regenerating backend OpenAPI spec..."
export REMNAWAVE_TOKEN="${REMNAWAVE_TOKEN:-dummy_token_for_generated_artifact_check}"
export REMNAWAVE_WEBHOOK_SECRET="${REMNAWAVE_WEBHOOK_SECRET:-dummy_webhook_secret_for_generated_artifact_check}"
export JWT_SECRET="${JWT_SECRET:-generated_artifact_check_dummy_secret_that_is_at_least_32_chars_long}"
export CRYPTOBOT_TOKEN="${CRYPTOBOT_TOKEN:-dummy_cryptobot_token}"
export SWAGGER_ENABLED="${SWAGGER_ENABLED:-true}"
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://x:x@localhost:5432/x}"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
if [[ "${PYTHON_BIN}" == *.exe ]] && is_wsl; then
    append_wslenv_entries \
        REMNAWAVE_TOKEN \
        REMNAWAVE_WEBHOOK_SECRET \
        JWT_SECRET \
        CRYPTOBOT_TOKEN \
        SWAGGER_ENABLED \
        DATABASE_URL \
        REDIS_URL \
        OAUTH_TOKEN_ENCRYPTION_KEY \
        TOTP_ENCRYPTION_KEY
fi
OPENAPI_EXPORT_SCRIPT="${BACKEND_DIR}/scripts/export_openapi.py"
if [[ "${PYTHON_BIN}" == *.exe ]] && command -v wslpath >/dev/null 2>&1; then
    OPENAPI_EXPORT_SCRIPT="$(wslpath -w "${OPENAPI_EXPORT_SCRIPT}")"
fi
"${PYTHON_BIN}" "${OPENAPI_EXPORT_SCRIPT}"

info "Regenerating frontend API types..."
(
    cd "${FRONTEND_DIR}"
    npm run generate:api-types
)

info "Regenerating admin API types..."
(
    cd "${ADMIN_DIR}"
    npm run generate:api-types
)

info "Regenerating partner API types..."
(
    cd "${PARTNER_DIR}"
    npm run generate:api-types
)

info "Regenerating frontend i18n bundles..."
(
    cd "${FRONTEND_DIR}"
    npm run prepare:i18n
)

info "Regenerating admin i18n bundles..."
(
    cd "${ADMIN_DIR}"
    npm run prepare:i18n
)

info "Regenerating partner i18n bundles..."
(
    cd "${PARTNER_DIR}"
    npm run prepare:i18n
)

info "Checking for generated artifact drift..."
if ! diff -u "${SNAPSHOT_DIR}/backend/docs/api/openapi.json" "${BACKEND_DIR}/docs/api/openapi.json" \
    || ! diff -u "${SNAPSHOT_DIR}/frontend/src/lib/api/generated/types.ts" "${FRONTEND_DIR}/src/lib/api/generated/types.ts" \
    || ! diff -u "${SNAPSHOT_DIR}/admin/src/lib/api/generated/types.ts" "${ADMIN_DIR}/src/lib/api/generated/types.ts" \
    || ! diff -u "${SNAPSHOT_DIR}/partner/src/lib/api/generated/types.ts" "${PARTNER_DIR}/src/lib/api/generated/types.ts" \
    || ! diff -ruN "${SNAPSHOT_DIR}/frontend/src/i18n/messages/generated" "${FRONTEND_DIR}/src/i18n/messages/generated" \
    || ! diff -ruN "${SNAPSHOT_DIR}/admin/src/i18n/messages/generated" "${ADMIN_DIR}/src/i18n/messages/generated" \
    || ! diff -ruN "${SNAPSHOT_DIR}/partner/src/i18n/messages/generated" "${PARTNER_DIR}/src/i18n/messages/generated"; then
    fail "Generated artifacts are out of date."
    echo "Run these commands and commit the results:"
    echo "  cd ${BACKEND_DIR} && ${PYTHON_BIN} scripts/export_openapi.py"
    echo "  cd ${FRONTEND_DIR} && npm run generate:api-types && npm run prepare:i18n"
    echo "  cd ${ADMIN_DIR} && npm run generate:api-types && npm run prepare:i18n"
    echo "  cd ${PARTNER_DIR} && npm run generate:api-types && npm run prepare:i18n"
    exit 1
fi

ok "Generated artifacts are in sync."
