# GitLab Restore Runbook

Host: `cybervpn-h-ops`

Production GitLab container:

```text
cybervpn-gitlab
```

Backup archive location:

```text
/srv/storage/backups/gitlab/*_gitlab_backup.tar
```

Config and secret backup source:

```text
/srv/gitlab/config
/srv/cybervpn-h/secrets
restic tag: configs
```

## Non-Production Archive Validation

Use this before any real restore. It does not touch the live GitLab container.

```bash
sudo -i
BACKUP="$(find /srv/storage/backups/gitlab -maxdepth 1 -type f -name '*_gitlab_backup.tar' -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)"
TARGET="/srv/storage/evidence/restores/gitlab-archive-validate-$(date -u +%Y%m%dT%H%M%SZ)"

install -d -m 0700 "$TARGET/extracted"
tar -xf "$BACKUP" -C "$TARGET/extracted"
test -s "$TARGET/extracted/backup_information.yml"
gzip -t "$TARGET/extracted/db/database.sql.gz"
find "$TARGET/extracted/repositories" -type f -name '*.bundle' | wc -l
```

This proves the backup archive can be unpacked, the database dump is readable, and repository bundle files exist.

## Full Restore Principles

Do not restore over production without a maintenance window.

1. Stop runners and block writes.
2. Confirm target GitLab version matches the backup version.
3. Restore `/srv/gitlab/config` and required secrets from restic.
4. Start the matching GitLab image.
5. Copy the selected backup tar into `/srv/storage/backups/gitlab`.
6. Run restore inside the container:

```bash
sudo docker exec -it cybervpn-gitlab gitlab-backup restore BACKUP=<backup-id>
sudo docker exec -it cybervpn-gitlab gitlab-ctl reconfigure
sudo docker exec -it cybervpn-gitlab gitlab-rake gitlab:check SANITIZE=true
```

`<backup-id>` is the filename prefix before `_gitlab_backup.tar`.

## Post-Restore Checks

```bash
curl -fsS http://127.0.0.1:8929/-/health
docker exec cybervpn-gitlab gitlab-rake gitlab:check SANITIZE=true
```

Verify in UI:

```text
admin login
project list
repository clone
LFS/artifacts availability if used
container registry only if registry data was included
```

Current backups skip registry during `gitlab-backup create SKIP=registry`; registry data must be backed up separately if it becomes production-critical.
