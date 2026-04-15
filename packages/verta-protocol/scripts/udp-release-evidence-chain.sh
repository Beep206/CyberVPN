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

verta_sync_release_evidence_envs

canonical_readiness_matrix_path="$(verta_output_path "$repo_root" "udp-rollout-matrix-summary.json")"
readiness_matrix_path="${VERTA_UDP_RELEASE_EVIDENCE_CHAIN_READINESS_MATRIX_PATH:-${VERTA_UDP_RELEASE_EVIDENCE_CHAIN_READINESS_MATRIX_PATH:-$canonical_readiness_matrix_path}}"
canonical_staged_matrix_path="$(verta_output_path "$repo_root" "udp-rollout-matrix-summary-staged.json")"
staged_matrix_path="${VERTA_UDP_RELEASE_EVIDENCE_CHAIN_STAGED_MATRIX_PATH:-${VERTA_UDP_RELEASE_EVIDENCE_CHAIN_STAGED_MATRIX_PATH:-$canonical_staged_matrix_path}}"

linux_readiness_path="${VERTA_UDP_RELEASE_EVIDENCE_CHAIN_LINUX_READINESS_PATH:-${VERTA_UDP_RELEASE_EVIDENCE_CHAIN_LINUX_READINESS_PATH:-$(verta_prefer_existing_path "$(verta_output_path "$repo_root" "udp-rollout-comparison-summary-linux.json")" "$(verta_legacy_output_path "$repo_root" "udp-rollout-comparison-summary-linux.json")")}}"
macos_readiness_path="${VERTA_UDP_RELEASE_EVIDENCE_CHAIN_MACOS_READINESS_PATH:-${VERTA_UDP_RELEASE_EVIDENCE_CHAIN_MACOS_READINESS_PATH:-$(verta_prefer_existing_path "$(verta_output_path "$repo_root" "udp-rollout-comparison-summary-macos.json")" "$(verta_legacy_output_path "$repo_root" "udp-rollout-comparison-summary-macos.json")")}}"
windows_readiness_path="${VERTA_UDP_RELEASE_EVIDENCE_CHAIN_WINDOWS_READINESS_PATH:-${VERTA_UDP_RELEASE_EVIDENCE_CHAIN_WINDOWS_READINESS_PATH:-$(verta_prefer_existing_path "$(verta_output_path "$repo_root" "udp-rollout-comparison-summary-windows.json")" "$(verta_legacy_output_path "$repo_root" "udp-rollout-comparison-summary-windows.json")")}}"
linux_staged_path="${VERTA_UDP_RELEASE_EVIDENCE_CHAIN_LINUX_STAGED_PATH:-${VERTA_UDP_RELEASE_EVIDENCE_CHAIN_LINUX_STAGED_PATH:-$(verta_prefer_existing_path "$(verta_output_path "$repo_root" "udp-rollout-comparison-summary-linux-staged.json")" "$(verta_legacy_output_path "$repo_root" "udp-rollout-comparison-summary-linux-staged.json")")}}"
macos_staged_path="${VERTA_UDP_RELEASE_EVIDENCE_CHAIN_MACOS_STAGED_PATH:-${VERTA_UDP_RELEASE_EVIDENCE_CHAIN_MACOS_STAGED_PATH:-$(verta_prefer_existing_path "$(verta_output_path "$repo_root" "udp-rollout-comparison-summary-macos-staged.json")" "$(verta_legacy_output_path "$repo_root" "udp-rollout-comparison-summary-macos-staged.json")")}}"

canonical_release_workflow_summary_path="$(verta_output_path "$repo_root" "udp-release-workflow-summary.json")"
legacy_release_workflow_summary_path="$(verta_legacy_output_path "$repo_root" "udp-release-workflow-summary.json")"
release_workflow_summary_path="${VERTA_UDP_RELEASE_WORKFLOW_SUMMARY_PATH:-${VERTA_UDP_RELEASE_WORKFLOW_SUMMARY_PATH:-$canonical_release_workflow_summary_path}}"
canonical_final_summary_path="$(verta_output_path "$repo_root" "udp-release-candidate-certification-summary.json")"
legacy_final_summary_path="$(verta_legacy_output_path "$repo_root" "udp-release-candidate-certification-summary.json")"
final_summary_path="${VERTA_UDP_RELEASE_CANDIDATE_CERTIFICATION_SUMMARY_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_CERTIFICATION_SUMMARY_PATH:-$canonical_final_summary_path}}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP release evidence chain."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-evidence-chain.sh."

for required_path in \
  "$linux_readiness_path" \
  "$macos_readiness_path" \
  "$windows_readiness_path" \
  "$linux_staged_path" \
  "$macos_staged_path"
do
  [[ -f "$required_path" ]] || fail "Required release-evidence input is missing at $required_path."
done

echo "==> Building machine-readable readiness rollout matrix"
bash "$script_dir/udp-rollout-matrix.sh" \
  --summary-path "$readiness_matrix_path" \
  --input "$linux_readiness_path" \
  --input "$macos_readiness_path" \
  --input "$windows_readiness_path"
verta_mirror_if_canonical_default "$readiness_matrix_path" "$canonical_readiness_matrix_path" "$(verta_legacy_output_path "$repo_root" "udp-rollout-matrix-summary.json")"

echo "==> Building machine-readable staged-rollout matrix"
bash "$script_dir/udp-rollout-matrix.sh" \
  --summary-path "$staged_matrix_path" \
  --input "$linux_staged_path" \
  --input "$macos_staged_path"
verta_mirror_if_canonical_default "$staged_matrix_path" "$canonical_staged_matrix_path" "$(verta_legacy_output_path "$repo_root" "udp-rollout-matrix-summary-staged.json")"

echo "==> Running release-facing evidence chain"
bash "$script_dir/udp-release-workflow.sh" \
  --summary-path "$release_workflow_summary_path" \
  --input "$readiness_matrix_path" \
  --input "$staged_matrix_path"
verta_mirror_if_canonical_default "$release_workflow_summary_path" "$canonical_release_workflow_summary_path" "$legacy_release_workflow_summary_path"
bash "$script_dir/udp-deployment-signoff.sh"
bash "$script_dir/udp-release-prep.sh"
bash "$script_dir/udp-release-candidate-signoff.sh"
bash "$script_dir/udp-release-burn-in.sh"
bash "$script_dir/udp-release-soak.sh"
bash "$script_dir/udp-release-gate.sh"
bash "$script_dir/udp-release-readiness-burndown.sh"
bash "$script_dir/udp-release-stability-signoff.sh"
bash "$script_dir/udp-release-candidate-consolidation.sh"
bash "$script_dir/udp-release-candidate-hardening.sh"
bash "$script_dir/udp-release-candidate-evidence-freeze.sh"
bash "$script_dir/udp-release-candidate-signoff-closure.sh"
bash "$script_dir/udp-release-candidate-stabilization.sh"
bash "$script_dir/udp-release-candidate-readiness.sh"
bash "$script_dir/udp-release-candidate-acceptance.sh"
VERTA_UDP_RELEASE_CANDIDATE_CERTIFICATION_SUMMARY_PATH="$final_summary_path" \
  bash "$script_dir/udp-release-candidate-certification.sh"
verta_mirror_if_canonical_default "$final_summary_path" "$canonical_final_summary_path" "$legacy_final_summary_path"

[[ -f "$final_summary_path" ]] || fail "UDP release candidate certification summary was not produced at $final_summary_path."

echo "Verta UDP release evidence chain completed successfully."
echo "readiness_matrix_summary=$readiness_matrix_path"
echo "staged_matrix_summary=$staged_matrix_path"
echo "release_candidate_certification_summary=$final_summary_path"
