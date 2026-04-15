#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running UDP fuzz smoke checks."

cd "$repo_root"

echo "==> Synchronizing UDP fuzz corpus"
cargo run -p ns-testkit --example sync_udp_fuzz_corpus

echo "==> Replaying UDP fuzz smoke seeds"
cargo run -p ns-testkit --example udp_fuzz_smoke

echo "UDP fuzz smoke checks completed successfully."
