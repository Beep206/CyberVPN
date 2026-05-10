# Security Pipeline Runbook

Host GitLab: `gitlab.h.cyber-vpn.net`

Project: `root/CyberVPN`

## Scope

Phase 20 adds CI jobs and repeatable local scripts for:

- Gitleaks current-tree secret scanning
- `npm audit` high/critical gate for the root, `admin`, `frontend`, and `partner` lockfiles
- `pip-audit` from `uv.lock` exports
- Trivy filesystem/container-adjacent scanning
- Grype filesystem/package scanning
- Syft SBOM generation

## CI Jobs

```text
security:gitleaks
npm-audit:high
pip-audit:python-locks
container-scan:trivy-grype
sbom:release-candidate
```

These jobs do not mount `/var/run/docker.sock` and do not require Docker-in-Docker.

The existing manual package jobs remain isolated behind the `dind` runner tag.

Security jobs run on schedules, tags, and explicit release-candidate web
pipelines with:

```text
SECURITY_RELEASE_CANDIDATE=true
```

Pinned scanner versions:

```text
TRIVY_VERSION=0.70.0
GRYPE_VERSION=0.112.0
SYFT_VERSION=1.44.0
```

The CI jobs verify SHA256 checksums before extracting downloaded scanner binaries.

## Artifacts

GitLab stores artifacts under:

```text
security-artifacts/
```

Release evidence should be copied to:

```text
/srv/storage/evidence/security-scans/<release-or-baseline-id>
```

## Local Re-run

From the repository root:

```bash
SECURITY_ARTIFACT_DIR=.tmp/phase20-security scripts/security/scan-secrets.sh
SECURITY_ARTIFACT_DIR=.tmp/phase20-security scripts/security/audit-dependencies.sh all
SECURITY_ARTIFACT_DIR=.tmp/phase20-security scripts/security/scan-filesystem-vulnerabilities.sh
SECURITY_ARTIFACT_DIR=.tmp/phase20-security scripts/security/generate-sbom.sh
```

## Policy

- Production secrets must not be committed to the repository.
- Production secrets must not be stored in home GitLab without encryption.
- `.env` files must stay `0600` on hosts and must remain ignored by Git.
- Docker socket must not be mounted into untrusted CI jobs.
- Security scan outputs are release evidence.

## Current Baselines

Gitleaks uses the redacted accepted baseline:

```text
.gitleaks.s1.current-tree.baseline.json
```

New findings must be reviewed. Real secrets must be removed and rotated. Test fixtures may be added to the baseline only with evidence and redacted values.
