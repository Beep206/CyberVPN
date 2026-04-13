#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

escape_sed_replacement() {
  printf '%s' "$1" | sed -e 's/[\/&]/\\&/g'
}

title="${1:-}"
[[ -n "$title" ]] || fail "Usage: ./scripts/new-adr.sh \"ADR title\""

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
template_path="$repo_root/docs/templates/adr-template.md"
adr_dir="$repo_root/docs/adr"

[[ -f "$template_path" ]] || fail "ADR template not found at $template_path."
mkdir -p "$adr_dir"

last_number="$(find "$adr_dir" -maxdepth 1 -type f -name '*.md' -printf '%f\n' 2>/dev/null | sed -n 's/^\([0-9][0-9][0-9][0-9]\)-.*$/\1/p' | sort | tail -n 1)"
if [[ -z "$last_number" ]]; then
  next_number="0001"
else
  next_number="$(printf '%04d' "$((10#$last_number + 1))")"
fi

slug="$(printf '%s' "$title" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')"
[[ -n "$slug" ]] || fail "Title '$title' did not produce a valid ADR slug."

output_path="$adr_dir/$next_number-$slug.md"
[[ ! -e "$output_path" ]] || fail "ADR already exists at $output_path."

title_escaped="$(escape_sed_replacement "$title")"
date_escaped="$(escape_sed_replacement "$(date +%F)")"

sed \
  -e "s/{{ADR_NUMBER}}/$next_number/g" \
  -e "s/{{ADR_TITLE}}/$title_escaped/g" \
  -e "s/{{ADR_DATE}}/$date_escaped/g" \
  -e "s/{{ADR_STATUS}}/Proposed/g" \
  "$template_path" > "$output_path"

echo "Created ADR: $output_path"
