#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
project_root="$(git -C "$repo_root" rev-parse --show-toplevel 2>/dev/null || true)"
source "$script_dir/verta-compat.sh"

verta_sync_phase_n_envs

canonical_summary_path="$(verta_output_path "$repo_root" "phase-n-production-ready-signoff-summary.json")"
legacy_summary_path="$(verta_legacy_output_path "$repo_root" "phase-n-production-ready-signoff-summary.json")"
summary_path="${VERTA_PHASE_N_SUMMARY_PATH:-${VERTA_PHASE_N_SUMMARY_PATH:-$canonical_summary_path}}"

canonical_phase_i_summary_path="$(verta_output_path "$repo_root" "remnawave-supported-upstream-phase-i-signoff-summary.json")"
legacy_phase_i_summary_path="$(verta_legacy_output_path "$repo_root" "remnawave-supported-upstream-phase-i-signoff-summary.json")"
phase_i_summary_path="${VERTA_PHASE_N_PHASE_I_SUMMARY_PATH:-${VERTA_PHASE_N_PHASE_I_SUMMARY_PATH:-$(verta_prefer_existing_path "$canonical_phase_i_summary_path" "$legacy_phase_i_summary_path")}}"

canonical_phase_j_summary_path="$(verta_output_path "$repo_root" "udp-phase-j-signoff-summary.json")"
legacy_phase_j_summary_path="$(verta_legacy_output_path "$repo_root" "udp-phase-j-signoff-summary.json")"
phase_j_summary_path="${VERTA_PHASE_N_PHASE_J_SUMMARY_PATH:-${VERTA_PHASE_N_PHASE_J_SUMMARY_PATH:-$(verta_prefer_existing_path "$canonical_phase_j_summary_path" "$legacy_phase_j_summary_path")}}"

canonical_phase_l_summary_path="$(verta_output_path "$repo_root" "phase-l-operator-readiness-signoff-summary.json")"
legacy_phase_l_summary_path="$(verta_legacy_output_path "$repo_root" "phase-l-operator-readiness-signoff-summary.json")"
phase_l_summary_path="${VERTA_PHASE_N_PHASE_L_SUMMARY_PATH:-${VERTA_PHASE_N_PHASE_L_SUMMARY_PATH:-$(verta_prefer_existing_path "$canonical_phase_l_summary_path" "$legacy_phase_l_summary_path")}}"

canonical_phase_m_summary_path="$(verta_output_path "$repo_root" "phase-m-soak-canary-signoff-summary.json")"
legacy_phase_m_summary_path="$(verta_legacy_output_path "$repo_root" "phase-m-soak-canary-signoff-summary.json")"
phase_m_summary_path="${VERTA_PHASE_N_PHASE_M_SUMMARY_PATH:-${VERTA_PHASE_N_PHASE_M_SUMMARY_PATH:-$(verta_prefer_existing_path "$canonical_phase_m_summary_path" "$legacy_phase_m_summary_path")}}"

release_checklist_path="${VERTA_PHASE_N_RELEASE_CHECKLIST_PATH:-${VERTA_PHASE_N_RELEASE_CHECKLIST_PATH:-$repo_root/docs/release/production-ready-checklist.json}}"
support_matrix_path="${VERTA_PHASE_N_SUPPORT_MATRIX_PATH:-${VERTA_PHASE_N_SUPPORT_MATRIX_PATH:-$repo_root/docs/release/supported-environment-matrix.json}}"
known_limitations_path="${VERTA_PHASE_N_KNOWN_LIMITATIONS_PATH:-${VERTA_PHASE_N_KNOWN_LIMITATIONS_PATH:-$repo_root/docs/release/known-limitations.json}}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the Phase N production-ready wrapper."
command -v git >/dev/null 2>&1 || fail "git was not found. Install git before running the Phase N production-ready wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/phase-n-production-ready.sh."
[[ -n "$project_root" ]] || fail "Unable to resolve the project root via git."

git_head="$(git -C "$project_root" rev-parse HEAD 2>/dev/null || true)"
git_branch="$(git -C "$project_root" branch --show-current 2>/dev/null || true)"
if [[ -n "$(git -C "$project_root" status --porcelain)" ]]; then
  git_clean="false"
else
  git_clean="true"
fi

echo "==> Running Phase N production-ready signoff"
cargo run --manifest-path "$workspace_manifest" -p ns-testkit --example phase_n_production_ready_signoff -- \
  --project-root "$project_root" \
  --summary-path "$summary_path" \
  --phase-i "$phase_i_summary_path" \
  --phase-j "$phase_j_summary_path" \
  --phase-l "$phase_l_summary_path" \
  --phase-m "$phase_m_summary_path" \
  --release-checklist "$release_checklist_path" \
  --support-matrix "$support_matrix_path" \
  --known-limitations "$known_limitations_path" \
  --git-head "$git_head" \
  --git-branch "$git_branch" \
  --git-clean "$git_clean" \
  "$@"
verta_mirror_if_canonical_default "$summary_path" "$canonical_summary_path" "$legacy_summary_path"
