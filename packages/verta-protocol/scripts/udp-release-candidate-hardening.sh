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

canonical_summary_path="$(verta_output_path "$repo_root" "udp-release-candidate-hardening-summary.json")"
legacy_summary_path="$(verta_legacy_output_path "$repo_root" "udp-release-candidate-hardening-summary.json")"
summary_path="${VERTA_UDP_RELEASE_CANDIDATE_HARDENING_SUMMARY_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_HARDENING_SUMMARY_PATH:-$canonical_summary_path}}"

canonical_release_candidate_consolidation_path="$(verta_output_path "$repo_root" "udp-release-candidate-consolidation-summary.json")"
legacy_release_candidate_consolidation_path="$(verta_legacy_output_path "$repo_root" "udp-release-candidate-consolidation-summary.json")"
release_candidate_consolidation_path="${VERTA_UDP_RELEASE_CANDIDATE_HARDENING_RELEASE_CANDIDATE_CONSOLIDATION_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_HARDENING_RELEASE_CANDIDATE_CONSOLIDATION_PATH:-$(verta_prefer_existing_path "$canonical_release_candidate_consolidation_path" "$legacy_release_candidate_consolidation_path")}}"

canonical_linux_validation_path="$(verta_output_path "$repo_root" "udp-rollout-validation-summary-linux.json")"
legacy_linux_validation_path="$(verta_legacy_output_path "$repo_root" "udp-rollout-validation-summary-linux.json")"
linux_validation_path="${VERTA_UDP_RELEASE_CANDIDATE_HARDENING_LINUX_VALIDATION_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_HARDENING_LINUX_VALIDATION_PATH:-$(verta_prefer_existing_path "$canonical_linux_validation_path" "$legacy_linux_validation_path")}}"

canonical_macos_validation_path="$(verta_output_path "$repo_root" "udp-rollout-validation-summary-macos.json")"
legacy_macos_validation_path="$(verta_legacy_output_path "$repo_root" "udp-rollout-validation-summary-macos.json")"
macos_validation_path="${VERTA_UDP_RELEASE_CANDIDATE_HARDENING_MACOS_VALIDATION_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_HARDENING_MACOS_VALIDATION_PATH:-$(verta_prefer_existing_path "$canonical_macos_validation_path" "$legacy_macos_validation_path")}}"

canonical_windows_validation_path="$(verta_output_path "$repo_root" "udp-rollout-validation-summary-windows.json")"
legacy_windows_validation_path="$(verta_legacy_output_path "$repo_root" "udp-rollout-validation-summary-windows.json")"
windows_validation_path="${VERTA_UDP_RELEASE_CANDIDATE_HARDENING_WINDOWS_VALIDATION_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_HARDENING_WINDOWS_VALIDATION_PATH:-$(verta_prefer_existing_path "$canonical_windows_validation_path" "$legacy_windows_validation_path")}}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate hardening wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-hardening.sh."

should_mirror_default="false"
if [[ "$#" -eq 0 ]]; then
  set -- \
    --summary-path "$summary_path" \
    --release-candidate-consolidation "$release_candidate_consolidation_path" \
    --linux-validation "$linux_validation_path" \
    --macos-validation "$macos_validation_path" \
    --windows-validation "$windows_validation_path"
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

echo "==> Running machine-readable UDP release candidate hardening"
set +e
cargo run -p ns-testkit --example udp_release_candidate_hardening -- "$@"
exit_code=$?
set -e
if [[ "$should_mirror_default" == "true" ]]; then
  verta_mirror_if_canonical_default "$summary_path" "$canonical_summary_path" "$legacy_summary_path"
fi
if [[ "$exit_code" -ne 0 ]]; then
  exit "$exit_code"
fi
