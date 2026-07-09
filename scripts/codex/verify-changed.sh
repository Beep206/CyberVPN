#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "${ROOT}"

TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG_DIR="${ROOT}/.codex/command-logs/${TIMESTAMP}"
RESULTS_FILE="${LOG_DIR}/results.tsv"
mkdir -p "${LOG_DIR}"
: > "${RESULTS_FILE}"

AUTO_INSTALL="${CODEX_VERIFY_AUTO_INSTALL:-1}"
VERIFY_SCOPE="${CYBERVPN_VERIFY_SCOPE:-all}"
BASE_REF=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --scope)
      if [[ $# -lt 2 || -z "${2:-}" ]]; then
        printf 'verify-changed.sh: --scope requires a comma-separated value\n' >&2
        exit 64
      fi
      VERIFY_SCOPE="$2"
      shift 2
      ;;
    --scope=*)
      VERIFY_SCOPE="${1#--scope=}"
      shift
      ;;
    --)
      shift
      break
      ;;
    -*)
      printf 'verify-changed.sh: unknown option: %s\n' "$1" >&2
      exit 64
      ;;
    *)
      if [[ -n "${BASE_REF}" ]]; then
        printf 'verify-changed.sh: unexpected extra argument: %s\n' "$1" >&2
        exit 64
      fi
      BASE_REF="$1"
      shift
      ;;
  esac
done

while [[ $# -gt 0 ]]; do
  if [[ -n "${BASE_REF}" ]]; then
    printf 'verify-changed.sh: unexpected extra argument: %s\n' "$1" >&2
    exit 64
  fi
  BASE_REF="$1"
  shift
done

VERIFY_SCOPE="${VERIFY_SCOPE//[[:space:]]/}"
if [[ -z "${BASE_REF}" ]]; then
  if git rev-parse --verify origin/main >/dev/null 2>&1; then
    BASE_REF="$(git merge-base HEAD origin/main)"
  elif git rev-parse --verify HEAD~1 >/dev/null 2>&1; then
    BASE_REF="HEAD~1"
  else
    BASE_REF="HEAD"
  fi
fi

mapfile -t CHANGED < <(
  {
    git diff --name-only "${BASE_REF}"...HEAD 2>/dev/null || true
    git diff --name-only 2>/dev/null || true
    git diff --cached --name-only 2>/dev/null || true
    git ls-files --others --exclude-standard 2>/dev/null || true
  } | sed '/^$/d' | sort -u
)
printf '%s\n' "${CHANGED[@]:-}" > "${LOG_DIR}/changed-files.txt"
printf '%s\n' "${VERIFY_SCOPE}" > "${LOG_DIR}/scope.txt"

scope_enabled() {
  if [[ "${VERIFY_SCOPE}" == "all" || "${VERIFY_SCOPE}" == "*" ]]; then
    return 0
  fi

  local needle
  for needle in "$@"; do
    case ",${VERIFY_SCOPE}," in
      *",${needle},"*) return 0 ;;
    esac
  done

  return 1
}

changed_prefix() {
  local prefix="$1"
  local path
  for path in "${CHANGED[@]:-}"; do
    if [[ "${path}" == "${prefix}" || "${path}" == "${prefix}/"* ]]; then
      return 0
    fi
  done
  return 1
}

changed_regex() {
  local regex="$1"
  local path
  for path in "${CHANGED[@]:-}"; do
    if [[ "${path}" =~ ${regex} ]]; then
      return 0
    fi
  done
  return 1
}

slugify() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9._-]+/-/g; s/^-+|-+$//g'
}

PASS_COUNT=0
FAIL_COUNT=0
NODE_BIN="${NODE_BIN:-}"
CARGO_BIN="${CARGO_BIN:-}"
UV_BIN="${UV_BIN:-}"

is_wsl() {
  [[ -r /proc/version ]] && grep -qi microsoft /proc/version
}

prepend_wsl_windows_node_path() {
  if ! is_wsl; then
    return
  fi

  local windows_node_dir="/mnt/c/Program Files/nodejs"
  if [[ -x "${windows_node_dir}/node.exe" && ( -x "${windows_node_dir}/npm" || -x "${windows_node_dir}/npm.cmd" ) ]]; then
    PATH="${windows_node_dir}:${PATH}"
    export PATH
  fi
}

find_node_bin() {
  if [[ -n "${NODE_BIN}" ]] && command -v "${NODE_BIN}" >/dev/null 2>&1; then
    printf '%s\n' "${NODE_BIN}"
    return 0
  fi
  if command -v node >/dev/null 2>&1; then
    printf 'node\n'
    return 0
  fi
  if command -v node.exe >/dev/null 2>&1; then
    printf 'node.exe\n'
    return 0
  fi
  return 1
}

find_cargo_bin() {
  local candidate
  if [[ -n "${CARGO_BIN}" ]]; then
    if command -v "${CARGO_BIN}" >/dev/null 2>&1; then
      command -v "${CARGO_BIN}"
      return 0
    fi
    if [[ -x "${CARGO_BIN}" ]]; then
      printf '%s\n' "${CARGO_BIN}"
      return 0
    fi
  fi

  for candidate in cargo cargo.exe "${HOME:-}/.cargo/bin/cargo" /mnt/c/Users/user/.cargo/bin/cargo.exe; do
    if [[ -z "${candidate}" ]]; then
      continue
    fi
    if command -v "${candidate}" >/dev/null 2>&1; then
      command -v "${candidate}"
      return 0
    fi
    if [[ -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done

  return 1
}

find_uv_bin() {
  local candidate
  if [[ -n "${UV_BIN}" ]]; then
    if command -v "${UV_BIN}" >/dev/null 2>&1; then
      command -v "${UV_BIN}"
      return 0
    fi
    if [[ -x "${UV_BIN}" ]]; then
      printf '%s\n' "${UV_BIN}"
      return 0
    fi
  fi

  for candidate in uv "${HOME:-}/.local/bin/uv" /mnt/c/Users/user/.local/bin/uv.exe; do
    if [[ -z "${candidate}" ]]; then
      continue
    fi
    if command -v "${candidate}" >/dev/null 2>&1; then
      command -v "${candidate}"
      return 0
    fi
    if [[ -x "${candidate}" ]]; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done

  return 1
}

prepend_wsl_windows_node_path

backend_wslenv() {
  local result="${WSLENV:-}"
  local entry
  for entry in \
    REMNAWAVE_TOKEN \
    JWT_SECRET \
    CRYPTOBOT_TOKEN \
    DATABASE_URL \
    REDIS_URL \
    CYBERVPN_TEST_POSTGRES_URL \
    CYBERVPN_TEST_REDIS_URL \
    SWAGGER_ENABLED \
    OAUTH_TOKEN_ENCRYPTION_KEY \
    TOTP_ENCRYPTION_KEY; do
    case ":${result}:" in
      *":${entry}:"*) ;;
      *) result="${result:+${result}:}${entry}" ;;
    esac
  done
  printf '%s\n' "${result}"
}

BACKEND_TEST_DB_NAME="${CYBERVPN_VERIFY_BACKEND_DB_NAME:-cybervpn_pytest_backend_clean}"

prepare_backend_test_database() {
  if [[ -n "${DATABASE_URL:-}" ]]; then
    return
  fi
  if [[ "${CYBERVPN_VERIFY_PREPARE_BACKEND_DB:-1}" != "1" ]]; then
    return
  fi
  if ! command -v docker >/dev/null 2>&1; then
    return
  fi
  if ! docker ps --format '{{.Names}}' | grep -qx remnawave-db; then
    return
  fi

  local postgres_user="${POSTGRES_USER:-postgres}"
  local redis_database="${CYBERVPN_VERIFY_REDIS_DB:-15}"
  local postgres_user_q db_name_q redis_database_q
  printf -v postgres_user_q '%q' "${postgres_user}"
  printf -v db_name_q '%q' "${BACKEND_TEST_DB_NAME}"
  printf -v redis_database_q '%q' "${redis_database}"

  run_gate "backend-prepare-test-database" bash -lc "
    set -Eeuo pipefail
    docker exec remnawave-db dropdb -U ${postgres_user_q} --if-exists ${db_name_q}
    docker exec remnawave-db createdb -U ${postgres_user_q} ${db_name_q}
    if docker ps --format '{{.Names}}' | grep -qx remnawave-redis; then
      docker exec remnawave-redis valkey-cli -n ${redis_database_q} FLUSHDB >/dev/null
    fi
  "

  if [[ -n "${BACKEND_PYTHON:-}" && -x "${BACKEND_PYTHON}" ]]; then
    local alembic_python alembic_python_q
    alembic_python="${BACKEND_PYTHON}"
    if [[ "${alembic_python}" != /* ]]; then
      alembic_python="../${alembic_python}"
    fi
    printf -v alembic_python_q '%q' "${alembic_python}"

    run_gate "backend-upgrade-test-database" "${backend_env[@]}" bash -lc "
      set -Eeuo pipefail
      cd backend
      ${alembic_python_q} -m alembic -c alembic.ini upgrade head
    "
  fi
}

run_gate() {
  local label="$1"
  shift
  local slug
  slug="$(slugify "${label}")"
  local log_file="${LOG_DIR}/${slug}.log"
  printf '\n\033[1;34m[RUN]\033[0m %s\n' "${label}"
  {
    printf 'COMMAND:'
    local arg key display_arg
    for arg in "$@"; do
      display_arg="${arg}"
      if [[ "${arg}" == *=* ]]; then
        key="${arg%%=*}"
        case "${key^^}" in
          *AUTH*|*COOKIE*|*CREDENTIAL*|*DATABASE_URL*|*DSN*|*KEY*|*PASSWORD*|*POSTGRES*|*PRIVATE*|*REDIS_URL*|*SECRET*|*SQL*|*TOKEN*|*TOTP*|*URL*)
            display_arg="${key}=[redacted]"
            ;;
        esac
      fi
      printf ' %q' "${display_arg}"
    done
    printf '\nSTARTED_AT: %s\n' "$(date -u +%FT%TZ)"
  } | tee "${log_file}"

  set +e
  "$@" 2>&1 | tee -a "${log_file}"
  local exit_code=${PIPESTATUS[0]}
  set -e

  printf 'FINISHED_AT: %s\nEXIT_CODE: %s\n' "$(date -u +%FT%TZ)" "${exit_code}" | tee -a "${log_file}"
  if [[ ${exit_code} -eq 0 ]]; then
    printf '\033[1;32m[PASS]\033[0m %s\n' "${label}"
    printf '%s\tpass\t0\t%s\n' "${label}" "${log_file#"${ROOT}"/}" >> "${RESULTS_FILE}"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    printf '\033[1;31m[FAIL]\033[0m %s (exit %s)\n' "${label}" "${exit_code}"
    printf '%s\tfail\t%s\t%s\n' "${label}" "${exit_code}" "${log_file#"${ROOT}"/}" >> "${RESULTS_FILE}"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

ensure_node_dependencies() {
  if ! NODE_BIN="$(find_node_bin)"; then
    printf 'Node.js is required for web verification, but neither node nor node.exe is available on PATH.\n' >&2
    FAIL_COUNT=$((FAIL_COUNT + 1))
    return 1
  fi
  if ! command -v npm >/dev/null 2>&1; then
    printf 'npm is required for web verification, but it is not available on PATH.\n' >&2
    FAIL_COUNT=$((FAIL_COUNT + 1))
    return 1
  fi
  if ! npm --version >/dev/null 2>&1; then
    printf 'npm is present but cannot run; ensure Node.js is available on PATH.\n' >&2
    FAIL_COUNT=$((FAIL_COUNT + 1))
    return 1
  fi

  if [[ "${AUTO_INSTALL}" == "1" && ! -d node_modules ]]; then
    run_gate "npm-ci-root" npm ci
  fi
}

ensure_cargo() {
  if ! CARGO_BIN="$(find_cargo_bin)"; then
    printf 'Rust cargo is required for Rust verification, but neither cargo nor cargo.exe is available on PATH.\n' >&2
    FAIL_COUNT=$((FAIL_COUNT + 1))
    return 1
  fi
}

verify_web_workspace() {
  local workspace="$1"
  ensure_node_dependencies || return
  if "${NODE_BIN}" -e "const p=require('./${workspace}/package.json'); process.exit(p.scripts?.['prepare:i18n']?0:1)" >/dev/null 2>&1; then
    run_gate "${workspace}-prepare-i18n" npm run prepare:i18n -w "${workspace}"
  fi
  run_gate "${workspace}-lint" npm run lint -w "${workspace}"
  run_gate "${workspace}-typecheck" "${NODE_BIN}" node_modules/typescript/bin/tsc --noEmit --project "${workspace}/tsconfig.json"
  run_gate "${workspace}-tests" npm run test:run -w "${workspace}"
  run_gate "${workspace}-build" env NEXT_TELEMETRY_DISABLED=1 npm run build -w "${workspace}"
}

find_backend_python() {
  local candidate
  for candidate in "${BACKEND_PYTHON_OVERRIDE:-}" backend/.venv/bin/python backend/.venv/Scripts/python.exe; do
    if [[ -n "${candidate}" && -x "${candidate}" ]] \
      && "${candidate}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 13) else 1)' >/dev/null 2>&1; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

ensure_backend_venv() {
  local recreate=1
  BACKEND_PYTHON=""
  if BACKEND_PYTHON="$(find_backend_python)"; then
    recreate=0
  fi

  if [[ ${recreate} -eq 1 ]]; then
    rm -rf backend/.venv
    if UV_BIN="$(find_uv_bin)"; then
      run_gate "backend-create-python313-venv" "${UV_BIN}" venv --python 3.13 backend/.venv
    elif command -v python3.13 >/dev/null 2>&1; then
      run_gate "backend-create-python313-venv" python3.13 -m venv backend/.venv
    else
      printf 'Python 3.13 is required. Run the pack bootstrap-wsl.sh or install uv.\n' >&2
      FAIL_COUNT=$((FAIL_COUNT + 1))
      return 1
    fi

    if ! BACKEND_PYTHON="$(find_backend_python)"; then
      printf 'Python 3.13 venv was created, but no executable was found under backend/.venv/bin/python or backend/.venv/Scripts/python.exe.\n' >&2
      FAIL_COUNT=$((FAIL_COUNT + 1))
      return 1
    fi
  fi

  if [[ "${AUTO_INSTALL}" == "1" ]]; then
    if ! "${BACKEND_PYTHON}" -m pip --version >/dev/null 2>&1; then
      run_gate "backend-bootstrap-pip" "${BACKEND_PYTHON}" -m ensurepip --upgrade
    fi
    run_gate "backend-install-dev-dependencies" "${BACKEND_PYTHON}" -m pip install -U pip
    run_gate "backend-install-project" "${BACKEND_PYTHON}" -m pip install -e 'backend[dev]' mypy
  fi
}

backend_env=(
  env
  "WSLENV=$(backend_wslenv)"
  "REMNAWAVE_TOKEN=${REMNAWAVE_TOKEN:-codex_local_remnawave_token}"
  "JWT_SECRET=${JWT_SECRET:-codex_local_jwt_secret_at_least_32_characters_long}"
  "CRYPTOBOT_TOKEN=${CRYPTOBOT_TOKEN:-codex_local_cryptobot_token}"
  # Match the host port published by infra/docker-compose.yml for local tests.
  "DATABASE_URL=${DATABASE_URL:-postgresql+asyncpg://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-local_dev_postgres}@127.0.0.1:6767/${BACKEND_TEST_DB_NAME}}"
  "REDIS_URL=${REDIS_URL:-redis://127.0.0.1:6379/15}"
  "CYBERVPN_TEST_POSTGRES_URL=${CYBERVPN_TEST_POSTGRES_URL:-postgresql+asyncpg://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-local_dev_postgres}@127.0.0.1:6767/${BACKEND_TEST_DB_NAME}}"
  "CYBERVPN_TEST_REDIS_URL=${CYBERVPN_TEST_REDIS_URL:-redis://127.0.0.1:6379/15}"
  "SWAGGER_ENABLED=${SWAGGER_ENABLED:-true}"
)

find_python_service_python() {
  local service_dir="$1"
  local candidate
  for candidate in "${service_dir}/.venv/bin/python" "${service_dir}/.venv/Scripts/python.exe"; do
    if [[ -x "${candidate}" ]] \
      && "${candidate}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 13) else 1)' >/dev/null 2>&1; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done
  return 1
}

ensure_python_service_venv() {
  local service_dir="$1"
  local label="$2"
  SERVICE_PYTHON=""

  if ! SERVICE_PYTHON="$(find_python_service_python "${service_dir}")"; then
    if UV_BIN="$(find_uv_bin)"; then
      run_gate "${label}-create-python313-venv" "${UV_BIN}" venv --python 3.13 "${service_dir}/.venv"
    elif command -v python3.13 >/dev/null 2>&1; then
      run_gate "${label}-create-python313-venv" python3.13 -m venv "${service_dir}/.venv"
    else
      printf 'Python 3.13 is required for %s. Install uv or python3.13.\n' "${label}" >&2
      FAIL_COUNT=$((FAIL_COUNT + 1))
      return 1
    fi

    if ! SERVICE_PYTHON="$(find_python_service_python "${service_dir}")"; then
      printf 'Python 3.13 venv was created for %s, but no executable was found.\n' "${label}" >&2
      FAIL_COUNT=$((FAIL_COUNT + 1))
      return 1
    fi
  fi

  if [[ "${AUTO_INSTALL}" == "1" ]]; then
    if ! "${SERVICE_PYTHON}" -m pip --version >/dev/null 2>&1; then
      run_gate "${label}-bootstrap-pip" "${SERVICE_PYTHON}" -m ensurepip --upgrade
    fi
    run_gate "${label}-install-dev-dependencies" "${SERVICE_PYTHON}" -m pip install -U pip
    run_gate "${label}-install-project" "${SERVICE_PYTHON}" -m pip install -e "${service_dir}[dev]"
  fi
}

verify_python_service_lock() {
  local service_dir="$1"
  local label="$2"

  if [[ -f "${service_dir}/uv.lock" ]]; then
    if UV_BIN="$(find_uv_bin)"; then
      local service_dir_q uv_bin_q
      printf -v service_dir_q '%q' "${service_dir}"
      printf -v uv_bin_q '%q' "${UV_BIN}"
      run_gate "${label}-uv-lock-check" bash -lc "cd ${service_dir_q} && ${uv_bin_q} lock --check"
    else
      printf 'uv is required to verify %s/uv.lock.\n' "${service_dir}" >&2
      printf '%s\tfail\t127\t\n' "${label}-uv-lock-check" >> "${RESULTS_FILE}"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
  fi
}

verify_python_service_base() {
  local service_dir="$1"
  local label="$2"

  verify_python_service_lock "${service_dir}" "${label}"
  ensure_python_service_venv "${service_dir}" "${label}"
  run_gate "${label}-ruff-check" "${SERVICE_PYTHON}" -m ruff check "${service_dir}"
  run_gate "${label}-ruff-format" "${SERVICE_PYTHON}" -m ruff format --check "${service_dir}"
}

python_in_service_cwd() {
  local service_dir="$1"
  local python_path="$2"

  if [[ "${python_path}" == "${service_dir}/"* ]]; then
    printf './%s\n' "${python_path#"${service_dir}/"}"
  else
    printf '%s\n' "${python_path}"
  fi
}

run_python_service_cwd_gate() {
  local service_dir="$1"
  local label="$2"
  shift 2

  local service_dir_q python_cmd python_cmd_q arg command
  printf -v service_dir_q '%q' "${service_dir}"
  python_cmd="$(python_in_service_cwd "${service_dir}" "${SERVICE_PYTHON}")"
  printf -v python_cmd_q '%q' "${python_cmd}"
  command="cd ${service_dir_q} && ${python_cmd_q}"
  for arg in "$@"; do
    local arg_q
    printf -v arg_q '%q' "${arg}"
    command+=" ${arg_q}"
  done

  run_gate "${label}" bash -lc "${command}"
}

# The repository is commonly edited from Windows and verified from WSL. Match
# Windows Git's CRLF normalization so historical CRLF files do not mask real
# whitespace errors in the current diff.
run_gate "git-diff-check" git -c core.autocrlf=true diff --check

ROOT_NODE_CHANGED=0
if changed_regex '^(package.json|package-lock.json)$'; then
  ROOT_NODE_CHANGED=1
fi

if scope_enabled web frontend && { changed_prefix frontend || [[ ${ROOT_NODE_CHANGED} -eq 1 ]]; }; then
  verify_web_workspace frontend
fi
if scope_enabled web admin && { changed_prefix admin || [[ ${ROOT_NODE_CHANGED} -eq 1 ]]; }; then
  verify_web_workspace admin
fi
if scope_enabled web partner && { changed_prefix partner || [[ ${ROOT_NODE_CHANGED} -eq 1 ]]; }; then
  verify_web_workspace partner
fi

if scope_enabled backend python && changed_prefix backend; then
  ensure_backend_venv
  run_gate "backend-ruff-check" "${BACKEND_PYTHON}" -m ruff check backend
  run_gate "backend-ruff-format" "${BACKEND_PYTHON}" -m ruff format --check backend
  run_gate "backend-mypy" "${BACKEND_PYTHON}" -m mypy backend/src --ignore-missing-imports --no-strict-optional
  prepare_backend_test_database
  run_gate "backend-pytest" "${backend_env[@]}" "${BACKEND_PYTHON}" -m pytest backend/tests -v --tb=short
fi

if scope_enabled web backend contract contracts generated && changed_regex '^(backend/(src/presentation|src/application/dto|docs/api/openapi.json)|frontend/src/lib/api/generated|admin/src/lib/api/generated|partner/src/lib/api/generated)'; then
  ensure_node_dependencies
  ensure_backend_venv
  prepare_backend_test_database
  if [[ -x scripts/run-partner-admin-conformance.sh ]]; then
    run_gate "partner-admin-conformance" "${backend_env[@]}" bash scripts/run-partner-admin-conformance.sh
  fi
fi

if scope_enabled mobile cybervpn_mobile && changed_prefix cybervpn_mobile; then
  run_gate "flutter-format" bash -lc 'cd cybervpn_mobile && dart format --output=none --set-exit-if-changed .'
  run_gate "flutter-analyze" bash -lc 'cd cybervpn_mobile && flutter analyze --fatal-warnings'
  run_gate "flutter-tests" bash -lc 'cd cybervpn_mobile && flutter test'
fi

if scope_enabled verta protocol packages/verta-protocol && changed_prefix packages/verta-protocol; then
  if ensure_cargo; then
    run_gate "verta-cargo-fmt" "${CARGO_BIN}" fmt --manifest-path packages/verta-protocol/Cargo.toml --all -- --check
    run_gate "verta-cargo-clippy" "${CARGO_BIN}" clippy --manifest-path packages/verta-protocol/Cargo.toml --workspace --all-targets --all-features -- -D warnings
    run_gate "verta-cargo-test" "${CARGO_BIN}" test --manifest-path packages/verta-protocol/Cargo.toml --workspace
  fi
fi

if scope_enabled services helix-node && changed_prefix services/helix-node; then
  if ensure_cargo; then
    run_gate "helix-node-fmt" "${CARGO_BIN}" fmt --manifest-path services/helix-node/Cargo.toml --all -- --check
    run_gate "helix-node-clippy" "${CARGO_BIN}" clippy --manifest-path services/helix-node/Cargo.toml --all-targets --all-features -- -D warnings
    run_gate "helix-node-test" "${CARGO_BIN}" test --manifest-path services/helix-node/Cargo.toml
  fi
fi

if scope_enabled services helix-adapter && changed_prefix services/helix-adapter; then
  if ensure_cargo; then
    run_gate "helix-adapter-fmt" "${CARGO_BIN}" fmt --manifest-path services/helix-adapter/Cargo.toml --all -- --check
    run_gate "helix-adapter-clippy" "${CARGO_BIN}" clippy --manifest-path services/helix-adapter/Cargo.toml --all-targets --all-features -- -D warnings
    run_gate "helix-adapter-test" "${CARGO_BIN}" test --manifest-path services/helix-adapter/Cargo.toml
  fi
fi

if scope_enabled services node-fleet-controller && changed_prefix services/node-fleet-controller; then
  verify_python_service_base services/node-fleet-controller node-fleet-controller
  run_python_service_cwd_gate services/node-fleet-controller "node-fleet-controller-pytest" -m pytest tests -v --tb=short
fi

if scope_enabled services task-worker && changed_prefix services/task-worker; then
  verify_python_service_base services/task-worker task-worker
  run_python_service_cwd_gate services/task-worker "task-worker-mypy" -m mypy src --ignore-missing-imports --no-strict-optional
  run_python_service_cwd_gate services/task-worker "task-worker-pytest" -m pytest tests -v --tb=short
fi

if scope_enabled services telegram-bot && changed_prefix services/telegram-bot; then
  verify_python_service_base services/telegram-bot telegram-bot
  run_python_service_cwd_gate services/telegram-bot "telegram-bot-mypy" -m mypy src
  run_python_service_cwd_gate services/telegram-bot "telegram-bot-pytest" -m pytest tests -v --tb=short
fi

if scope_enabled services vpn-test-agent && changed_prefix services/vpn-test-agent; then
  verify_python_service_base services/vpn-test-agent vpn-test-agent
  run_python_service_cwd_gate services/vpn-test-agent "vpn-test-agent-compileall" -m compileall -q src
fi

if scope_enabled desktop apps/desktop-client && changed_prefix apps/desktop-client; then
  ensure_node_dependencies
  if [[ -f apps/desktop-client/package.json ]]; then
    run_gate "desktop-frontend-lint" npm run lint -w apps/desktop-client
    run_gate "desktop-frontend-test" npm run test -w apps/desktop-client
    run_gate "desktop-frontend-build" npm run build -w apps/desktop-client
  fi
  if [[ -f apps/desktop-client/src-tauri/Cargo.toml ]]; then
    if ensure_cargo; then
      run_gate "desktop-rust-fmt" "${CARGO_BIN}" fmt --manifest-path apps/desktop-client/src-tauri/Cargo.toml --all -- --check
      run_gate "desktop-rust-clippy" "${CARGO_BIN}" clippy --manifest-path apps/desktop-client/src-tauri/Cargo.toml --all-targets --all-features -- -D warnings
      run_gate "desktop-rust-test" "${CARGO_BIN}" test --manifest-path apps/desktop-client/src-tauri/Cargo.toml
    fi
  fi
fi

mapfile -t CHANGED_SHELL < <(printf '%s\n' "${CHANGED[@]:-}" | grep -E '\.sh$' || true)
if scope_enabled release testing scripts infra services backend web && [[ ${#CHANGED_SHELL[@]} -gt 0 ]]; then
  if command -v shellcheck >/dev/null 2>&1; then
    run_gate "shellcheck" shellcheck "${CHANGED_SHELL[@]}"
  else
    printf 'shellcheck\tmissing\t127\t\n' >> "${RESULTS_FILE}"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

if scope_enabled infra && changed_prefix infra && command -v docker >/dev/null 2>&1; then
  if [[ -f infra/docker-compose.yml ]]; then
    run_gate "docker-compose-config" docker compose -f infra/docker-compose.yml config --quiet
  elif [[ -f infra/compose.yml ]]; then
    run_gate "docker-compose-config" docker compose -f infra/compose.yml config --quiet
  fi
fi

python3 - "${RESULTS_FILE}" "${LOG_DIR}/summary.json" "${BASE_REF}" "${PASS_COUNT}" "${FAIL_COUNT}" <<'PY'
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

results_file, summary_file, base_ref, passes, failures = sys.argv[1:]
results = []
for line in Path(results_file).read_text(encoding="utf-8").splitlines():
    label, status, exit_code, evidence = (line.split("\t") + ["", "", "", ""])[:4]
    results.append(
        {
            "command_label": label,
            "status": status,
            "exit_code": int(exit_code) if exit_code.lstrip("-").isdigit() else None,
            "evidence": evidence,
        }
    )
summary = {
    "created_at": datetime.now(UTC).isoformat(),
    "base_ref": base_ref,
    "pass_count": int(passes),
    "fail_count": int(failures),
    "results": results,
}
Path(summary_file).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

ln -sfn "${LOG_DIR}" "${ROOT}/.codex/command-logs/latest"
printf '\nVerification logs: %s\n' "${LOG_DIR#"${ROOT}"/}"
printf 'Passed: %s; Failed: %s\n' "${PASS_COUNT}" "${FAIL_COUNT}"

if [[ ${FAIL_COUNT} -ne 0 ]]; then
  exit 1
fi
