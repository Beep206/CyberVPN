# Phase 16 GitHub Mirror Evidence

Date: `2026-05-10`

Host: `cybervpn-h-ops`

Server: `10.10.10.34`

## Scope

Phase 16 configured the CyberVPN project mirror so the home GitLab instance is not the only place where project state exists.

Mirror direction:

```text
GitHub -> home GitLab
```

GitHub remains the external source of truth and emergency fallback. Do not create unique project work only in the home GitLab mirror.

## Repositories

GitHub source:

```text
https://github.com/Beep206/CyberVPN
visibility=public
default_branch=main
pushed_at=2026-05-09T15:01:26Z
main=dd7ac0473c6ea827dfec7bf68f398f93735b4d4a
```

Home GitLab mirror:

```text
https://gitlab.h.cyber-vpn.net/root/CyberVPN
project_full_path=root/CyberVPN
project_visibility=0
```

`0` means private visibility in GitLab.

## Remote Files

```text
/srv/cybervpn-h/scripts/mirror-github-to-gitlab.sh
/srv/cybervpn-h/configs/mirror/cybervpn-github-to-gitlab.env
/srv/cybervpn-h/runbooks/github-mirror.md
/etc/systemd/system/cybervpn-github-to-gitlab-mirror.service
/etc/systemd/system/cybervpn-github-to-gitlab-mirror.timer
```

Mirror credential:

```text
/srv/cybervpn-h/secrets/mirror_github_to_gitlab_ed25519
```

The private key is root-owned and is not committed to the repository.

## Systemd Timer

```text
cybervpn-github-to-gitlab-mirror.timer enabled
cybervpn-github-to-gitlab-mirror.timer active
```

Latest observed schedule:

```text
NEXT                         LEFT LAST                              PASSED UNIT                                   ACTIVATES
Sun 2026-05-10 06:55:41 UTC 12min Sun 2026-05-10 06:39:10 UTC 3min 43s ago cybervpn-github-to-gitlab-mirror.timer cybervpn-github-to-gitlab-mirror.service
```

Latest service state:

```text
cybervpn-github-to-gitlab-mirror.service inactive/dead
ExecStart=/srv/cybervpn-h/scripts/mirror-github-to-gitlab.sh
status=0/SUCCESS
```

## Mirror Verification

Successful mirror evidence:

```text
/srv/cybervpn-h/evidence/mirror/phase16-mirror-run-20260510T063819Z
/srv/cybervpn-h/evidence/mirror/phase16-mirror-run-20260510T063910Z
```

First successful run:

```text
github_ref_count=41
gitlab_ref_count=41
github_main=dd7ac0473c6ea827dfec7bf68f398f93735b4d4a
gitlab_main=dd7ac0473c6ea827dfec7bf68f398f93735b4d4a
main_match=true
finished_at_utc=2026-05-10T06:38:30+00:00
status=ok
```

Timer-triggered idempotency run:

```text
github_ref_count=41
gitlab_ref_count=41
github_main=dd7ac0473c6ea827dfec7bf68f398f93735b4d4a
gitlab_main=dd7ac0473c6ea827dfec7bf68f398f93735b4d4a
main_match=true
finished_at_utc=2026-05-10T06:39:13+00:00
status=ok
```

GitLab project bootstrap evidence:

```text
/srv/cybervpn-h/evidence/mirror/phase16-gitlab-project-20260510T063650Z.txt
project_full_path=root/CyberVPN
project_visibility=0
ssh_key_id=1
ssh_key_title=cybervpn-phase16-github-to-gitlab-mirror
```

Earlier bootstrap attempts produced incomplete evidence files and were superseded by the successful evidence above.

## Emergency Registry Path

The GitHub Actions workflow for publishing control-plane images is active:

```text
name=Control Plane Images
path=.github/workflows/control-plane-images.yml
state=active
url=https://github.com/Beep206/CyberVPN/blob/main/.github/workflows/control-plane-images.yml
```

The workflow has `packages: write`, logs into `ghcr.io`, and publishes these image names when relevant source paths change or when the workflow is manually dispatched:

```text
ghcr.io/beep206/cybervpn/backend:sha-<commit>
ghcr.io/beep206/cybervpn/task-worker:sha-<commit>
ghcr.io/beep206/cybervpn/helix-adapter:sha-<commit>
```

This keeps emergency image publishing independent from the home GitLab registry. Actual production deploys should use immutable digest refs from successful workflow runs.

## Backups

GitLab application backup after mirror:

```text
/srv/storage/backups/gitlab/1778395234_2026_05_10_18.11.2_gitlab_backup.tar
```

Config restic snapshot after Phase 16:

```text
0e54a2c2
```

Note: `gitlab-backup` was run with `SKIP=registry`. Registry data remains on HDD at `/srv/storage/gitlab-registry`; registry restore still needs a dedicated restore drill.

## Permissions

```text
600 root:root /srv/cybervpn-h/secrets/mirror_github_to_gitlab_ed25519
700 root:root /srv/cybervpn-h/scripts/mirror-github-to-gitlab.sh
640 root:root /srv/cybervpn-h/configs/mirror/cybervpn-github-to-gitlab.env
644 root:root /etc/systemd/system/cybervpn-github-to-gitlab-mirror.service
644 root:root /etc/systemd/system/cybervpn-github-to-gitlab-mirror.timer
640 root:root /srv/cybervpn-h/runbooks/github-mirror.md
```

## Acceptance

- [x] Mirror sync works.
- [x] Emergency deploy can use GitHub and the active GHCR publishing workflow without home GitLab.
- [x] Mirror credentials are stored as root-owned secrets and are not committed.
