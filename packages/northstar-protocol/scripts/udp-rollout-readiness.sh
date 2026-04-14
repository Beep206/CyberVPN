#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
smoke_summary_path="${NORTHSTAR_UDP_FUZZ_SMOKE_SUMMARY_PATH:-$repo_root/target/northstar/udp-fuzz-smoke-summary.json}"
perf_summary_path="${NORTHSTAR_UDP_PERF_SUMMARY_PATH:-$repo_root/target/northstar/udp-perf-gate-summary.json}"
interop_summary_path="${NORTHSTAR_UDP_INTEROP_SUMMARY_PATH:-$repo_root/target/northstar/udp-interop-lab-summary.json}"
rollout_summary_path="${NORTHSTAR_UDP_ROLLOUT_VALIDATION_SUMMARY_PATH:-$repo_root/target/northstar/udp-rollout-validation-summary.json}"
comparison_summary_path="${NORTHSTAR_UDP_ROLLOUT_COMPARISON_SUMMARY_PATH:-$repo_root/target/northstar/udp-rollout-comparison-summary.json}"
active_fuzz_summary_path="${NORTHSTAR_UDP_ACTIVE_FUZZ_SUMMARY_PATH:-$repo_root/target/northstar/udp-active-fuzz-summary.json}"
rollout_compare_profile="${NORTHSTAR_UDP_ROLLOUT_COMPARE_PROFILE:-readiness}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP rollout-readiness path."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-rollout-readiness.sh."

echo "==> Synchronizing reviewed UDP fuzz corpus"
cargo run -p ns-testkit --example sync_udp_fuzz_corpus

echo "==> Replaying reviewed UDP fuzz smoke seeds"
cargo run -p ns-testkit --example udp_fuzz_smoke

echo "==> Running UDP performance threshold gate"
cargo run -p ns-testkit --example udp_perf_gate

echo "==> Running machine-readable UDP interoperability lab"
cargo run -p ns-testkit --example udp_interop_lab -- --all --summary-path "$interop_summary_path"

echo "==> Running machine-readable UDP rollout validation lab"
cargo run -p ns-testkit --example udp_rollout_validation_lab -- --summary-path "$rollout_summary_path"

if [[ "${NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ:-0}" == "1" ]]; then
  echo "==> Running optional compatible-host UDP active fuzz gate"
  bash "$script_dir/fuzz-udp-active.sh"
fi

echo "==> Running machine-readable UDP rollout comparison surface"
cargo run -p ns-testkit --example udp_rollout_compare -- --profile "$rollout_compare_profile" --summary-path "$comparison_summary_path"

[[ -f "$smoke_summary_path" ]] || fail "UDP fuzz smoke summary was not produced at $smoke_summary_path."
[[ -f "$perf_summary_path" ]] || fail "UDP perf summary was not produced at $perf_summary_path."
[[ -f "$interop_summary_path" ]] || fail "UDP interop summary was not produced at $interop_summary_path."
[[ -f "$rollout_summary_path" ]] || fail "UDP rollout validation summary was not produced at $rollout_summary_path."
[[ -f "$comparison_summary_path" ]] || fail "UDP rollout comparison summary was not produced at $comparison_summary_path."
if [[ "${NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ:-0}" == "1" ]]; then
  [[ -f "$active_fuzz_summary_path" ]] || fail "UDP active fuzz summary was not produced at $active_fuzz_summary_path."
fi

echo "Northstar UDP rollout-readiness path completed successfully."
echo "smoke_summary=$smoke_summary_path"
echo "perf_summary=$perf_summary_path"
echo "interop_summary=$interop_summary_path"
echo "rollout_validation_summary=$rollout_summary_path"
if [[ "${NORTHSTAR_ENABLE_UDP_ACTIVE_FUZZ:-0}" == "1" ]]; then
  echo "active_fuzz_summary=$active_fuzz_summary_path"
fi
echo "rollout_comparison_summary=$comparison_summary_path"
