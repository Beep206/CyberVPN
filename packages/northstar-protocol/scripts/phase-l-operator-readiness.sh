#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
summary_path="${NORTHSTAR_PHASE_L_OPERATOR_READINESS_SUMMARY_PATH:-$repo_root/target/northstar/phase-l-operator-readiness-signoff-summary.json}"
runbook_matrix_path="${NORTHSTAR_PHASE_L_OPERATOR_READINESS_RUNBOOK_MATRIX_PATH:-$repo_root/docs/runbooks/operator-recovery-matrix.json}"
profile_disable_drill_path="${NORTHSTAR_PHASE_L_OPERATOR_READINESS_PROFILE_DISABLE_DRILL_PATH:-$repo_root/target/northstar/remnawave-supported-upstream-lifecycle-summary.json}"
rollback_drill_path="${NORTHSTAR_PHASE_L_OPERATOR_READINESS_ROLLBACK_DRILL_PATH:-$repo_root/target/northstar/operator-rollout-rollback-drill-summary.json}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the Phase L operator-readiness wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/phase-l-operator-readiness.sh."

if [[ "$#" -eq 0 ]]; then
  bash "$script_dir/operator-rollout-rollback-drill.sh"
  set -- \
    --summary-path "$summary_path" \
    --runbook-matrix "$runbook_matrix_path" \
    --profile-disable-drill "$profile_disable_drill_path" \
    --rollback-drill "$rollback_drill_path"
fi

echo "==> Running Phase L operator readiness signoff"
cargo run -p ns-testkit --example phase_l_operator_readiness_signoff -- "$@"
