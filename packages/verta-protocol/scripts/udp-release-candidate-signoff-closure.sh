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

canonical_summary_path="$(verta_output_path "$repo_root" "udp-release-candidate-signoff-closure-summary.json")"
legacy_summary_path="$(verta_legacy_output_path "$repo_root" "udp-release-candidate-signoff-closure-summary.json")"
summary_path="${VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_SUMMARY_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_SUMMARY_PATH:-$canonical_summary_path}}"

canonical_release_candidate_evidence_freeze_path="$(verta_output_path "$repo_root" "udp-release-candidate-evidence-freeze-summary.json")"
legacy_release_candidate_evidence_freeze_path="$(verta_legacy_output_path "$repo_root" "udp-release-candidate-evidence-freeze-summary.json")"
release_candidate_evidence_freeze_path="${VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_RELEASE_CANDIDATE_EVIDENCE_FREEZE_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_RELEASE_CANDIDATE_EVIDENCE_FREEZE_PATH:-$(verta_prefer_existing_path "$canonical_release_candidate_evidence_freeze_path" "$legacy_release_candidate_evidence_freeze_path")}}"

canonical_linux_readiness_path="$(verta_output_path "$repo_root" "udp-rollout-comparison-summary-linux.json")"
legacy_linux_readiness_path="$(verta_legacy_output_path "$repo_root" "udp-rollout-comparison-summary-linux.json")"
linux_readiness_path="${VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_LINUX_READINESS_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_LINUX_READINESS_PATH:-$(verta_prefer_existing_path "$canonical_linux_readiness_path" "$legacy_linux_readiness_path")}}"

canonical_macos_readiness_path="$(verta_output_path "$repo_root" "udp-rollout-comparison-summary-macos.json")"
legacy_macos_readiness_path="$(verta_legacy_output_path "$repo_root" "udp-rollout-comparison-summary-macos.json")"
macos_readiness_path="${VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_MACOS_READINESS_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_MACOS_READINESS_PATH:-$(verta_prefer_existing_path "$canonical_macos_readiness_path" "$legacy_macos_readiness_path")}}"

canonical_windows_readiness_path="$(verta_output_path "$repo_root" "udp-rollout-comparison-summary-windows.json")"
legacy_windows_readiness_path="$(verta_legacy_output_path "$repo_root" "udp-rollout-comparison-summary-windows.json")"
windows_readiness_path="${VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_WINDOWS_READINESS_PATH:-${VERTA_UDP_RELEASE_CANDIDATE_SIGNOFF_CLOSURE_WINDOWS_READINESS_PATH:-$(verta_prefer_existing_path "$canonical_windows_readiness_path" "$legacy_windows_readiness_path")}}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP release candidate signoff closure wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-candidate-signoff-closure.sh."

should_mirror_default="false"
if [[ "$#" -eq 0 ]]; then
  set -- \
    --summary-path "$summary_path" \
    --release-candidate-evidence-freeze "$release_candidate_evidence_freeze_path" \
    --linux-readiness "$linux_readiness_path" \
    --macos-readiness "$macos_readiness_path" \
    --windows-readiness "$windows_readiness_path"
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

echo "==> Running machine-readable UDP release candidate signoff closure"
set +e
cargo run -p ns-testkit --example udp_release_candidate_signoff_closure -- "$@"
exit_code=$?
set -e
if [[ "$should_mirror_default" == "true" ]]; then
  verta_mirror_if_canonical_default "$summary_path" "$canonical_summary_path" "$legacy_summary_path"
fi
if [[ "$exit_code" -ne 0 ]]; then
  exit "$exit_code"
fi
