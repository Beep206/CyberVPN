#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./verta-compat.sh
source "$script_dir/verta-compat.sh"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
verta_sync_rollout_readiness_envs
canonical_default_summary_path="$(verta_output_path "$repo_root" "udp-interop-lab-summary.json")"
legacy_default_summary_path="$(verta_legacy_output_path "$repo_root" "udp-interop-lab-summary.json")"
summary_path="${VERTA_UDP_INTEROP_SUMMARY_PATH:-$canonical_default_summary_path}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP WAN-lab verification path."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-wan-lab.sh."

echo "==> Running reusable UDP interoperability lab harness"
cargo run -p ns-testkit --example udp_interop_lab -- "$@" --summary-path "$summary_path"

[[ -f "$summary_path" ]] || fail "UDP interoperability lab did not produce the expected machine-readable summary at $summary_path."

verta_mirror_if_canonical_default "$summary_path" "$canonical_default_summary_path" "$legacy_default_summary_path"

echo "Verta UDP WAN-lab verification path completed successfully."
echo "machine_readable_summary=$summary_path"
