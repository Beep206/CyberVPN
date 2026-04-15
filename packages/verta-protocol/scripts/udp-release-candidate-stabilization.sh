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

canonical_summary_path="$(verta_output_path "$repo_root" "udp-release-candidate-stabilization-summary.json")"
legacy_summary_path="$(verta_legacy_output_path "$repo_root" "udp-release-candidate-stabilization-summary.json")"
summary_path="${VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_SUMMARY_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_SUMMARY_PATH:-$canonical_summary_path}}"

canonical_signoff_closure_path="$(verta_output_path "$repo_root" "udp-release-candidate-signoff-closure-summary.json")"
legacy_signoff_closure_path="$(verta_legacy_output_path "$repo_root" "udp-release-candidate-signoff-closure-summary.json")"
signoff_closure_path="${VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_PATH:-$(verta_prefer_existing_path "$canonical_signoff_closure_path" "$legacy_signoff_closure_path")}}"

canonical_linux_catalog_path="$(verta_output_path "$repo_root" "udp-interop-profile-catalog-linux.json")"
legacy_linux_catalog_path="$(verta_legacy_output_path "$repo_root" "udp-interop-profile-catalog-linux.json")"
linux_catalog_path="${VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_LINUX_INTEROP_CATALOG_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_LINUX_INTEROP_CATALOG_PATH:-$(verta_prefer_existing_path "$canonical_linux_catalog_path" "$legacy_linux_catalog_path")}}"

canonical_macos_catalog_path="$(verta_output_path "$repo_root" "udp-interop-profile-catalog-macos.json")"
legacy_macos_catalog_path="$(verta_legacy_output_path "$repo_root" "udp-interop-profile-catalog-macos.json")"
macos_catalog_path="${VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_MACOS_INTEROP_CATALOG_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_MACOS_INTEROP_CATALOG_PATH:-$(verta_prefer_existing_path "$canonical_macos_catalog_path" "$legacy_macos_catalog_path")}}"

canonical_windows_catalog_path="$(verta_output_path "$repo_root" "udp-interop-profile-catalog-windows.json")"
legacy_windows_catalog_path="$(verta_legacy_output_path "$repo_root" "udp-interop-profile-catalog-windows.json")"
windows_catalog_path="${VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_WINDOWS_INTEROP_CATALOG_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_STABILIZATION_WINDOWS_INTEROP_CATALOG_PATH:-$(verta_prefer_existing_path "$canonical_windows_catalog_path" "$legacy_windows_catalog_path")}}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate stabilization wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-stabilization.sh."

should_mirror_default="false"
if [[ "$#" -eq 0 ]]; then
  set -- \
    --summary-path "$summary_path" \
    --release-candidate-signoff-closure "$signoff_closure_path" \
    --linux-interop-catalog "$linux_catalog_path" \
    --macos-interop-catalog "$macos_catalog_path" \
    --windows-interop-catalog "$windows_catalog_path"
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

echo "==> Running machine-readable UDP release candidate stabilization"
set +e
cargo run -p ns-testkit --example udp_release_candidate_stabilization -- "$@"
exit_code=$?
set -e
if [[ "$should_mirror_default" == "true" ]]; then
  verta_mirror_if_canonical_default "$summary_path" "$canonical_summary_path" "$legacy_summary_path"
fi
if [[ "$exit_code" -ne 0 ]]; then
  exit "$exit_code"
fi
