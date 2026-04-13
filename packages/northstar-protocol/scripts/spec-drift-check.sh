#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
index_path="$repo_root/docs/spec/INDEX.md"

expected_docs=(
  "docs/spec/adaptive_proxy_vpn_protocol_master_plan.md"
  "docs/spec/northstar_blueprint_v0.md"
  "docs/spec/northstar_wire_format_freeze_candidate_v0_1.md"
  "docs/spec/northstar_remnawave_bridge_spec_v0_1.md"
  "docs/spec/northstar_threat_model_v0_1.md"
  "docs/spec/northstar_security_test_and_interop_plan_v0_1.md"
  "docs/spec/northstar_implementation_spec_rust_workspace_plan_v0_1.md"
  "docs/spec/northstar_protocol_rfc_draft_v0_1.md"
)

[[ -f "$index_path" ]] || fail "Spec index not found at $index_path."
index_content="$(cat "$index_path")"

missing_files=()
unindexed_files=()

for doc in "${expected_docs[@]}"; do
  [[ -f "$repo_root/$doc" ]] || missing_files+=("$doc")
  leaf_name="$(basename "$doc")"
  grep -Fq "$leaf_name" <<<"$index_content" || unindexed_files+=("$doc")
done

if (( ${#missing_files[@]} > 0 )); then
  printf 'ERROR: Missing authoritative spec files:\n' >&2
  printf ' - %s\n' "${missing_files[@]}" >&2
  exit 1
fi

if (( ${#unindexed_files[@]} > 0 )); then
  printf 'ERROR: Spec index is missing entries for:\n' >&2
  printf ' - %s\n' "${unindexed_files[@]}" >&2
  exit 1
fi

if [[ ! -f "$repo_root/Cargo.toml" ]]; then
  echo "Authoritative specs are present and indexed."
  echo "Deep code-vs-spec drift checks are not active yet because the Rust workspace has not been bootstrapped."
  exit 0
fi

echo "Authoritative specs are present and indexed."
echo "WARNING: This script currently performs baseline spec presence checks only. Extend it with code-vs-spec assertions once production crates exist."
