#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
transition_delay_seconds="${NORTHSTAR_SUPPORTED_UPSTREAM_DISABLE_DELAY_SECONDS:-2}"

echo "==> Running operator profile-disable drill"
exec bash "$script_dir/with-local-remnawave-supported-upstream-env.sh" \
  bash -lc '
script_dir="$1"
transition_delay_seconds="$2"
shift 2

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
