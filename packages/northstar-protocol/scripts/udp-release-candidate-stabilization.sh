#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
summary_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_STABILIZATION_SUMMARY_PATH:-$repo_root/target/northstar/udp-release-candidate-stabilization-summary.json}"
signoff_closure_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_STABILIZATION_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_PATH:-$repo_root/target/northstar/udp-release-candidate-signoff-closure-summary.json}"
linux_catalog_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_STABILIZATION_LINUX_INTEROP_CATALOG_PATH:-$repo_root/target/northstar/udp-interop-profile-catalog-linux.json}"
macos_catalog_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_STABILIZATION_MACOS_INTEROP_CATALOG_PATH:-$repo_root/target/northstar/udp-interop-profile-catalog-macos.json}"
windows_catalog_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_STABILIZATION_WINDOWS_INTEROP_CATALOG_PATH:-$repo_root/target/northstar/udp-interop-profile-catalog-windows.json}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate stabilization wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-stabilization.sh."

if [[ "$#" -eq 0 ]]; then
  set -- \
    --summary-path "$summary_path" \
    --release-candidate-signoff-closure "$signoff_closure_path" \
    --linux-interop-catalog "$linux_catalog_path" \
    --macos-interop-catalog "$macos_catalog_path" \
    --windows-interop-catalog "$windows_catalog_path"
fi

echo "==> Running machine-readable UDP release candidate stabilization"
cargo run -p ns-testkit --example udp_release_candidate_stabilization -- "$@"
