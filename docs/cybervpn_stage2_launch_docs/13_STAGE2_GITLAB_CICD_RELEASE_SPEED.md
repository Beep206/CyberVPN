# Stage 2 GitLab CI/CD And Release Speed

**Stage:** `S2-STAGE-14`
**Status:** Passed with controlled gaps
**Date:** 2026-05-23
**Owner:** `@Sasha_Beep`

---

## 1. Purpose

Stage 2 needs a faster, repeatable delivery path than manual local rebuilds and ad-hoc production edits.

The goal is not to make every production change automatic. The goal is to make GitLab the first operational path while keeping production deployment under owner control.

Target flow:

```text
local change
-> commit to main
-> push to GitLab first
-> path-gated CI validates only relevant surfaces
-> S2 release evidence job records changed files and immutable release input
-> S2 deploy dry-run validates deploy contract without touching production
-> owner runs service-specific manual deploy job if needed
-> push same commit to GitHub mirror
```

GitHub remains a fallback remote. Customer runtime must not depend on home GitLab being online.

---

## 2. Current Decision

| Area | S2 decision |
|---|---|
| Primary repository authority | GitLab `origin/main` first |
| External fallback | GitHub `github/main` mirror |
| Production deploy style | Manual service-specific jobs first |
| Full deploy | Manual only |
| Automatic deploy | Allowed later only per service after clean S2 deploy history |
| Release identity | Immutable commit SHA or release tag, never floating `main` |
| Deploy evidence | CI artifact under `docs/evidence/releases/ci-stage2/` |
| Emergency rollback | Directly on `prod-app-1`, not dependent on GitLab |
| Key rotation | No key rotation is required by this stage; no new production secret material is introduced |

---

## 3. GitLab Runner And Remote State

Observed home server:

```text
host=cybervpn-h-ops
gitlab_container=cybervpn-gitlab Up healthy
runner_container=cybervpn-gitlab-runner Up
gitlab_runner_version=18.11.2
runner_executor=docker
```

Current remote state before this stage:

```text
GitLab main d6d8d1d9c76929b429e59c840a0828bbbef9929c
GitHub main d6d8d1d9c76929b429e59c840a0828bbbef9929c
```

This proves GitLab and GitHub were synchronized before the S2 release-speed patch.

---

## 4. CI/CD Surface

Existing GitLab pipeline already covers:

- monorepo path-gated rules;
- frontend lint/test/build;
- admin lint/test/build;
- backend lint/smoke tests;
- Telegram bot lint/smoke tests;
- task-worker lint/smoke tests;
- secret scan;
- gitleaks scan;
- npm high/critical audit;
- Python dependency audit;
- filesystem vulnerability scan;
- SBOM generation;
- manual Docker image build jobs;
- Stage 1 manual service deploy jobs;
- Stage 1 limited-publication preflight.

S2-STAGE-14 adds:

| Job | Stage | Purpose |
|---|---|---|
| `stage2:release-evidence-pack` | `package` | Writes a Stage 2 CI evidence artifact with commit, ref, changed files and immutable release input |
| `stage2:deploy:dry-run` | `deploy` | Validates deploy script/service/tag contract without SSH, rsync, Docker build or compose restart |

Both jobs write artifacts under:

```text
docs/evidence/releases/ci-stage2/
```

---

## 5. Deploy Dry-Run Contract

`scripts/deploy/stage1-gitlab-deploy.sh` now supports:

```text
STAGE1_DEPLOY_DRY_RUN=true
```

Dry-run mode:

1. validates requested services;
2. validates release tag characters;
3. writes deploy evidence;
4. exits before SSH key setup;
5. does not run SSH;
6. does not run rsync;
7. does not build images;
8. does not restart compose services;
9. does not run public smoke probes.

Local proof:

```text
STAGE1_DEPLOY_DRY_RUN=true
STAGE1_RELEASE_TAG=s2-ci-local-dry-run
service=frontend
result=ok
```

This gives us a fast deploy-contract check inside GitLab before a human runs real production deploy.

---

## 6. Normal S2 Fix Path

### Frontend / Mini App

```text
1. Commit local fix.
2. Push to GitLab first.
3. Wait for frontend path-gated lint/test/build.
4. Run stage2:release-evidence-pack.
5. Run stage2:deploy:dry-run with S2_DRY_RUN_SERVICES=frontend.
6. Owner runs stage1:deploy:frontend if the dry-run and relevant jobs pass.
7. Validate public Mini App/user path.
8. Push same commit to GitHub.
```

### Backend

```text
1. Push to GitLab first.
2. Wait for backend lint/smoke/security jobs.
3. Run stage2:deploy:dry-run with S2_DRY_RUN_SERVICES=backend.
4. Owner runs stage1:deploy:backend.
5. Verify API health and affected user flow.
6. Push GitHub mirror.
```

### Telegram Bot

```text
1. Push to GitLab first.
2. Wait for telegram-bot lint/smoke tests.
3. Run stage2:deploy:dry-run with S2_DRY_RUN_SERVICES=telegram-bot.
4. Owner runs stage1:deploy:telegram-bot.
5. Verify bot command/Mini App entrypoint.
6. Push GitHub mirror.
```

### Worker / Scheduler

```text
1. Push to GitLab first.
2. Wait for task-worker tests and affected backend checks.
3. Run stage2:deploy:dry-run with S2_DRY_RUN_SERVICES=task-worker.
4. Owner runs stage1:deploy:task-worker.
5. Verify worker lag/retry/dead-letter and related user flow.
6. Push GitHub mirror.
```

### Admin

```text
1. Push to GitLab first.
2. Wait for admin lint/test/build.
3. Run stage2:deploy:dry-run with S2_DRY_RUN_SERVICES=admin.
4. Owner runs stage1:deploy:admin.
5. Verify admin login, 2FA and affected support/admin action.
6. Push GitHub mirror.
```

---

## 7. Release Tag Policy

For S2 CI dry-runs:

```text
s2-ci-<pipeline-iid>-<commit-short-sha>
```

For real S2 release candidates:

```text
stage2-public-rc.N
```

For production rollout evidence:

```text
stage2-public-live.N
```

Deploy jobs must use immutable tag/SHA. Floating `main` is not an accepted production identity.

---

## 8. GitLab-Down Fallback

If home GitLab is offline:

1. customer frontend/API/admin/bot/VPN keep running on rented servers;
2. production rollback remains direct on `prod-app-1`;
3. GitHub mirror remains available for source recovery;
4. manual direct deploy is allowed only as an incident/hotfix path;
5. after GitLab returns, backfill evidence and push the exact resulting commit/tag to GitLab first.

This is acceptable for S2 because customer runtime is not hosted on the home server.

---

## 9. Controlled Gaps

| Gap | Impact | S2 decision |
|---|---|---|
| Real GitLab pipeline for this patch starts only after push | Local contract proves shape; server pipeline evidence follows after push | Accept for this stage; verify pipeline before S2-STAGE-15 |
| Deploy jobs still carry `stage1:*` names | Runtime compose/deploy stack is still the S1 rented production stack | Accept for S2; rename only when deployment stack itself is renamed |
| Docker build jobs are manual and advisory | No automatic registry/image digest publication yet | Accept for current cost/simplicity; digest-pinned registry can be added later |
| GitLab is home-hosted | CI visibility can go down during home outage | Accept because production customer runtime and rollback do not depend on GitLab |
| Full auto-deploy is not enabled | Slower than fully automated deploy | Intentional for S2 safety |

---

## 10. Exit Criteria

`S2-STAGE-14` is accepted when:

1. GitLab and GitHub remotes are synchronized before patching;
2. GitLab runner is up;
3. local GitLab CI contract passes;
4. S2 release-evidence and deploy-dry-run jobs exist;
5. deploy dry-run works without production access;
6. deploy jobs remain manual/service-specific;
7. immutable tag/SHA policy is documented;
8. GitHub fallback and direct rollback are documented;
9. no production secret or key rotation is required by this stage.

Result:

```text
PASS_WITH_CONTROLLED_GAPS
```

Next stage:

```text
S2-STAGE-15: Full Staging/Public-Release Rehearsal
```
