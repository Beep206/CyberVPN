#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
summary_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_ACCEPTANCE_SUMMARY_PATH:-$repo_root/target/northstar/udp-release-candidate-acceptance-summary.json}"
release_candidate_readiness_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_ACCEPTANCE_RELEASE_CANDIDATE_READINESS_PATH:-$repo_root/target/northstar/udp-release-candidate-readiness-summary.json}"
linux_readiness_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_ACCEPTANCE_LINUX_READINESS_PATH:-$repo_root/target/northstar/udp-rollout-comparison-summary-linux.json}"
macos_readiness_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_ACCEPTANCE_MACOS_READINESS_PATH:-$repo_root/target/northstar/udp-rollout-comparison-summary-macos.json}"
windows_readiness_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_ACCEPTANCE_WINDOWS_READINESS_PATH:-$repo_root/target/northstar/udp-rollout-comparison-summary-windows.json}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate acceptance wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-acceptance.sh."

if [[ "$#" -eq 0 ]]; then
  set -- \
    --summary-path "$summary_path" \
    --release-candidate-readiness "$release_candidate_readiness_path" \
    --linux-readiness "$linux_readiness_path" \
    --macos-readiness "$macos_readiness_path" \
    --windows-readiness "$windows_readiness_path"
fi

echo "==> Running machine-readable UDP release candidate acceptance"
cargo run -p ns-testkit --example udp_release_candidate_acceptance -- "$@"
