#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
fuzz_root="$repo_root/fuzz/cargo-fuzz"
fuzz_seconds="${NORTHSTAR_UDP_ACTIVE_FUZZ_SECONDS:-15}"
fuzz_sanitizer="${NORTHSTAR_UDP_ACTIVE_FUZZ_SANITIZER:-none}"
summary_path="${NORTHSTAR_UDP_ACTIVE_FUZZ_SUMMARY_PATH:-$repo_root/target/northstar/udp-active-fuzz-summary.json}"

[[ "$fuzz_seconds" =~ ^[0-9]+$ ]] || fail "NORTHSTAR_UDP_ACTIVE_FUZZ_SECONDS must be a positive integer."
(( fuzz_seconds > 0 )) || fail "NORTHSTAR_UDP_ACTIVE_FUZZ_SECONDS must be greater than zero."
[[ "$fuzz_sanitizer" == "none" || "$fuzz_sanitizer" == "address" ]] || fail "NORTHSTAR_UDP_ACTIVE_FUZZ_SANITIZER must be either 'none' or 'address'."

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP active fuzz gate."
command -v cargo-fuzz >/dev/null 2>&1 || fail "cargo-fuzz was not found. Install it with 'cargo install cargo-fuzz' before enabling the UDP active fuzz gate."
cargo +nightly --version >/dev/null 2>&1 || fail "the nightly Rust toolchain was not found. Install it with 'rustup toolchain install nightly --profile minimal' before enabling the UDP active fuzz gate."

echo "==> Synchronizing reviewed UDP fuzz corpora"
cargo run -p ns-testkit --example sync_udp_fuzz_corpus

echo "==> Replaying the reviewed UDP fuzz smoke corpus"
cargo run -p ns-testkit --example udp_fuzz_smoke

cd "$fuzz_root"

mkdir -p "$(dirname "$summary_path")"
results_json=""
first_result=1

for target in control_frame_decoder udp_fallback_frame_decoder udp_datagram_decoder; do
  corpus_dir="$fuzz_root/corpus/$target"
  echo "==> Running active UDP fuzz target $target for $fuzz_seconds seconds with sanitizer $fuzz_sanitizer"
  set +e
  cargo +nightly fuzz run --fuzz-dir "$fuzz_root" --sanitizer "$fuzz_sanitizer" "$target" "$corpus_dir" -- -max_total_time="$fuzz_seconds"
  exit_code=$?
  set -e
  status="passed"
  if (( exit_code != 0 )); then
    status="failed"
  fi
  if (( first_result == 0 )); then
    results_json+=","
  fi
  first_result=0
  results_json+="$(printf '{"target":"%s","seconds":%s,"sanitizer":"%s","corpus_path":"%s","exit_code":%s,"status":"%s"}' "$target" "$fuzz_seconds" "$fuzz_sanitizer" "$corpus_dir" "$exit_code" "$status")"
  if (( exit_code != 0 )); then
    printf '{\n  "summary_version": 1,\n  "seconds": %s,\n  "sanitizer": "%s",\n  "all_passed": false,\n  "results": [%s]\n}\n' "$fuzz_seconds" "$fuzz_sanitizer" "$results_json" > "$summary_path"
    exit "$exit_code"
  fi
done

printf '{\n  "summary_version": 1,\n  "seconds": %s,\n  "sanitizer": "%s",\n  "all_passed": true,\n  "results": [%s]\n}\n' "$fuzz_seconds" "$fuzz_sanitizer" "$results_json" > "$summary_path"

echo "UDP active fuzz gate completed successfully."
echo "machine_readable_summary=$summary_path"
