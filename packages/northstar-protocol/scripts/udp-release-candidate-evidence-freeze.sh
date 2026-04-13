#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
summary_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_EVIDENCE_FREEZE_SUMMARY_PATH:-$repo_root/target/northstar/udp-release-candidate-evidence-freeze-summary.json}"
release_candidate_hardening_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_EVIDENCE_FREEZE_RELEASE_CANDIDATE_HARDENING_PATH:-$repo_root/target/northstar/udp-release-candidate-hardening-summary.json}"
linux_interop_catalog_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_EVIDENCE_FREEZE_LINUX_INTEROP_CATALOG_PATH:-$repo_root/target/northstar/udp-interop-profile-catalog-linux.json}"
macos_interop_catalog_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_EVIDENCE_FREEZE_MACOS_INTEROP_CATALOG_PATH:-$repo_root/target/northstar/udp-interop-profile-catalog-macos.json}"
windows_interop_catalog_path="${NORTHSTAR_UDP_RELEASE_CANDIDATE_EVIDENCE_FREEZE_WINDOWS_INTEROP_CATALOG_PATH:-$repo_root/target/northstar/udp-interop-profile-catalog-windows.json}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate evidence freeze wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-evidence-freeze.sh."

if [[ "$#" -eq 0 ]]; then
  set -- \
    --summary-path "$summary_path" \
    --release-candidate-hardening "$release_candidate_hardening_path" \
    --linux-interop-catalog "$linux_interop_catalog_path" \
    --macos-interop-catalog "$macos_interop_catalog_path" \
    --windows-interop-catalog "$windows_interop_catalog_path"
fi

echo "==> Running machine-readable UDP release candidate evidence freeze"
cargo run -p ns-testkit --example udp_release_candidate_evidence_freeze -- "$@"
