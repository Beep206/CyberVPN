#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
summary_path="${NORTHSTAR_UDP_RELEASE_SOAK_SUMMARY_PATH:-$repo_root/target/northstar/udp-release-soak-summary.json}"
release_burn_in_path="${NORTHSTAR_UDP_RELEASE_SOAK_RELEASE_BURN_IN_PATH:-$repo_root/target/northstar/udp-release-burn-in-summary.json}"
linux_interop_path="${NORTHSTAR_UDP_RELEASE_SOAK_LINUX_INTEROP_PATH:-$repo_root/target/northstar/udp-interop-lab-summary-linux.json}"
macos_interop_path="${NORTHSTAR_UDP_RELEASE_SOAK_MACOS_INTEROP_PATH:-$repo_root/target/northstar/udp-interop-lab-summary-macos.json}"
windows_interop_path="${NORTHSTAR_UDP_RELEASE_SOAK_WINDOWS_INTEROP_PATH:-$repo_root/target/northstar/udp-interop-lab-summary-windows.json}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP release soak wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-soak.sh."

if [[ "$#" -eq 0 ]]; then
  set -- \
    --summary-path "$summary_path" \
    --release-burn-in "$release_burn_in_path" \
    --linux-interop "$linux_interop_path" \
    --macos-interop "$macos_interop_path" \
    --windows-interop "$windows_interop_path"
fi

echo "==> Running machine-readable UDP release soak"
cargo run -p ns-testkit --example udp_release_soak -- "$@"
