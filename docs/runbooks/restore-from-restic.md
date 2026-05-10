# Restore From Restic

Host: `cybervpn-h-ops`

Restic repository:

```text
/srv/storage/backups/restic/cybervpn-h-local
```

Root-only environment:

```text
/srv/cybervpn-h/secrets/restic.env
```

Do not print or commit values from `restic.env`. It contains the repository password and is intentionally excluded from restic snapshots.

## List Snapshots

```bash
sudo -i
set -a
. /srv/cybervpn-h/secrets/restic.env
set +a
restic snapshots --compact
```

## Restore One File To A Test Directory

Use this first under pressure. It proves the repository, password, snapshot metadata, and restore path all work without touching production paths.

```bash
sudo -i
set -a
. /srv/cybervpn-h/secrets/restic.env
set +a

SNAPSHOT="$(restic snapshots --tag configs --latest 1 --json | jq -r '.[0].short_id // .[0].id')"
TARGET="/srv/storage/evidence/restores/manual-restic-$(date -u +%Y%m%dT%H%M%SZ)"
FILE="/srv/cybervpn-h/runbooks/security-pipeline.md"

install -d -m 0700 "$TARGET"
restic restore "$SNAPSHOT" --target "$TARGET" --include "$FILE"
cmp -s "$FILE" "$TARGET$FILE"
```

Expected result:

```text
cmp exits 0
restored file exists below $TARGET/srv/...
```

## Restore A Full Config Snapshot To A Test Directory

```bash
sudo -i
set -a
. /srv/cybervpn-h/secrets/restic.env
set +a

SNAPSHOT=<snapshot-id>
TARGET="/srv/storage/evidence/restores/config-restore-$(date -u +%Y%m%dT%H%M%SZ)"
install -d -m 0700 "$TARGET"
restic restore "$SNAPSHOT" --target "$TARGET" --tag configs
```

Review files under `$TARGET` first. Do not restore directly over `/etc` or `/srv` unless the affected services are stopped and a rollback path exists.

## Repository Check

```bash
sudo /srv/cybervpn-h/scripts/restic-check.sh
```

## Current Config Scope

The config backup currently includes:

```text
/srv/cybervpn-h/compose
/srv/cybervpn-h/configs
/srv/cybervpn-h/runbooks
/srv/cybervpn-h/scripts
/srv/cybervpn-h/secrets, excluding restic.env and rclone.conf
/etc/caddy
/etc/docker/daemon.json
/etc/fail2ban
/etc/fstab
/etc/hostname
/etc/hosts
/etc/netplan
/etc/ssh
/etc/sysctl.conf
/etc/sysctl.d
/etc/systemd/system
/etc/ufw
```

Service data restore is covered by service-specific runbooks.
