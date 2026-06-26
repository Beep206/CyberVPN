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
BASE_REF="${1:-}"
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

changed_prefix() {
  local prefix="$1"
  printf '%s\n' "${CHANGED[@]:-}" | grep -Eq "^${prefix}(/|$)"
}

changed_regex() {
  local regex="$1"
  printf '%s\n' "${CHANGED[@]:-}" | grep -Eq "${regex}"
}

slugify() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9._-]+/-/g; s/^-+|-+$//g'
}

PASS_COUNT=0
FAIL_COUNT=0

run_gate() {
  local label="$1"
  shift
  local slug
  slug="$(slugify "${label}")"
  local log_file="${LOG_DIR}/${slug}.log"
  printf '\n\033[1;34m[RUN]\033[0m %s\n' "${label}"
  printf 'COMMAND:' | tee "${log_file}"
  printf ' %q' "$@" | tee -a "${log_file}"
  printf '\nSTARTED_AT: %s\n' "$(date -u +%FT%TZ)" | tee -a "${log_file}"

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
  if [[ "${AUTO_INSTALL}" == "1" && ! -d node_modules ]]; then
    run_gate "npm-ci-root" npm ci
  fi
}

verify_web_workspace() {
  local workspace="$1"
  ensure_node_dependencies
  if node -e "const p=require('./${workspace}/package.json'); process.exit(p.scripts?.['prepare:i18n']?0:1)" >/dev/null 2>&1; then
    run_gate "${workspace}-prepare-i18n" npm run prepare:i18n -w "${workspace}"
  fi
  run_gate "${workspace}-lint" npm run lint -w "${workspace}"
  run_gate "${workspace}-typecheck" npm exec -w "${workspace}" -- tsc --noEmit
  run_gate "${workspace}-tests" npm run test:run -w "${workspace}"
  run_gate "${workspace}-build" env NEXT_TELEMETRY_DISABLED=1 npm run build -w "${workspace}"
}

ensure_backend_venv() {
  local recreate=0
  if [[ ! -x backend/.venv/bin/python ]]; then
    recreate=1
  elif ! backend/.venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 13) else 1)' >/dev/null 2>&1; then
    recreate=1
  fi

  if [[ ${recreate} -eq 1 ]]; then
    rm -rf backend/.venv
    if command -v uv >/dev/null 2>&1; then
      run_gate "backend-create-python313-venv" uv venv --python 3.13 backend/.venv
    elif command -v python3.13 >/dev/null 2>&1; then
      run_gate "backend-create-python313-venv" python3.13 -m venv backend/.venv
    else
      printf 'Python 3.13 is required. Run the pack bootstrap-wsl.sh or install uv.\n' >&2
      FAIL_COUNT=$((FAIL_COUNT + 1))
      return 1
    fi
  fi

  if [[ "${AUTO_INSTALL}" == "1" ]]; then
    run_gate "backend-install-dev-dependencies" backend/.venv/bin/python -m pip install -U pip
    run_gate "backend-install-project" backend/.venv/bin/python -m pip install -e 'backend[dev]' mypy
  fi
}

backend_env=(
  env
  "REMNAWAVE_TOKEN=${REMNAWAVE_TOKEN:-codex_local_remnawave_token}"
  "JWT_SECRET=${JWT_SECRET:-codex_local_jwt_secret_at_least_32_characters_long}"
  "CRYPTOBOT_TOKEN=${CRYPTOBOT_TOKEN:-codex_local_cryptobot_token}"
  "DATABASE_URL=${DATABASE_URL:-postgresql+asyncpg://test:test@127.0.0.1:5432/cybervpn_test}"
  "REDIS_URL=${REDIS_URL:-redis://127.0.0.1:6379/15}"
  "SWAGGER_ENABLED=${SWAGGER_ENABLED:-true}"
)

run_gate "git-diff-check" git diff --check

ROOT_NODE_CHANGED=0
if changed_regex '^(package.json|package-lock.json)$'; then
  ROOT_NODE_CHANGED=1
fi

if changed_prefix frontend || [[ ${ROOT_NODE_CHANGED} -eq 1 ]]; then
  verify_web_workspace frontend
fi
if changed_prefix admin || [[ ${ROOT_NODE_CHANGED} -eq 1 ]]; then
  verify_web_workspace admin
fi
if changed_prefix partner || [[ ${ROOT_NODE_CHANGED} -eq 1 ]]; then
  verify_web_workspace partner
fi

if changed_prefix backend; then
  ensure_backend_venv
  run_gate "backend-ruff-check" backend/.venv/bin/python -m ruff check backend
  run_gate "backend-ruff-format" backend/.venv/bin/python -m ruff format --check backend
  run_gate "backend-mypy" bash -lc 'cd backend && .venv/bin/python -m mypy src --ignore-missing-imports --no-strict-optional'
  run_gate "backend-pytest" "${backend_env[@]}" backend/.venv/bin/python -m pytest backend/tests -v --tb=short
fi

if changed_regex '^(backend/(src/presentation|src/application/dto|docs/api/openapi.json)|frontend/src/lib/api/generated|admin/src/lib/api/generated|partner/src/lib/api/generated)'; then
  ensure_node_dependencies
  ensure_backend_venv
  if [[ -x scripts/run-partner-admin-conformance.sh ]]; then
    run_gate "partner-admin-conformance" "${backend_env[@]}" bash scripts/run-partner-admin-conformance.sh
  fi
fi

if changed_prefix cybervpn_mobile; then
  run_gate "flutter-format" bash -lc 'cd cybervpn_mobile && dart format --output=none --set-exit-if-changed .'
  run_gate "flutter-analyze" bash -lc 'cd cybervpn_mobile && flutter analyze --fatal-warnings'
  run_gate "flutter-tests" bash -lc 'cd cybervpn_mobile && flutter test'
fi

if changed_prefix packages/verta-protocol; then
  run_gate "verta-cargo-fmt" cargo fmt --manifest-path packages/verta-protocol/Cargo.toml --all -- --check
  run_gate "verta-cargo-clippy" cargo clippy --manifest-path packages/verta-protocol/Cargo.toml --workspace --all-targets --all-features -- -D warnings
  run_gate "verta-cargo-test" cargo test --manifest-path packages/verta-protocol/Cargo.toml --workspace
fi

if changed_prefix services/helix-node; then
  run_gate "helix-node-fmt" cargo fmt --manifest-path services/helix-node/Cargo.toml --all -- --check
  run_gate "helix-node-clippy" cargo clippy --manifest-path services/helix-node/Cargo.toml --all-targets --all-features -- -D warnings
  run_gate "helix-node-test" cargo test --manifest-path services/helix-node/Cargo.toml
fi

if changed_prefix services/helix-adapter; then
  run_gate "helix-adapter-fmt" cargo fmt --manifest-path services/helix-adapter/Cargo.toml --all -- --check
  run_gate "helix-adapter-clippy" cargo clippy --manifest-path services/helix-adapter/Cargo.toml --all-targets --all-features -- -D warnings
  run_gate "helix-adapter-test" cargo test --manifest-path services/helix-adapter/Cargo.toml
fi

if changed_prefix apps/desktop-client; then
  ensure_node_dependencies
  if [[ -f apps/desktop-client/package.json ]]; then
    run_gate "desktop-frontend-lint" npm run lint -w apps/desktop-client
    run_gate "desktop-frontend-test" npm run test -w apps/desktop-client
    run_gate "desktop-frontend-build" npm run build -w apps/desktop-client
  fi
  if [[ -f apps/desktop-client/src-tauri/Cargo.toml ]]; then
    run_gate "desktop-rust-fmt" cargo fmt --manifest-path apps/desktop-client/src-tauri/Cargo.toml --all -- --check
    run_gate "desktop-rust-clippy" cargo clippy --manifest-path apps/desktop-client/src-tauri/Cargo.toml --all-targets --all-features -- -D warnings
    run_gate "desktop-rust-test" cargo test --manifest-path apps/desktop-client/src-tauri/Cargo.toml
  fi
fi

mapfile -t CHANGED_SHELL < <(printf '%s\n' "${CHANGED[@]:-}" | grep -E '\.sh$' || true)
if [[ ${#CHANGED_SHELL[@]} -gt 0 ]]; then
  if command -v shellcheck >/dev/null 2>&1; then
    run_gate "shellcheck" shellcheck "${CHANGED_SHELL[@]}"
  else
    printf 'shellcheck\tmissing\t127\t\n' >> "${RESULTS_FILE}"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

if changed_prefix infra && command -v docker >/dev/null 2>&1; then
  if [[ -f infra/docker-compose.yml ]]; then
    run_gate "docker-compose-config" docker compose -f infra/docker-compose.yml config
  elif [[ -f infra/compose.yml ]]; then
    run_gate "docker-compose-config" docker compose -f infra/compose.yml config
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
