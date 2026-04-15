#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP rollout matrix wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-rollout-matrix.sh."
[[ "$#" -gt 0 ]] || fail "Usage: ./scripts/udp-rollout-matrix.sh --summary-path <path> --input <comparison-summary-path> [--input <comparison-summary-path> ...]"

echo "==> Running machine-readable UDP rollout matrix"
cargo run -p ns-testkit --example udp_rollout_matrix -- "$@"
