# Stage 1 GitLab-First CI/CD Deployment Runbook

Date: 2026-05-21

Status: active Stage 1 runbook

## Purpose

Reduce Stage 1 delivery time by moving production packaging and service redeploys into GitLab CI/CD.

GitLab is first for CyberVPN Stage 1 delivery. GitHub remains the external fallback remote.

## Delivery Model

Default model:

```text
local change
-> commit to main
-> push to GitLab origin/main
-> GitLab path-gated CI validates changed areas
-> protected manual deploy job builds changed service on prod-app-1
-> compose recreates only the requested runtime service
-> same commit is pushed to GitHub main as fallback
```

This keeps customer runtime independent from the home server. If home GitLab is offline, existing production containers on rented servers continue to serve users.

## Why Manual Deploy Jobs First

Stage 1 is already live with beta users. For that reason, production deploy jobs are manual by default.

Recommended transition:

1. Use manual `stage1:deploy:*` jobs while the first beta cohort is small.
2. After several clean deploys, enable `STAGE1_AUTO_DEPLOY=true` for selected services only.
3. Keep `stage1:deploy:all` manual even after service-specific deploys become automatic.

## GitLab CI Jobs

Deployment jobs:

| Job | Purpose |
|---|---|
| `stage1:deploy:frontend` | Build and deploy the public frontend / Telegram Mini App web surface. |
| `stage1:deploy:admin` | Build and deploy the admin web app. |
| `stage1:deploy:backend` | Build and deploy backend API. |
| `stage1:deploy:telegram-bot` | Build and deploy Telegram bot runtime. |
| `stage1:deploy:task-worker` | Build and deploy worker and scheduler from the same image. |
| `stage1:deploy:all` | Build and deploy all CyberVPN runtime images. Manual only. |

All deploy jobs use `resource_group: stage1-production`, so GitLab will not run two production deploys at the same time.

## Deploy Runner

Production deploy jobs use a dedicated shell runner tagged `wsl-deploy`.

Reason:

- the home Docker runner remains valid for repository checks and non-production CI work;
- the home-server direct SSH path to `prod-app-1` currently reaches the SSH banner but does not complete SSH key exchange;
- the WSL shell runner reaches both `gitlab.h.cyber-vpn.net` and `prod-app-1`, so GitLab can still be the first delivery authority without moving customer runtime to the home server.

Runner contract:

- tags: `wsl-deploy`, `protected`;
- executor: shell;
- scope: production deploy jobs only;
- required local tools: `bash`, `curl`, `ssh`, `rsync`;
- no production runtime secrets are stored on the runner outside GitLab protected variables.

Keep the deploy runner separate from the normal `h-docker` runner. Do not run untagged jobs on it.

## Required Protected CI Variables

Set these in GitLab project/group CI/CD variables. Mark secret values as masked and protected.

| Variable | Required | Secret | Recommended value |
|---|---:|---:|---|
| `STAGE1_PROD_HOST` | yes | no | `45.87.41.146` |
| `STAGE1_PROD_USER` | yes | no | `deploy` |
| `STAGE1_PROD_PORT` | no | no | `22` |
| `STAGE1_PROD_SSH_PRIVATE_KEY` | yes | yes | private deploy key content |
| `STAGE1_PROD_KNOWN_HOSTS` | recommended | no | pinned `ssh-keyscan` output for prod-app-1 |
| `STAGE1_PROD_COMPOSE_DIR` | no | no | `/srv/cybervpn/compose/app` |
| `STAGE1_PROD_RELEASE_ROOT` | no | no | `/srv/cybervpn/releases` |
| `STAGE1_IMAGE_REGISTRY` | no | no | `cybervpn` |
| `STAGE1_AUTO_DEPLOY` | no | no | unset/`false` for now |

Do not store Telegram, payment, Remnawave, database, JWT, OAuth or TOTP production secrets in deploy jobs unless a specific job needs them. Current Stage 1 deploy jobs do not need those runtime secrets because they already live on prod-app-1.

Key rotation is not required for this change. Existing deploy key access can be reused if it is already limited to the `deploy` user and production server scope.

## Deploy Script

CI calls:

```bash
bash scripts/deploy/stage1-gitlab-deploy.sh "$STAGE1_DEPLOY_SERVICES"
```

The script:

- prepares SSH access from protected variables;
- syncs source to `/srv/cybervpn/releases/src-<release-tag>`;
- excludes `.private`, `.env*`, keys, caches, build output and test artifacts;
- builds only requested service images on prod-app-1;
- retags unchanged runtime images to the same release tag for compose compatibility;
- updates `CYBERVPN_IMAGE_TAG` in the production compose `.env`;
- recreates only requested compose services;
- runs local and public smoke checks;
- writes a CI artifact under `docs/evidence/releases/ci-stage1/`.

## Normal Hotfix Flow

Frontend/Mini App only:

```text
push to GitLab main
wait for frontend lint/test/build
run stage1:deploy:frontend
verify Mini App manually
push same commit to GitHub main
```

Backend only:

```text
push to GitLab main
wait for backend lint/smoke tests
run stage1:deploy:backend
verify /health and affected API flow
push same commit to GitHub main
```

Bot only:

```text
push to GitLab main
wait for telegram-bot lint/smoke tests
run stage1:deploy:telegram-bot
verify bot command/Mini App entrypoint
push same commit to GitHub main
```

Full release:

```text
push to GitLab main
wait for relevant path-gated jobs
run stage1:deploy:all manually
run stage1:limited-publication-preflight
push same commit to GitHub main
```

## Rollback

The existing rollback model remains valid:

1. Find the last known good `CYBERVPN_IMAGE_TAG` from compose `.env`, evidence, or Docker image list.
2. Set `CYBERVPN_IMAGE_TAG=<known-good-tag>` on prod-app-1.
3. Run `docker compose up -d <affected services>`.
4. Verify public smoke and affected user flow.
5. Save rollback evidence.

Do not rely on GitLab availability for emergency rollback. Rollback must remain possible directly on prod-app-1.

## Safety Rules

- Do not commit `.private/`, `.env*`, SSH keys, provider tokens or production credentials.
- Do not deploy to the VPN node from this pipeline. The VPN node remains node-only.
- Do not disable HTTP/3/QUIC while deploying frontend or Caddy changes.
- Do not make `stage1:deploy:all` automatic during Stage 1 controlled beta.
- Keep GitHub synchronized after GitLab accepts the commit.

## References

- `.gitlab-ci.yml`
- `scripts/deploy/stage1-gitlab-deploy.sh`
- `docs/evidence/gitlab/stage1-gitlab-first-ci-cd-20260511.md`
- `docs/plans/2026-05-18-cybervpn-stage1-rented-client-production-deployment-playbook.md`
