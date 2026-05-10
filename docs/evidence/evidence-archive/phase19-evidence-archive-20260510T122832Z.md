# Phase 19 Evidence Archive Evidence

Date: `2026-05-10`

Host: `cybervpn-h-ops`

Server: `10.10.10.34`

## Scope

Phase 19 creates the canonical evidence archive for CyberVPN h and stores the first baseline evidence pack.

## Remote Paths

Canonical evidence tree:

```text
/srv/storage/evidence/releases
/srv/storage/evidence/backups
/srv/storage/evidence/restores
/srv/storage/evidence/security-scans
/srv/storage/evidence/incidents
```

Baseline pack:

```text
/srv/storage/evidence/releases/cybervpn-h-baseline-20260510T122832Z
```

Baseline security scan pack:

```text
/srv/storage/evidence/security-scans/cybervpn-h-baseline-20260510T122832Z
```

## Installed Files

```text
/srv/cybervpn-h/scripts/create-baseline-evidence-pack.sh
/srv/cybervpn-h/scripts/evidence-retention-report.sh
/srv/cybervpn-h/runbooks/evidence-archive.md
```

Local source files:

```text
infra/evidence/create-baseline-evidence-pack.sh
infra/evidence/evidence-retention-report.sh
docs/runbooks/EVIDENCE_ARCHIVE.md
```

## Baseline Pack Contents

The baseline pack contains `39` files across:

```text
host
services
backups
observability
security
configs
```

Key artifacts:

```text
manifest.json
checksums.sha256
evidence-tree.txt
retention-report.txt
host/lsblk.txt
host/df.txt
services/docker-ps.txt
services/docker-compose-ps.txt
services/systemd-timers.txt
backups/restic-snapshots.txt
backups/gitlab-backups.txt
backups/sentry-backups.txt
observability/prometheus-targets.json
observability/prometheus-active-alerts.json
observability/alertmanager-status.json
security/ufw-status.txt
security/fail2ban-status.txt
security/sshd-effective-security.txt
security/secret-file-permissions.txt
```

Secret values are not copied. Secret files are represented only by permissions and ownership metadata.

## Security Scan Pack

Security scan pack files:

```text
checksums.sha256
fail2ban-status.txt
npm-audit-critical.txt
pip-audit.txt
secret-file-permissions.txt
secret-scan-sanitized.txt
static-dangerous-patterns.txt
tool-availability.txt
ufw-status.txt
```

Local audit summary:

```text
npm audit --omit=dev --audit-level=critical: exit_code=0
pip-audit via PYENV_VERSION=3.13.11: exit_code=1
```

`npm audit` reported no critical vulnerabilities, but did report the already-known moderate `postcss` issue through `next`.

`pip-audit` found `37` known vulnerabilities in `18` packages in the local Python audit environment. This is evidence for Phase 20 triage; it is not treated as a Phase 19 blocker because Phase 19 only establishes archive storage and baseline reporting.

Secret scan:

```text
redacted lines: 2045
known high-risk token patterns in stored evidence: 0
```

The sanitized report keeps paths and key names but removes values.

Static scan:

```text
rg_exit_code=1
```

No dangerous patterns were found in the new Phase 19 scripts/docs by the static pattern scan.

## Retention Policy

Retention policy is documented in:

```text
docs/runbooks/EVIDENCE_ARCHIVE.md
/srv/cybervpn-h/runbooks/evidence-archive.md
```

Policy summary:

```text
releases: keep indefinitely
incidents: keep indefinitely
restores: keep at least 24 months
backups: keep evidence logs at least 12 months
security-scans: keep at least 12 months
```

No automatic destructive cleanup is enabled. Cleanup script defaults to dry-run:

```text
/srv/cybervpn-h/scripts/evidence-retention-report.sh
```

Dry-run result:

```text
mode=dry-run
apply_status=dry_run_only
```

## Verification

Evidence tree verification:

```text
ok:releases
ok:backups
ok:restores
ok:security-scans
ok:incidents
```

Manifest verification:

```text
Phase 19: Evidence Archive
```

Permissions:

```text
750 root:root /srv/storage/evidence
750 root:root /srv/storage/evidence/releases
750 root:root /srv/storage/evidence/releases/cybervpn-h-baseline-20260510T122832Z
750 root:root /srv/storage/evidence/security-scans/cybervpn-h-baseline-20260510T122832Z
```

Known secret pattern check against stored Phase 19 evidence:

```text
known_secret_pattern_hits=0
env_value_files=0
```

## Backup

Configuration backup completed after installing Phase 19 scripts and runbook:

```text
restic snapshot: 10c54d40
repository: /srv/storage/backups/restic/cybervpn-h-local
```

## Acceptance Status

- [x] Evidence tree exists.
- [x] First baseline evidence pack is stored.
- [x] Retention and cleanup policy is documented.

