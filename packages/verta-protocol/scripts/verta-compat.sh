#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo "error: scripts/verta-compat.sh must be sourced, not executed directly." >&2
  exit 1
fi

verta_sync_global_envs() {
  :
}

verta_sync_rollout_readiness_envs() {
  verta_sync_global_envs
}

verta_sync_phase_i_envs() {
  verta_sync_global_envs
}

verta_sync_phase_n_envs() {
  verta_sync_global_envs
}

verta_sync_phase_j_envs() {
  verta_sync_global_envs
}

verta_sync_phase_l_envs() {
  verta_sync_phase_i_envs
  verta_sync_phase_j_envs
}

verta_sync_phase_m_envs() {
  verta_sync_phase_l_envs
}

verta_sync_release_evidence_envs() {
  verta_sync_global_envs
}

verta_target_root() {
  local repo_root="$1"
  printf '%s\n' "${VERTA_TARGET_ROOT:-$repo_root/target/verta}"
}

verta_output_path() {
  local repo_root="$1"
  local file_name="$2"
  printf '%s/%s\n' "$(verta_target_root "$repo_root")" "$file_name"
}

verta_legacy_output_path() {
  verta_output_path "$@"
}

verta_prefer_existing_path() {
  local primary_path="$1"
  local fallback_path="$2"
  if [[ -e "$primary_path" ]]; then
    printf '%s\n' "$primary_path"
  else
    printf '%s\n' "$fallback_path"
  fi
}

verta_mirror_if_canonical_default() {
  :
}
