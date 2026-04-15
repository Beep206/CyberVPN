#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/verta-compat.sh"

verta_sync_phase_i_envs

canonical_summary_path="$(verta_output_path "$repo_root" "remnawave-supported-upstream-summary.json")"
legacy_summary_path="$(verta_legacy_output_path "$repo_root" "remnawave-supported-upstream-summary.json")"
summary_path="${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_PATH:-${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_PATH:-$canonical_summary_path}}"

fail() {
  echo "error: $*" >&2
  exit 1
}

if ! command -v cargo >/dev/null 2>&1; then
  fail "cargo was not found. Install the Rust stable toolchain before running the supported-upstream verification wrapper."
fi

if [[ ! -f "$workspace_manifest" ]]; then
  fail "No root Cargo.toml was found at $workspace_manifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/remnawave-supported-upstream-verify.sh."
fi

should_mirror_default="false"
if [[ "$#" -eq 0 ]]; then
  set -- --summary-path "$summary_path"
  should_mirror_default="true"
fi

echo "==> Running Remnawave supported-upstream verification"
cargo run -p ns-testkit --example remnawave_supported_upstream_verification -- "$@"
if [[ "$should_mirror_default" == "true" ]]; then
  verta_mirror_if_canonical_default "$summary_path" "$canonical_summary_path" "$legacy_summary_path"
fi
