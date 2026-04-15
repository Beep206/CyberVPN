#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
source "$script_dir/verta-compat.sh"

verta_sync_release_evidence_envs

canonical_summary_path="$(verta_output_path "$repo_root" "udp-release-candidate-evidence-freeze-summary.json")"
legacy_summary_path="$(verta_legacy_output_path "$repo_root" "udp-release-candidate-evidence-freeze-summary.json")"
summary_path="${VERTA_UDP_RELEASE_CANDIDATE_EVIDENCE_FREEZE_SUMMARY_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_EVIDENCE_FREEZE_SUMMARY_PATH:-$canonical_summary_path}}"

canonical_release_candidate_hardening_path="$(verta_output_path "$repo_root" "udp-release-candidate-hardening-summary.json")"
legacy_release_candidate_hardening_path="$(verta_legacy_output_path "$repo_root" "udp-release-candidate-hardening-summary.json")"
release_candidate_hardening_path="${VERTA_UDP_RELEASE_CANDIDATE_EVIDENCE_FREEZE_RELEASE_CANDIDATE_HARDENING_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_EVIDENCE_FREEZE_RELEASE_CANDIDATE_HARDENING_PATH:-$(verta_prefer_existing_path "$canonical_release_candidate_hardening_path" "$legacy_release_candidate_hardening_path")}}"

canonical_linux_interop_catalog_path="$(verta_output_path "$repo_root" "udp-interop-profile-catalog-linux.json")"
legacy_linux_interop_catalog_path="$(verta_legacy_output_path "$repo_root" "udp-interop-profile-catalog-linux.json")"
linux_interop_catalog_path="${VERTA_UDP_RELEASE_CANDIDATE_EVIDENCE_FREEZE_LINUX_INTEROP_CATALOG_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_EVIDENCE_FREEZE_LINUX_INTEROP_CATALOG_PATH:-$(verta_prefer_existing_path "$canonical_linux_interop_catalog_path" "$legacy_linux_interop_catalog_path")}}"

canonical_macos_interop_catalog_path="$(verta_output_path "$repo_root" "udp-interop-profile-catalog-macos.json")"
legacy_macos_interop_catalog_path="$(verta_legacy_output_path "$repo_root" "udp-interop-profile-catalog-macos.json")"
macos_interop_catalog_path="${VERTA_UDP_RELEASE_CANDIDATE_EVIDENCE_FREEZE_MACOS_INTEROP_CATALOG_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_EVIDENCE_FREEZE_MACOS_INTEROP_CATALOG_PATH:-$(verta_prefer_existing_path "$canonical_macos_interop_catalog_path" "$legacy_macos_interop_catalog_path")}}"

canonical_windows_interop_catalog_path="$(verta_output_path "$repo_root" "udp-interop-profile-catalog-windows.json")"
legacy_windows_interop_catalog_path="$(verta_legacy_output_path "$repo_root" "udp-interop-profile-catalog-windows.json")"
windows_interop_catalog_path="${VERTA_UDP_RELEASE_CANDIDATE_EVIDENCE_FREEZE_WINDOWS_INTEROP_CATALOG_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_EVIDENCE_FREEZE_WINDOWS_INTEROP_CATALOG_PATH:-$(verta_prefer_existing_path "$canonical_windows_interop_catalog_path" "$legacy_windows_interop_catalog_path")}}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate evidence freeze wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-evidence-freeze.sh."

should_mirror_default="false"
if [[ "$#" -eq 0 ]]; then
  set -- \
    --summary-path "$summary_path" \
    --release-candidate-hardening "$release_candidate_hardening_path" \
    --linux-interop-catalog "$linux_interop_catalog_path" \
    --macos-interop-catalog "$macos_interop_catalog_path" \
    --windows-interop-catalog "$windows_interop_catalog_path"
  should_mirror_default="true"
else
  have_summary_path="false"
  for arg in "$@"; do
    if [[ "$arg" == "--summary-path" ]]; then
      have_summary_path="true"
      break
    fi
  done
  if [[ "$have_summary_path" == "false" ]]; then
    set -- --summary-path "$summary_path" "$@"
    should_mirror_default="true"
  fi
fi

echo "==> Running machine-readable UDP release candidate evidence freeze"
set +e
cargo run -p ns-testkit --example udp_release_candidate_evidence_freeze -- "$@"
exit_code=$?
set -e
if [[ "$should_mirror_default" == "true" ]]; then
  verta_mirror_if_canonical_default "$summary_path" "$canonical_summary_path" "$legacy_summary_path"
fi
if [[ "$exit_code" -ne 0 ]]; then
  exit "$exit_code"
fi
