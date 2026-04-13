#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
summary_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_CONSOLIDATION_SUMMARY_PATH:-$repo_root/target/northstar/udp-release-candidate-consolidation-summary.json}"
release_stability_signoff_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_CONSOLIDATION_RELEASE_STABILITY_SIGNOFF_PATH:-$repo_root/target/northstar/udp-release-stability-signoff-summary.json}"
linux_interop_catalog_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_CONSOLIDATION_LINUX_INTEROP_CATALOG_PATH:-$repo_root/target/northstar/udp-interop-profile-catalog-linux.json}"
macos_interop_catalog_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_CONSOLIDATION_MACOS_INTEROP_CATALOG_PATH:-$repo_root/target/northstar/udp-interop-profile-catalog-macos.json}"
windows_interop_catalog_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_CONSOLIDATION_WINDOWS_INTEROP_CATALOG_PATH:-$repo_root/target/northstar/udp-interop-profile-catalog-windows.json}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate consolidation wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-consolidation.sh."

if [[ "$#" -eq 0 ]]; then
  set -- \
    --summary-path "$summary_path" \
    --release-stability-signoff "$release_stability_signoff_path" \
    --linux-interop-catalog "$linux_interop_catalog_path" \
    --macos-interop-catalog "$macos_interop_catalog_path" \
    --windows-interop-catalog "$windows_interop_catalog_path"
fi

echo "==> Running machine-readable UDP release candidate consolidation"
cargo run -p ns-testkit --example udp_release_candidate_consolidation -- "$@"
