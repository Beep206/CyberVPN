#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
summary_path="${NORTHSTAR_UDP_RELEASE_PREP_SUMMARY_PATH:-$repo_root/target/northstar/udp-release-prep-summary.json}"
deployment_signoff_path="${NORTHSTAR_UDP_RELEASE_PREP_DEPLOYMENT_SIGNOFF_PATH:-$repo_root/target/northstar/udp-deployment-signoff-summary.json}"
linux_validation_path="${NORTHSTAR_UDP_RELEASE_PREP_LINUX_VALIDATION_PATH:-$repo_root/target/northstar/udp-rollout-validation-summary-linux.json}"
macos_validation_path="${NORTHSTAR_UDP_RELEASE_PREP_MACOS_VALIDATION_PATH:-$repo_root/target/northstar/udp-rollout-validation-summary-macos.json}"
windows_validation_path="${NORTHSTAR_UDP_RELEASE_PREP_WINDOWS_VALIDATION_PATH:-$repo_root/target/northstar/udp-rollout-validation-summary-windows.json}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP release prep wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-prep.sh."

if [[ "$#" -eq 0 ]]; then
  set -- \
    --summary-path "$summary_path" \
    --deployment-signoff "$deployment_signoff_path" \
    --validation "$linux_validation_path" \
    --validation "$macos_validation_path" \
    --validation "$windows_validation_path"
fi

echo "==> Running machine-readable UDP release prep"
cargo run -p ns-testkit --example udp_release_prep -- "$@"
