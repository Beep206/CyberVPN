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

canonical_summary_path="$(verta_output_path "$repo_root" "udp-release-burn-in-summary.json")"
legacy_summary_path="$(verta_legacy_output_path "$repo_root" "udp-release-burn-in-summary.json")"
summary_path="${VERTA_UDP_RELEASE_BURN_IN_SUMMARY_PATH:-${VERTA_UDP_RELEASE_BURN_IN_SUMMARY_PATH:-$canonical_summary_path}}"

canonical_release_candidate_signoff_path="$(verta_output_path "$repo_root" "udp-release-candidate-signoff-summary.json")"
legacy_release_candidate_signoff_path="$(verta_legacy_output_path "$repo_root" "udp-release-candidate-signoff-summary.json")"
release_candidate_signoff_path="${VERTA_UDP_RELEASE_BURN_IN_RELEASE_CANDIDATE_SIGNOFF_PATH:-${VERTA_UDP_RELEASE_BURN_IN_RELEASE_CANDIDATE_SIGNOFF_PATH:-$(verta_prefer_existing_path "$canonical_release_candidate_signoff_path" "$legacy_release_candidate_signoff_path")}}"

canonical_linux_readiness_path="$(verta_output_path "$repo_root" "udp-rollout-comparison-summary-linux.json")"
legacy_linux_readiness_path="$(verta_legacy_output_path "$repo_root" "udp-rollout-comparison-summary-linux.json")"
linux_readiness_path="${VERTA_UDP_RELEASE_BURN_IN_LINUX_READINESS_PATH:-${VERTA_UDP_RELEASE_BURN_IN_LINUX_READINESS_PATH:-$(verta_prefer_existing_path "$canonical_linux_readiness_path" "$legacy_linux_readiness_path")}}"

canonical_macos_readiness_path="$(verta_output_path "$repo_root" "udp-rollout-comparison-summary-macos.json")"
legacy_macos_readiness_path="$(verta_legacy_output_path "$repo_root" "udp-rollout-comparison-summary-macos.json")"
macos_readiness_path="${VERTA_UDP_RELEASE_BURN_IN_MACOS_READINESS_PATH:-${VERTA_UDP_RELEASE_BURN_IN_MACOS_READINESS_PATH:-$(verta_prefer_existing_path "$canonical_macos_readiness_path" "$legacy_macos_readiness_path")}}"

canonical_windows_readiness_path="$(verta_output_path "$repo_root" "udp-rollout-comparison-summary-windows.json")"
legacy_windows_readiness_path="$(verta_legacy_output_path "$repo_root" "udp-rollout-comparison-summary-windows.json")"
windows_readiness_path="${VERTA_UDP_RELEASE_BURN_IN_WINDOWS_READINESS_PATH:-${VERTA_UDP_RELEASE_BURN_IN_WINDOWS_READINESS_PATH:-$(verta_prefer_existing_path "$canonical_windows_readiness_path" "$legacy_windows_readiness_path")}}"

canonical_staged_matrix_path="$(verta_output_path "$repo_root" "udp-rollout-matrix-summary-staged.json")"
legacy_staged_matrix_path="$(verta_legacy_output_path "$repo_root" "udp-rollout-matrix-summary-staged.json")"
staged_matrix_path="${VERTA_UDP_RELEASE_BURN_IN_STAGED_MATRIX_PATH:-${VERTA_UDP_RELEASE_BURN_IN_STAGED_MATRIX_PATH:-${VERTA_UDP_RELEASE_EVIDENCE_CHAIN_STAGED_MATRIX_PATH:-${VERTA_UDP_RELEASE_EVIDENCE_CHAIN_STAGED_MATRIX_PATH:-$(verta_prefer_existing_path "$canonical_staged_matrix_path" "$legacy_staged_matrix_path")}}}}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP release burn-in wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-burn-in.sh."

should_mirror_default="false"
if [[ "$#" -eq 0 ]]; then
  set -- \
    --summary-path "$summary_path" \
    --release-candidate-signoff "$release_candidate_signoff_path" \
    --linux-readiness "$linux_readiness_path" \
    --macos-readiness "$macos_readiness_path" \
    --windows-readiness "$windows_readiness_path" \
    --staged-matrix "$staged_matrix_path"
  should_mirror_default="true"
else
  have_summary_path="false"
  for arg in "$@"; do
    if [[ "$arg" == "--summary-path" ]]; then
      have_summary_path="true"
      break
    fi
  done
  if [[ "$have_summary_path" == "false" ]]; then
    set -- --summary-path "$summary_path" "$@"
    should_mirror_default="true"
  fi
fi

echo "==> Running machine-readable UDP release burn-in"
set +e
cargo run -p ns-testkit --example udp_release_burn_in -- "$@"
exit_code=$?
set -e
if [[ "$should_mirror_default" == "true" ]]; then
  verta_mirror_if_canonical_default "$summary_path" "$canonical_summary_path" "$legacy_summary_path"
fi
if [[ "$exit_code" -ne 0 ]]; then
  exit "$exit_code"
fi
