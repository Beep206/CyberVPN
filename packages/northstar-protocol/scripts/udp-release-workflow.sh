#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP release workflow wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-workflow.sh."
[[ "$#" -gt 0 ]] || fail "Usage: ./scripts/udp-release-workflow.sh --summary-path <path> --input <matrix-summary-path> [--input <matrix-summary-path> ...]"

echo "==> Running machine-readable UDP release workflow"
cargo run -p ns-testkit --example udp_release_workflow -- "$@"
