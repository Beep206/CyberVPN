#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
summary_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_HARDENING_SUMMARY_PATH:-$repo_root/target/northstar/udp-release-candidate-hardening-summary.json}"
release_candidate_consolidation_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_HARDENING_RELEASE_CANDIDATE_CONSOLIDATION_PATH:-$repo_root/target/northstar/udp-release-candidate-consolidation-summary.json}"
linux_validation_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_HARDENING_LINUX_VALIDATION_PATH:-$repo_root/target/northstar/udp-rollout-validation-summary-linux.json}"
macos_validation_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_HARDENING_MACOS_VALIDATION_PATH:-$repo_root/target/northstar/udp-rollout-validation-summary-macos.json}"
windows_validation_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_HARDENING_WINDOWS_VALIDATION_PATH:-$repo_root/target/northstar/udp-rollout-validation-summary-windows.json}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate hardening wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-hardening.sh."

if [[ "$#" -eq 0 ]]; then
  set -- \
    --summary-path "$summary_path" \
    --release-candidate-consolidation "$release_candidate_consolidation_path" \
    --linux-validation "$linux_validation_path" \
    --macos-validation "$macos_validation_path" \
    --windows-validation "$windows_validation_path"
fi

echo "==> Running machine-readable UDP release candidate hardening"
cargo run -p ns-testkit --example udp_release_candidate_hardening -- "$@"
