#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
summary_path="${NORTHSTAR_UDP_NET_CHAOS_SUMMARY_PATH:-$repo_root/target/northstar/udp-net-chaos-campaign-summary.json}"
artifact_root="${NORTHSTAR_UDP_NET_CHAOS_ARTIFACT_ROOT:-$repo_root/target/northstar/net-chaos}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP net-chaos wrapper."
command -v unshare >/dev/null 2>&1 || fail "unshare was not found. Install util-linux before running the UDP net-chaos wrapper."
command -v tc >/dev/null 2>&1 || fail "tc was not found. Install iproute2 before running the UDP net-chaos wrapper."
command -v tcpdump >/dev/null 2>&1 || fail "tcpdump was not found. Install tcpdump before running the UDP net-chaos wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-net-chaos-campaign.sh."

have_summary_path=0
have_artifact_root=0
for arg in "$@"; do
  if [[ "$arg" == "--summary-path" ]]; then
    have_summary_path=1
  elif [[ "$arg" == "--artifact-root" ]]; then
    have_artifact_root=1
  fi
done

if [[ "$have_summary_path" -eq 0 ]]; then
  set -- "$@" --summary-path "$summary_path"
fi

if [[ "$have_artifact_root" -eq 0 ]]; then
  set -- "$@" --artifact-root "$artifact_root"
fi

echo "==> Running machine-readable UDP net-chaos campaign"
cargo run -p ns-testkit --example udp_net_chaos_campaign -- "$@"
