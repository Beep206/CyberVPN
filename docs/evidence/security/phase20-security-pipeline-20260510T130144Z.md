# Phase 20 Security Pipeline Evidence

Date: 2026-05-10

Project: CyberVPN

## Summary

Phase 20 adds repeatable CI security jobs and local rerun scripts for secret scanning, dependency auditing, filesystem/container-adjacent scanning, and SBOM generation.

Local evidence artifacts were generated under:

```text
.tmp/phase20-security
```

Canonical server evidence target:

```text
/srv/storage/evidence/security-scans/cybervpn-h-phase20-security-pipeline-20260510T130144Z
```

## CI Jobs Added

```text
security:gitleaks
npm-audit:high
pip-audit:python-locks
container-scan:trivy-grype
sbom:release-candidate
```

Security jobs run on schedules, tags, and explicit release-candidate web pipelines with:

```text
SECURITY_RELEASE_CANDIDATE=true
```

The security jobs do not mount `/var/run/docker.sock`. Existing Docker-in-Docker package jobs remain manual and isolated behind the `dind` runner tag.

Scanner versions:

```text
Trivy 0.70.0
Grype 0.112.0
Syft 1.44.0
Gitleaks 8.30.1
```

## Local Validation

```text
bash -n scripts/security/scan-secrets.sh scripts/security/audit-dependencies.sh scripts/security/scan-filesystem-vulnerabilities.sh scripts/security/generate-sbom.sh
python3 scripts/validate_gitlab_ci_contract.py
python3 GitLab CI YAML parse check
git diff --check
```

Result:

```text
PASS
```

## Secret Scan

Command:

```bash
SECURITY_ARTIFACT_DIR="$PWD/.tmp/phase20-security" GITLEAKS_EXIT_CODE=1 scripts/security/scan-secrets.sh
```

Result:

```text
Gitleaks findings: 0
```

Artifacts:

```text
gitleaks-s1-current-tree-redacted.json
gitleaks-s1-current-tree-by-file.tsv
gitleaks-s1-current-tree-by-rule.tsv
```

## Dependency Scan

Command:

```bash
SECURITY_ARTIFACT_DIR="$PWD/.tmp/phase20-security" scripts/security/audit-dependencies.sh npm
PYENV_VERSION=3.13.11 SECURITY_ARTIFACT_DIR="$PWD/.tmp/phase20-security" scripts/security/audit-dependencies.sh python
```

Results:

```text
npm root high/critical: 0/0
npm admin high/critical: 0/0
npm frontend high/critical: 0/0
npm partner high/critical: 0/0
pip-audit backend vulnerabilities: 0
pip-audit task-worker vulnerabilities: 0
pip-audit telegram-bot vulnerabilities: 0
```

Known npm note: `npm audit --audit-level=high` passes. The reports still contain two moderate advisories through Next/PostCSS, which are not treated as Phase 20 blockers.

## Container And Filesystem Scan

Command:

```bash
SECURITY_ARTIFACT_DIR="$PWD/.tmp/phase20-security" scripts/security/scan-filesystem-vulnerabilities.sh
```

Results:

```text
Trivy: CRITICAL=1, HIGH=24, MEDIUM=36, LOW=25
Grype: Critical=17, High=135, Medium=132, Low=42
```

Notes:

- Generated/cache directories are excluded: `.git`, `node_modules`, `.tmp`, `.cache`, `.terraform`, `.venv`, `build`, `dist`, `target`, `.next`, `.dart_tool`, `.gradle`, and coverage outputs.
- Trivy generated `trivy-fs.json`.
- Grype generated `grype-dir.json`.
- The remaining high/critical findings are release-triage inputs, mainly from non-S1 or auxiliary lockfiles such as SDK, desktop/Rust, and app-specific package locks. They are intentionally preserved as evidence.

Artifacts:

```text
container/trivy-fs.json
container/grype-dir.json
```

## SBOM

Command:

```bash
SECURITY_ARTIFACT_DIR="$PWD/.tmp/phase20-security" scripts/security/generate-sbom.sh
```

Results:

```text
CycloneDX components: 5953
SPDX SBOM generated: yes
```

Artifacts:

```text
sbom/cybervpn-sbom.cyclonedx.json
sbom/cybervpn-sbom.spdx.json
```

## Acceptance Status

```text
Secret scan job runs: yes
Dependency scan job runs: yes
Container scan job runs: yes
SBOM artifact generated for release candidates: yes
Security scan results stored as release evidence: yes
```

## Follow-Up Triage

Before treating a release candidate as shippable, triage the high/critical Trivy and Grype findings and decide which packages are in S1 scope, which are generated artifacts, and which require dependency upgrades.
