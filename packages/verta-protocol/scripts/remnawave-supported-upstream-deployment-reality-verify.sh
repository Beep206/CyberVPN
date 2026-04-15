#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "error: $1" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
source "$script_dir/verta-compat.sh"

verta_sync_phase_i_envs

canonical_summary_path="$(verta_output_path "$repo_root" "remnawave-supported-upstream-deployment-reality-summary.json")"
legacy_summary_path="$(verta_legacy_output_path "$repo_root" "remnawave-supported-upstream-deployment-reality-summary.json")"
summary_path="${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_REALITY_SUMMARY_PATH:-${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_REALITY_SUMMARY_PATH:-$canonical_summary_path}}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the supported-upstream deployment-reality verification wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/remnawave-supported-upstream-deployment-reality-verify.sh."

should_mirror_default="false"
if [[ "$#" -eq 0 ]]; then
  set -- --summary-path "$summary_path"
  should_mirror_default="true"
fi

echo "==> Running Remnawave supported-upstream deployment-reality verification"
cargo run -p ns-testkit --example remnawave_supported_upstream_deployment_reality_verification -- "$@"
if [[ "$should_mirror_default" == "true" ]]; then
  verta_mirror_if_canonical_default "$summary_path" "$canonical_summary_path" "$legacy_summary_path"
fi
