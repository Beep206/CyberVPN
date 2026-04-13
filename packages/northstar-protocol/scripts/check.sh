#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running repository checks."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/check.sh."

echo "==> Running cargo fmt"
cargo fmt --all --check

echo "==> Running cargo clippy"
cargo clippy --workspace --all-targets --all-features -- -D warnings

echo "==> Running cargo test"
cargo test --workspace --all-targets --all-features

if [[ "${NORTHSTAR_ENABLE_UDP_FUZZ_SMOKE:-0}" == "1" ]]; then
  echo "==> Running optional UDP fuzz smoke gate"
  cargo run -p ns-testkit --example sync_udp_fuzz_corpus
  cargo run -p ns-testkit --example udp_fuzz_smoke
fi

if [[ "${NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ:-0}" == "1" ]]; then
  echo "==> Running optional UDP active fuzz gate"
  "$repo_root/scripts/fuzz-udp-active.sh"
fi

if [[ "${NORTHSTAR_ENABLE_UDP_PERF_GATE:-0}" == "1" ]]; then
  echo "==> Running optional UDP performance gate"
  cargo run -p ns-testkit --example udp_perf_gate
fi

if [[ "${NORTHSTAR_ENABLE_UDP_WAN_LAB:-0}" == "1" ]]; then
  echo "==> Running optional UDP WAN-lab verification path"
  "$repo_root/scripts/udp-wan-lab.sh"
fi

echo "All configured checks completed successfully."
