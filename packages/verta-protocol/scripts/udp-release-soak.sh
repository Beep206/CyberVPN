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

canonical_summary_path="$(verta_output_path "$repo_root" "udp-release-soak-summary.json")"
legacy_summary_path="$(verta_legacy_output_path "$repo_root" "udp-release-soak-summary.json")"
summary_path="${VERTA_UDP_RELEASE_SOAK_SUMMARY_PATH:-${VERTA_UDP_RELEASE_SOAK_SUMMARY_PATH:-$canonical_summary_path}}"

canonical_release_burn_in_path="$(verta_output_path "$repo_root" "udp-release-burn-in-summary.json")"
legacy_release_burn_in_path="$(verta_legacy_output_path "$repo_root" "udp-release-burn-in-summary.json")"
release_burn_in_path="${VERTA_UDP_RELEASE_SOAK_RELEASE_BURN_IN_PATH:-${VERTA_UDP_RELEASE_SOAK_RELEASE_BURN_IN_PATH:-$(verta_prefer_existing_path "$canonical_release_burn_in_path" "$legacy_release_burn_in_path")}}"

canonical_linux_interop_path="$(verta_output_path "$repo_root" "udp-interop-lab-summary-linux.json")"
legacy_linux_interop_path="$(verta_legacy_output_path "$repo_root" "udp-interop-lab-summary-linux.json")"
linux_interop_path="${VERTA_UDP_RELEASE_SOAK_LINUX_INTEROP_PATH:-${VERTA_UDP_RELEASE_SOAK_LINUX_INTEROP_PATH:-$(verta_prefer_existing_path "$canonical_linux_interop_path" "$legacy_linux_interop_path")}}"

canonical_macos_interop_path="$(verta_output_path "$repo_root" "udp-interop-lab-summary-macos.json")"
legacy_macos_interop_path="$(verta_legacy_output_path "$repo_root" "udp-interop-lab-summary-macos.json")"
macos_interop_path="${VERTA_UDP_RELEASE_SOAK_MACOS_INTEROP_PATH:-${VERTA_UDP_RELEASE_SOAK_MACOS_INTEROP_PATH:-$(verta_prefer_existing_path "$canonical_macos_interop_path" "$legacy_macos_interop_path")}}"

canonical_windows_interop_path="$(verta_output_path "$repo_root" "udp-interop-lab-summary-windows.json")"
legacy_windows_interop_path="$(verta_legacy_output_path "$repo_root" "udp-interop-lab-summary-windows.json")"
windows_interop_path="${VERTA_UDP_RELEASE_SOAK_WINDOWS_INTEROP_PATH:-${VERTA_UDP_RELEASE_SOAK_WINDOWS_INTEROP_PATH:-$(verta_prefer_existing_path "$canonical_windows_interop_path" "$legacy_windows_interop_path")}}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the UDP release soak wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/udp-release-soak.sh."

should_mirror_default="false"
if [[ "$#" -eq 0 ]]; then
  set -- \
    --summary-path "$summary_path" \
    --release-burn-in "$release_burn_in_path" \
    --linux-interop "$linux_interop_path" \
    --macos-interop "$macos_interop_path" \
    --windows-interop "$windows_interop_path"
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

echo "==> Running machine-readable UDP release soak"
set +e
cargo run -p ns-testkit --example udp_release_soak -- "$@"
exit_code=$?
set -e
if [[ "$should_mirror_default" == "true" ]]; then
  verta_mirror_if_canonical_default "$summary_path" "$canonical_summary_path" "$legacy_summary_path"
fi
if [[ "$exit_code" -ne 0 ]]; then
  exit "$exit_code"
fi
