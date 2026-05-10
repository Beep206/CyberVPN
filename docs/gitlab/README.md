# CyberVPN GitLab Monorepo Readiness

Status: initial repository preparation  
Date: 2026-05-09  
Scope: GitLab import/mirroring, home GitLab runner, CI baseline and GitHub coexistence

## Goal

Prepare the CyberVPN monorepo so it can run in a home GitLab instance while GitHub remains available.

This does not make the home GitLab instance production-critical. Customer-facing CyberVPN services, payment webhooks, VPN nodes and production provisioning must continue to run outside the home server.

## Source Of Truth Recommendation

For the first GitLab phase:

1. Keep GitHub as the external fallback remote.
2. Add the home GitLab instance as a second remote.
3. Run GitLab CI on the home server for repository validation, security scans, evidence generation and non-production packaging.
4. Do not make production deploys depend only on the home GitLab server.

After the GitLab instance is stable, choose one of two models:

| Model | When to use | Rule |
|---|---|---|
| GitHub primary, GitLab CI mirror | Lowest launch risk | Push to GitHub; mirror or manually push to GitLab for CI |
| GitLab primary, GitHub push mirror | Better internal DevOps | Merge in GitLab; push mirror to GitHub as external fallback |

Because home power can be offline for several hours, the first model is safer until S1 is launched.

## Repository Remotes

Recommended local remotes:

```bash
git remote -v
git remote add gitlab ssh://git@gitlab.home.cyber-vpn.net:2222/cybervpn/cybervpn.git
git push gitlab main
git push gitlab --tags
```

If GitLab is made primary later:

```bash
git remote rename origin github
git remote rename gitlab origin
```

Keep GitHub available:

```bash
git push github main
git push github --tags
```

## GitLab Project Settings

Set these before enabling normal development:

| Setting | Recommendation |
|---|---|
| Default branch | `main` |
| Visibility | Private |
| Public pipelines | Disabled |
| Merge request approvals | At least 1 owner approval for protected branches |
| Protected `main` | Maintainers can merge; direct pushes disabled after import |
| Force push | Disabled after the initial import |
| Container Registry | Enabled, but production deploys must not depend only on home registry |
| Packages | Enabled for internal artifacts only |
| CI job token permissions | Restricted to this project/group |
| 2FA | Required for all maintainers |
| Sign-up | Disabled |

## GitLab CI Baseline

The repository now includes:

- `.gitlab-ci.yml`
- `scripts/validate_gitlab_ci_contract.py`

The baseline pipeline is intentionally conservative:

- path-based jobs for `frontend`, `admin`, `partner`, `backend`, `services/telegram-bot`, `services/task-worker`;
- no production deployment jobs;
- manual Docker image build jobs;
- no automatic `docker push`;
- security scans that can run on schedule or default branch changes;
- Docker-in-Docker jobs isolated behind the `dind` runner tag.

This keeps the home server useful without making it part of the customer critical path.

## Runner Layout

Create two runner classes:

| Runner | Purpose | Privileged | Tags |
|---|---|---:|---|
| `cybervpn-home-docker` | Normal lint/test/build jobs | No | untagged or `docker` |
| `cybervpn-home-dind` | Manual Docker build jobs | Yes | `dind` |

Recommended concurrency:

| Runner | Concurrency |
|---|---:|
| Normal Docker runner | 1-2 |
| DIND runner | 1 |

Do not let GitLab Runner consume the whole server. GitLab, Sentry and observability will share the same machine.

## Home Server Storage Mapping

Use fast NVMe for hot GitLab data and HDD for bulky/cold artifacts.

| Data | Placement |
|---|---|
| GitLab PostgreSQL | NVMe |
| GitLab Redis | NVMe |
| Git repositories / Gitaly | NVMe |
| GitLab config | NVMe |
| CI caches | HDD or NVMe depending on speed/capacity |
| GitLab artifacts | HDD |
| GitLab uploads | HDD |
| GitLab packages | HDD |
| GitLab registry | HDD |
| GitLab backups | HDD plus offline copy |
| Evidence archive | HDD plus offline copy |

Existing HDD paths that fit this plan:

```text
/srv/storage/backups
/srv/storage/archives
/srv/storage/gitlab-artifacts
/srv/storage/docker-cold
/srv/storage/tmp
```

## CI Variables

Do not import production secrets into GitLab during the first phase.

Allowed early variables:

| Variable | Scope | Notes |
|---|---|---|
| `CODECOV_TOKEN` | Optional | Only if coverage upload is needed |
| `SENTRY_DSN` placeholders | CI only | Use test DSNs or placeholders |
| `SENTRY_AUTH_TOKEN` | Later | Only after self-hosted Sentry is ready and token is protected/masked |
| `CI_REGISTRY_*` | Built-in | Use only for manual image publishing later |

Forbidden in early GitLab:

- real payment provider secrets;
- production Telegram bot token;
- production Remnawave token;
- production database credentials;
- production JWT/TOTP/OAuth secrets;
- production SSH private keys.

## Mirror Strategy

GitLab supports repository mirroring. Use it only after the GitLab instance is stable.

Recommended first step:

1. Import GitHub repo into GitLab manually.
2. Push `main` and tags to GitLab.
3. Run GitLab CI.
4. Keep GitHub as fallback.
5. Decide later whether GitLab should push mirror back to GitHub.

If enabling GitLab -> GitHub push mirror:

- use a dedicated GitHub machine user or fine-scoped token;
- protect the token in GitLab;
- mirror only after validating that GitLab branch protection is correct;
- do not mirror experimental branches unless needed.

## What GitLab Should Own By Stage

### S1

GitLab can own:

- CI validation;
- security scans;
- release evidence;
- local/manual Docker image build checks;
- non-production package artifacts.

GitLab must not be the only authority for:

- production deploy artifacts;
- production rollback;
- production secrets;
- customer-facing runtime.

### S2

GitLab can add:

- scheduled dependency audits;
- scheduled frontend bundle/env scans;
- source map upload to self-hosted Sentry;
- release candidate evidence jobs;
- status/report generation.

### S3

GitLab can add:

- partner portal CI;
- partner reporting contract tests;
- payout simulation jobs;
- settlement evidence artifacts;
- anti-fraud test pipelines.

GitLab still must not become the only production authority while it lives on the home server.

## Validation Commands

Run locally before pushing GitLab changes:

```bash
python scripts/validate_gitlab_ci_contract.py
git diff --check -- .gitlab-ci.yml scripts/validate_gitlab_ci_contract.py docs/gitlab
```

The real GitLab server-side CI linter should also be used after import.

## Official References

- GitLab CI workflow rules: https://docs.gitlab.com/ci/yaml/workflow/
- GitLab CI/CD YAML reference: https://docs.gitlab.com/ee/ci/yaml/
- GitLab CI cache: https://docs.gitlab.com/ci/caching/
- GitLab Docker build jobs: https://docs.gitlab.com/ci/docker/using_docker_build/
- GitLab repository mirroring: https://docs.gitlab.com/user/project/repository/mirror/
- GitLab push mirroring: https://docs.gitlab.com/user/project/repository/mirror/push/
