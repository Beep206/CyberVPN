#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
summary_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_SIGNOFF_SUMMARY_PATH:-$repo_root/target/northstar/udp-release-candidate-signoff-summary.json}"
release_prep_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_SIGNOFF_RELEASE_PREP_PATH:-$repo_root/target/northstar/udp-release-prep-summary.json}"
windows_readiness_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_SIGNOFF_WINDOWS_READINESS_PATH:-$repo_root/target/northstar/udp-rollout-comparison-summary-windows.json}"
windows_interop_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_SIGNOFF_WINDOWS_INTEROP_PATH:-$repo_root/target/northstar/udp-interop-lab-summary-windows.json}"
macos_interop_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_SIGNOFF_MACOS_INTEROP_PATH:-$repo_root/target/northstar/udp-interop-lab-summary-macos.json}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate signoff wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-signoff.sh."

if [[ "$#" -eq 0 ]]; then
  set -- \
    --summary-path "$summary_path" \
    --release-prep "$release_prep_path" \
    --windows-readiness "$windows_readiness_path" \
    --windows-interop "$windows_interop_path" \
    --macos-interop "$macos_interop_path"
fi

echo "==> Running machine-readable UDP release candidate signoff"
cargo run -p ns-testkit --example udp_release_candidate_signoff -- "$@"
