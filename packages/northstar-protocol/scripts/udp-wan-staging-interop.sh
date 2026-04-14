#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
summary_path="${NORTHSTAR_UDP_WAN_STAGING_SUMMARY_PATH:-$repo_root/target/northstar/udp-wan-staging-interop-summary.json}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP WAN staging interop wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-wan-staging-interop.sh."

if [[ "$#" -eq 0 ]]; then
  set -- --summary-path "$summary_path"
fi

echo "==> Running machine-readable UDP WAN staging interop"
cargo run -p ns-testkit --example udp_wan_staging_interop -- "$@"
