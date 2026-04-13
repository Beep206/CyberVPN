#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "error: $1" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
summary_path="${NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_REALITY_SUMMARY_PATH:-$repo_root/target/northstar/remnawave-supported-upstream-deployment-reality-summary.json}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the supported-upstream deployment-reality verification wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/remnawave-supported-upstream-deployment-reality-verify.sh."

if [[ "$#" -eq 0 ]]; then
  set -- --summary-path "$summary_path"
fi

echo "==> Running Remnawave supported-upstream deployment-reality verification"
cargo run -p ns-testkit --example remnawave_supported_upstream_deployment_reality_verification -- "$@"
