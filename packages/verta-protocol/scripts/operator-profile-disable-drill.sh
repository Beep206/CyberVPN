#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/verta-compat.sh"

verta_sync_phase_i_envs

transition_delay_seconds="${VERTA_SUPPORTED_UPSTREAM_DISABLE_DELAY_SECONDS:-2}"

have_supported_upstream_env() {
  [[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BASE_URL:-}" ]] \
    && [[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_API_TOKEN:-}" ]] \
    && [[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_BOOTSTRAP_SUBJECT:-}" ]] \
    && [[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_WEBHOOK_SIGNATURE:-}" ]] \
    && [[ -n "${VERTA_REMNAWAVE_SUPPORTED_UPSTREAM_EXPECTED_ACCOUNT_ID:-}" ]]
}

echo "==> Running operator profile-disable drill"
if ! have_supported_upstream_env; then
  exec bash "$script_dir/with-local-remnawave-supported-upstream-env.sh" \
    bash "$0" "$@"
fi

exec \
  bash -lc '
script_dir="$1"
transition_delay_seconds="$2"
shift 2

if [[ -n "${VERTA_SUPPORTED_UPSTREAM_DISABLE_COMMAND:-}" ]]; then
  eval "${VERTA_SUPPORTED_UPSTREAM_ENABLE_COMMAND:-true}"
  (
    sleep "$transition_delay_seconds"
    eval "$VERTA_SUPPORTED_UPSTREAM_DISABLE_COMMAND"
  ) &
  disable_pid=$!

  set +e
  bash "$script_dir/remnawave-supported-upstream-lifecycle-verify.sh" "$@"
  exit_code=$?
  set -e

  wait "$disable_pid"
  exit "$exit_code"
fi

bash "$script_dir/ensure-local-remnawave-supported-upstream-user-active.sh"
(
  sleep "$transition_delay_seconds"
  bash "$script_dir/ensure-local-remnawave-supported-upstream-user-disabled.sh"
) &
disable_pid=$!

set +e
bash "$script_dir/remnawave-supported-upstream-lifecycle-verify.sh" "$@"
exit_code=$?
set -e

wait "$disable_pid"
exit "$exit_code"
' bash "$script_dir" "$transition_delay_seconds" "$@"
