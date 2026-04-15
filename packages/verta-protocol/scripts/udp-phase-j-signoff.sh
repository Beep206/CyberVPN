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

verta_sync_phase_j_envs

canonical_summary_path="$(verta_output_path "$repo_root" "udp-phase-j-signoff-summary.json")"
legacy_summary_path="$(verta_legacy_output_path "$repo_root" "udp-phase-j-signoff-summary.json")"
summary_path="${VERTA_UDP_PHASE_J_SIGNOFF_SUMMARY_PATH:-${VERTA_UDP_PHASE_J_SIGNOFF_SUMMARY_PATH:-$canonical_summary_path}}"

canonical_wan_staging_path="$(verta_output_path "$repo_root" "udp-wan-staging-interop-summary.json")"
legacy_wan_staging_path="$(verta_legacy_output_path "$repo_root" "udp-wan-staging-interop-summary.json")"
wan_staging_path="${VERTA_UDP_PHASE_J_SIGNOFF_WAN_STAGING_PATH:-${VERTA_UDP_PHASE_J_SIGNOFF_WAN_STAGING_PATH:-$(verta_prefer_existing_path "$canonical_wan_staging_path" "$legacy_wan_staging_path")}}"

canonical_net_chaos_path="$(verta_output_path "$repo_root" "udp-net-chaos-campaign-summary.json")"
legacy_net_chaos_path="$(verta_legacy_output_path "$repo_root" "udp-net-chaos-campaign-summary.json")"
net_chaos_path="${VERTA_UDP_PHASE_J_SIGNOFF_NET_CHAOS_PATH:-${VERTA_UDP_PHASE_J_SIGNOFF_NET_CHAOS_PATH:-$(verta_prefer_existing_path "$canonical_net_chaos_path" "$legacy_net_chaos_path")}}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP Phase J signoff wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-phase-j-signoff.sh."

should_mirror_default="false"
if [[ "$#" -eq 0 ]]; then
  set -- \
    --summary-path "$summary_path" \
    --wan-staging "$wan_staging_path" \
    --net-chaos "$net_chaos_path"
  should_mirror_default="true"
fi

echo "==> Running machine-readable UDP Phase J signoff"
cargo run -p ns-testkit --example udp_phase_j_signoff -- "$@"
if [[ "$should_mirror_default" == "true" ]]; then
  verta_mirror_if_canonical_default "$summary_path" "$canonical_summary_path" "$legacy_summary_path"
fi
