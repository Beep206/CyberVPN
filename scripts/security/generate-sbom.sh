#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
ARTIFACT_DIR="${SECURITY_ARTIFACT_DIR:-${ROOT_DIR}/security-artifacts}"
SYFT_IMAGE="${SYFT_IMAGE:-anchore/syft:v1.46.0}"
SECURITY_SCAN_SCOPE="${SECURITY_SCAN_SCOPE:-phase20}"

mkdir -p "${ARTIFACT_DIR}/sbom"

SNAPSHOT_DIR="$(mktemp -d "${TMPDIR:-/tmp}/cybervpn-sbom-source.XXXXXX")"
FILE_LIST="$(mktemp "${TMPDIR:-/tmp}/cybervpn-sbom-files.XXXXXX")"

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
  cat > "${ARTIFACT_DIR}/sbom/cybervpn-sbom.scope.txt" <<EOF
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

if command -v syft >/dev/null 2>&1; then
  syft dir:"${SNAPSHOT_DIR}" \
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
    -o cyclonedx-json="${ARTIFACT_DIR}/sbom/cybervpn-sbom.cyclonedx.json" \
    -o spdx-json="${ARTIFACT_DIR}/sbom/cybervpn-sbom.spdx.json"
else
  docker run --rm \
    -v "${SNAPSHOT_DIR}:/repo:ro" \
    -v "${ARTIFACT_DIR}/sbom:/out" \
    "${SYFT_IMAGE}" \
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
    -o cyclonedx-json=/out/cybervpn-sbom.cyclonedx.json \
    -o spdx-json=/out/cybervpn-sbom.spdx.json
fi
