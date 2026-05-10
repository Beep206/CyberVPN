# Phase 16.1 GitLab Runner Evidence

Date: `2026-05-10`

Host: `cybervpn-h-ops`

Server: `10.10.10.34`

## Scope

Phase 16.1 deployed the first conservative GitLab Runner for CyberVPN CI.

Runner policy:

```text
runner=cybervpn-h-docker-protected
runner_type=instance_type
executor=docker
protected refs only
required tags=h-docker,protected
run_untagged=false
privileged=false
default job CPU=8
default job memory=8g
default job memory+swap=12g
cache=/srv/storage/gitlab-cache
```

Docker-in-Docker is not enabled in Phase 16.1. Manual Docker build jobs that need `dind` should use a separate protected runner later.

## Remote Files

```text
/srv/cybervpn-h/compose/gitlab-runner/compose.yml
/srv/cybervpn-h/secrets/gitlab-runner/config.toml
/srv/cybervpn-h/secrets/gitlab-runner/runner-token
/srv/cybervpn-h/configs/gitlab-runner/config.toml.example
/srv/cybervpn-h/configs/gitlab-runner/README.md
/srv/cybervpn-h/runbooks/gitlab-runner.md
/srv/storage/gitlab-cache
```

The real `config.toml` contains the runner authentication token and is stored under `/srv/cybervpn-h/secrets/gitlab-runner`.

## Image

```text
gitlab/gitlab-runner:alpine-v18.11.2
sha256:8ceefa10eb9503f812371019875e26d0e8ced955953173ee3cd9556f528eb6a4
```

This matches the installed GitLab release family:

```text
GitLab 18.11.2
GitLab Runner 18.11.2
```

## Runner State

Remote evidence:

```text
/srv/cybervpn-h/evidence/gitlab/phase17-runner-20260510T100341Z
```

Runner verification:

```text
runner_id=2
description=cybervpn-h-docker-protected
runner_type=instance_type
active=true
paused=false
run_untagged=false
locked=false
access_level=ref_protected
maximum_timeout=3600
tag_list=h-docker,protected
contacted_at=2026-05-10 15:05:36 +0500
```

Container state:

```text
name=cybervpn-gitlab-runner
image=gitlab/gitlab-runner:alpine-v18.11.2
status=Up
```

`gitlab-runner verify` result:

```text
Verifying runner... is alive
runner_name=cybervpn-h-docker-protected
```

## Smoke Pipeline

Smoke project:

```text
https://gitlab.h.cyber-vpn.net/root/phase17-runner-smoke
```

Pipeline:

```text
pipeline_id=5
pipeline_status=success
pipeline_url=https://gitlab.h.cyber-vpn.net/root/phase17-runner-smoke/-/pipelines/5
duration=26s
```

Job:

```text
job_id=25
job=phase17_runner_smoke
status=success
runner=cybervpn-h-docker-protected
runner_id=2
tag_list=h-docker
job_url=https://gitlab.h.cyber-vpn.net/root/phase17-runner-smoke/-/jobs/25
```

The smoke job checked:

```text
/cache exists
/var/run/docker.sock is not mounted into the job container
cache archive is written after the job
```

Cache files on HDD:

```text
/srv/storage/gitlab-cache/root/phase17-runner-smoke/phase17-runner-smoke-protected/cache.zip
/srv/storage/gitlab-cache/root/phase17-runner-smoke/phase17-runner-smoke-protected/metadata.json
```

## Security Notes

- Runner service container mounts `/var/run/docker.sock` so the Docker executor can create job containers.
- Job containers do not receive `/var/run/docker.sock` in runner `volumes`.
- Untagged jobs are disabled.
- Runner is restricted to protected refs.
- `CI_DEBUG_TRACE` is disabled for this runner.
- Temporary PAT used for smoke API setup was revoked at the end.
- Old Phase 15 raw evidence containing a legacy project `runners_token` was sanitized and the Phase 15 smoke project runner token was rotated.

## Permissions

```text
640 root:root /srv/cybervpn-h/compose/gitlab-runner/compose.yml
600 root:root /srv/cybervpn-h/secrets/gitlab-runner/config.toml
600 root:root /srv/cybervpn-h/secrets/gitlab-runner/runner-token
640 root:root /srv/cybervpn-h/configs/gitlab-runner/config.toml.example
640 root:root /srv/cybervpn-h/configs/gitlab-runner/README.md
640 root:root /srv/cybervpn-h/runbooks/gitlab-runner.md
750 root:root /srv/storage/gitlab-cache
```

## Backups

GitLab application backup after runner and token rotation:

```text
/srv/storage/backups/gitlab/1778408068_2026_05_10_18.11.2_gitlab_backup.tar
```

Config restic snapshot after runner:

```text
ac127b0a
```

## Local Repository Updates

Local files were aligned with the deployed runner policy:

```text
.gitlab-ci.yml
infra/gitlab-runner/README.md
infra/gitlab-runner/config.toml.example
```

The local `.gitlab-ci.yml` now uses default tag `h-docker` for normal jobs. Manual Docker package jobs still use the separate `dind` tag and will remain pending until a dedicated DIND runner is added.

Validation:

```text
python scripts/validate_gitlab_ci_contract.py
PASS: GitLab CI contract is ready for initial GitLab import
```

## Acceptance

- [x] Runner registers.
- [x] Test pipeline runs.
- [x] Runner resource limits are configured.
- [x] Cache lands on HDD.
