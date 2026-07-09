#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
ARTIFACT_DIR="${SECURITY_ARTIFACT_DIR:-${ROOT_DIR}/security-artifacts}"
TRIVY_IMAGE="${TRIVY_IMAGE:-aquasec/trivy:0.72.0}"
TRIVY_EXIT_CODE="${TRIVY_EXIT_CODE:-1}"
TRIVY_SEVERITY="${TRIVY_SEVERITY:-HIGH,CRITICAL}"
GRYPE_IMAGE="${GRYPE_IMAGE:-anchore/grype:v0.115.0}"
GRYPE_SCAN_ATTEMPTS="${GRYPE_SCAN_ATTEMPTS:-2}"
GRYPE_SCAN_TIMEOUT_SECONDS="${GRYPE_SCAN_TIMEOUT_SECONDS:-300}"
GRYPE_DB_CACHE_DIR="${GRYPE_DB_CACHE_DIR:-${ROOT_DIR}/.cache/grype-db}"
GRYPE_DB_REQUIRE_UPDATE_CHECK="${GRYPE_DB_REQUIRE_UPDATE_CHECK:-false}"
GRYPE_DB_UPDATE_DOWNLOAD_TIMEOUT="${GRYPE_DB_UPDATE_DOWNLOAD_TIMEOUT:-10m0s}"
GRYPE_FAIL_SEVERITY="${GRYPE_FAIL_SEVERITY:-high}"
PHASE20_GRYPE_REQUIRED="${PHASE20_GRYPE_REQUIRED:-true}"
SECURITY_SCAN_SCOPE="${SECURITY_SCAN_SCOPE:-phase20}"

mkdir -p "${ARTIFACT_DIR}/container" "${GRYPE_DB_CACHE_DIR}"

SNAPSHOT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/cybervpn-security-scan-source.XXXXXX")"
FILE_LIST="$(mktemp "${TMPDIR:-/tmp}/cybervpn-security-scan-files.XXXXXX")"

cleanup() {
  rm -rf "${SNAPSHOT_DIR}" "${FILE_LIST}"
}
trap cleanup EXIT

is_artifact_path() {
  case "$1" in
    .codex/*|.playwright-cli/*|.tmp/*|docs/evidence/*|evidence/*|qa-artifacts/*|security-artifacts/*)
      return 0
      ;;
  esac
  return 1
}

is_phase20_path() {
  case "$1" in
    .github/*|.gitattributes|.gitignore|.gitlab-ci.yml|.node-version|package.json|package-lock.json|admin/*|backend/*|charts/*|frontend/*|infra/*|partner/*|scripts/*|services/*)
      return 0
      ;;
  esac
  return 1
}

is_in_scope_path() {
  case "${SECURITY_SCAN_SCOPE}" in
    repository|repo|all)
      return 0
      ;;
    phase20|current|task)
      is_phase20_path "$1"
      return
      ;;
    *)
      echo "ERROR: unsupported SECURITY_SCAN_SCOPE=${SECURITY_SCAN_SCOPE}; use phase20 or repository" >&2
      exit 2
      ;;
  esac
}

write_scope_metadata() {
  cat > "${ARTIFACT_DIR}/container/security-scan.scope.txt" <<EOF
scope=${SECURITY_SCAN_SCOPE}
default_scope=phase20
phase20_roots=.github,.gitlab-ci.yml,.node-version,package.json,package-lock.json,admin,backend,charts,frontend,infra,partner,scripts,services
repository_scope_hint=run with SECURITY_SCAN_SCOPE=repository for all tracked and unignored files outside local artifact/cache directories
excluded_artifact_roots=.codex,.playwright-cli,.tmp,docs/evidence,evidence,qa-artifacts,security-artifacts
EOF
}

build_file_list() {
  (
    cd "${ROOT_DIR}"
    git ls-files -z
    git ls-files --others --exclude-standard -z
  ) | while IFS= read -r -d '' rel_path; do
    if is_artifact_path "${rel_path}" || ! is_in_scope_path "${rel_path}"; then
      continue
    fi

    if [[ -e "${ROOT_DIR}/${rel_path}" || -L "${ROOT_DIR}/${rel_path}" ]]; then
      printf '%s\0' "${rel_path}"
    fi
  done > "${FILE_LIST}"
}

write_scope_metadata
build_file_list
tar --null -C "${ROOT_DIR}" -T "${FILE_LIST}" -cf - | tar -C "${SNAPSHOT_DIR}" -xf -

run_trivy_fs() {
  if command -v trivy >/dev/null 2>&1; then
    trivy fs \
      --scanners vuln,misconfig \
      --severity "${TRIVY_SEVERITY}" \
      --exit-code "${TRIVY_EXIT_CODE}" \
      --skip-dirs '**/.git' \
      --skip-dirs '**/node_modules' \
      --skip-dirs '**/node_modules/**' \
      --skip-dirs '**/.tmp' \
      --skip-dirs '**/.tmp/**' \
      --skip-dirs '**/.cache' \
      --skip-dirs '**/.cache/**' \
      --skip-dirs '**/.codex' \
      --skip-dirs '**/.codex/**' \
      --skip-dirs '**/.playwright-cli' \
      --skip-dirs '**/.playwright-cli/**' \
      --skip-dirs '**/.terraform' \
      --skip-dirs '**/.terraform/**' \
      --skip-dirs '**/.venv' \
      --skip-dirs '**/.venv/**' \
      --skip-dirs '**/build' \
      --skip-dirs '**/build/**' \
      --skip-dirs '**/dist' \
      --skip-dirs '**/dist/**' \
      --skip-dirs '**/target' \
      --skip-dirs '**/target/**' \
      --skip-dirs '**/coverage' \
      --skip-dirs '**/coverage/**' \
      --skip-dirs '**/docs/evidence' \
      --skip-dirs '**/docs/evidence/**' \
      --skip-dirs '**/evidence' \
      --skip-dirs '**/evidence/**' \
      --skip-dirs '**/qa-artifacts' \
      --skip-dirs '**/qa-artifacts/**' \
      --skip-dirs '**/security-artifacts' \
      --skip-dirs '**/security-artifacts/**' \
      --skip-dirs '**/.gradle' \
      --skip-dirs '**/.gradle/**' \
      --skip-dirs '**/apps/android-tv/app/build' \
      --skip-dirs '**/cybervpn_mobile/.dart_tool' \
      --skip-dirs '**/frontend/.next' \
      --skip-dirs '**/admin/.next' \
      --skip-dirs '**/partner/.next' \
      --format json \
      --output "${ARTIFACT_DIR}/container/trivy-fs.json" \
      "${SNAPSHOT_DIR}"
  else
    docker run --rm \
      -v "${SNAPSHOT_DIR}:/repo:ro" \
      -v "${ARTIFACT_DIR}/container:/out" \
      "${TRIVY_IMAGE}" \
      fs \
      --scanners vuln,misconfig \
      --severity "${TRIVY_SEVERITY}" \
      --exit-code "${TRIVY_EXIT_CODE}" \
      --skip-dirs '**/.git' \
      --skip-dirs '**/node_modules' \
      --skip-dirs '**/node_modules/**' \
      --skip-dirs '**/.tmp' \
      --skip-dirs '**/.tmp/**' \
      --skip-dirs '**/.cache' \
      --skip-dirs '**/.cache/**' \
      --skip-dirs '**/.codex' \
      --skip-dirs '**/.codex/**' \
      --skip-dirs '**/.playwright-cli' \
      --skip-dirs '**/.playwright-cli/**' \
      --skip-dirs '**/.terraform' \
      --skip-dirs '**/.terraform/**' \
      --skip-dirs '**/.venv' \
      --skip-dirs '**/.venv/**' \
      --skip-dirs '**/build' \
      --skip-dirs '**/build/**' \
      --skip-dirs '**/dist' \
      --skip-dirs '**/dist/**' \
      --skip-dirs '**/target' \
      --skip-dirs '**/target/**' \
      --skip-dirs '**/coverage' \
      --skip-dirs '**/coverage/**' \
      --skip-dirs '**/docs/evidence' \
      --skip-dirs '**/docs/evidence/**' \
      --skip-dirs '**/evidence' \
      --skip-dirs '**/evidence/**' \
      --skip-dirs '**/qa-artifacts' \
      --skip-dirs '**/qa-artifacts/**' \
      --skip-dirs '**/security-artifacts' \
      --skip-dirs '**/security-artifacts/**' \
      --skip-dirs '**/.gradle' \
      --skip-dirs '**/.gradle/**' \
      --skip-dirs '**/apps/android-tv/app/build' \
      --skip-dirs '**/cybervpn_mobile/.dart_tool' \
      --skip-dirs '**/frontend/.next' \
      --skip-dirs '**/admin/.next' \
      --skip-dirs '**/partner/.next' \
      --format json \
      --output /out/trivy-fs.json \
      /repo
  fi
}

grype_blocking_severities_json() {
  case "$(printf '%s' "${GRYPE_FAIL_SEVERITY}" | tr '[:upper:]' '[:lower:]')" in
    none|off|disabled)
      printf '[]'
      ;;
    critical)
      printf '["Critical"]'
      ;;
    high)
      printf '["Critical","High"]'
      ;;
    medium)
      printf '["Critical","High","Medium"]'
      ;;
    low)
      printf '["Critical","High","Medium","Low"]'
      ;;
    negligible)
      printf '["Critical","High","Medium","Low","Negligible"]'
      ;;
    *)
      echo "ERROR: unsupported GRYPE_FAIL_SEVERITY=${GRYPE_FAIL_SEVERITY}; use critical, high, medium, low, negligible, or none" >&2
      return 2
      ;;
  esac
}

write_grype_severity_status() {
  local grype_json="${ARTIFACT_DIR}/container/grype-dir.json"
  local status_file="${ARTIFACT_DIR}/container/grype-dir.status.txt"
  local summary_tmp="${ARTIFACT_DIR}/container/grype-dir.status.tmp"
  local blocking_severities
  blocking_severities="$(grype_blocking_severities_json)"

  if command -v jq >/dev/null 2>&1; then
    jq -r --argjson severities "${blocking_severities}" '
      [
        (.matches // [])[]
        | {
            severity: (.vulnerability.severity // "Unknown"),
            id: (.vulnerability.id // "unknown"),
            package: (.artifact.name // "unknown"),
            version: (.artifact.version // "unknown"),
            locations: ([.artifact.locations[]?.path] | .[0:3])
          }
        | select(.severity as $severity | $severities | index($severity))
      ] as $hits
      | [
          "blocking_count=\($hits | length)",
          "blocking_summary=\($hits | group_by(.severity) | map("\(.[0].severity)=\(length)") | join(","))",
          "blocking_findings=\($hits[0:20] | map("\(.severity) \(.id) \(.package)@\(.version) \((.locations | join(";")))") | join(" | "))"
        ]
      | .[]
    ' "${grype_json}" > "${summary_tmp}"
  elif command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1; then
    local py_bin="python3"
    if ! command -v python3 >/dev/null 2>&1; then
      py_bin="python"
    fi
    "${py_bin}" - "${grype_json}" "${blocking_severities}" > "${summary_tmp}" <<'PY'
import json
import sys

path = sys.argv[1]
severities = set(json.loads(sys.argv[2]))
with open(path, "r", encoding="utf-8") as handle:
    report = json.load(handle)

hits = []
for match in report.get("matches") or []:
    vulnerability = match.get("vulnerability") or {}
    artifact = match.get("artifact") or {}
    severity = vulnerability.get("severity") or "Unknown"
    if severity not in severities:
        continue
    locations = [
        (location or {}).get("path", "")
        for location in (artifact.get("locations") or [])
    ][:3]
    hits.append(
        {
            "severity": severity,
            "id": vulnerability.get("id") or "unknown",
            "package": artifact.get("name") or "unknown",
            "version": artifact.get("version") or "unknown",
            "locations": locations,
        }
    )

summary = {}
for hit in hits:
    summary[hit["severity"]] = summary.get(hit["severity"], 0) + 1

print(f"blocking_count={len(hits)}")
print("blocking_summary=" + ",".join(f"{key}={summary[key]}" for key in sorted(summary)))
print(
    "blocking_findings="
    + " | ".join(
        f"{hit['severity']} {hit['id']} {hit['package']}@{hit['version']} {';'.join(hit['locations'])}"
        for hit in hits[:20]
    )
)
PY
  else
    echo "ERROR: jq, python3, or python is required to summarize Grype severity output" >&2
    return 2
  fi

  local blocking_count
  blocking_count="$(sed -n 's/^blocking_count=//p' "${summary_tmp}" | head -n 1)"
  {
    if [[ "${blocking_count}" == "0" ]]; then
      printf 'status=pass\n'
    else
      printf 'status=blocking\n'
    fi
    printf 'scanner=grype\n'
    printf 'fail_severity=%s\n' "${GRYPE_FAIL_SEVERITY}"
    cat "${summary_tmp}"
  } > "${status_file}"
  rm -f "${summary_tmp}"

  if [[ "${blocking_count}" != "0" ]]; then
    echo "ERROR: grype found ${blocking_count} vulnerabilities at or above ${GRYPE_FAIL_SEVERITY}" >&2
    return 1
  fi
}

run_grype_dir() {
  local output_tmp="${ARTIFACT_DIR}/container/grype-dir.json.tmp"
  local grype_log="${ARTIFACT_DIR}/container/grype-dir.stderr.log"
  rm -f "${output_tmp}"
  rm -f "${grype_log}"

  if command -v grype >/dev/null 2>&1; then
    for attempt in $(seq 1 "${GRYPE_SCAN_ATTEMPTS}"); do
      if GRYPE_DB_CACHE_DIR="${GRYPE_DB_CACHE_DIR}" \
        GRYPE_DB_REQUIRE_UPDATE_CHECK="${GRYPE_DB_REQUIRE_UPDATE_CHECK}" \
        GRYPE_DB_UPDATE_DOWNLOAD_TIMEOUT="${GRYPE_DB_UPDATE_DOWNLOAD_TIMEOUT}" \
        timeout "${GRYPE_SCAN_TIMEOUT_SECONDS}s" grype dir:"${SNAPSHOT_DIR}" \
        --exclude '**/.git/**' \
        --exclude '**/node_modules/**' \
        --exclude '**/.tmp/**' \
        --exclude '**/.cache/**' \
        --exclude '**/.codex/**' \
        --exclude '**/.playwright-cli/**' \
        --exclude '**/.terraform/**' \
        --exclude '**/.venv/**' \
        --exclude '**/build/**' \
        --exclude '**/dist/**' \
        --exclude '**/target/**' \
        --exclude '**/coverage/**' \
        --exclude '**/docs/evidence/**' \
        --exclude '**/evidence/**' \
        --exclude '**/qa-artifacts/**' \
        --exclude '**/security-artifacts/**' \
        --exclude '**/.gradle/**' \
        --exclude '**/apps/android-tv/app/build/**' \
        --exclude '**/cybervpn_mobile/.dart_tool/**' \
        --exclude '**/frontend/.next/**' \
        --exclude '**/admin/.next/**' \
        --exclude '**/partner/.next/**' \
        -o json > "${output_tmp}" 2>> "${grype_log}"; then
        mv "${output_tmp}" "${ARTIFACT_DIR}/container/grype-dir.json"
        write_grype_severity_status
        return
      fi
      sleep "$((attempt * 5))"
    done
  else
    for attempt in $(seq 1 "${GRYPE_SCAN_ATTEMPTS}"); do
      if timeout "${GRYPE_SCAN_TIMEOUT_SECONDS}s" docker run --rm \
        -e GRYPE_DB_CACHE_DIR=/grype-db \
        -e GRYPE_DB_REQUIRE_UPDATE_CHECK="${GRYPE_DB_REQUIRE_UPDATE_CHECK}" \
        -e GRYPE_DB_UPDATE_DOWNLOAD_TIMEOUT="${GRYPE_DB_UPDATE_DOWNLOAD_TIMEOUT}" \
        -v "${GRYPE_DB_CACHE_DIR}:/grype-db" \
        -v "${SNAPSHOT_DIR}:/repo:ro" \
        "${GRYPE_IMAGE}" \
        dir:/repo \
        --exclude '**/.git/**' \
        --exclude '**/node_modules/**' \
        --exclude '**/.tmp/**' \
        --exclude '**/.cache/**' \
        --exclude '**/.codex/**' \
        --exclude '**/.playwright-cli/**' \
        --exclude '**/.terraform/**' \
        --exclude '**/.venv/**' \
        --exclude '**/build/**' \
        --exclude '**/dist/**' \
        --exclude '**/target/**' \
        --exclude '**/coverage/**' \
        --exclude '**/docs/evidence/**' \
        --exclude '**/evidence/**' \
        --exclude '**/qa-artifacts/**' \
        --exclude '**/security-artifacts/**' \
        --exclude '**/.gradle/**' \
        --exclude '**/apps/android-tv/app/build/**' \
        --exclude '**/cybervpn_mobile/.dart_tool/**' \
        --exclude '**/frontend/.next/**' \
        --exclude '**/admin/.next/**' \
        --exclude '**/partner/.next/**' \
        -o json > "${output_tmp}" 2>> "${grype_log}"; then
        mv "${output_tmp}" "${ARTIFACT_DIR}/container/grype-dir.json"
        write_grype_severity_status
        return
      fi
      sleep "$((attempt * 5))"
    done
  fi

  rm -f "${output_tmp}"
  cat > "${ARTIFACT_DIR}/container/grype-dir.json" <<'EOF'
{"status":"error","scanner":"grype","message":"grype scan failed after retries; see CI job log"}
EOF
  local grype_last_error=""
  if [[ -f "${grype_log}" ]]; then
    grype_last_error="$(tail -n 20 "${grype_log}" | tr '\n' ' ' | sed 's/[[:space:]]\+/ /g; s/^ //; s/ $//')"
  fi
  printf 'status=error\nscanner=grype\nmessage=grype scan failed after retries; see CI job log\n' \
    > "${ARTIFACT_DIR}/container/grype-dir.status.txt"
  printf 'last_error=%s\n' "${grype_last_error}" >> "${ARTIFACT_DIR}/container/grype-dir.status.txt"

  if [[ "${PHASE20_GRYPE_REQUIRED}" == "true" ]]; then
    echo "ERROR: grype scan failed after retries" >&2
    return 1
  fi

  echo "WARN: grype scan failed after retries; continuing with trivy evidence" >&2
  return 0
}

run_trivy_fs
run_grype_dir
