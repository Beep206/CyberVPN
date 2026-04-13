#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
summary_path="${NORTHSTAR_UDP_DEPLOYMENT_SIGNOFF_SUMMARY_PATH:-$repo_root/target/northstar/udp-deployment-signoff-summary.json}"
release_workflow_path="${NORTHSTAR_UDP_RELEASE_WORKFLOW_SUMMARY_PATH:-$repo_root/target/northstar/udp-release-workflow-summary.json}"
validation_path="${NORTHSTAR_UDP_DEPLOYMENT_VALIDATION_PATH:-$repo_root/target/northstar/udp-rollout-validation-summary-windows.json}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP deployment signoff wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-deployment-signoff.sh."

if [[ "$#" -eq 0 ]]; then
  set -- --summary-path "$summary_path" --release-workflow "$release_workflow_path" --validation "$validation_path"
fi

echo "==> Running machine-readable UDP deployment signoff"
cargo run -p ns-testkit --example udp_deployment_signoff -- "$@"
