#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
summary_path="${NORTHSTAR_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_PATH:-$repo_root/target/northstar/remnawave-supported-upstream-summary.json}"

fail() {
  echo "error: $*" >&2
  exit 1
}

if ! command -v cargo >/dev/null 2>&1; then
  fail "cargo was not found. Install the Rust stable toolchain before running the supported-upstream verification wrapper."
fi

if [[ ! -f "$workspace_manifest" ]]; then
  fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/remnawave-supported-upstream-verify.sh."
fi

if [[ "$#" -eq 0 ]]; then
  set -- --summary-path "$summary_path"
fi

echo "==> Running Remnawave supported-upstream verification"
cargo run -p ns-testkit --example remnawave_supported_upstream_verification -- "$@"
