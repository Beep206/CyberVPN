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

canonical_summary_path="$(verta_output_path "$repo_root" "udp-wan-staging-interop-summary.json")"
legacy_summary_path="$(verta_legacy_output_path "$repo_root" "udp-wan-staging-interop-summary.json")"
summary_path="${VERTA_UDP_WAN_STAGING_SUMMARY_PATH:-${VERTA_UDP_WAN_STAGING_SUMMARY_PATH:-$canonical_summary_path}}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP WAN staging interop wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-wan-staging-interop.sh."

should_mirror_default="false"
if [[ "$#" -eq 0 ]]; then
  set -- --summary-path "$summary_path"
  should_mirror_default="true"
fi

echo "==> Running machine-readable UDP WAN staging interop"
cargo run -p ns-testkit --example udp_wan_staging_interop -- "$@"
if [[ "$should_mirror_default" == "true" ]]; then
  verta_mirror_if_canonical_default "$summary_path" "$canonical_summary_path" "$legacy_summary_path"
fi
