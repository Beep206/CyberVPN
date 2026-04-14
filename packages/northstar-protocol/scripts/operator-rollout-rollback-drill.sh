#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
workspace_manifest="$repo_root/Cargo.toml"
summary_path="${NORTHSTAR_OPERATOR_ROLLOUT_ROLLBACK_DRILL_SUMMARY_PATH:-$repo_root/target/northstar/operator-rollout-rollback-drill-summary.json}"
artifact_root="${NORTHSTAR_OPERATOR_ROLLOUT_ROLLBACK_DRILL_ARTIFACT_ROOT:-$repo_root/target/northstar/operator-rollback-drill}"
deployment_label="${NORTHSTAR_OPERATOR_ROLLOUT_ROLLBACK_DRILL_DEPLOYMENT_LABEL:-operator-rollback-drill}"
host_label="${NORTHSTAR_OPERATOR_ROLLOUT_ROLLBACK_DRILL_HOST_LABEL:-local-operator}"
summary_path="${NORTHSTAR_UDP_NET_CHAOS_SUMMARY_PATH:-$summary_path}"
artifact_root="${NORTHSTAR_UDP_NET_CHAOS_ARTIFACT_ROOT:-$artifact_root}"

command -v cargo >/dev/null 2>&1 || fail "cargo was not found. Install the Rust stable toolchain before running the operator rollback drill wrapper."
command -v unshare >/dev/null 2>&1 || fail "unshare was not found. Install util-linux before running the operator rollback drill wrapper."
command -v tc >/dev/null 2>&1 || fail "tc was not found. Install iproute2 before running the operator rollback drill wrapper."
command -v tcpdump >/dev/null 2>&1 || fail "tcpdump was not found. Install tcpdump before running the operator rollback drill wrapper."
[[ -f "$workspace_manifest" ]] || fail "No root Cargo.toml was found at $workspace_manifest. Northstar is still in setup-only state; bootstrap the Rust workspace before using scripts/operator-rollout-rollback-drill.sh."

have_summary_path=0
have_artifact_root=0
have_deployment_label=0
have_host_label=0
have_profile=0
run_all=0
expects_value=0
for arg in "$@"; do
  if [[ "$expects_value" -eq 1 ]]; then
    expects_value=0
    continue
  fi
  case "$arg" in
    --summary-path)
      have_summary_path=1
      expects_value=1
      ;;
    --artifact-root)
      have_artifact_root=1
      expects_value=1
      ;;
    --deployment-label)
      have_deployment_label=1
      expects_value=1
      ;;
    --host-label)
      have_host_label=1
      expects_value=1
      ;;
    --format)
      expects_value=1
      ;;
    --all)
      run_all=1
      ;;
    --help|-h)
      ;;
    -*)
      ;;
    *)
      have_profile=1
      ;;
  esac
done

if [[ "$have_profile" -eq 0 && "$run_all" -eq 0 ]]; then
  set -- --profile udp-blocked "$@"
fi
if [[ "$have_summary_path" -eq 0 ]]; then
  set -- "$@" --summary-path "$summary_path"
fi
if [[ "$have_artifact_root" -eq 0 ]]; then
  set -- "$@" --artifact-root "$artifact_root"
fi
if [[ "$have_deployment_label" -eq 0 ]]; then
  set -- "$@" --deployment-label "$deployment_label"
fi
if [[ "$have_host_label" -eq 0 ]]; then
  set -- "$@" --host-label "$host_label"
fi

echo "==> Running operator rollout rollback drill"
cargo run -p ns-testkit --example udp_net_chaos_campaign -- "$@"
