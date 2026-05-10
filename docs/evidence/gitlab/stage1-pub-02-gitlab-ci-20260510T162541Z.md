# STAGE1-PUB-02 GitLab And CI Alignment Evidence

Date: 2026-05-10 16:25 UTC  
Server: `10.10.10.34`  
Host: `cybervpn-h-ops`  
Scope: GitHub fallback, home GitLab availability, mirror/timer state, runner policy, CI contract and DIND isolation.

## Result

Status: **PARTIAL GO for deployment preparation.**

GitLab and the protected runner are ready enough for the next preparation step. A real CyberVPN repository pipeline still needs to run after the current GitLab CI files are committed and mirrored/imported, because `.gitlab-ci.yml`, `docs/gitlab/`, `infra/gitlab-runner/` and `scripts/validate_gitlab_ci_contract.py` are still untracked in the local worktree at review time.

## Local Repository State

Current branch and commit:

```text
branch=main
commit=dd7ac0473c6ea827dfec7bf68f398f93735b4d4a
```

Remote:

```text
origin=https://github.com/Beep206/CyberVPN.git
```

Interpretation:

- GitHub remains the external source-of-truth/fallback remote.
- Home GitLab is not the only authority for emergency recovery.
- Current untracked GitLab CI/docs files must be committed and pushed before the GitHub -> GitLab mirror can run this exact CI configuration.

## CI Contract

Command:

```bash
python scripts/validate_gitlab_ci_contract.py
```

Result:

```text
PASS: GitLab CI contract is ready for initial GitLab import
```

Whitespace check:

```bash
git diff --check -- .gitlab-ci.yml scripts/validate_gitlab_ci_contract.py docs/gitlab infra/gitlab-runner
```

Result: no output, no whitespace errors.

## GitLab Server Availability

Current server containers:

```text
cybervpn-gitlab          Up, healthy
cybervpn-gitlab-runner   Up
```

Public/Caddy smoke:

```text
https://gitlab.h.cyber-vpn.net/users/sign_in               200
https://registry.h.cyber-vpn.net/.well-known/cybervpn-edge-health 200
```

## Mirror State

GitHub -> GitLab mirror timer:

```text
cybervpn-github-to-gitlab-mirror.timer active
cybervpn-github-to-gitlab-mirror.service inactive
last observed run: 2026-05-10 16:19:12 UTC
next observed run: 2026-05-10 16:34:23 UTC
```

Prior mirror evidence:

```text
docs/evidence/gitlab/phase16-github-mirror-20260510T063910Z.md
```

Prior mirror result:

```text
github_main=dd7ac0473c6ea827dfec7bf68f398f93735b4d4a
gitlab_main=dd7ac0473c6ea827dfec7bf68f398f93735b4d4a
main_match=true
status=ok
```

## Runner State

Live runner listing:

```text
cybervpn-h-docker-protected
executor=docker
url=https://gitlab.h.cyber-vpn.net
```

Prior runner evidence:

```text
docs/evidence/gitlab/phase16-1-gitlab-runner-20260510T100341Z.md
```

Prior runner policy:

```text
runner=cybervpn-h-docker-protected
runner_type=instance_type
executor=docker
active=true
paused=false
run_untagged=false
access_level=ref_protected
tag_list=h-docker,protected
privileged=false
```

Prior smoke pipeline:

```text
pipeline_status=success
job=phase17_runner_smoke
runner=cybervpn-h-docker-protected
tag_list=h-docker
```

## `.gitlab-ci.yml` Alignment

Observed policy:

- default runner tag: `h-docker`;
- normal jobs run on the non-privileged protected Docker runner;
- Docker-in-Docker package jobs use `dind`;
- DIND jobs are `when: manual`;
- DIND jobs are `allow_failure: true`;
- no production deployment jobs are present;
- no automatic Docker push is configured;
- real production payment, Telegram, Remnawave, database or JWT secrets must not be imported into early GitLab CI variables.

Current DIND decision:

```text
DIND runner is not enabled for normal Stage 1 work.
Manual Docker package jobs remain pending until a separate protected DIND runner is intentionally added.
```

## Remaining Action Before Marking Full PASS

1. Commit `.gitlab-ci.yml`, `docs/gitlab/`, `infra/gitlab-runner/` and `scripts/validate_gitlab_ci_contract.py`.
2. Push to GitHub `main`.
3. Let the GitHub -> GitLab mirror timer sync the commit or trigger the mirror manually.
4. Run the real `gitlab:ci-contract` job in the `root/CyberVPN` GitLab project.
5. Save CI job URL/status as final `STAGE1-PUB-02` completion evidence.

## Decision

Proceed to `STAGE1-PUB-03` preparation only as repository packaging/planning work.

Do not claim GitLab CI is fully launch-proven until the real mirrored CyberVPN project runs at least the `gitlab:ci-contract` job on the protected `h-docker` runner.
