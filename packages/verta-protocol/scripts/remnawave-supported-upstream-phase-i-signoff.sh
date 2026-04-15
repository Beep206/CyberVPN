#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")"/.. && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/verta-compat.sh"

verta_sync_phase_i_envs

canonical_upstream_summary_path="$(verta_output_path "$repo_root" "remnawave-supported-upstream-summary.json")"
legacy_upstream_summary_path="$(verta_legacy_output_path "$repo_root" "remnawave-supported-upstream-summary.json")"
upstream_summary_path="${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_PATH:-${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_SUMMARY_PATH:-$canonical_upstream_summary_path}}"

canonical_lifecycle_summary_path="$(verta_output_path "$repo_root" "remnawave-supported-upstream-lifecycle-summary.json")"
legacy_lifecycle_summary_path="$(verta_legacy_output_path "$repo_root" "remnawave-supported-upstream-lifecycle-summary.json")"
lifecycle_summary_path="${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_SUMMARY_PATH:-${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_LIFECYCLE_SUMMARY_PATH:-$canonical_lifecycle_summary_path}}"

canonical_deployment_reality_summary_path="$(verta_output_path "$repo_root" "remnawave-supported-upstream-deployment-reality-summary.json")"
legacy_deployment_reality_summary_path="$(verta_legacy_output_path "$repo_root" "remnawave-supported-upstream-deployment-reality-summary.json")"
deployment_reality_summary_path="${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_REALITY_SUMMARY_PATH:-${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_REALITY_SUMMARY_PATH:-$canonical_deployment_reality_summary_path}}"

canonical_phase_i_summary_path="$(verta_output_path "$repo_root" "remnawave-supported-upstream-phase-i-signoff-summary.json")"
legacy_phase_i_summary_path="$(verta_legacy_output_path "$repo_root" "remnawave-supported-upstream-phase-i-signoff-summary.json")"
phase_i_summary_path="${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_PHASE_I_SIGNOFF_SUMMARY_PATH:-${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_PHASE_I_SIGNOFF_SUMMARY_PATH:-$canonical_phase_i_summary_path}}"

if ! command -v cargo >/dev/null 2>&1; then
  echo "cargo was not found. Install the Rust stable toolchain before running the supported-upstream Phase I signoff wrapper." >&2
  exit 1
fi

if [[ ! -f "$workspace_manifest" ]]; then
  echo "No root Cargo.toml was found at $workspace_manifest. Verta is still in setup-only state; bootstrap the Rust workspace before using scripts/remnawave-supported-upstream-phase-i-signoff.sh." >&2
  exit 1
fi

have_supported_upstream_env() {
  [[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL:-}" ]] \
    && [[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN:-}" ]] \
    && [[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT:-}" ]] \
    && [[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_SIGNATURE:-}" ]] \
    && [[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID:-}" ]] \
    && [[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_STORE_AUTH_TOKEN:-}" ]] \
    && [[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_LABEL:-}" ]]
}

run_lane() {
  local label="$1"
  local expected_summary="$2"
  shift 2

  echo "==> Running $label"
  rm -f -- "$expected_summary"
  set +e
  cargo "$@"
  local exit_code=$?
  set -e

  if [[ $exit_code -ne 0 && ! -f "$expected_summary" ]]; then
    return "$exit_code"
  fi
  if [[ $exit_code -ne 0 ]]; then
    echo "   Lane returned non-ready status; continuing because $expected_summary exists."
  fi
}

if ! have_supported_upstream_env; then
  exec bash "$repo_root/scripts/with-local-remnawave-supported-upstream-env.sh" \
    bash "$0" "$@"
fi

export canonical_upstream_summary_path
export legacy_upstream_summary_path
export canonical_lifecycle_summary_path
export legacy_lifecycle_summary_path
export canonical_deployment_reality_summary_path
export legacy_deployment_reality_summary_path
export canonical_phase_i_summary_path
export legacy_phase_i_summary_path

exec bash -lc '
run_lane() {
  local label="$1"
  local expected_summary="$2"
  shift 2

  echo "==> Running $label"
  rm -f -- "$expected_summary"
  set +e
  cargo "$@"
  local exit_code=$?
  set -e

  if [[ $exit_code -ne 0 && ! -f "$expected_summary" ]]; then
    return "$exit_code"
  fi
  if [[ $exit_code -ne 0 ]]; then
    echo "   Lane returned non-ready status; continuing because $expected_summary exists."
  fi
}

repo_root="$1"
upstream_summary_path="$2"
lifecycle_summary_path="$3"
deployment_reality_summary_path="$4"
phase_i_summary_path="$5"
shift 5
source "$repo_root/scripts/verta-compat.sh"

if [[ -n "${VERTA_SUPPORTED_UPSTREAM_ENABLE_COMMAND:-}" ]]; then
  eval "$VERTA_SUPPORTED_UPSTREAM_ENABLE_COMMAND"
elif [[ "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_LABEL:-}" == "remnawave-local-docker" ]]; then
  bash "$repo_root/scripts/ensure-local-remnawave-supported-upstream-user-active.sh"
fi

run_lane "Remnawave supported-upstream verification" "$upstream_summary_path" \
  run -p ns-testkit --example remnawave_supported_upstream_verification -- \
  --summary-path "$upstream_summary_path"
verta_mirror_if_canonical_default "$upstream_summary_path" "$canonical_upstream_summary_path" "$legacy_upstream_summary_path"

bash "$repo_root/scripts/operator-profile-disable-drill.sh" --summary-path "$lifecycle_summary_path"
verta_mirror_if_canonical_default "$lifecycle_summary_path" "$canonical_lifecycle_summary_path" "$legacy_lifecycle_summary_path"
if [[ -n "${VERTA_SUPPORTED_UPSTREAM_ENABLE_COMMAND:-}" ]]; then
  eval "$VERTA_SUPPORTED_UPSTREAM_ENABLE_COMMAND"
elif [[ "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_DEPLOYMENT_LABEL:-}" == "remnawave-local-docker" ]]; then
  bash "$repo_root/scripts/ensure-local-remnawave-supported-upstream-user-active.sh"
fi

run_lane "Remnawave supported-upstream deployment-reality verification" "$deployment_reality_summary_path" \
  run -p ns-testkit --example remnawave_supported_upstream_deployment_reality_verification -- \
  --summary-path "$deployment_reality_summary_path" \
  --supported-upstream-summary "$upstream_summary_path" \
  --supported-upstream-lifecycle-summary "$lifecycle_summary_path"
verta_mirror_if_canonical_default "$deployment_reality_summary_path" "$canonical_deployment_reality_summary_path" "$legacy_deployment_reality_summary_path"

run_lane "Remnawave supported-upstream Phase I signoff" "$phase_i_summary_path" \
  run -p ns-testkit --example remnawave_supported_upstream_phase_i_signoff -- \
  --summary-path "$phase_i_summary_path" \
  --upstream-summary-path "$upstream_summary_path" \
  --lifecycle-summary-path "$lifecycle_summary_path" \
  --deployment-reality-summary-path "$deployment_reality_summary_path" \
  "$@"
verta_mirror_if_canonical_default "$phase_i_summary_path" "$canonical_phase_i_summary_path" "$legacy_phase_i_summary_path"
' bash "$repo_root" "$upstream_summary_path" "$lifecycle_summary_path" "$deployment_reality_summary_path" "$phase_i_summary_path" "$@"
