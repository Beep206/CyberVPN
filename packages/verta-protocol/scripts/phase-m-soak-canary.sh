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

verta_sync_phase_m_envs

stage_root="${VERTA_PHASE_M_STAGE_ROOT:-${VERTA_PHASE_M_STAGE_ROOT:-$(verta_output_path "$repo_root" "phase-m-soak")}}"
canonical_summary_path="$(verta_output_path "$repo_root" "phase-m-soak-canary-signoff-summary.json")"
legacy_summary_path="$(verta_legacy_output_path "$repo_root" "phase-m-soak-canary-signoff-summary.json")"
summary_path="${VERTA_PHASE_M_SUMMARY_PATH:-${VERTA_PHASE_M_SUMMARY_PATH:-$canonical_summary_path}}"
canary_plan_path="${VERTA_PHASE_M_CANARY_PLAN_PATH:-${VERTA_PHASE_M_CANARY_PLAN_PATH:-$repo_root/docs/runbooks/phase-m-canary-plan.json}}"
regression_ledger_path="${VERTA_PHASE_M_REGRESSION_LEDGER_PATH:-${VERTA_PHASE_M_REGRESSION_LEDGER_PATH:-$repo_root/docs/development/phase-m-regression-ledger.json}}"

canonical_phase_i_summary_path="$(verta_output_path "$repo_root" "remnawave-supported-upstream-phase-i-signoff-summary.json")"
legacy_phase_i_summary_path="$(verta_legacy_output_path "$repo_root" "remnawave-supported-upstream-phase-i-signoff-summary.json")"
phase_i_summary_path="${VERTA_PHASE_M_PHASE_I_SUMMARY_PATH:-${VERTA_PHASE_M_PHASE_I_SUMMARY_PATH:-$(verta_prefer_existing_path "$canonical_phase_i_summary_path" "$legacy_phase_i_summary_path")}}"

canonical_wan_staging_summary_path="$(verta_output_path "$repo_root" "udp-wan-staging-interop-summary.json")"
legacy_wan_staging_summary_path="$(verta_legacy_output_path "$repo_root" "udp-wan-staging-interop-summary.json")"
wan_staging_summary_path="${VERTA_PHASE_M_WAN_STAGING_SUMMARY_PATH:-${VERTA_PHASE_M_WAN_STAGING_SUMMARY_PATH:-$(verta_prefer_existing_path "$canonical_wan_staging_summary_path" "$legacy_wan_staging_summary_path")}}"

stage_pause_seconds="${VERTA_PHASE_M_STAGE_PAUSE_SECONDS:-${VERTA_PHASE_M_STAGE_PAUSE_SECONDS:-5}}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the Phase M soak/canary wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/phase-m-soak-canary.sh."

bash "$script_dir/remnawave-supported-upstream-phase-i-signoff.sh"

for stage_id in canary_5 canary_25 canary_100; do
  stage_dir="$stage_root/$stage_id"
  lifecycle_summary_path="$stage_dir/lifecycle-summary.json"
  rollback_summary_path="$stage_dir/rollback-summary.json"
  rollback_artifact_root="$stage_dir/rollback-artifacts"
  phase_l_summary_path="$stage_dir/phase-l-summary.json"

  mkdir -p "$stage_dir"
  bash "$script_dir/ensure-local-remnawave-supported-upstream-user-active.sh"

  VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_SUMMARY_PATH="$lifecycle_summary_path" \
    bash "$script_dir/operator-profile-disable-drill.sh"

  VERTA_UDP_NET_CHAOS_SUMMARY_PATH="$rollback_summary_path" \
    VERTA_UDP_NET_CHAOS_ARTIFACT_ROOT="$rollback_artifact_root" \
    bash "$script_dir/operator-rollout-rollback-drill.sh"

  cargo run -p ns-testkit --example phase_l_operator_readiness_signoff -- \
    --summary-path "$phase_l_summary_path" \
    --profile-disable-drill "$lifecycle_summary_path" \
    --rollback-drill "$rollback_summary_path"

  if [[ "$stage_id" != "canary_100" ]]; then
    sleep "$stage_pause_seconds"
  fi
done

cargo run -p ns-testkit --example phase_m_soak_canary_signoff -- \
  --summary-path "$summary_path" \
  --stage-root "$stage_root" \
  --canary-plan "$canary_plan_path" \
  --regression-ledger "$regression_ledger_path" \
  --phase-i "$phase_i_summary_path" \
  --wan-staging "$wan_staging_summary_path" \
  "$@"
verta_mirror_if_canonical_default "$summary_path" "$canonical_summary_path" "$legacy_summary_path"
