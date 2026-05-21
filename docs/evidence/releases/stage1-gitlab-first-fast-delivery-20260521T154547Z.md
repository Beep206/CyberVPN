# Stage 1 GitLab-First Fast Delivery Evidence

Date: 2026-05-21 15:45:47 UTC

## Scope

Prepare CyberVPN Stage 1 for faster production delivery through GitLab CI/CD.

GitLab remains first. GitHub remains fallback.

## Added

- GitLab production deploy jobs:
  - `stage1:deploy:backend`
  - `stage1:deploy:frontend`
  - `stage1:deploy:admin`
  - `stage1:deploy:telegram-bot`
  - `stage1:deploy:task-worker`
  - `stage1:deploy:all`
- SSH/rsync deploy script:
  - `scripts/deploy/stage1-gitlab-deploy.sh`
- Operator runbook:
  - `docs/runbooks/STAGE1_GITLAB_CICD_DEPLOYMENT.md`

## Deployment Design

Default behavior:

- deploy jobs are path-gated;
- deploy jobs are manual on `main`;
- selected jobs can become automatic later with `STAGE1_AUTO_DEPLOY=true`;
- `stage1:deploy:all` remains manual;
- `resource_group: stage1-production` prevents concurrent production deploys;
- production runtime secrets stay on prod-app-1 and are not copied into GitLab CI;
- deploy source sync excludes `.private`, `.env*`, SSH keys, caches and build outputs;
- unchanged runtime images are retagged to the same release tag for compose compatibility.

## Required GitLab Variables

Protected project/group variables:

- `STAGE1_PROD_HOST`
- `STAGE1_PROD_USER`
- `STAGE1_PROD_PORT`
- `STAGE1_PROD_SSH_PRIVATE_KEY`
- `STAGE1_PROD_KNOWN_HOSTS`

Key rotation is not required for this change.

## Validation

Commands:

```bash
bash -n scripts/deploy/stage1-gitlab-deploy.sh
python scripts/validate_gitlab_ci_contract.py
git diff --check
```

Results:

```text
PASS: deploy script syntax
PASS: GitLab CI contract is ready for initial GitLab import
PASS: whitespace check
```

Security checks:

```text
tracked private/env/key file check: no production private material found
high-confidence secret pattern scan on working tree: no matches
gitleaks changed-file scan: no leaks found
```

Full current-tree gitleaks with the existing baseline still reports historical/test-fixture findings when run outside the Docker `/scan` path. Changed-file gitleaks is clean for this delivery change.

## Next Runtime Use

For the next Mini App/frontend hotfix:

```text
push to GitLab main
wait for frontend jobs
run stage1:deploy:frontend
verify Mini App
push same commit to GitHub main
```
