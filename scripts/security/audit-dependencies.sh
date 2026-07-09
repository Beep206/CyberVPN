#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
ARTIFACT_DIR="${SECURITY_ARTIFACT_DIR:-${ROOT_DIR}/security-artifacts}"
SCOPE="${PHASE20_DEPENDENCY_SCOPE:-${1:-all}}"
mkdir -p "${ARTIFACT_DIR}/npm" "${ARTIFACT_DIR}/python"

run_npm() {
  if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
    npm "$@"
    return
  fi

  if command -v cmd.exe >/dev/null 2>&1; then
    cmd.exe /D /C npm.cmd "$@"
    return
  fi

  npm "$@"
}

run_npm_audit() {
  cd "${ROOT_DIR}"
  local failed=0
  local project safe json text rc
  local -a audit_args

  for project in . admin frontend partner; do
    if [[ "${project}" == "." ]]; then
      if [[ ! -f "${ROOT_DIR}/package.json" || ! -f "${ROOT_DIR}/package-lock.json" ]]; then
        continue
      fi
    elif [[ ! -f "${ROOT_DIR}/${project}/package.json" ]]; then
      continue
    fi

    if [[ "${project}" == "." ]]; then
      safe="root"
      audit_args=(--workspaces --audit-level=high)
    else
      safe="${project#./}"
      audit_args=(--workspace "${project}" --audit-level=high)
    fi
    safe="${safe//\//__}"
    json="${ARTIFACT_DIR}/npm/${safe}.npm-audit-high.json"
    text="${ARTIFACT_DIR}/npm/${safe}.npm-audit-high.txt"

    rc=0
    (
      cd "${ROOT_DIR}"
      run_npm audit "${audit_args[@]}" --json > "${json}"
    ) || rc=$?
    (
      cd "${ROOT_DIR}"
      run_npm audit "${audit_args[@]}" > "${text}" 2>&1
    ) || true
    printf 'exit_code=%s\n' "${rc}" >> "${text}"
    if [[ "${rc}" -ne 0 ]]; then
      failed=1
    fi
  done

  return "${failed}"
}

run_python_audit() {
  cd "${ROOT_DIR}"
  local failed=0
  local project safe req json text rc

  for project in backend services/telegram-bot services/task-worker services/node-fleet-controller services/vpn-test-agent; do
    safe="${project//\//__}"
    safe="${safe//-/_}"
    req="${ARTIFACT_DIR}/python/${safe}.requirements.txt"
    json="${ARTIFACT_DIR}/python/${safe}.pip-audit.json"
    text="${ARTIFACT_DIR}/python/${safe}.pip-audit.txt"

    (
      cd "${ROOT_DIR}/${project}"
      uv export \
        --frozen \
        --no-dev \
        --no-emit-project \
        --no-hashes \
        --format requirements.txt \
        --output-file "${req}" >/dev/null
    )

    rc=0
    pip-audit --progress-spinner off --no-deps --disable-pip --format json --output "${json}" --requirement "${req}" || rc=$?
    pip-audit --progress-spinner off --no-deps --disable-pip --requirement "${req}" > "${text}" 2>&1 || true
    printf 'exit_code=%s\n' "${rc}" >> "${text}"
    if [[ "${rc}" -ne 0 ]]; then
      failed=1
    fi
  done

  return "${failed}"
}

case "${SCOPE}" in
  npm)
    run_npm_audit
    ;;
  python)
    run_python_audit
    ;;
  all)
    npm_rc=0
    python_rc=0
    run_npm_audit || npm_rc=$?
    run_python_audit || python_rc=$?
    if [[ "${npm_rc}" -ne 0 || "${python_rc}" -ne 0 ]]; then
      exit 1
    fi
    ;;
  *)
    echo "ERROR: unknown scope '${SCOPE}', expected npm, python, or all" >&2
    exit 2
    ;;
esac
