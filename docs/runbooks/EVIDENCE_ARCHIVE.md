# Evidence Archive Runbook

Host: `cybervpn-h-ops`

Server: `10.10.10.34`

Root:

```text
/srv/storage/evidence
```

## Canonical Tree

```text
/srv/storage/evidence/releases
/srv/storage/evidence/backups
/srv/storage/evidence/restores
/srv/storage/evidence/security-scans
/srv/storage/evidence/incidents
```

Legacy directories such as `baseline`, `edge-caddy`, and `security` are kept for historical Phase 0-11 evidence. New evidence should use the canonical tree above.

## What Goes Where

`releases`:

- release manifests
- image digests
- SBOM references
- rollout evidence
- rollback dry-run artifacts
- baseline packs that represent a known-good operational state

`backups`:

- backup logs
- restic summaries
- GitLab/Sentry backup indexes
- backup failure evidence

`restores`:

- restore drill logs
- restored file checksums
- restore timing and operator notes
- failed restore attempts with root cause notes

`security-scans`:

- secret scan reports
- `npm audit` reports
- `pip audit` reports
- Trivy/Grype reports
- SBOM files or references

`incidents`:

- incident timeline
- operator commands
- impacted services
- mitigation evidence
- follow-up decisions

## Baseline Pack

Create a baseline pack after major infrastructure phases:

```bash
sudo /srv/cybervpn-h/scripts/create-baseline-evidence-pack.sh
```

The script writes:

```text
/srv/storage/evidence/releases/cybervpn-h-baseline-<timestamp>
/srv/storage/evidence/security-scans/cybervpn-h-baseline-<timestamp>
```

It captures host, Docker, systemd, backup, observability, and security metadata. It does not copy secret values; secret files are represented by permissions and ownership only.

## Retention Policy

Default policy:

- `releases`: keep indefinitely.
- `incidents`: keep indefinitely.
- `restores`: keep at least `24` months; keep first successful restore evidence for each major service indefinitely.
- `backups`: keep backup evidence logs at least `12` months. Actual restic snapshot retention is controlled by restic policy, not this archive cleanup.
- `security-scans`: keep at least `12` months. Security scans tied to a release are referenced from that release pack.

No automatic destructive cleanup is enabled by default.

Dry-run retention report:

```bash
sudo /srv/cybervpn-h/scripts/evidence-retention-report.sh
```

Apply cleanup only after reviewing the dry-run output:

```bash
sudo /srv/cybervpn-h/scripts/evidence-retention-report.sh --apply
```

## Permissions

Evidence directories should be root-owned:

```text
directories: 0750 or stricter
files:       0640 or stricter where practical
```

Do not store raw API tokens, `.env` content, private keys, database passwords, or MaxMind/Cloudflare credentials in evidence.

## Verification

Baseline acceptance checks:

```bash
sudo test -d /srv/storage/evidence/releases
sudo test -d /srv/storage/evidence/backups
sudo test -d /srv/storage/evidence/restores
sudo test -d /srv/storage/evidence/security-scans
sudo test -d /srv/storage/evidence/incidents
sudo find /srv/storage/evidence/releases -maxdepth 1 -type d -name 'cybervpn-h-baseline-*' | sort | tail -1
```

