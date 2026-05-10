#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
ARTIFACT_DIR="${SECURITY_ARTIFACT_DIR:-${ROOT_DIR}/security-artifacts}"
SYFT_IMAGE="${SYFT_IMAGE:-anchore/syft:v1.44.0}"

mkdir -p "${ARTIFACT_DIR}/sbom"

if command -v syft >/dev/null 2>&1; then
  syft dir:"${ROOT_DIR}" \
    --exclude '**/.git/**' \
    --exclude '**/node_modules/**' \
    --exclude '**/.tmp/**' \
    --exclude '**/.cache/**' \
    --exclude '**/.terraform/**' \
    --exclude '**/.venv/**' \
    --exclude '**/build/**' \
    --exclude '**/dist/**' \
    --exclude '**/target/**' \
    --exclude '**/coverage/**' \
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
    -v "${ROOT_DIR}:/repo:ro" \
    -v "${ARTIFACT_DIR}/sbom:/out" \
    "${SYFT_IMAGE}" \
    dir:/repo \
    --exclude '**/.git/**' \
    --exclude '**/node_modules/**' \
    --exclude '**/.tmp/**' \
    --exclude '**/.cache/**' \
    --exclude '**/.terraform/**' \
    --exclude '**/.venv/**' \
    --exclude '**/build/**' \
    --exclude '**/dist/**' \
    --exclude '**/target/**' \
    --exclude '**/coverage/**' \
    --exclude '**/.gradle/**' \
    --exclude '**/apps/android-tv/app/build/**' \
    --exclude '**/cybervpn_mobile/.dart_tool/**' \
    --exclude '**/frontend/.next/**' \
    --exclude '**/admin/.next/**' \
    --exclude '**/partner/.next/**' \
    -o cyclonedx-json=/out/cybervpn-sbom.cyclonedx.json \
    -o spdx-json=/out/cybervpn-sbom.spdx.json
fi
