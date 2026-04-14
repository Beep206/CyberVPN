#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
summary_path="${NORTHSTAR_UDP_PHASE_J_SIGNOFF_SUMMARY_PATH:-$repo_root/target/northstar/udp-phase-j-signoff-summary.json}"
wan_staging_path="${NORTHSTAR_UDP_PHASE_J_SIGNOFF_WAN_STAGING_PATH:-$repo_root/target/northstar/udp-wan-staging-interop-summary.json}"
net_chaos_path="${NORTHSTAR_UDP_PHASE_J_SIGNOFF_NET_CHAOS_PATH:-$repo_root/target/northstar/udp-net-chaos-campaign-summary.json}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP Phase J signoff wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-phase-j-signoff.sh."

if [[ "$#" -eq 0 ]]; then
  set -- \
    --summary-path "$summary_path" \
    --wan-staging "$wan_staging_path" \
    --net-chaos "$net_chaos_path"
fi

echo "==> Running machine-readable UDP Phase J signoff"
cargo run -p ns-testkit --example udp_phase_j_signoff -- "$@"
