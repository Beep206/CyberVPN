#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OLD_INPUT="${1:-${RELEASE_COMPARISON_BASE:-}}"
NEW_INPUT="${2:-${RELEASE_COMPARISON_HEAD:-HEAD}}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT="${RELEASE_COMPARISON_OUTPUT:-${ROOT_DIR}/docs/evidence/releases/release-comparison-${STAMP}.md}"

mkdir -p "$(dirname "${OUTPUT}")"

has_git_ref() {
  git -C "${ROOT_DIR}" rev-parse --verify --quiet "$1^{commit}" >/dev/null 2>&1
}

list_dir_files() {
  local dir="$1"
  if [[ -d "${dir}" ]]; then
    find "${dir}" -type f | sed "s#^${dir}/##" | sort
  fi
}

count_matches() {
  local pattern="$1"
  local source="$2"
  if [[ -d "${source}" ]]; then
    find "${source}" -type f -iname "${pattern}" | wc -l | tr -d ' '
  else
    printf '0'
  fi
}

{
  printf '# CyberVPN Release Comparison Report\n\n'
  printf '**Generated:** `%s`  \n' "${STAMP}"
  printf '**Base:** `%s`  \n' "${OLD_INPUT:-not-provided}"
  printf '**Head:** `%s`  \n\n' "${NEW_INPUT}"

  printf '## Summary\n\n'
  if [[ -n "${OLD_INPUT}" ]] && has_git_ref "${OLD_INPUT}" && has_git_ref "${NEW_INPUT}"; then
    printf 'Git ref comparison is available.\n\n'
    printf '```text\n'
    git -C "${ROOT_DIR}" diff --name-status "${OLD_INPUT}" "${NEW_INPUT}" -- \
      docs/evidence infra scripts/security scripts/release scripts/sentry .gitlab-ci.yml || true
    printf '```\n\n'
  elif [[ -n "${OLD_INPUT}" && -d "${OLD_INPUT}" && -d "${NEW_INPUT}" ]]; then
    printf 'Evidence directory comparison is available.\n\n'
    printf '### Added or changed file names\n\n'
    printf '```text\n'
    comm -13 <(list_dir_files "${OLD_INPUT}") <(list_dir_files "${NEW_INPUT}") || true
    printf '```\n\n'
  else
    printf 'Base input was not available as a git ref or evidence directory. This report is a checklist-only baseline.\n\n'
  fi

  printf '## Mandatory Evidence Presence\n\n'
  printf '| Artifact family | Base count | Head count | Notes |\n'
  printf '|---|---:|---:|---|\n'
  if [[ -d "${OLD_INPUT:-}" && -d "${NEW_INPUT}" ]]; then
    printf '| release manifests | %s | %s | `*manifest*` |\n' "$(count_matches '*manifest*' "${OLD_INPUT}")" "$(count_matches '*manifest*' "${NEW_INPUT}")"
    printf '| image digests | %s | %s | `*digest*` |\n' "$(count_matches '*digest*' "${OLD_INPUT}")" "$(count_matches '*digest*' "${NEW_INPUT}")"
    printf '| SBOM | %s | %s | `*sbom*` |\n' "$(count_matches '*sbom*' "${OLD_INPUT}")" "$(count_matches '*sbom*' "${NEW_INPUT}")"
    printf '| Trivy reports | %s | %s | `*trivy*` |\n' "$(count_matches '*trivy*' "${OLD_INPUT}")" "$(count_matches '*trivy*' "${NEW_INPUT}")"
    printf '| Grype reports | %s | %s | `*grype*` |\n' "$(count_matches '*grype*' "${OLD_INPUT}")" "$(count_matches '*grype*' "${NEW_INPUT}")"
    printf '| npm audit reports | %s | %s | `*npm*audit*` |\n' "$(count_matches '*npm*audit*' "${OLD_INPUT}")" "$(count_matches '*npm*audit*' "${NEW_INPUT}")"
    printf '| pip audit reports | %s | %s | `*pip*audit*` |\n' "$(count_matches '*pip*audit*' "${OLD_INPUT}")" "$(count_matches '*pip*audit*' "${NEW_INPUT}")"
    printf '| secret scan reports | %s | %s | `*gitleaks*` or `*secret*` |\n' "$(count_matches '*gitleaks*' "${OLD_INPUT}")" "$(count_matches '*gitleaks*' "${NEW_INPUT}")"
  else
    printf '| release manifests | n/a | n/a | provide evidence directories for exact counts |\n'
    printf '| image digests | n/a | n/a | provide evidence directories for exact counts |\n'
    printf '| SBOM | n/a | n/a | release candidate must include SBOM |\n'
    printf '| Trivy reports | n/a | n/a | release candidate must include Trivy output |\n'
    printf '| Grype reports | n/a | n/a | release candidate must include Grype output |\n'
    printf '| npm audit reports | n/a | n/a | required when Node dependencies are present |\n'
    printf '| pip audit reports | n/a | n/a | required when Python lock files are present |\n'
    printf '| secret scan reports | n/a | n/a | required for every release candidate |\n'
  fi

  printf '\n## Operator Checklist\n\n'
  printf '%s\n' '- [ ] Security gates passed or reviewed with written exception.'
  printf '%s\n' '- [ ] SBOM generated for the release candidate.'
  printf '%s\n' '- [ ] Image digests recorded for deployable images.'
  printf '%s\n' '- [ ] Sentry release/deploy marker created where applicable.'
  printf '%s\n' '- [ ] Latest restore drill evidence is not older than 30 days.'
  printf '%s\n' '- [ ] Dashboard and alerting validators passed.'
  printf '%s\n' '- [ ] Rollback path and previous image digests are known.'
} > "${OUTPUT}"

printf '%s\n' "${OUTPUT}"
