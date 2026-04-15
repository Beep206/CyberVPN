#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
source "$script_dir/verta-compat.sh"

verta_sync_phase_l_envs

canonical_summary_path="$(verta_output_path "$repo_root" "phase-l-operator-readiness-signoff-summary.json")"
legacy_summary_path="$(verta_legacy_output_path "$repo_root" "phase-l-operator-readiness-signoff-summary.json")"
summary_path="${VERTA_PHASE_L_OPERATOR_READINESS_SUMMARY_PATH:-${VERTA_PHASE_L_OPERATOR_READINESS_SUMMARY_PATH:-$canonical_summary_path}}"
runbook_matrix_path="${VERTA_PHASE_L_OPERATOR_READINESS_RUNBOOK_MATRIX_PATH:-${VERTA_PHASE_L_OPERATOR_READINESS_RUNBOOK_MATRIX_PATH:-$repo_root/docs/runbooks/operator-recovery-matrix.json}}"

canonical_profile_disable_drill_path="$(verta_output_path "$repo_root" "remnawave-supported-upstream-lifecycle-summary.json")"
legacy_profile_disable_drill_path="$(verta_legacy_output_path "$repo_root" "remnawave-supported-upstream-lifecycle-summary.json")"
profile_disable_drill_path="${VERTA_PHASE_L_OPERATOR_READINESS_PROFILE_DISABLE_DRILL_PATH:-${VERTA_PHASE_L_OPERATOR_READINESS_PROFILE_DISABLE_DRILL_PATH:-$(verta_prefer_existing_path "$canonical_profile_disable_drill_path" "$legacy_profile_disable_drill_path")}}"

canonical_rollback_drill_path="$(verta_output_path "$repo_root" "operator-rollout-rollback-drill-summary.json")"
legacy_rollback_drill_path="$(verta_legacy_output_path "$repo_root" "operator-rollout-rollback-drill-summary.json")"
rollback_drill_path="${VERTA_PHASE_L_OPERATOR_READINESS_ROLLBACK_DRILL_PATH:-${VERTA_PHASE_L_OPERATOR_READINESS_ROLLBACK_DRILL_PATH:-$(verta_prefer_existing_path "$canonical_rollback_drill_path" "$legacy_rollback_drill_path")}}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the Phase L operator-readiness wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/phase-l-operator-readiness.sh."

should_mirror_default="false"
if [[ "$#" -eq 0 ]]; then
  bash "$script_dir/operator-rollout-rollback-drill.sh"
  set -- \
    --summary-path "$summary_path" \
    --runbook-matrix "$runbook_matrix_path" \
    --profile-disable-drill "$profile_disable_drill_path" \
    --rollback-drill "$rollback_drill_path"
  should_mirror_default="true"
fi

echo "==> Running Phase L operator readiness signoff"
cargo run -p ns-testkit --example phase_l_operator_readiness_signoff -- "$@"
if [[ "$should_mirror_default" == "true" ]]; then
  verta_mirror_if_canonical_default "$summary_path" "$canonical_summary_path" "$legacy_summary_path"
fi
